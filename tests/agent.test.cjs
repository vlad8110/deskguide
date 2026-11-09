/* Agent queue and request-detail regressions using isolated fetch and DOM substitutes. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../app/static/agent.js"), "utf8");
const uid = (n) => `aaaaaaaa-0000-4000-8000-${String(n).padStart(12, "0")}`;
const QUEUE = "GET /v1/agent/escalations?limit=25";

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
const error = (status, code, message) => reply(status, { error: { code, message } });
const item = (n, state = "queued", version = 1) => ({
  request_id: uid(n),
  state,
  content: `Request text ${n}`,
  reason: "human_requested",
  created_at: "2026-11-08T00:00:00Z",
  assigned_agent_id: state === "queued" ? null : "AGT-1",
  customer_ref: "CUST-1",
  account_status: null,
  version,
});
const detail = (n, state, version, messages = []) => ({
  ...item(n, state, version),
  note: null,
  messages,
});
const queueOf = (...items) => reply(200, { items, next_cursor: null });
const detailKey = (n) => `GET /v1/agent/escalations/${uid(n)}`;
const claimKey = (n) => `POST /v1/agent/escalations/${uid(n)}/claim`;
const moveKey = (n) => `POST /v1/agent/escalations/${uid(n)}/transition`;

/* routes: "METHOD /path" -> response, or a list consumed one at a time. */
function load(routes, elements = null) {
  const calls = [];
  const context = {
    TypeError,
    document: {
      querySelector: (selector) => (elements ? (elements[selector] ?? null) : null),
      createElement: (tag) => fakeElement(tag),
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
      return typeof response === "function" ? response() : response;
    },
  };
  vm.runInNewContext(source, context, { filename: "agent.js" });
  return { ctx: context, calls, keys: () => calls.map((c) => c.key) };
}
const count = (page, key) => page.keys().filter((k) => k === key).length;
const api = (page) => (method, url, body) => page.ctx.agentApi(method, url, body);

/* ---------- logic-level tests ---------- */

test("queue loading validates the response and passes the filter and cursor", async () => {
  const page = load({
    [`${QUEUE}&state=queued&cursor=abc%2F1`]: [
      reply(200, { items: [item(1)], next_cursor: "next" }),
    ],
  });
  const result = await page.ctx.agentLoadQueue(api(page), { state: "queued", cursor: "abc/1" });
  assert.equal(result.outcome, "ok");
  assert.equal(result.nextCursor, "next");
  assert.equal(result.items.length, 1);
});

test("malformed queue responses are errors, never an empty queue", async () => {
  for (const bad of [
    reply(200, undefined),
    reply(200, {}),
    reply(200, { items: "x", next_cursor: null }),
    reply(200, { items: [{ request_id: "nope" }], next_cursor: null }),
    reply(200, { items: [{ ...item(1), state: "weird" }], next_cursor: null }),
    reply(200, { items: [], next_cursor: 5 }),
  ]) {
    const page = load({ [QUEUE]: [bad] });
    assert.equal((await page.ctx.agentLoadQueue(api(page))).outcome, "error");
  }
});

test("an ended session redirects and a non-agent is told they have no access", async () => {
  const gone = load({ [QUEUE]: [error(401, "UNAUTHENTICATED", "x")] });
  assert.equal((await gone.ctx.agentLoadQueue(api(gone))).outcome, "redirect");
  const forbidden = load({ [QUEUE]: [error(403, "FORBIDDEN", "x")] });
  assert.equal((await forbidden.ctx.agentLoadQueue(api(forbidden))).outcome, "forbidden");
});

test("a claim succeeds only with a valid assigned summary", async () => {
  const page = load({ [claimKey(1)]: [reply(200, item(1, "assigned", 2))] });
  const result = await page.ctx.agentClaim(api(page), uid(1));
  assert.equal(result.outcome, "claimed");
  const call = page.calls.find((c) => c.key === claimKey(1));
  assert.equal(call.options.headers["X-CSRF-Token"], "tok");
  assert.equal(call.options.body, undefined);
});

