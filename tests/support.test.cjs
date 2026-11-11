/* Support-request flow regressions using isolated fetch and DOM substitutes. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../app/static/support.js"), "utf8");
const SID = "5c4d3e2f-4444-4d55-8e66-2f77a88b99cc";
const RID = "11111111-2222-4333-8444-555555555555";
const PAYLOAD = { reason: "human_requested", content: "VPN profile missing", consent_to_share: true };
const STATUS_URL = `GET /v1/escalations/${SID}`;

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

const EXPIRES = "2026-11-08T00:30:00Z";
const registered = (id = SID) =>
  reply(201, {
    submission_id: id,
    operation: "escalation",
    registration_state: "unused",
    expires_at: EXPIRES,
  });
const saved = (status = 201) =>
  reply(status, {
    request_id: RID,
    submission_id: SID,
    state: "queued",
    created_at: "2026-11-08T00:00:00Z",
    acknowledgement: "Your request has been saved.",
  });
const statusSaved = () =>
  reply(200, {
    submission_id: SID,
    operation: "escalation",
    registration_state: "completed",
    saved: true,
    request_id: RID,
    state: "queued",
    version: 1,
    created_at: "2026-11-08T00:00:00Z",
    expires_at: null,
  });
const statusUnsaved = (registration_state = "unused") =>
  reply(200, {
    submission_id: SID,
    operation: "escalation",
    registration_state,
    saved: false,
    request_id: null,
    state: null,
    version: null,
    created_at: null,
    expires_at: EXPIRES,
  });

/* routes: "METHOD /path" -> response, or a list consumed one at a time. */
function load(routes, elements = null) {
  const calls = [];
  const events = [];
  const context = {
    TypeError,
    document: {
      querySelector: (selector) => (elements ? (elements[selector] ?? null) : null),
      dispatchEvent: (event) => events.push(event),
    },
    CustomEvent: class {
      constructor(type, init = {}) {
        this.type = type;
        this.detail = init.detail;
      }
    },
    window: { location: { assign: (url) => (context.assigned = url) } },
    fetch: async (url, options = {}) => {
      const method = options.method ?? "GET";
      const key = `${method} ${url}`;
      calls.push({ key, options });
      if (key === "GET /v1/session") return reply(200, { csrf_token: "tok" });
      const route = routes[key];
      const response = Array.isArray(route) ? route.shift() : route;
      if (response instanceof Error) throw response;
      if (!response) throw new Error(`unexpected request ${key}`);
      return response;
    },
  };
  vm.runInNewContext(source, context, { filename: "support.js" });
  return { ctx: context, calls, events, keys: () => calls.map((c) => c.key) };
}
const count = (page, key) => page.keys().filter((k) => k === key).length;
const fresh = () => ({ payload: { ...PAYLOAD }, submissionId: null, unresolved: false });

/* ---------- logic-level tests ---------- */

test("registers an ID at confirm, then saves with the CSRF token", async () => {
  const page = load({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [saved()],
  });
  const result = await page.ctx.sendSupport(fresh());
  assert.equal(result.outcome, "saved");
  assert.equal(result.requestId, RID);
  const submit = page.calls.find((c) => c.key === "POST /v1/escalations");
  assert.equal(submit.options.headers["X-CSRF-Token"], "tok");
  const body = JSON.parse(submit.options.body);
  assert.equal(body.submission_id, SID);
  assert.equal(body.consent_to_share, true);
});

test("a lost acknowledgement is resolved by status without a new ID or request", async () => {
  const page = load({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [error(503, "SAVE_OUTCOME_UNCERTAIN", "uncertain")],
    [STATUS_URL]: [statusSaved()],
  });
  const result = await page.ctx.sendSupport(fresh());
  assert.equal(result.outcome, "saved");
  assert.equal(count(page, "POST /v1/escalations"), 1);
  assert.equal(count(page, "POST /v1/escalations/submission-ids"), 1);
});

test("server commits but the response is dropped: status finds it, no duplicate", async () => {
  for (const drop of [new TypeError("network"), reply(502, undefined)]) {
    const page = load({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [drop],
      [STATUS_URL]: [statusSaved()],
    });
    const state = fresh();
    const result = await page.ctx.sendSupport(state);
    assert.equal(result.outcome, "saved");
    assert.equal(result.requestId, RID);
    assert.equal(state.submissionId, null);
    assert.equal(count(page, "POST /v1/escalations"), 1);
    assert.equal(count(page, "POST /v1/escalations/submission-ids"), 1);
  }
});

