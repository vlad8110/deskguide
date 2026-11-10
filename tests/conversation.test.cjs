/* Customer conversation (list, detail, reply) regressions using isolated fetch and DOM substitutes. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const read = (name) => fs.readFileSync(path.join(__dirname, "../app/static", name), "utf8");
const conversationSource = read("conversation.js");

const uid = (n) => `aaaaaaaa-0000-4000-8000-${String(n).padStart(12, "0")}`;
const TIME = "2026-11-08T00:00:00Z";

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
const error = (status, code, message = "Server message.") =>
  reply(status, { error: { code, message } });

const summary = (n, state = "queued", version = 1) => ({
  request_id: uid(n),
  state,
  version,
  created_at: TIME,
});
const message = (n, kind, content, version = null) => ({
  message_id: uid(900 + n),
  kind,
  content,
  created_at: TIME,
  version,
});
const detail = (n, state, version, messages = [], over = {}) => ({
  request_id: uid(n),
  state,
  version,
  content: "My VPN profile is missing.",
  note: null,
  reason: "human_requested",
  created_at: TIME,
  messages,
  correlation_id: uid(1),
  contract_version: "0.3.3",
  ...over,
});
const registration = (n, version = 4, over = {}) => ({
  submission_id: uid(500 + n),
  operation: "reply",
  registration_state: "unused",
  expires_at: "2026-11-08T02:00:00Z",
  request_id: uid(n),
  state: "waiting_for_customer",
  version,
  ...over,
});
const savedReply = (n, version = 5, over = {}) => ({
  reply_id: uid(700 + n),
  request_id: uid(n),
  state: "in_review",
  version,
  ...over,
});
const status = (n, saved, over = {}) => ({
  submission_id: uid(500 + n),
  operation: "reply",
  registration_state: saved ? "completed" : "unused",
  saved,
  request_id: uid(n),
  state: saved ? "in_review" : "waiting_for_customer",
  version: saved ? 5 : 4,
  created_at: saved ? TIME : null,
  expires_at: saved ? null : "2026-11-08T02:00:00Z",
  ...over,
});

const LIST = "GET /v1/escalations/requests";
const DETAIL = (n) => `GET /v1/escalations/requests/${uid(n)}`;
const REG = (n) => `POST /v1/escalations/${uid(n)}/reply-ids`;
const SEND = (n) => `POST /v1/escalations/${uid(n)}/replies`;
const STATUS = (n) => `GET /v1/escalations/${uid(500 + n)}`;

/* routes: "METHOD /path" -> response, or a list consumed one at a time. */
function load(routes, elements = null) {
  const calls = [];
  const listeners = {};
  const context = {
    TypeError,
    document: {
      querySelector: (selector) => (elements ? (elements[selector] ?? null) : null),
      createElement: (tag) => fakeElement(tag),
      addEventListener: (type, fn) => (listeners[type] ??= []).push(fn),
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
  vm.createContext(context);
  vm.runInContext(conversationSource, context, { filename: "conversation.js" });
  return { ctx: context, calls, listeners, keys: () => calls.map((c) => c.key) };
}
const count = (page, key) => page.keys().filter((k) => k === key).length;
const api = (page) => (method, url, body) => page.ctx.convApi(method, url, body);
const newState = (n, over = {}) => ({
  requestId: uid(n),
  message: "Windows 11, client 4.2.",
  expectedVersion: 4,
  submissionId: null,
  unresolved: false,
  ...over,
});
const plain = (value) => JSON.parse(JSON.stringify(value));
const body = (page, key) => JSON.parse(page.calls.find((c) => c.key === key).options.body);

/* ---------- list and detail ---------- */

test("the list keeps the server's order and only the fields the screen shows", async () => {
  const items = [summary(2, "waiting_for_customer", 4), summary(1, "resolved", 6)];
  items[0].content = "must not be carried along";
  const page = load({ [LIST]: [reply(200, { items })] });
  const result = await page.ctx.convLoadList(api(page));
  assert.equal(result.outcome, "ok");
  assert.deepEqual(
    result.items.map((i) => i.request_id),
    [uid(2), uid(1)],
  );
  assert.equal(result.items[0].content, undefined);
});

test("an empty list is a valid answer, but malformed lists are errors", async () => {
  const empty = load({ [LIST]: [reply(200, { items: [] })] });
  assert.deepEqual(plain(await empty.ctx.convLoadList(api(empty))), { outcome: "ok", items: [] });
  for (const bad of [
    reply(200, undefined),
    reply(200, {}),
    reply(200, { items: "x" }),
    reply(200, { items: [{ ...summary(1), request_id: "nope" }] }),
    reply(200, { items: [{ ...summary(1), state: "weird" }] }),
    reply(200, { items: [{ ...summary(1), version: 0 }] }),
    reply(200, { items: [{ ...summary(1), created_at: "2026-02-31T00:00:00Z" }] }),
    reply(200, { items: [summary(1), summary(1)] }),
  ]) {
    const page = load({ [LIST]: [bad] });
    assert.equal((await page.ctx.convLoadList(api(page))).outcome, "error");
  }
});

test("list failures: 401 redirects, 503 shows the server's message", async () => {
  const gone = load({ [LIST]: [error(401, "UNAUTHENTICATED")] });
  assert.equal((await gone.ctx.convLoadList(api(gone))).outcome, "redirect");
  const down = load({ [LIST]: [error(503, "DEPENDENCY_UNAVAILABLE", "Support is down.")] });
  const result = await down.ctx.convLoadList(api(down));
  assert.deepEqual(plain(result), { outcome: "error", message: "Support is down." });
  const dropped = load({ [LIST]: [new TypeError("fetch failed")] });
  assert.match((await dropped.ctx.convLoadList(api(dropped))).message, /Connection unavailable/);
});

test("detail keeps only visible fields and rejects anything the customer must not see", async () => {
  const messages = [
    message(1, "message_to_customer", "Which OS?", 3),
    message(2, "customer_reply", "Windows 11", 4),
  ];
  const page = load({ [DETAIL(1)]: [reply(200, detail(1, "in_review", 4, messages))] });
  const result = await page.ctx.convLoadDetail(api(page), uid(1));
  assert.equal(result.outcome, "ok");
  assert.equal(result.detail.messages.length, 2);
  assert.equal(result.detail.reason, undefined);
  assert.equal(result.detail.correlation_id, undefined);

  for (const bad of [
    detail(2, "in_review", 4),
    detail(1, "weird", 4),
    detail(1, "in_review", 0),
    detail(1, "in_review", 4, [message(1, "resolution_note", "internal")]),
    detail(1, "in_review", 4, [message(1, "customer_reply", 5)]),
    detail(1, "in_review", 4, [{ ...message(1, "customer_reply", "x"), message_id: "nope" }]),
    detail(1, "in_review", 4, [], { messages: undefined }),
    detail(1, "in_review", 4, [], { note: undefined }),
    detail(1, "in_review", 4, [], { created_at: "yesterday" }),
  ]) {
    const attempt = load({ [DETAIL(1)]: [reply(200, bad)] });
    assert.equal((await attempt.ctx.convLoadDetail(api(attempt), uid(1))).outcome, "error");
  }
});

test("detail: 404 means gone, 401 redirects, and a bad id never reaches the network", async () => {
  const missing = load({ [DETAIL(1)]: [error(404, "NOT_FOUND")] });
  assert.equal((await missing.ctx.convLoadDetail(api(missing), uid(1))).outcome, "gone");
  const out = load({ [DETAIL(1)]: [error(401, "UNAUTHENTICATED")] });
  assert.equal((await out.ctx.convLoadDetail(api(out), uid(1))).outcome, "redirect");
  const bad = load({});
  assert.equal((await bad.ctx.convLoadDetail(api(bad), "../x")).outcome, "gone");
  assert.deepEqual(bad.keys(), []);
});

/* ---------- reply text ---------- */

test("reply text is trimmed and normalized, and limits match the server", () => {
  const page = load({});
  assert.equal(page.ctx.convBuildReply("  café \n second line  ").message, "café \n second line");
  assert.ok(page.ctx.convBuildReply("   ").error);
  assert.ok(page.ctx.convBuildReply("x".repeat(2001)).error);
  assert.equal(page.ctx.convBuildReply("x".repeat(2000)).message.length, 2000);
  assert.ok(page.ctx.convBuildReply("bad\u0000text").error);
  assert.ok(page.ctx.convBuildReply("a\tb\r\nc").message);
});

/* ---------- sending a reply ---------- */

test("a reply registers one ID, sends the reviewed version once, and is acknowledged", async () => {
  const page = load({
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [reply(201, savedReply(1, 5))],
  });
  const state = newState(1);
  const result = await page.ctx.convSendReply(state, api(page));
  assert.deepEqual(plain(result), { outcome: "saved", state: "in_review", version: 5 });
  assert.equal(state.submissionId, null);
  assert.deepEqual(body(page, SEND(1)), {
    submission_id: uid(501),
    message: "Windows 11, client 4.2.",
    expected_version: 4,
  });
  assert.equal(page.calls.find((c) => c.key === SEND(1)).options.headers["X-CSRF-Token"], "tok");
});

test("a conversation that moved before registration asks for a fresh review and keeps the ID", async () => {
  const page = load({ [REG(1)]: [reply(201, registration(1, 5))] });
  const state = newState(1);
  const result = await page.ctx.convSendReply(state, api(page));
  assert.equal(result.outcome, "changed");
  assert.equal(state.submissionId, uid(501));
  assert.equal(count(page, SEND(1)), 0);
});

test("registering on a request that is not waiting, or is gone, sends nothing", async () => {
  const closed = load({ [REG(1)]: [error(409, "NOT_WAITING_FOR_CUSTOMER")] });
  const first = await closed.ctx.convSendReply(newState(1), api(closed));
  assert.equal(first.outcome, "changed");
  assert.equal(count(closed, SEND(1)), 0);
  const missing = load({ [REG(1)]: [error(404, "NOT_FOUND")] });
  assert.equal((await missing.ctx.convSendReply(newState(1), api(missing))).outcome, "gone");
});

test("a malformed registration never produces a send", async () => {
  for (const bad of [
    registration(1, 4, { operation: "escalation" }),
    registration(1, 4, { request_id: uid(2) }),
    registration(1, 4, { submission_id: "nope" }),
    registration(1, 4, { registration_state: "completed" }),
    registration(1, 4, { version: 0 }),
  ]) {
    const page = load({ [REG(1)]: [reply(201, bad)] });
    const state = newState(1);
    const result = await page.ctx.convSendReply(state, api(page));
    assert.equal(result.outcome, "retry");
    assert.equal(state.submissionId, null);
    assert.equal(count(page, SEND(1)), 0);
  }
});

test("STALE_VERSION and NOT_WAITING_FOR_CUSTOMER are definite: nothing saved, review again", async () => {
  for (const code of ["STALE_VERSION", "NOT_WAITING_FOR_CUSTOMER"]) {
    const page = load({
      [REG(1)]: [reply(201, registration(1, 4))],
      [SEND(1)]: [error(409, code)],
    });
    const state = newState(1);
    const result = await page.ctx.convSendReply(state, api(page));
    assert.equal(result.outcome, "changed");
    assert.equal(state.unresolved, false);
    assert.equal(state.submissionId, uid(501));
    assert.equal(count(page, STATUS(1)), 0);
  }
});

test("a retry after a known failure reuses the same ID and never registers another", async () => {
  const page = load({
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [error(503, "DEPENDENCY_UNAVAILABLE"), reply(201, savedReply(1, 5))],
  });
  const state = newState(1);
  assert.equal((await page.ctx.convSendReply(state, api(page))).outcome, "retry");
  assert.equal((await page.ctx.convSendReply(state, api(page))).outcome, "saved");
  assert.equal(count(page, REG(1)), 1);
});

test("an uncertain commit is checked through the status endpoint, not resent blindly", async () => {
  const page = load({
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [error(503, "SAVE_OUTCOME_UNCERTAIN")],
    [STATUS(1)]: [reply(200, status(1, true))],
  });
  const state = newState(1);
  const result = await page.ctx.convSendReply(state, api(page));
  assert.deepEqual(plain(result), { outcome: "saved", state: "in_review", version: 5 });
  assert.equal(count(page, SEND(1)), 1);
  assert.equal(state.unresolved, false);
});

test("unknown outcome stays locked on the same ID until a valid status answer arrives", async () => {
  const page = load({
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [new TypeError("fetch failed"), reply(200, savedReply(1, 5))],
    [STATUS(1)]: [error(503, "DEPENDENCY_UNAVAILABLE"), reply(200, status(1, false)), reply(200, status(1, false))],
  });
  const state = newState(1);
  const first = await page.ctx.convSendReply(state, api(page));
  assert.equal(first.outcome, "unresolved");
  assert.equal(state.unresolved, true);

  // While locked, sending again only checks status.
  const second = await page.ctx.convSendReply(state, api(page));
  assert.equal(second.outcome, "retry");
  assert.equal(count(page, REG(1)), 1);
  assert.equal(count(page, SEND(1)), 1);
  assert.equal(state.unresolved, false);

  // Now unlocked, the retry resends the same ID and payload.
  const third = await page.ctx.convSendReply(state, api(page));
  assert.equal(third.outcome, "saved");
  assert.equal(body(page, SEND(1)).submission_id, uid(501));
  assert.equal(count(page, REG(1)), 1);
});

test("a malformed success response is treated as unknown, not as a save", async () => {
  for (const bad of [
    savedReply(1, 5, { reply_id: "nope" }),
    savedReply(1, 5, { request_id: uid(2) }),
    savedReply(1, 7), // a first save is exactly one version past the reviewed one
    savedReply(1, 5, { state: "waiting_for_customer" }),
  ]) {
    const page = load({
      [REG(1)]: [reply(201, registration(1, 4))],
      [SEND(1)]: [reply(201, bad)],
      [STATUS(1)]: [error(503, "DEPENDENCY_UNAVAILABLE")],
    });
    const state = newState(1);
    assert.equal((await page.ctx.convSendReply(state, api(page))).outcome, "unresolved");
    assert.equal(state.unresolved, true);
  }
});

test("a replay (200) is accepted whatever the request has moved on to", async () => {
  const page = load({
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [reply(200, savedReply(1, 9, { state: "resolved" }))],
  });
  const result = await page.ctx.convSendReply(newState(1), api(page));
  assert.deepEqual(plain(result), { outcome: "saved", state: "resolved", version: 9 });
});

test("CONFLICT reports the earlier saved reply and never overwrites it", async () => {
  const page = load({
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [error(409, "CONFLICT")],
    [STATUS(1)]: [reply(200, status(1, true))],
  });
  const state = newState(1);
  const result = await page.ctx.convSendReply(state, api(page));
  assert.equal(result.outcome, "conflict");
  assert.equal(state.submissionId, null);
});

test("an expired or unknown reply ID returns to editing without a hidden replacement", async () => {
  for (const response of [error(410, "SUBMISSION_ID_EXPIRED"), error(404, "NOT_FOUND")]) {
    const page = load({
      [REG(1)]: [reply(201, registration(1, 4))],
      [SEND(1)]: [response],
    });
    const state = newState(1);
    const result = await page.ctx.convSendReply(state, api(page));
    assert.equal(result.outcome, "edit");
    assert.equal(state.submissionId, null);
    assert.equal(count(page, REG(1)), 1);
  }
});

test("status answers about the wrong operation or request keep the reply locked", async () => {
  for (const bad of [
    status(1, true, { operation: "escalation" }),
    status(1, true, { request_id: uid(2) }),
    status(1, true, { submission_id: uid(999) }),
    status(1, true, { expires_at: TIME }),
    status(1, false, { created_at: TIME }),
    status(1, false, { registration_state: "completed" }),
    status(1, true, { version: null }),
  ]) {
    const page = load({
      [REG(1)]: [reply(201, registration(1, 4))],
      [SEND(1)]: [error(503, "SAVE_OUTCOME_UNCERTAIN")],
      [STATUS(1)]: [reply(200, bad)],
    });
    const state = newState(1);
    assert.equal((await page.ctx.convSendReply(state, api(page))).outcome, "unresolved");
    assert.equal(state.unresolved, true);
  }
});

test("an expired reply ID found by status goes back to editing", async () => {
  const page = load({
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [error(503, "SAVE_OUTCOME_UNCERTAIN")],
    [STATUS(1)]: [reply(200, status(1, false, { registration_state: "expired" }))],
  });
  const state = newState(1);
  assert.equal((await page.ctx.convSendReply(state, api(page))).outcome, "edit");
  assert.equal(state.submissionId, null);
});

test("an ended session redirects at every step", async () => {
  const atRegister = load({ [REG(1)]: [error(401, "UNAUTHENTICATED")] });
  assert.equal((await atRegister.ctx.convSendReply(newState(1), api(atRegister))).outcome, "redirect");
  const atSend = load({
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [error(401, "UNAUTHENTICATED")],
  });
  assert.equal((await atSend.ctx.convSendReply(newState(1), api(atSend))).outcome, "redirect");
  const atStatus = load({
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [new TypeError("fetch failed")],
    [STATUS(1)]: [error(401, "UNAUTHENTICATED")],
  });
  assert.equal((await atStatus.ctx.convSendReply(newState(1), api(atStatus))).outcome, "redirect");
});

/* ---------- page-level tests: real handlers on fake elements ---------- */

function fakeElement(tag = "div") {
  return {
    tag,
    hidden: false,
    disabled: false,
    readOnly: false,
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
  "list-view", "detail-view", "list", "empty", "refresh", "retry", "back", "reload",
  "detail-title", "detail-state", "content", "note", "messages", "no-messages", "hint",
  "reply-box", "reply-form", "reply", "review", "preview", "send", "edit", "status",
];

async function settle() {
  await new Promise((resolve) => setImmediate(resolve));
}

async function openPage(routes) {
  const elements = Object.fromEntries(IDS.map((id) => [`#conv-${id}`, fakeElement()]));
  elements["#conversations"] = fakeElement();
  elements["#conversations"].hidden = true;
  for (const id of ["detail-view", "empty", "retry", "no-messages", "hint", "reply-box", "review"])
    elements[`#conv-${id}`].hidden = true;
  const page = load(routes, elements);
  const el = (id) => elements[`#conv-${id}`];
  const click = async (node) => {
    await Promise.all((node.handlers.click ?? []).map((fn) => fn({})));
    await settle();
  };
  const submit = async () => {
    await Promise.all(
      (el("reply-form").handlers.submit ?? []).map((fn) => fn({ preventDefault() {} })),
    );
    await settle();
  };
  const dispatch = async (type) => {
    await Promise.all((page.listeners[type] ?? []).map((fn) => fn({})));
    await settle();
  };
  const openButtons = () =>
    walk(el("list")).filter((n) => n.tag === "button" && n.textContent === "Open");
  const messageTexts = () =>
    el("messages").children.map((li) => li.children.map((c) => c.textContent));
  await settle();
  return { ...page, el, click, submit, dispatch, openButtons, messageTexts };
}

const waitingDetail = (version = 4, extra = []) =>
  detail(1, "waiting_for_customer", version, [
    message(1, "message_to_customer", "Which operating system do you use?", 3),
    ...extra,
  ]);

test("the list shows each request and the screen stays hidden elements correct", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(2, "waiting_for_customer", 4), summary(1, "resolved", 6)] })],
  });
  assert.equal(page.el("list").children.length, 2);
  assert.match(page.el("list").children[0].children[0].textContent, /Support is waiting for your reply/);
  assert.equal(page.el("empty").hidden, true);
  assert.equal(page.el("detail-view").hidden, true);
  assert.equal(page.ctx.document.querySelector("#conversations").hidden, false);
  assert.equal(page.el("status").textContent, "");
});