test("competing claims: 409 in either code is a lost race, 404 is gone", async () => {
  for (const code of ["ALREADY_CLAIMED", "CONFLICT"]) {
    const page = load({ [claimKey(1)]: [error(409, code, "x")] });
    assert.equal((await page.ctx.agentClaim(api(page), uid(1))).outcome, "lost");
  }
  const page = load({ [claimKey(1)]: [error(404, "NOT_FOUND", "x")] });
  assert.equal((await page.ctx.agentClaim(api(page), uid(1))).outcome, "gone");
});

test("a claim whose result is unknown requires a reload", async () => {
  for (const bad of [
    new TypeError("network"),
    reply(502, undefined),
    error(503, "DEPENDENCY_UNAVAILABLE", "x"),
    reply(200, undefined),
    reply(200, item(1, "queued", 2)),
    reply(200, item(2, "assigned", 2)),
  ]) {
    const page = load({ [claimKey(1)]: [bad] });
    assert.equal((await page.ctx.agentClaim(api(page), uid(1))).outcome, "unknown");
  }
});

test("a claim that never left the browser is a plain error", async () => {
  const page = load({});
  page.ctx.fetch = async () => {
    throw new TypeError("offline");
  };
  assert.equal((await page.ctx.agentClaim(api(page), uid(1))).outcome, "error");
});

test("a transition sends the loaded version and only the field it needs", async () => {
  const cases = [
    ["in_review", undefined, {}],
    ["waiting_for_customer", "Which network?", { message_to_customer: "Which network?" }],
    ["resolved", "Fixed.", { resolution_note: "Fixed." }],
    ["queued", "Needs a specialist.", { release_reason: "Needs a specialist." }],
  ];
  for (const [target, text, extra] of cases) {
    const page = load({ [moveKey(1)]: [reply(200, item(1, target, 5))] });
    const result = await page.ctx.agentTransition(api(page), detail(1, "in_review", 4), target, text);
    assert.equal(result.outcome, "done");
    const body = JSON.parse(page.calls.find((c) => c.key === moveKey(1)).options.body);
    assert.deepEqual(body, { to_state: target, expected_version: 4, ...extra });
  }
});

test("a stale or conflicting transition is a definite change, 404 is gone, 400 is invalid", async () => {
  for (const code of ["STALE_VERSION", "CONFLICT"]) {
    const page = load({ [moveKey(1)]: [error(409, code, "x")] });
    assert.equal(
      (await page.ctx.agentTransition(api(page), detail(1, "in_review", 4), "resolved", "n")).outcome,
      "changed",
    );
  }
  const gone = load({ [moveKey(1)]: [error(404, "NOT_FOUND", "x")] });
  assert.equal(
    (await gone.ctx.agentTransition(api(gone), detail(1, "in_review", 4), "in_review")).outcome,
    "gone",
  );
  const bad = load({ [moveKey(1)]: [error(400, "VALIDATION_FAILED", "Too long.")] });
  const result = await bad.ctx.agentTransition(api(bad), detail(1, "in_review", 4), "resolved", "n");
  assert.equal(result.outcome, "invalid");
  assert.equal(result.message, "Too long.");
});

test("an unknown transition result is never treated as saved or failed", async () => {
  for (const bad of [
    new TypeError("network"),
    reply(502, undefined),
    error(503, "DEPENDENCY_UNAVAILABLE", "Reload the request."),
    reply(200, undefined),
    reply(200, item(1, "in_review", 4)), // version did not advance
    reply(200, item(1, "assigned", 5)), // wrong state
  ]) {
    const page = load({ [moveKey(1)]: [bad] });
    const result = await page.ctx.agentTransition(api(page), detail(1, "assigned", 4), "in_review");
    assert.equal(result.outcome, "unknown");
  }
});