test("a dropped response with an unreadable status stays locked on the same ID", async () => {
  const state = fresh();
  const page = load({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [new TypeError("network")],
    [STATUS_URL]: [reply(502, undefined), new TypeError("down"), statusSaved()],
  });
  const first = await page.ctx.sendSupport(state);
  assert.equal(first.outcome, "unresolved");
  assert.equal(state.unresolved, true);
  assert.equal(state.submissionId, SID);
  const second = await page.ctx.sendSupport(state);
  assert.equal(second.outcome, "unresolved");
  assert.equal(state.submissionId, SID);
  const third = await page.ctx.sendSupport(state);
  assert.equal(third.outcome, "saved");
  assert.equal(count(page, "POST /v1/escalations"), 1); // never re-posted while unresolved
  assert.equal(count(page, "POST /v1/escalations/submission-ids"), 1);
});

test("a definitively unsaved status allows an explicit same-ID retry without duplicates", async () => {
  const state = fresh();
  const page = load({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [reply(502, undefined), saved()],
    [STATUS_URL]: [statusUnsaved()],
  });
  const first = await page.ctx.sendSupport(state);
  assert.equal(first.outcome, "retry");
  assert.equal(state.unresolved, false);
  assert.equal(state.submissionId, SID);
  const second = await page.ctx.sendSupport(state);
  assert.equal(second.outcome, "saved");
  assert.equal(count(page, "POST /v1/escalations/submission-ids"), 1);
  const bodies = page.calls
    .filter((c) => c.key === "POST /v1/escalations")
    .map((c) => JSON.parse(c.options.body).submission_id);
  assert.deepEqual(bodies, [SID, SID]);
});

test("malformed success bodies preserve the ID and enter status recovery", async () => {
  const malformed = [
    reply(201, undefined),
    reply(201, {}),
    reply(201, { request_id: "not-a-uuid", submission_id: SID, state: "queued", created_at: "x" }),
    reply(200, { request_id: RID, submission_id: "other-id", state: "queued", created_at: "x" }),
  ];
  for (const bad of malformed) {
    const state = fresh();
    const page = load({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [bad],
      [STATUS_URL]: [reply(200, undefined)],
    });
    const result = await page.ctx.sendSupport(state);
    assert.equal(result.outcome, "unresolved");
    assert.equal(state.submissionId, SID);
    assert.equal(state.unresolved, true);
    assert.equal(count(page, STATUS_URL), 1);
  }
});

const goodStatus = () => ({
  submission_id: SID,
  operation: "escalation",
  registration_state: "completed",
  saved: true,
  request_id: RID,
  state: "queued",
  version: 1,
  created_at: "2026-11-08T00:00:00Z",
  expires_at: null,
});
const goodUnsaved = () => ({
  ...goodStatus(),
  registration_state: "unused",
  saved: false,
  request_id: null,
  state: null,
  version: null,
  created_at: null,
  expires_at: EXPIRES,
});

test("status responses are validated for values and consistency, not just HTTP success", async () => {
  const invalid = [
    { saved: true },
    { ...goodStatus(), request_id: "nope" },
    { ...goodStatus(), state: "not_a_request_state" },
    { ...goodStatus(), state: null },
    { ...goodStatus(), version: 0 },
    { ...goodStatus(), version: "1" },
    { ...goodStatus(), created_at: "not_a_timestamp" },
    { ...goodStatus(), created_at: null },
    { ...goodStatus(), expires_at: EXPIRES },
    { ...goodStatus(), registration_state: "unused" },
    { ...goodStatus(), registration_state: "weird" },
    { ...goodStatus(), saved: "yes" },
    { ...goodStatus(), operation: "reply" },
    { ...goodStatus(), submission_id: "other" },
    { ...goodUnsaved(), registration_state: "completed" },
    { ...goodUnsaved(), request_id: RID },
    { ...goodUnsaved(), state: "queued" },
    { ...goodUnsaved(), version: 1 },
    { ...goodUnsaved(), created_at: "2026-11-08T00:00:00Z" },
    { ...goodUnsaved(), expires_at: null },
    { ...goodUnsaved(), expires_at: "not_a_timestamp" },
  ];
  for (const bad of invalid) {
    const state = fresh();
    const page = load({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [error(503, "SAVE_OUTCOME_UNCERTAIN", "x")],
      [STATUS_URL]: [reply(200, bad)],
    });
    const result = await page.ctx.sendSupport(state);
    assert.equal(result.outcome, "unresolved", JSON.stringify(bad));
    assert.equal(state.submissionId, SID);
    assert.equal(state.unresolved, true);
  }
  for (const good of [goodStatus(), goodUnsaved(), { ...goodUnsaved(), registration_state: "expired" }]) {
    const page = load({});
    const ok = page.ctx.validStatusResponse(
      { status: 200, ok: true, data: JSON.parse(JSON.stringify(good)) },
      SID,
    );
    assert.equal(ok, true, JSON.stringify(good));
  }
});