test("an empty list says so and a failed load offers a retry, never an empty list", async () => {
  const empty = await openPage({ [LIST]: [reply(200, { items: [] })] });
  assert.equal(empty.el("empty").hidden, false);

  const failed = await openPage({
    [LIST]: [error(503, "DEPENDENCY_UNAVAILABLE", "Support is down."), reply(200, { items: [summary(1)] })],
  });
  assert.equal(failed.el("empty").hidden, true);
  assert.equal(failed.el("retry").hidden, false);
  assert.equal(failed.el("status").textContent, "Support is down.");
  await failed.click(failed.el("retry"));
  assert.equal(failed.el("list").children.length, 1);
  assert.equal(failed.el("retry").hidden, true);
});

test("an ended session sends the customer back to sign in", async () => {
  const page = await openPage({ [LIST]: [error(401, "UNAUTHENTICATED")] });
  assert.equal(page.ctx.assigned, "/");
});

test("opening a request shows the conversation as plain text", async () => {
  const hostile = "<img src=x onerror=alert(1)>";
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(1, "waiting_for_customer", 4)] })],
    [DETAIL(1)]: [
      reply(200, {
        ...waitingDetail(4, [message(2, "customer_reply", hostile, 4)]),
        content: hostile,
        note: "A note",
      }),
    ],
  });
  await page.click(page.openButtons()[0]);
  assert.equal(page.el("detail-view").hidden, false);
  assert.equal(page.el("list-view").hidden, true);
  assert.equal(page.el("content").textContent, hostile);
  assert.equal(page.el("content").innerHTML, undefined);
  assert.equal(page.el("note").textContent, "A note");
  assert.equal(page.el("detail-state").textContent, "Support is waiting for your reply.");
  assert.equal(page.messageTexts().length, 2);
  assert.match(page.messageTexts()[0][0], /^Support/);
  assert.match(page.messageTexts()[1][0], /^You/);
  assert.equal(page.messageTexts()[1][1], hostile);
  assert.equal(page.el("reply-box").hidden, false);
  assert.equal(page.el("review").hidden, true);
});