test("reply text is trimmed, normalized and bounded like the server", () => {
  const { ctx } = load({});
  assert.equal(ctx.agentText("  Café  ", 2000, "note").text, "Café");
  assert.ok(ctx.agentText("   ", 2000, "note").error);
  assert.ok(ctx.agentText("x".repeat(2001), 2000, "note").error);
  assert.equal(ctx.agentText("x".repeat(500), 500, "reason").error, undefined);
  assert.ok(ctx.agentText("x".repeat(501), 500, "reason").error);
  assert.ok(ctx.agentText("bad\u0000", 2000, "note").error);
});

test("controls follow the state and resolved requests allow none", () => {
  const { ctx } = load({});
  const names = (state) => Array.from(ctx.agentActionsFor(state));
  assert.deepEqual(names("assigned"), ["start", "release"]);
  assert.deepEqual(names("in_review"), ["ask", "resolve", "release"]);
  assert.deepEqual(names("waiting_for_customer"), ["resume", "release"]);
  assert.deepEqual(names("resolved"), []);
  assert.deepEqual(names("queued"), []);
});

/* ---------- page-level tests: real handlers on fake elements ---------- */

function fakeElement(tag = "div") {
  return {
    tag,
    hidden: false,
    disabled: false,
    textContent: "",
    className: "",
    value: "",
    children: [],
    handlers: {},
    attrs: {},
    addEventListener(type, fn) {
      (this.handlers[type] ??= []).push(fn);
    },
    append(...nodes) {
      this.children.push(...nodes);
    },
    replaceChildren(...nodes) {
      this.children = nodes;
    },
    setAttribute(key, value) {
      this.attrs[key] = value;
    },
  };
}
const walk = (node, out = []) => {
  out.push(node);
  node.children.forEach((c) => walk(c, out));
  return out;
};

const IDS = [
  "agent", "agent-queue-view", "agent-detail-view", "agent-list", "agent-empty", "agent-more",
  "agent-filter", "agent-refresh", "agent-retry", "agent-status", "agent-back", "agent-reload",
  "agent-start-box", "agent-ask-box", "agent-resume-box", "agent-resolve-box", "agent-release-box",
  "agent-start", "agent-ask-send", "agent-resume", "agent-resolve-send", "agent-release-send",
  "agent-ask", "agent-resolution", "agent-release-reason", "agent-detail-title",
  "agent-detail-state", "agent-content", "agent-note", "agent-messages", "agent-no-messages",
  "agent-resolved-box",
];

async function settle() {
  await new Promise((resolve) => setImmediate(resolve));
}

async function openPage(routes) {
  const elements = Object.fromEntries(IDS.map((id) => [`#${id}`, fakeElement()]));
  for (const id of ["agent-detail-view", "agent-empty", "agent-more", "agent-retry", "agent-reload"])
    elements[`#${id}`].hidden = true;
  const page = load(routes, elements);
  const el = (id) => elements[`#agent-${id}`];
  const click = async (node) => {
    await Promise.all((node.handlers.click ?? []).map((fn) => fn({})));
    await settle();
  };
  const rowButton = (label) =>
    walk(el("list")).find((n) => n.tag === "button" && n.textContent === label);
  const view = () => (el("queue-view").hidden ? "detail" : "queue");
  await settle();
  return { ...page, el, click, rowButton, view };
}

function states(p) {
  const shown = (name) => !p.el(`${name}-box`).hidden;
  return ["start", "ask", "resume", "resolve", "release"].filter(shown);
}

test("the queue lists requests with a Claim button for unassigned ones", async () => {
  const p = await openPage({ [QUEUE]: [queueOf(item(1), item(2, "assigned", 3))] });
  assert.equal(p.el("list").children.length, 2);
  assert.ok(p.rowButton("Claim"));
  assert.ok(p.rowButton("Open"));
  assert.equal(p.el("empty").hidden, true);
});

test("an empty queue shows a clear empty state", async () => {
  const p = await openPage({ [QUEUE]: [queueOf()] });
  assert.equal(p.el("list").children.length, 0);
  assert.equal(p.el("empty").hidden, false);
});