test("save responses with invalid values are not trusted and use status recovery", async () => {
  const base = () => ({
    request_id: RID,
    submission_id: SID,
    state: "queued",
    created_at: "2026-11-08T00:00:00Z",
    acknowledgement: "Your request has been saved.",
  });
  const invalid = [
    { ...base(), state: "not_a_request_state" },
    { ...base(), state: undefined },
    { ...base(), state: 5 },
    { ...base(), created_at: "not_a_timestamp" },
    { ...base(), created_at: "2026-02-30T00:00:00Z" },
    { ...base(), created_at: "2026-11-08 00:00:00" },
    { ...base(), created_at: "2026-11-08T00:00:00+01:00" },
    { ...base(), created_at: "" },
    { ...base(), created_at: 1762560000 },
    { ...base(), request_id: "r1" },
    { ...base(), submission_id: "other" },
    { ...base(), version: 0 },
    { ...base(), version: "2" },
    { ...base(), acknowledgement: 7 },
  ];
  for (const bad of invalid) {
    const state = fresh();
    const page = load({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [reply(201, bad)],
      [STATUS_URL]: [reply(503, undefined)],
    });
    const result = await page.ctx.sendSupport(state);
    assert.equal(result.outcome, "unresolved", JSON.stringify(bad));
    assert.equal(state.submissionId, SID);
    assert.equal(state.unresolved, true);
    assert.equal(count(page, STATUS_URL), 1);
  }
  for (const good of [
    base(),
    { ...base(), version: 1 },
    { ...base(), created_at: "2026-11-08T00:00:00.123456Z" },
  ]) {
    const page = load({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [reply(201, good)],
    });
    assert.equal((await page.ctx.sendSupport(fresh())).outcome, "saved");
  }
});

test("an invalid save response resolves through a valid status check", async () => {
  const state = fresh();
  const page = load({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [
      reply(201, {
        request_id: RID,
        submission_id: SID,
        state: "not_a_request_state",
        created_at: "not_a_timestamp",
      }),
    ],
    [STATUS_URL]: [statusSaved()],
  });
  const result = await page.ctx.sendSupport(state);
  assert.equal(result.outcome, "saved");
  assert.equal(result.requestId, RID);
  assert.equal(count(page, "POST /v1/escalations"), 1);
});

test("registration responses with invalid values send nothing", async () => {
  const good = () => ({
    submission_id: SID,
    operation: "escalation",
    registration_state: "unused",
    expires_at: EXPIRES,
  });
  const invalid = [
    { ...good(), submission_id: "nope" },
    { ...good(), operation: "reply" },
    { ...good(), registration_state: "completed" },
    { ...good(), expires_at: "not_a_timestamp" },
    { ...good(), expires_at: undefined },
  ];
  for (const bad of invalid) {
    const page = load({ "POST /v1/escalations/submission-ids": [reply(201, bad)] });
    assert.equal((await page.ctx.sendSupport(fresh())).outcome, "retry", JSON.stringify(bad));
    assert.equal(page.keys().includes("POST /v1/escalations"), false);
  }
});

test("the timestamp check accepts ISO UTC and rejects anything else", () => {
  const { ctx } = load({});
  for (const ok of ["2026-11-08T00:00:00Z", "2026-02-28T23:59:59Z", "2026-11-08T00:00:00.5Z"])
    assert.equal(ctx.validTimestamp(ok), true, ok);
  for (const bad of [
    "", "x", null, undefined, 5, "2026-11-08", "2026-11-08T00:00:00", "2026-13-01T00:00:00Z",
    "2026-02-30T00:00:00Z", "2026-11-08T24:00:00Z", "2026-11-08T00:60:00Z", "2026-11-08T00:00:00+00:00",
  ])
    assert.equal(ctx.validTimestamp(bad), false, String(bad));
});

