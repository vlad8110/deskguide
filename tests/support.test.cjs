/* Support-request flow regressions using isolated fetch and DOM substitutes. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../app/static/support.js"), "utf8");
const SID = "5c4d3e2f-4444-4d55-8e66-2f77a88b99cc";
const PAYLOAD = { reason: "human_requested", content: "VPN profile missing", consent_to_share: true };

function reply(status, value, headers = {}) {
  return {
    status,
    ok: status >= 200 && status < 300,
    headers: { get: (name) => headers[name] ?? null },
    json: async () => {
      if (value === undefined) throw new SyntaxError("Unexpected token '<'");
      return value;
    },
  };
}
const error = (status, code, message, headers) =>
  reply(status, { error: { code, message } }, headers);

/* routes: "METHOD /path" -> response, or a list consumed one at a time. */
function load(routes) {
  const calls = [];
  const context = {
    TypeError,
    document: { querySelector: () => null },
    window: { location: { assign: () => {} } },
    fetch: async (url, options = {}) => {
      const method = options.method ?? "GET";
      const key = `${method} ${url}`;
      calls.push({ key, options });
      const route = routes[key];
      const response = Array.isArray(route) ? route.shift() : route;
      if (response instanceof Error) throw response;
      if (!response) throw new Error(`unexpected request ${key}`);
      return response;
    },
  };
  vm.runInNewContext(source, context, { filename: "support.js" });
  return { ctx: context, calls, keys: () => calls.map((c) => c.key) };
}

function sessionRoutes(routes) {
  // The session endpoint answers every token request.
  const all = { ...routes };
  all["GET /v1/session"] = Array.from({ length: 10 }, () => reply(200, { csrf_token: "tok" }));
  return all;
}
const registered = () => reply(201, { submission_id: SID, registration_state: "unused" });
const saved = () =>
  reply(201, { request_id: "r1", acknowledgement: "Your request has been saved." });
const fresh = () => ({ payload: { ...PAYLOAD }, submissionId: null, uncertain: false });

test("registers an ID at confirm, then saves with the CSRF token", async () => {
  const page = load(
    sessionRoutes({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [saved()],
    }),
  );
  const result = await page.ctx.sendSupport(fresh());
  assert.equal(result.outcome, "saved");
  assert.equal(result.requestId, "r1");
  const submit = page.calls.find((c) => c.key === "POST /v1/escalations");
  assert.equal(submit.options.headers["X-CSRF-Token"], "tok");
  const body = JSON.parse(submit.options.body);
  assert.equal(body.submission_id, SID);
  assert.equal(body.consent_to_share, true);
});

test("a lost acknowledgement is resolved by status without a new ID or request", async () => {
  const page = load(
    sessionRoutes({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [
        error(503, "SAVE_OUTCOME_UNCERTAIN", "We could not confirm whether this was saved."),
      ],
      [`GET /v1/escalations/${SID}`]: [reply(200, { saved: true, request_id: "r1" })],
    }),
  );
  const result = await page.ctx.sendSupport(fresh());
  assert.equal(result.outcome, "saved");
  assert.equal(page.keys().filter((k) => k === "POST /v1/escalations").length, 1);
  assert.equal(page.keys().filter((k) => k.endsWith("submission-ids")).length, 1);
});

test("an uncertain save that did not commit keeps the same ID for a retry", async () => {
  const state = fresh();
  const page = load(
    sessionRoutes({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [error(503, "SAVE_OUTCOME_UNCERTAIN", "x"), saved()],
      [`GET /v1/escalations/${SID}`]: [
        reply(200, { saved: false, registration_state: "unused" }),
      ],
    }),
  );
  const first = await page.ctx.sendSupport(state);
  assert.equal(first.outcome, "retry");
  assert.equal(state.submissionId, SID);
  const second = await page.ctx.sendSupport(state);
  assert.equal(second.outcome, "saved");
  assert.equal(page.keys().filter((k) => k.endsWith("submission-ids")).length, 1);
});