test("a queue error is shown with a way to try again", async () => {
  const p = await openPage({
    [QUEUE]: [error(503, "DEPENDENCY_UNAVAILABLE", "Support is unavailable."), queueOf(item(1))],
  });
  assert.match(p.el("status").textContent, /unavailable/);
  assert.equal(p.el("retry").hidden, false);
  await p.click(p.el("retry"));
  assert.equal(p.el("list").children.length, 1);
});

test("an expired session sends the agent to sign in", async () => {
  const p = await openPage({ [QUEUE]: [error(401, "UNAUTHENTICATED", "x")] });
  assert.equal(p.ctx.assigned, "/");
  assert.match(p.el("status").textContent, /session has ended/);
});

test("claiming opens the request detail with the right controls", async () => {
  const p = await openPage({
    [QUEUE]: [queueOf(item(1))],
    [claimKey(1)]: [reply(200, item(1, "assigned", 2))],
    [detailKey(1)]: [reply(200, detail(1, "assigned", 2))],
  });
  await p.click(p.rowButton("Claim"));
  assert.equal(p.view(), "detail");
  assert.deepEqual(states(p), ["start", "release"]);
  assert.match(p.el("detail-state").textContent, /version 2/);
  assert.match(p.el("status").textContent, /You claimed/);
});

test("losing a claim race refreshes the queue and never opens the request", async () => {
  const p = await openPage({
    [QUEUE]: [queueOf(item(1)), queueOf(item(2))],
    [claimKey(1)]: [error(409, "ALREADY_CLAIMED", "Taken.")],
  });
  await p.click(p.rowButton("Claim"));
  assert.equal(p.view(), "queue");
  assert.match(p.el("status").textContent, /already taken/);
  assert.equal(count(p, QUEUE), 2);
  assert.equal(p.el("list").children.length, 1);
  assert.equal(p.keys().includes(detailKey(1)), false);
});

test("an unknown claim result reloads the queue before anything else", async () => {
  const p = await openPage({
    [QUEUE]: [queueOf(item(1)), queueOf(item(1, "assigned", 2))],
    [claimKey(1)]: [new TypeError("network")],
  });
  await p.click(p.rowButton("Claim"));
  assert.equal(count(p, QUEUE), 2);
  assert.equal(count(p, claimKey(1)), 1); // never retried automatically
  assert.ok(p.rowButton("Open"));
});

async function openRequest(state, version, messages, extra = {}) {
  const p = await openPage({
    [QUEUE]: Array.from({ length: 4 }, () => queueOf(item(1, state, version))),
    [detailKey(1)]: [reply(200, detail(1, state, version, messages))],
    ...extra,
  });
  await p.click(p.rowButton("Open"));
  assert.equal(p.view(), "detail");
  return p;
}

test("each state offers only the permitted controls and resolved offers none", async () => {
  const expected = {
    assigned: ["start", "release"],
    in_review: ["ask", "resolve", "release"],
    waiting_for_customer: ["resume", "release"],
    resolved: [],
  };
  for (const [state, controls] of Object.entries(expected)) {
    const p = await openRequest(state, 3, []);
    assert.deepEqual(states(p), controls, state);
    assert.equal(p.el("resolved-box").hidden, state !== "resolved");
  }
});

test("customer messages, agent questions and internal notes are kept apart", async () => {
  const messages = [
    { message_id: "m1", kind: "customer_reply", content: "It is the Campus network.", version: 3 },
    { message_id: "m2", kind: "message_to_customer", content: "Which network?", version: 2 },
    { message_id: "m3", kind: "resolution_note", content: "Reinstalled the profile.", version: 5 },
  ];
  const p = await openRequest("resolved", 5, messages);
  const rows = p.el("messages").children;
  assert.equal(rows.length, 3);
  assert.match(rows[0].className, /customer_reply/);
  assert.match(rows[1].className, /message_to_customer/);
  assert.match(rows[2].className, /internal/);
  const labels = rows.map((r) => r.children[0].textContent);
  assert.match(labels[2], /never shown to the customer/);
  assert.doesNotMatch(labels[0] + labels[1], /resolution note/i);
});