test("a malformed registration response sends nothing", async () => {
  const page = load({
    "POST /v1/escalations/submission-ids": [reply(201, {}), reply(201, undefined)],
  });
  assert.equal((await page.ctx.sendSupport(fresh())).outcome, "retry");
  assert.equal((await page.ctx.sendSupport(fresh())).outcome, "retry");
  assert.equal(page.keys().includes("POST /v1/escalations"), false);
});

test("an expired ID is dropped and the customer must confirm again", async () => {
  const state = fresh();
  const page = load({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [
      error(410, "SUBMISSION_ID_EXPIRED", "This form timed out before it was sent."),
    ],
  });
  const result = await page.ctx.sendSupport(state);
  assert.equal(result.outcome, "edit");
  assert.equal(state.submissionId, null);
  assert.match(result.message, /timed out/);
});

test("rate limits show readable waits and keep the ID", async () => {
  const cases = [
    ["90", /about 2 minutes/],
    ["3574", /about 60 minutes/],
    ["7300", /about 3 hours/],
    ["30", /about 30 seconds/],
  ];
  for (const [seconds, pattern] of cases) {
    const state = fresh();
    const page = load({
      "POST /v1/escalations/submission-ids": [registered()],
      "POST /v1/escalations": [
        error(429, "RATE_LIMITED", "Please wait before sending another support request.", {
          "Retry-After": seconds,
        }),
      ],
    });
    const result = await page.ctx.sendSupport(state);
    assert.equal(result.outcome, "retry");
    assert.match(result.message, pattern);
    assert.doesNotMatch(result.message, /3574/);
    assert.equal(state.submissionId, SID);
  }
});

test("a full pending-ID cap on registration is reported without sending", async () => {
  const page = load({
    "POST /v1/escalations/submission-ids": [
      error(429, "RATE_LIMITED", "You have too many pending submissions.", { "Retry-After": "600" }),
    ],
  });
  const result = await page.ctx.sendSupport(fresh());
  assert.equal(result.outcome, "retry");
  assert.equal(page.keys().includes("POST /v1/escalations"), false);
});

test("an ended session redirects to sign-in", async () => {
  const page = load({});
  page.ctx.fetch = async () => error(401, "UNAUTHENTICATED", "Your session has ended.");
  assert.equal((await page.ctx.sendSupport(fresh())).outcome, "redirect");
});

test("a completed-payload conflict shows the original saved request and drops the ID", async () => {
  const state = fresh();
  const page = load({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [error(409, "CONFLICT", "Already saved with different content.")],
    [STATUS_URL]: [statusSaved()],
  });
  const result = await page.ctx.sendSupport(state);
  assert.equal(result.outcome, "conflict");
  assert.equal(result.requestId, RID);
  assert.equal(state.submissionId, null);
  assert.equal(count(page, "POST /v1/escalations"), 1);
});

test("a conflict whose status cannot be read stays locked on the original ID", async () => {
  const state = fresh();
  const page = load({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [error(409, "CONFLICT", "x")],
    [STATUS_URL]: [reply(502, undefined)],
  });
  const result = await page.ctx.sendSupport(state);
  assert.equal(result.outcome, "unresolved");
  assert.equal(state.submissionId, SID);
});

test("payload building trims, normalizes and enforces the server limits", () => {
  const { ctx } = load({});
  const ok = ctx.buildSupportPayload("  Café  ", "  ");
  assert.deepEqual(JSON.parse(JSON.stringify(ok.payload)), {
    reason: "human_requested",
    content: "Café",
  });
  assert.ok(ctx.buildSupportPayload("   ", "").error);
  assert.ok(ctx.buildSupportPayload("x".repeat(1001), "").error);
  assert.equal(ctx.buildSupportPayload("x".repeat(1000), "").error, undefined);
  assert.ok(ctx.buildSupportPayload("ok", "n".repeat(2001)).error);
  assert.ok(ctx.buildSupportPayload("bad\u0000text", "").error);
  assert.equal(ctx.buildSupportPayload("line one\nline two\ttab", "").error, undefined);
  assert.equal(ctx.buildSupportPayload("\u{1F600}".repeat(1000), "").error, undefined);
});