test("only a request waiting for the customer offers a reply box", async () => {
  for (const [state, hint] of [
    ["queued", false],
    ["in_review", false],
    ["resolved", true],
  ]) {
    const page = await openPage({
      [LIST]: [reply(200, { items: [summary(1, state, 3)] })],
      [DETAIL(1)]: [reply(200, detail(1, state, 3))],
    });
    await page.click(page.openButtons()[0]);
    assert.equal(page.el("reply-box").hidden, true);
    assert.equal(page.el("review").hidden, true);
    assert.equal(page.el("hint").hidden, hint);
  }
});

test("a request that has gone returns to the list with an explanation", async () => {
  const page = await openPage({
    [LIST]: [
      reply(200, { items: [summary(1, "resolved", 3)] }),
      reply(200, { items: [] }),
    ],
    [DETAIL(1)]: [error(404, "NOT_FOUND")],
  });
  await page.click(page.openButtons()[0]);
  assert.equal(page.el("list-view").hidden, false);
  assert.equal(page.el("status").textContent, "That request is no longer available.");
  assert.equal(page.el("empty").hidden, false);
});

test("reviewing a reply reloads the conversation first, then sends the reviewed version", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(1, "waiting_for_customer", 4)] })],
    [DETAIL(1)]: [
      reply(200, waitingDetail(4)),
      reply(200, waitingDetail(4)), // fresh read when the customer chooses Review
      reply(200, detail(1, "in_review", 5, [
        message(1, "message_to_customer", "Which operating system do you use?", 3),
        message(2, "customer_reply", "Windows 11", 5),
      ])),
    ],
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [reply(201, savedReply(1, 5))],
  });
  await page.click(page.openButtons()[0]);
  page.el("reply").value = "  Windows 11  ";
  await page.submit();

  assert.equal(count(page, DETAIL(1)), 2);
  assert.equal(page.el("review").hidden, false);
  assert.equal(page.el("reply-box").hidden, true);
  assert.equal(page.el("preview").textContent, "Windows 11");
  assert.equal(count(page, REG(1)), 0, "reviewing alone registers nothing");

  await page.click(page.el("send"));
  assert.deepEqual(body(page, SEND(1)), {
    submission_id: uid(501),
    message: "Windows 11",
    expected_version: 4,
  });
  assert.match(page.el("status").textContent, /Your reply was saved\./);
  assert.doesNotMatch(page.el("status").textContent, /within|hours|minutes/);
  assert.equal(page.el("status").className, "ok");
  assert.equal(page.el("reply-box").hidden, true);
  assert.equal(page.el("review").hidden, true);
  assert.equal(page.el("detail-state").textContent, "Support is reviewing.");
  assert.equal(page.messageTexts().length, 2);
  assert.equal(page.el("reply").value, "");
});