test("resolving requires a note, sends the version and reloads the saved request", async () => {
  const p = await openRequest("in_review", 4, [], {
    [moveKey(1)]: [reply(200, item(1, "resolved", 5))],
  });
  await p.click(p.el("resolve-send"));
  assert.match(p.el("status").textContent, /Write the resolution note/);
  assert.equal(count(p, moveKey(1)), 0);
});

test("a saved resolution reloads the request and removes every control", async () => {
  const note = { message_id: "m9", kind: "resolution_note", content: "Done.", version: 5 };
  const p = await openRequest("in_review", 4, [], {
    [moveKey(1)]: [reply(200, item(1, "resolved", 5))],
  });
  // Route the reload to the resolved detail.
  const original = p.ctx.fetch;
  p.ctx.fetch = async (url, options = {}) =>
    (options.method ?? "GET") === "GET" && url === `/v1/agent/escalations/${uid(1)}`
      ? reply(200, detail(1, "resolved", 5, [note]))
      : original(url, options);
  p.el("resolution").value = "Done.";
  await p.click(p.el("resolve-send"));
  const body = JSON.parse(p.calls.find((c) => c.key === moveKey(1)).options.body);
  assert.deepEqual(body, { to_state: "resolved", expected_version: 4, resolution_note: "Done." });
  assert.deepEqual(states(p), []);
  assert.equal(p.el("resolved-box").hidden, false);
  assert.equal(p.el("resolution").value, "");
  assert.equal(p.el("messages").children.length, 1);
});

test("a stale update reloads the request, keeps the text and does not overwrite", async () => {
  const p = await openRequest("in_review", 4, [], {
    [moveKey(1)]: [error(409, "STALE_VERSION", "Stale.")],
  });
  const original = p.ctx.fetch;
  p.ctx.fetch = async (url, options = {}) =>
    (options.method ?? "GET") === "GET" && url === `/v1/agent/escalations/${uid(1)}`
      ? reply(200, detail(1, "waiting_for_customer", 6))
      : original(url, options);
  p.el("resolution").value = "Fixed.";
  await p.click(p.el("resolve-send"));
  assert.match(p.el("detail-state").textContent, /version 6/);
  assert.deepEqual(states(p), ["resume", "release"]);
  assert.match(p.el("status").textContent, /changed/);
  assert.equal(p.el("resolution").value, "Fixed.");
  assert.equal(count(p, moveKey(1)), 1);
});

test("an unknown update locks the controls until the reload succeeds", async () => {
  const p = await openRequest("in_review", 4, [], {
    [moveKey(1)]: [new TypeError("network")],
  });
  const original = p.ctx.fetch;
  let reloads = 0;
  p.ctx.fetch = async (url, options = {}) => {
    if ((options.method ?? "GET") === "GET" && url === `/v1/agent/escalations/${uid(1)}`) {
      reloads += 1;
      if (reloads < 3) return reply(502, undefined);
      return reply(200, detail(1, "in_review", 4));
    }
    return original(url, options);
  };
  p.el("ask").value = "Which network?";
  await p.click(p.el("ask-send"));
  assert.equal(p.el("reload").hidden, false);
  assert.equal(p.el("ask-send").disabled, true);
  assert.equal(p.el("resolve-send").disabled, true);
  assert.equal(p.el("release-send").disabled, true);
  await p.click(p.el("ask-send")); // locked: nothing is sent
  assert.equal(count(p, moveKey(1)), 1);
  await p.click(p.el("reload")); // still unreadable
  assert.equal(p.el("ask-send").disabled, true);
  await p.click(p.el("reload")); // readable at last
  assert.equal(p.el("reload").hidden, true);
  assert.equal(p.el("ask-send").disabled, false);
  assert.equal(p.el("ask").value, "Which network?"); // not applied, text kept
  assert.equal(count(p, moveKey(1)), 1); // never replayed automatically
});