/* ---------- page-level tests: real event handlers on fake elements ---------- */

function fakePage(routes) {
  const el = (extra = {}) => {
    const handlers = {};
    return {
      hidden: false,
      disabled: false,
      textContent: "",
      className: "",
      value: "",
      checked: false,
      handlers,
      addEventListener(type, fn) {
        (handlers[type] ??= []).push(fn);
      },
      ...extra,
    };
  };
  const names = [
    "#support", "#support-form", "#support-review", "#support-done", "#support-status",
    "#support-content", "#support-note", "#support-consent", "#support-edit", "#support-send",
    "#support-another", "#support-saved", "#support-preview-content", "#support-preview-note",
  ];
  const elements = Object.fromEntries(names.map((n) => [n, el()]));
  elements["#support-send"].textContent = "Send to support";
  elements["#support-review"].hidden = true;
  elements["#support-done"].hidden = true;
  const page = load(routes, elements);
  const fire = async (name, type, event = { preventDefault() {} }) => {
    await Promise.all((elements[name].handlers[type] ?? []).map((fn) => fn(event)));
  };
  const view = () =>
    ["form", "review", "done"].find((s) => !elements[`#support-${s}`].hidden);
  return { ...page, elements, fire, view };
}

async function toReview(p, text = "VPN profile missing") {
  p.elements["#support-content"].value = text;
  await p.fire("#support-form", "submit");
  assert.equal(p.view(), "review");
}

test("review step: consent is required and the Edit button clears it", async () => {
  const p = fakePage({});
  await toReview(p);
  await p.fire("#support-send", "click");
  assert.match(p.elements["#support-status"].textContent, /agree to share/);
  assert.equal(p.calls.length, 0);
  p.elements["#support-consent"].checked = true;
  await p.fire("#support-edit", "click");
  assert.equal(p.view(), "form");
  assert.equal(p.elements["#support-consent"].checked, false);
  await toReview(p, "VPN profile missing, revised");
  assert.equal(p.elements["#support-consent"].checked, false); // fresh consent required
});

test("Try again is reset to Send to support when returning through Edit and review", async () => {
  const p = fakePage({
    "POST /v1/escalations/submission-ids": [reply(503, { error: { code: "SERVICE_BUSY", message: "Busy." } })],
  });
  await toReview(p);
  p.elements["#support-consent"].checked = true;
  await p.fire("#support-send", "click");
  assert.equal(p.elements["#support-send"].textContent, "Try again");
  await p.fire("#support-edit", "click");
  assert.equal(p.elements["#support-send"].textContent, "Send to support");
  await toReview(p);
  assert.equal(p.elements["#support-send"].textContent, "Send to support");
});

test("unresolved save locks Edit and Review, then Check status resolves it", async () => {
  const p = fakePage({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [new TypeError("network")],
    [STATUS_URL]: [reply(502, undefined), reply(502, undefined), statusSaved()],
  });
  await toReview(p);
  p.elements["#support-consent"].checked = true;
  await p.fire("#support-send", "click");
  assert.equal(p.elements["#support-edit"].disabled, true);
  assert.equal(p.elements["#support-send"].disabled, false);
  assert.equal(p.elements["#support-send"].textContent, "Check status");
  await p.fire("#support-edit", "click");
  assert.equal(p.view(), "review"); // still locked
  await p.fire("#support-form", "submit");
  assert.equal(p.view(), "review");
  await p.fire("#support-send", "click"); // still unreadable
  assert.equal(p.elements["#support-edit"].disabled, true);
  await p.fire("#support-send", "click"); // saved
  assert.equal(p.view(), "done");
  assert.equal(p.elements["#support-edit"].disabled, false); // state resolved
  assert.equal(count(p, "POST /v1/escalations"), 1);
  assert.equal(count(p, "POST /v1/escalations/submission-ids"), 1);
  assert.match(p.elements["#support-saved"].textContent, /11111111/);
});

test("after a definite not-saved status Edit unlocks and Send retries the same ID", async () => {
  const p = fakePage({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [reply(502, undefined), saved()],
    [STATUS_URL]: [statusUnsaved()],
  });
  await toReview(p);
  p.elements["#support-consent"].checked = true;
  await p.fire("#support-send", "click");
  assert.equal(p.elements["#support-send"].textContent, "Try again");
  assert.equal(p.elements["#support-edit"].disabled, false);
  await p.fire("#support-send", "click");
  assert.equal(p.view(), "done");
  assert.equal(count(p, "POST /v1/escalations/submission-ids"), 1);
});