test("new messages found on reload are shown first, the draft is kept, and a second review proceeds", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(1, "waiting_for_customer", 4)] })],
    [DETAIL(1)]: [
      reply(200, waitingDetail(4)),
      reply(200, waitingDetail(5, [message(2, "message_to_customer", "Also, which client version?", 5)])),
      reply(200, waitingDetail(5, [message(2, "message_to_customer", "Also, which client version?", 5)])),
    ],
  });
  await page.click(page.openButtons()[0]);
  page.el("reply").value = "Windows 11";
  await page.submit();
  assert.equal(page.el("review").hidden, true);
  assert.equal(page.el("reply-box").hidden, false);
  assert.equal(page.el("reply").value, "Windows 11");
  assert.equal(page.messageTexts().length, 2);
  assert.match(page.el("status").textContent, /latest messages are shown above/);
  assert.equal(count(page, REG(1)), 0);

  await page.submit();
  assert.equal(page.el("review").hidden, false);
});

test("a request that stopped waiting while the customer typed is not reviewed or sent", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(1, "waiting_for_customer", 4)] })],
    [DETAIL(1)]: [reply(200, waitingDetail(4)), reply(200, detail(1, "resolved", 6))],
  });
  await page.click(page.openButtons()[0]);
  page.el("reply").value = "Too late";
  await page.submit();
  assert.equal(page.el("review").hidden, true);
  assert.equal(page.el("reply-box").hidden, true);
  assert.match(page.el("status").textContent, /no longer waiting for your reply/);
  assert.equal(count(page, REG(1)), 0);
});