const mine = (n, state, version, messages) => reply(200, detail(n, state, version, messages));
function reloadTo(p, n, response) {
  const original = p.ctx.fetch;
  p.ctx.fetch = async (url, options = {}) =>
    (options.method ?? "GET") === "GET" && url === `/v1/agent/escalations/${uid(n)}`
      ? typeof response === "function"
        ? response()
        : response
      : original(url, options);
}

test("an unknown update that committed is recognized only with matching saved text", async () => {
  const p = await openRequest("in_review", 4, [], { [moveKey(1)]: [reply(502, undefined)] });
  reloadTo(
    p,
    1,
    mine(1, "waiting_for_customer", 5, [
      { message_id: "m1", kind: "message_to_customer", content: "Which network?", version: 5 },
    ]),
  );
  p.el("ask").value = "Which network?";
  await p.click(p.el("ask-send"));
  assert.match(p.el("status").textContent, /was saved/);
  assert.equal(p.el("ask").value, "");
  assert.deepEqual(states(p), ["resume", "release"]);
  assert.equal(count(p, moveKey(1)), 1);
});

test("an unknown update with a matching state and newer version alone is not claimed as saved", async () => {
  // Another tab moved the request to the same target with different text.
  const p = await openRequest("in_review", 4, [], { [moveKey(1)]: [new TypeError("network")] });
  reloadTo(
    p,
    1,
    mine(1, "waiting_for_customer", 5, [
      { message_id: "m1", kind: "message_to_customer", content: "Someone else's text", version: 5 },
    ]),
  );
  p.el("ask").value = "Which network?";
  await p.click(p.el("ask-send"));
  assert.doesNotMatch(p.el("status").textContent, /was saved/);
  assert.match(p.el("status").textContent, /could not tell/);
  assert.equal(p.el("ask").value, "Which network?");
  assert.equal(count(p, moveKey(1)), 1);
});

test("an unknown update on an unchanged request is reported as not saved", async () => {
  const p = await openRequest("in_review", 4, [], { [moveKey(1)]: [reply(502, undefined)] });
  reloadTo(p, 1, mine(1, "in_review", 4, []));
  p.el("resolution").value = "Fixed.";
  await p.click(p.el("resolve-send"));
  assert.match(p.el("status").textContent, /not saved/);
  assert.equal(p.el("resolution").value, "Fixed.");
});

test("two tabs: a definite 409 at the same target state is a conflict, never saved", async () => {
  const p = await openRequest("in_review", 4, [], {
    [moveKey(1)]: [error(409, "STALE_VERSION", "This request changed.")],
  });
  // The other tab already resolved it with its own note.
  reloadTo(
    p,
    1,
    mine(1, "resolved", 5, [
      { message_id: "m1", kind: "resolution_note", content: "Fixed.", version: 5 },
    ]),
  );
  p.el("resolution").value = "Fixed.";
  await p.click(p.el("resolve-send"));
  assert.doesNotMatch(p.el("status").textContent, /was saved|Saved/);
  assert.match(p.el("status").textContent, /changed/);
  assert.equal(p.el("resolution").value, "Fixed."); // preserved for that request
  assert.match(p.el("detail-state").textContent, /Resolved · version 5/);
  assert.deepEqual(states(p), []);
  assert.equal(count(p, moveKey(1)), 1);
});