test("malformed success never shows saved and keeps Edit locked", async () => {
  const p = fakePage({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [reply(201, {})],
    [STATUS_URL]: [reply(200, undefined)],
  });
  await toReview(p);
  p.elements["#support-consent"].checked = true;
  await p.fire("#support-send", "click");
  assert.equal(p.view(), "review");
  assert.equal(p.elements["#support-edit"].disabled, true);
  assert.doesNotMatch(p.elements["#support-status"].textContent, /has been saved/);
});

test("completed-payload conflict offers a deliberate new request that resets everything", async () => {
  const NEW_SID = "6d5e4f30-5555-4e66-9f77-3a88b99ccdd0";
  const p = fakePage({
    "POST /v1/escalations/submission-ids": [registered(), registered(NEW_SID)],
    "POST /v1/escalations": [
      error(409, "CONFLICT", "Already saved with different content."),
      reply(201, {
        request_id: "22222222-3333-4444-8555-666666666666",
        submission_id: NEW_SID,
        state: "queued",
        created_at: "2026-11-08T00:01:00Z",
      }),
    ],
    [STATUS_URL]: [statusSaved()],
  });
  await toReview(p, "first text");
  p.elements["#support-consent"].checked = true;
  await p.fire("#support-send", "click");
  assert.equal(p.view(), "done");
  assert.match(p.elements["#support-saved"].textContent, /original request was already saved/);
  assert.match(p.elements["#support-saved"].textContent, /11111111/);
  assert.equal(p.elements["#support-another"].textContent, "Start new request");
  assert.equal(p.elements["#support-consent"].checked, false);
  assert.equal(p.elements["#support-edit"].disabled, false);
  assert.equal(p.elements["#support-send"].disabled, false);
  assert.equal(p.elements["#support-send"].textContent, "Send to support");
  await p.fire("#support-another", "click");
  assert.equal(p.view(), "form");
  await toReview(p, "changed text");
  p.elements["#support-consent"].checked = true;
  await p.fire("#support-send", "click");
  assert.equal(p.view(), "done");
  const ids = p.calls
    .filter((c) => c.key === "POST /v1/escalations")
    .map((c) => JSON.parse(c.options.body).submission_id);
  assert.deepEqual(ids, [SID, NEW_SID]);
});

test("an invalid save acknowledgement never shows saved and keeps Edit locked", async () => {
  const p = fakePage({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [
      reply(201, {
        request_id: RID,
        submission_id: SID,
        state: "not_a_request_state",
        created_at: "not_a_timestamp",
      }),
    ],
    [STATUS_URL]: [reply(502, undefined), statusSaved()],
  });
  await toReview(p);
  p.elements["#support-consent"].checked = true;
  await p.fire("#support-send", "click");
  assert.equal(p.view(), "review");
  assert.equal(p.elements["#support-edit"].disabled, true);
  assert.equal(p.elements["#support-send"].textContent, "Check status");
  assert.doesNotMatch(p.elements["#support-status"].textContent, /has been saved/);
  await p.fire("#support-edit", "click");
  assert.equal(p.view(), "review"); // still locked
  await p.fire("#support-send", "click"); // status now readable and saved
  assert.equal(p.view(), "done");
  assert.equal(count(p, "POST /v1/escalations"), 1);
  assert.equal(count(p, "POST /v1/escalations/submission-ids"), 1);
});

test("a confirmed save announces itself so the request list can refresh", async () => {
  const p = fakePage({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [saved()],
  });
  await toReview(p);
  p.elements["#support-consent"].checked = true;
  await p.fire("#support-send", "click");
  assert.equal(p.view(), "done");
  assert.equal(p.events.length, 1);
  assert.equal(p.events[0].type, "deskguide:support-saved");
  assert.equal(p.events[0].detail.requestId, RID);
});

test("nothing is announced while a save is unconfirmed or failed", async () => {
  const p = fakePage({
    "POST /v1/escalations/submission-ids": [registered()],
    "POST /v1/escalations": [error(503, "DEPENDENCY_UNAVAILABLE", "Try later.")],
  });
  await toReview(p);
  p.elements["#support-consent"].checked = true;
  await p.fire("#support-send", "click");
  assert.equal(p.events.length, 0);
});