test("invalid reply text is rejected before any request", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(1, "waiting_for_customer", 4)] })],
    [DETAIL(1)]: [reply(200, waitingDetail(4))],
  });
  await page.click(page.openButtons()[0]);
  page.el("reply").value = "   ";
  await page.submit();
  assert.equal(page.el("status").textContent, "Write your reply first.");
  assert.equal(count(page, DETAIL(1)), 1);
});

test("a changed conversation at send time reloads it and asks for a fresh review", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(1, "waiting_for_customer", 4)] })],
    [DETAIL(1)]: [
      reply(200, waitingDetail(4)),
      reply(200, waitingDetail(4)),
      reply(200, waitingDetail(5, [message(2, "message_to_customer", "New question", 5)])),
    ],
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [error(409, "STALE_VERSION")],
  });
  await page.click(page.openButtons()[0]);
  page.el("reply").value = "Windows 11";
  await page.submit();
  await page.click(page.el("send"));
  assert.equal(page.el("review").hidden, true);
  assert.equal(page.el("reply-box").hidden, false);
  assert.equal(page.el("reply").value, "Windows 11");
  assert.equal(page.messageTexts().length, 2);
  assert.match(page.el("status").textContent, /changed while you were writing/);
});

test("an unknown outcome locks the screen on the same reply until it is checked", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(1, "waiting_for_customer", 4)] })],
    [DETAIL(1)]: [
      reply(200, waitingDetail(4)),
      reply(200, waitingDetail(4)),
      reply(200, detail(1, "in_review", 5, [message(2, "customer_reply", "Windows 11", 5)])),
    ],
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [new TypeError("fetch failed")],
    [STATUS(1)]: [error(503, "DEPENDENCY_UNAVAILABLE"), reply(200, status(1, true))],
  });
  await page.click(page.openButtons()[0]);
  page.el("reply").value = "Windows 11";
  await page.submit();
  await page.click(page.el("send"));

  assert.equal(page.el("send").textContent, "Check status");
  assert.match(page.el("status").textContent, /could not confirm/);
  assert.equal(page.el("edit").disabled, true);
  assert.equal(page.el("back").disabled, true);
  assert.equal(page.el("reload").disabled, true);
  assert.equal(page.el("reply").readOnly, true);
  assert.equal(count(page, REG(1)), 1);

  await page.click(page.el("edit")); // ignored while locked
  assert.equal(page.el("review").hidden, false);

  await page.click(page.el("send"));
  assert.match(page.el("status").textContent, /Your reply was saved\./);
  assert.equal(page.el("back").disabled, false);
  assert.equal(page.el("reply").readOnly, false);
  assert.equal(count(page, SEND(1)), 1);
  assert.equal(count(page, REG(1)), 1);
});