test("unsent text never carries to a different request", async () => {
  const p = await openPage({
    [QUEUE]: Array.from({ length: 4 }, () =>
      queueOf(item(1, "in_review", 4), item(2, "in_review", 7)),
    ),
    [detailKey(1)]: [mine(1, "in_review", 4, []), mine(1, "in_review", 4, [])],
    [detailKey(2)]: [mine(2, "in_review", 7, [])],
  });
  const opens = () => walk(p.el("list")).filter((n) => n.tag === "button" && n.textContent === "Open");
  await p.click(opens()[0]);
  p.el("ask").value = "Question for customer one";
  p.el("resolution").value = "Note for customer one";
  p.el("release-reason").value = "Reason for one";
  await p.click(p.el("back"));
  await p.click(opens()[1]);
  assert.match(p.el("detail-title").textContent, /aaaaaaaa/);
  assert.equal(p.el("ask").value, "");
  assert.equal(p.el("resolution").value, "");
  assert.equal(p.el("release-reason").value, "");
  assert.match(p.el("detail-state").textContent, /version 7/);
});

test("text is kept when the same request is reloaded after a failed update", async () => {
  const p = await openRequest("in_review", 4, [], {
    [moveKey(1)]: [error(400, "VALIDATION_FAILED", "Too long.")],
  });
  p.el("ask").value = "Which network?";
  await p.click(p.el("ask-send"));
  assert.equal(p.el("ask").value, "Which network?");
  await p.click(p.el("back"));
  await p.click(p.rowButton("Open")); // same request again
  assert.equal(p.el("ask").value, "Which network?");
});

test("changing the filter drops the old cursor and disables Load More until the new list arrives", async () => {
  let release;
  const slow = new Promise((resolve) => (release = resolve));
  const p = await openPage({
    [QUEUE]: [reply(200, { items: [item(1)], next_cursor: "old-cursor" })],
    [`${QUEUE}&state=assigned`]: [() => slow],
  });
  assert.equal(p.el("more").hidden, false);
  p.el("filter").value = "assigned";
  await Promise.all((p.el("filter").handlers.change ?? []).map((fn) => fn({})));
  await settle();
  assert.equal(p.el("more").hidden, true);
  assert.equal(p.el("list").children.length, 0);
  assert.equal(p.el("empty").hidden, true); // loading, not "no requests"
  await p.click(p.el("more")); // an immediate Load More does nothing
  assert.equal(p.keys().some((k) => k.includes("cursor")), false);
  release(reply(200, { items: [item(2, "assigned", 3)], next_cursor: null }));
  await settle();
  await settle();
  assert.equal(p.el("list").children.length, 1);
  assert.equal(p.el("more").hidden, true);
  assert.equal(p.keys().some((k) => k.includes("cursor")), false);
});

test("Load More appends with the cursor of the current filter only", async () => {
  const p = await openPage({
    [QUEUE]: [reply(200, { items: [item(1)], next_cursor: "c1" })],
    [`${QUEUE}&cursor=c1`]: [reply(200, { items: [item(2)], next_cursor: null })],
  });
  await p.click(p.el("more"));
  assert.equal(p.el("list").children.length, 2);
  assert.equal(p.el("more").hidden, true);
  assert.equal(count(p, `${QUEUE}&cursor=c1`), 1);
});

test("releasing returns to a refreshed queue and clears the form", async () => {
  const p = await openRequest("in_review", 4, [], {
    [moveKey(1)]: [reply(200, { ...item(1, "queued", 5), assigned_agent_id: null })],
  });
  p.el("release-reason").value = "Needs a specialist.";
  await p.click(p.el("release-send"));
  const body = JSON.parse(p.calls.find((c) => c.key === moveKey(1)).options.body);
  assert.deepEqual(body, { to_state: "queued", expected_version: 4, release_reason: "Needs a specialist." });
  assert.equal(p.view(), "queue");
  assert.match(p.el("status").textContent, /Released/);
  assert.equal(p.el("release-reason").value, "");
  assert.equal(count(p, QUEUE), 2);
});

test("losing ownership returns to the queue instead of showing stale controls", async () => {
  const p = await openRequest("assigned", 2, [], {
    [moveKey(1)]: [error(404, "NOT_FOUND", "x")],
  });
  await p.click(p.el("start"));
  assert.equal(p.view(), "queue");
  assert.match(p.el("status").textContent, /no longer assigned to you/);
  assert.equal(count(p, QUEUE), 2);
});