test("editing stays locked while a save is uncertain and the status check fails", async () => {
  const state = fresh();
  const page = load(
    sessionRoutes({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [error(503, "SAVE_OUTCOME_UNCERTAIN", "x")],
      [`GET /v1/escalations/${SID}`]: [error(503, "DEPENDENCY_UNAVAILABLE", "down")],
    }),
  );
  const result = await page.ctx.sendSupport(state);
  assert.equal(result.outcome, "retry");
  assert.equal(state.uncertain, true);
  assert.equal(state.submissionId, SID);
});

test("an expired ID is dropped and the customer must confirm again", async () => {
  const state = fresh();
  const page = load(
    sessionRoutes({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [
        error(410, "SUBMISSION_ID_EXPIRED", "This form timed out before it was sent."),
      ],
    }),
  );
  const result = await page.ctx.sendSupport(state);
  assert.equal(result.outcome, "edit");
  assert.equal(state.submissionId, null);
  assert.match(result.message, /timed out/);
});

test("rate limits show the wait time and keep the ID", async () => {
  const state = fresh();
  const page = load(
    sessionRoutes({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [
        error(429, "RATE_LIMITED", "Please wait before sending another support request.", {
          "Retry-After": "90",
        }),
      ],
    }),
  );
  const result = await page.ctx.sendSupport(state);
  assert.equal(result.outcome, "retry");
  assert.match(result.message, /about 90 seconds/);
  assert.equal(state.submissionId, SID);
});

test("a full pending-ID cap on registration is reported without sending", async () => {
  const page = load(
    sessionRoutes({
      "POST /v1/escalations/submission-ids": [
        error(429, "RATE_LIMITED", "You have too many pending submissions.", {
          "Retry-After": "600",
        }),
      ],
    }),
  );
  const result = await page.ctx.sendSupport(fresh());
  assert.equal(result.outcome, "retry");
  assert.equal(page.keys().includes("POST /v1/escalations"), false);
});

test("an ended session redirects to sign-in", async () => {
  const page = load({
    "GET /v1/session": [error(401, "UNAUTHENTICATED", "Your session has ended.")],
  });
  const result = await page.ctx.sendSupport(fresh());
  assert.equal(result.outcome, "redirect");
});

test("HTML proxy errors and network failures use safe messages and keep the ID", async () => {
  const state = fresh();
  const page = load(
    sessionRoutes({
      "POST /v1/escalations/submission-ids": [registered(), registered()],
      "POST /v1/escalations": [reply(502, undefined), new TypeError("raw detail")],
    }),
  );
  const proxy = await page.ctx.sendSupport(state);
  assert.equal(proxy.message, "Service temporarily unavailable. Try again.");
  const offline = await page.ctx.sendSupport(state);
  assert.equal(offline.message, "Connection unavailable. Your text is still here; try again.");
  assert.equal(state.submissionId, SID);
});

test("a conflict never overwrites the completed submission", async () => {
  const page = load(
    sessionRoutes({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [error(409, "CONFLICT", "Already sent with different text.")],
    }),
  );
  assert.equal((await page.ctx.sendSupport(fresh())).outcome, "stop");
});

test("payload building trims, normalizes and enforces the server limits", () => {
  const { ctx } = load({});
  const ok = ctx.buildSupportPayload("  Cafe\u0301  ", "  ");
  assert.deepEqual(JSON.parse(JSON.stringify(ok.payload)), {
    reason: "human_requested",
    content: "Caf\u00e9",
  });
  assert.ok(ctx.buildSupportPayload("   ", "").error);
  assert.ok(ctx.buildSupportPayload("x".repeat(1001), "").error);
  assert.equal(ctx.buildSupportPayload("x".repeat(1000), "").error, undefined);
  assert.ok(ctx.buildSupportPayload("ok", "n".repeat(2001)).error);
  assert.ok(ctx.buildSupportPayload("bad\u0000text", "").error);
  assert.equal(ctx.buildSupportPayload("line one\nline two\ttab", "").error, undefined);
  assert.equal(ctx.buildSupportPayload("\u{1F600}".repeat(1000), "").error, undefined);
});