test("an unfinished reply survives going back to the list", async () => {
  const page = await openPage({
    [LIST]: [
      reply(200, { items: [summary(1, "waiting_for_customer", 4)] }),
      reply(200, { items: [summary(1, "waiting_for_customer", 4)] }),
    ],
    [DETAIL(1)]: [reply(200, waitingDetail(4)), reply(200, waitingDetail(4))],
  });
  await page.click(page.openButtons()[0]);
  page.el("reply").value = "Half written";
  await page.click(page.el("back"));
  assert.equal(page.el("list-view").hidden, false);
  await page.click(page.openButtons()[0]);
  assert.equal(page.el("reply").value, "Half written");
});

test("Edit leaves review without sending, and an unused reply ID is reused later", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(1, "waiting_for_customer", 4)] })],
    [DETAIL(1)]: [
      reply(200, waitingDetail(4)),
      reply(200, waitingDetail(4)),
      reply(200, waitingDetail(4)),
      reply(200, detail(1, "in_review", 5)),
    ],
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [error(503, "DEPENDENCY_UNAVAILABLE"), reply(201, savedReply(1, 5))],
  });
  await page.click(page.openButtons()[0]);
  page.el("reply").value = "First wording";
  await page.submit();
  await page.click(page.el("send")); // known failure: nothing saved
  assert.equal(page.el("send").textContent, "Try again");
  await page.click(page.el("edit"));
  assert.equal(page.el("review").hidden, true);
  assert.equal(page.el("reply").value, "First wording");

  page.el("reply").value = "Better wording";
  await page.submit();
  await page.click(page.el("send"));
  assert.equal(count(page, REG(1)), 1, "the same unused ID is reused");
  assert.equal(body(page, SEND(1)).message, "First wording");
  const sends = page.calls.filter((c) => c.key === SEND(1));
  assert.equal(JSON.parse(sends[1].options.body).message, "Better wording");
  assert.equal(JSON.parse(sends[1].options.body).submission_id, uid(501));
});

/* ---------- review follow-ups: failed reload, new saves, emoji limit ---------- */

async function reviewThenSend(page) {
  await page.click(page.openButtons()[0]);
  page.el("reply").value = "Windows 11";
  await page.submit();
  assert.equal(page.el("review").hidden, false);
  await page.click(page.el("send"));
}

test("a failed reload after a changed conversation leaves review and keeps the draft", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(1, "waiting_for_customer", 4)] })],
    [DETAIL(1)]: [
      reply(200, waitingDetail(4)),
      reply(200, waitingDetail(4)),
      error(503, "DEPENDENCY_UNAVAILABLE", "Support is down."),
      reply(200, waitingDetail(5, [message(2, "message_to_customer", "New question", 5)])),
      reply(200, waitingDetail(5, [message(2, "message_to_customer", "New question", 5)])),
    ],
    [REG(1)]: [reply(201, registration(1, 4))],
    [SEND(1)]: [error(409, "STALE_VERSION")],
  });
  await reviewThenSend(page);

  // No dead Send button: review is closed, the draft is kept and Reload is offered.
  assert.equal(page.el("review").hidden, true);
  assert.equal(page.el("reply-box").hidden, true);
  assert.equal(page.el("reply").value, "Windows 11");
  assert.match(page.el("status").textContent, /choose Reload/);
  assert.equal(page.el("reload").disabled, false);
  assert.equal(page.el("back").disabled, false);
  assert.equal(page.el("send").disabled, false);

  await page.click(page.el("reload"));
  assert.equal(page.el("reply-box").hidden, false);
  assert.equal(page.el("reply").value, "Windows 11");
  assert.equal(page.messageTexts().length, 2);

  await page.submit();
  assert.equal(page.el("review").hidden, false);
  assert.equal(page.el("preview").textContent, "Windows 11");
});

test("a failed reload after the request stopped waiting also leaves review", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [summary(1, "waiting_for_customer", 4)] })],
    [DETAIL(1)]: [
      reply(200, waitingDetail(4)),
      reply(200, waitingDetail(4)),
      reply(502, undefined),
    ],
    [REG(1)]: [error(409, "NOT_WAITING_FOR_CUSTOMER")],
  });
  await reviewThenSend(page);
  assert.equal(page.el("review").hidden, true);
  assert.equal(page.el("reply-box").hidden, true);
  assert.equal(page.el("reply").value, "Windows 11");
  assert.match(page.el("status").textContent, /no longer waiting/);
  assert.match(page.el("status").textContent, /choose Reload/);
  assert.equal(page.el("reload").disabled, false);
});

test("a newly saved request appears in the list without a manual refresh", async () => {
  const page = await openPage({
    [LIST]: [reply(200, { items: [] }), reply(200, { items: [summary(1)] })],
  });
  assert.equal(page.el("empty").hidden, false);
  await page.dispatch("deskguide:support-saved");
  assert.equal(count(page, LIST), 2);
  assert.equal(page.el("list").children.length, 1);
  assert.equal(page.el("empty").hidden, true);
});

test("a save announced while the list is loading triggers one more load", async () => {
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  const page = await openPage({
    [LIST]: [
      () => gate.then(() => reply(200, { items: [] })),
      reply(200, { items: [summary(1)] }),
    ],
  });
  await page.dispatch("deskguide:support-saved"); // first load still in flight
  assert.equal(count(page, LIST), 1);
  release();
  await settle();
  await settle();
  assert.equal(count(page, LIST), 2);
  assert.equal(page.el("list").children.length, 1);
  assert.equal(page.el("empty").hidden, true);
});

test("a save announced while a request is open does not pull the customer back to the list", async () => {
  const page = await openPage({
    [LIST]: [
      reply(200, { items: [summary(1, "waiting_for_customer", 4)] }),
      reply(200, { items: [summary(2), summary(1, "waiting_for_customer", 4)] }),
    ],
    [DETAIL(1)]: [reply(200, waitingDetail(4))],
  });
  await page.click(page.openButtons()[0]);
  await page.dispatch("deskguide:support-saved");
  assert.equal(page.el("detail-view").hidden, false);
  assert.equal(count(page, LIST), 1);
  await page.click(page.el("back"));
  assert.equal(page.el("list").children.length, 2);
});

test("the reply limit counts characters like the server, so emoji are not cut at 1,000", () => {
  const page = load({});
  const emoji = "\u{1F600}"; // two UTF-16 units, one character
  assert.equal(page.ctx.convBuildReply(emoji.repeat(1000)).message, emoji.repeat(1000));
  assert.equal(page.ctx.convBuildReply(emoji.repeat(2000)).message, emoji.repeat(2000));
  assert.ok(page.ctx.convBuildReply(emoji.repeat(2001)).error);
  assert.ok(page.ctx.convBuildReply("a".repeat(2000)).message);
  assert.ok(page.ctx.convBuildReply("a".repeat(2001)).error);
});

test("the reply box has no HTML length limit that counts UTF-16 units", () => {
  const html = fs.readFileSync(path.join(__dirname, "../app/templates/home.html"), "utf8");
  const box = html.match(/<textarea[^>]*id="conv-reply"[^>]*>/);
  assert.ok(box, "reply textarea not found");
  assert.doesNotMatch(box[0], /maxlength/i);
  assert.match(html, /Your reply \(up to 2,000 characters\)/);
});
