/* Customer question screen (ask, sources, feedback) regressions using isolated fetch and DOM substitutes. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const read = (name, dir = "static") =>
  fs.readFileSync(path.join(__dirname, "../app", dir, name), "utf8");
const questionSource = read("question.js");

const uid = (n) => `aaaaaaaa-0000-4000-8000-${String(n).padStart(12, "0")}`;

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
const error = (status, code, message = "Server message.", headers = {}) =>
  reply(status, { error: { code, message } }, headers);

const REF = { source_id: "DOC-003", section_id: "s2", source_version: "3" };
const source = (over = {}) => ({
  ref: { ...REF },
  title: "VPN Setup Guide",
  section_title: "Installing the client",
  url: "/v1/sources/DOC-003/sections/s2?version=3",
  ...over,
});
const base = {
  contract_version: "0.3.3",
  configuration_version: "cfg-0.1",
  correlation_id: uid(9),
  route: "ai",
};
const answered = (over = {}) => ({
  ...base,
  inquiry_id: uid(1),
  answer_id: uid(2),
  status: "answered",
  answer_origin: "ai_generated",
  answer: "Install the Acme VPN client, sign in, and select the Campus profile.",
  sources: [source()],
  clarification_prompt: null,
  escalation_offered: false,
  suggested_reason: null,
  ...over,
});
const unanswered = (status, reason, over = {}) => ({
  ...base,
  inquiry_id: uid(3),
  answer_id: null,
  status,
  answer_origin: null,
  answer: null,
  sources: [],
  clarification_prompt: null,
  escalation_offered: status === "escalation_offered" || status === "temporarily_unavailable",
  suggested_reason: reason,
  ...over,
});
const section = (over = {}) => ({
  contract_version: "0.3.3",
  ref: { ...REF },
  document_title: "VPN Setup Guide",
  section_title: "Installing the client",
  text: "Install the Acme VPN client, sign in, and select the Campus profile.",
  correlation_id: uid(8),
  ...over,
});
const feedbackSaved = () => ({
  contract_version: "0.3.3",
  feedback_id: uid(50),
  state: "pending_review",
  correlation_id: uid(51),
});

const ASK = "POST /v1/inquiries";
const SOURCE = "GET /v1/sources/DOC-003/sections/s2?version=3";
const FEEDBACK = "POST /v1/feedback";

const plain = (value) => JSON.parse(JSON.stringify(value));
const deferred = () => {
  let resolve;
  const promise = new Promise((r) => (resolve = r));
  return { promise, resolve };
};

/* routes: "METHOD /path" -> response, or a list consumed one at a time. */
function load(routes, elements = null, extra = {}) {
  const calls = [];
  const context = {
    TypeError,
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
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
    ...extra,
  };
  vm.createContext(context);
  vm.runInContext(questionSource, context, { filename: "question.js" });
  return { ctx: context, calls, keys: () => calls.map((c) => c.key) };
}
const count = (page, key) => page.keys().filter((k) => k === key).length;
const api = (page) => (method, url, body) => page.ctx.askApi(method, url, body);
const sentBody = (page, key) => JSON.parse(page.calls.find((c) => c.key === key).options.body);

/* ---------- question text ---------- */

test("a question is trimmed, normalized and line breaks become spaces", () => {
  const page = load({});
  assert.equal(page.ctx.askBuildQuestion("  How do I set up\nthe VPN?\r\n  ").question, "How do I set up the VPN?");
  assert.equal(page.ctx.askBuildQuestion("Café").question, "Café");
  assert.match(page.ctx.askBuildQuestion("   ").error, /Type your question/);
  assert.match(page.ctx.askBuildQuestion("a\u0000b").error, /control characters/);
  assert.match(page.ctx.askBuildQuestion("a\u007Fb").error, /control characters/);
  assert.match(page.ctx.askBuildQuestion("a\uD800b").error, /control characters/);
});

test("the question limit counts characters like the server, so emoji are not cut at 500", () => {
  const page = load({});
  assert.equal(page.ctx.askBuildQuestion("😀".repeat(1000)).question.length, 2000);
  assert.match(page.ctx.askBuildQuestion("😀".repeat(1001)).error, /1,000 characters/);
});

/* ---------- inquiry validation ---------- */

test("every contract outcome is accepted and carries only what the screen needs", () => {
  const page = load({});
  const valid = (data) => page.ctx.askValidInquiry(data);
  const fixtures = [
    answered(),
    unanswered("escalation_offered", "insufficient_evidence"),
    unanswered("temporarily_unavailable", "provider_failure"),
    unanswered("temporarily_unavailable", "service_unavailable"),
    unanswered("escalation_offered", "validation_failed"),
    unanswered("clarification_requested", null, { clarification_prompt: "Which VPN client do you use?" }),
    unanswered("clarification_requested", "insufficient_evidence"),
    unanswered("escalation_offered", "human_requested", { route: "human_requested" }),
  ];
  for (const data of fixtures) assert.notEqual(valid(data), null, data.status);
  const result = valid(answered());
  assert.equal(result.inquiryId, uid(1));
  assert.equal(result.sources.length, 1);
  assert.equal(result.sources[0].title, "VPN Setup Guide");
  assert.equal(result.url, undefined);
  assert.equal(valid(answered()).sources[0].url, undefined);
});

test("inconsistent or incomplete inquiry results are never shown", () => {
  const page = load({});
  const bad = [
    ["no citations", answered({ sources: [] })],
    ["no answer id", answered({ answer_id: null })],
    ["bad answer id", answered({ answer_id: "nope" })],
    ["empty answer", answered({ answer: "  " })],
    ["control characters in the answer", answered({ answer: "a\u0000b" })],
    ["oversized answer", answered({ answer: "x".repeat(4001) })],
    ["unknown origin", answered({ answer_origin: "model" })],
    ["account origin on the ai route", answered({ answer_origin: "account_status", sources: [] })],
    ["ai origin on the account route", answered({ route: "account_status" })],
    ["account answer with sources", answered({ answer_origin: "account_status", route: "account_status" })],
    ["too many sources", answered({ sources: Array.from({ length: 9 }, (_, n) => source({ ref: { ...REF, section_id: `s${n}` } })) })],
    ["duplicate sources", answered({ sources: [source(), source()] })],
    ["source without a title", answered({ sources: [source({ title: "" })] })],
    ["source with a control character", answered({ sources: [source({ section_title: "a\nb" })] })],
    ["source without a reference", answered({ sources: [{ title: "x", section_title: "y" }] })],
    ["bad inquiry id", answered({ inquiry_id: "1" })],
    ["unknown status", answered({ status: "done" })],
    ["unknown route", answered({ route: "web" })],
    ["unknown reason", unanswered("escalation_offered", "because")],
    ["missing reason", (() => { const d = unanswered("escalation_offered", null); delete d.suggested_reason; return d; })()],
    ["escalation flag missing on a fallback", unanswered("escalation_offered", "insufficient_evidence", { escalation_offered: false })],
    ["escalation flag set on an answer", answered({ escalation_offered: true })],
    ["escalation flag set on a clarification", unanswered("clarification_requested", null, { escalation_offered: true })],
    ["answer text on a fallback", unanswered("escalation_offered", "insufficient_evidence", { answer: "Maybe." })],
    ["answer id on a fallback", unanswered("temporarily_unavailable", "provider_failure", { answer_id: uid(2) })],
    ["origin on a fallback", unanswered("temporarily_unavailable", "provider_failure", { answer_origin: "ai_generated" })],
    ["sources on a fallback", unanswered("escalation_offered", "insufficient_evidence", { sources: [source()] })],
    ["prompt on a fallback", unanswered("escalation_offered", "insufficient_evidence", { clarification_prompt: "Hmm" })],
    ["prompt on an answer", answered({ clarification_prompt: "Hmm" })],
    ["empty prompt", unanswered("clarification_requested", null, { clarification_prompt: " " })],
    ["not an object", "answered"],
    ["null", null],
  ];
  for (const [name, data] of bad) assert.equal(page.ctx.askValidInquiry(data), null, name);
});

/* ---------- asking ---------- */

test("asking sends the question as ask_question with the CSRF token and returns the answer", async () => {
  const page = load({ [ASK]: [reply(200, answered())] });
  const result = await page.ctx.askSubmitQuestion("How do I set up the Campus VPN profile?", api(page));
  assert.equal(result.outcome, "ok");
  assert.equal(result.inquiry.status, "answered");
  assert.deepEqual(plain(sentBody(page, ASK)), {
    requested_operation: "ask_question",
    question: "How do I set up the Campus VPN profile?",
  });
  const call = page.calls.find((c) => c.key === ASK);
  assert.equal(call.options.headers["X-CSRF-Token"], "tok");
});

test("a result that fails validation is reported as unverified, never as an answer", async () => {
  for (const response of [
    reply(200, answered({ sources: [] })),
    reply(200, undefined),
    reply(201, answered()),
    reply(200, { items: [] }),
  ]) {
    const page = load({ [ASK]: [response] });
    const result = await page.ctx.askSubmitQuestion("q", api(page));
    assert.equal(result.outcome, "invalid");
    assert.match(result.message, /could not verify/);
    assert.match(result.message, /still here/);
  }
});

test("failures keep the question and use readable messages", async () => {
  const run = async (response) => {
    const page = load({ [ASK]: [response] });
    return page.ctx.askSubmitQuestion("q", api(page));
  };
  assert.equal((await run(error(401, "UNAUTHENTICATED"))).outcome, "redirect");
  const limited = await run(error(429, "RATE_LIMITED", "Please wait before asking again.", { "Retry-After": "40" }));
  assert.equal(limited.message, "Please wait before asking again. Try again in about 40 seconds.");
  const busy = await run(error(503, "SERVICE_BUSY", "DeskGuide is busy. Please try again shortly.", { "Retry-After": "1" }));
  assert.match(busy.message, /DeskGuide is busy/);
  assert.match((await run(error(504, "DEADLINE_EXCEEDED", "This took too long. Try again."))).message, /too long/);
  assert.equal((await run(error(400, "VALIDATION_FAILED", "Use between 1 and 1000 characters."))).message, "Use between 1 and 1000 characters.");
  const proxy = await run(reply(502, undefined));
  assert.match(proxy.message, /unavailable right now/);
  assert.match(proxy.message, /still here/);
  assert.doesNotMatch(proxy.message, /Unexpected token|<html/i);
  const dropped = load({ [ASK]: [new TypeError("Failed to fetch")] });
  const network = await dropped.ctx.askSubmitQuestion("q", api(dropped));
  assert.equal(network.message, "Connection unavailable. Your question is still here. Try again.");
});

test("a call that never finishes is abandoned and reported as a lost connection", async () => {
  const timers = [];
  const cleared = [];
  let rejectFetch;
  class FakeAbortController {
    constructor() {
      this.signal = { aborted: false };
    }
    abort() {
      this.signal.aborted = true;
      rejectFetch(new TypeError("aborted"));
    }
  }
  const page = load(
    { [ASK]: () => new Promise((_, reject) => (rejectFetch = reject)) },
    null,
    {
      AbortController: FakeAbortController,
      setTimeout: (fn, ms) => (timers.push({ fn, ms }), timers.length),
      clearTimeout: (id) => cleared.push(id),
    },
  );
  const pending = page.ctx.askSubmitQuestion("q", api(page));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(timers.length, 1);
  assert.equal(timers[0].ms, 30000);
  timers[0].fn();
  const result = await pending;
  assert.equal(result.outcome, "error");
  assert.match(result.message, /Connection unavailable/);
  assert.deepEqual(cleared, [1]);
});

/* ---------- sources ---------- */

test("a source address is built from the reference, never from the server's url field", async () => {
  const page = load({});
  assert.equal(page.ctx.askSourceUrl(REF), "/v1/sources/DOC-003/sections/s2?version=3");
  assert.equal(
    page.ctx.askSourceUrl({ source_id: "a/b", section_id: "c d", source_version: "1&x=2" }),
    "/v1/sources/a%2Fb/sections/c%20d?version=1%26x%3D2",
  );
  const hostile = load({ [SOURCE]: [reply(200, section())] });
  const result = await hostile.ctx.askLoadSource(plain(source({ url: "https://evil.example/steal" })).ref, api(hostile));
  assert.equal(result.outcome, "ok");
  assert.deepEqual(hostile.keys().filter((k) => k !== "GET /v1/session"), [SOURCE]);
});

test("a section is accepted only when it is the one that was requested", async () => {
  const run = async (response) => {
    const page = load({ [SOURCE]: [response] });
    return page.ctx.askLoadSource(plain(REF), api(page));
  };
  const ok = await run(reply(200, section()));
  assert.equal(ok.outcome, "ok");
  assert.equal(ok.section.text.startsWith("Install the Acme"), true);
  for (const bad of [
    section({ ref: { ...REF, section_id: "s3" } }),
    section({ ref: { ...REF, source_version: "2" } }),
    section({ ref: undefined }),
    section({ text: "" }),
    section({ text: 7 }),
    section({ document_title: " " }),
    section({ section_title: null }),
  ])
    assert.equal((await run(reply(200, bad))).outcome, "invalid");
  assert.equal((await run(reply(200, undefined))).outcome, "invalid");
});

test("source failures: 404 means no longer available, 401 redirects, 503 is shown", async () => {
  const run = async (response) => {
    const page = load({ [SOURCE]: [response] });
    return page.ctx.askLoadSource(plain(REF), api(page));
  };
  const gone = await run(error(404, "NOT_FOUND", "Not found."));
  assert.equal(gone.outcome, "gone");
  assert.equal(gone.message, "This source is no longer available to you.");
  assert.equal((await run(error(401, "UNAUTHENTICATED"))).outcome, "redirect");
  const down = await run(error(503, "DEPENDENCY_UNAVAILABLE", "Sources are unavailable."));
  assert.equal(down.outcome, "error");
  assert.equal(down.message, "Sources are unavailable.");
  assert.equal((await run(error(400, "VALIDATION_FAILED", "Malformed."))).outcome, "error");
});

/* ---------- feedback ---------- */

const inquiryOf = (data) => load({}).ctx.askValidInquiry(data);

test("feedback is built from the inquiry, a rating and optional category and comment", () => {
  const page = load({});
  const build = (data, input) => plain(page.ctx.askBuildFeedback(inquiryOf(data), input));
  assert.deepEqual(build(answered(), { rating: "helpful", category: "wrong_source", comment: "  " }), {
    payload: { inquiry_id: uid(1), rating: "helpful" },
  });
  assert.deepEqual(
    build(answered(), { rating: "not_helpful", category: "wrong_source", comment: " Wrong VPN.\n" }),
    { payload: { inquiry_id: uid(1), rating: "not_helpful", category: "wrong_source", comment: "Wrong VPN." } },
  );
  assert.deepEqual(build(answered(), { rating: "not_helpful", category: "", comment: "" }), {
    payload: { inquiry_id: uid(1), rating: "not_helpful" },
  });
  const payload = build(answered(), { rating: "helpful" }).payload;
  assert.equal(payload.answer_id, undefined);
  assert.match(build(answered(), { rating: "" }).error, /Choose whether/);
  assert.match(build(answered(), { rating: "meh" }).error, /Choose whether/);
});

test("feedback on a question with no answer is allowed and uses the fallback categories", () => {
  const page = load({});
  const fallback = unanswered("temporarily_unavailable", "provider_failure");
  const result = plain(
    page.ctx.askBuildFeedback(inquiryOf(fallback), {
      rating: "not_helpful",
      category: "fallback_unhelpful",
      comment: "I only needed the VPN steps.",
    }),
  );
  assert.deepEqual(result, {
    payload: {
      inquiry_id: uid(3),
      rating: "not_helpful",
      category: "fallback_unhelpful",
      comment: "I only needed the VPN steps.",
    },
  });
  assert.deepEqual(plain(page.ctx.askCategoriesFor("escalation_offered")), [
    "too_much_escalation", "fallback_unhelpful", "unclear", "other",
  ]);
  assert.deepEqual(plain(page.ctx.askCategoriesFor("answered")), [
    "incorrect", "incomplete", "wrong_source", "unclear", "other",
  ]);
});

test("a category that does not fit the outcome is rejected before sending", () => {
  const page = load({});
  const wrong = (data, category) =>
    page.ctx.askBuildFeedback(inquiryOf(data), { rating: "not_helpful", category }).error;
  assert.match(wrong(answered(), "fallback_unhelpful"), /listed reasons/);
  assert.match(wrong(answered(), "too_much_escalation"), /listed reasons/);
  assert.match(wrong(unanswered("escalation_offered", "insufficient_evidence"), "wrong_source"), /listed reasons/);
  assert.match(wrong(unanswered("clarification_requested", null), "incorrect"), /listed reasons/);
  assert.match(wrong(answered(), "bogus"), /listed reasons/);
});

test("the comment limit counts characters like the server, both sides of 500", () => {
  const page = load({});
  const build = (comment) =>
    page.ctx.askBuildFeedback(inquiryOf(answered()), { rating: "helpful", comment });
  assert.equal(build("😀".repeat(500)).payload.comment.length, 1000);
  assert.match(build("😀".repeat(501)).error, /500 characters/);
  assert.match(build("a\u0000b").error, /control characters/);
  assert.equal(build("line one\nline two").payload.comment, "line one\nline two");
});

test("feedback outcomes: saved, already recorded, unavailable, definite error, unknown", async () => {
  const run = async (response) => {
    const page = load({ [FEEDBACK]: [response] });
    return page.ctx.askSendFeedback({ inquiry_id: uid(1), rating: "helpful" }, api(page));
  };
  assert.equal((await run(reply(201, feedbackSaved()))).outcome, "saved");
  assert.equal((await run(error(409, "CONFLICT"))).outcome, "recorded");
  assert.equal((await run(error(404, "NOT_FOUND"))).outcome, "unavailable");
  assert.equal((await run(reply(404, undefined))).outcome, "unavailable");
  assert.equal((await run(error(401, "UNAUTHENTICATED"))).outcome, "redirect");
  assert.equal((await run(error(400, "VALIDATION_FAILED", "Bad category."))).outcome, "error");
  assert.equal((await run(error(429, "RATE_LIMITED", "Slow down."))).outcome, "error");
  assert.equal((await run(error(503, "SERVICE_BUSY", "Busy."))).outcome, "error");
  assert.equal((await run(error(503, "DEPENDENCY_UNAVAILABLE", "Down."))).outcome, "error");
  for (const unknown of [
    reply(201, { ...feedbackSaved(), state: "published" }),
    reply(201, { ...feedbackSaved(), feedback_id: "x" }),
    reply(201, undefined),
    reply(200, feedbackSaved()),
    reply(500, undefined),
    error(503, "SAVE_OUTCOME_UNCERTAIN"),
    new TypeError("Failed to fetch"),
  ]) {
    const result = await run(unknown);
    assert.equal(result.outcome, "unknown");
    assert.match(result.message, /will not be counted twice/);
  }
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
    focused: false,
    scrolled: false,
    children: [],
    handlers: {},
    attrs: {},
    addEventListener(type, fn) {
      (this.handlers[type] ??= []).push(fn);
    },
    dispatchEvent(event) {
      for (const fn of this.handlers[event.type] ?? []) fn(event);
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
    focus() {
      this.focused = true;
    },
    scrollIntoView() {
      this.scrolled = true;
    },
  };
}
const walk = (node, out = []) => {
  out.push(node);
  node.children.forEach((c) => walk(c, out));
  return out;
};

const IDS = [
  "form", "question", "submit", "clear", "result", "headline", "answer", "sources-box",
  "sources", "source-view", "source-title", "source-text", "source-close", "notice", "offer",
  "contact", "feedback", "feedback-form", "rating", "category-box", "category", "comment",
  "feedback-send", "feedback-status", "status",
];

async function settle() {
  await new Promise((resolve) => setImmediate(resolve));
}

async function openPage(routes, { support = true, extra = {} } = {}) {
  const elements = Object.fromEntries(IDS.map((id) => [`#ask-${id}`, fakeElement()]));
  elements["#questions"] = Object.assign(fakeElement(), { hidden: true });
  for (const id of [
    "result", "answer", "sources-box", "source-view", "notice", "offer", "feedback", "category-box",
  ])
    elements[`#ask-${id}`].hidden = true;
  if (support) {
    elements["#support"] = Object.assign(fakeElement(), { hidden: true });
    for (const id of ["form", "review", "done", "status", "content", "note", "consent",
      "edit", "send", "another", "saved", "preview-content", "preview-note"])
      elements[`#support-${id}`] = fakeElement();
    elements["#support-review"].hidden = true;
    elements["#support-done"].hidden = true;
  }
  const page = load(routes, elements, extra);
  if (support) vm.runInContext(read("support.js"), page.ctx, { filename: "support.js" });
  const el = (id) => elements[`#ask-${id}`];
  const fire = async (node, type, event = { preventDefault() {} }) => {
    await Promise.all((node.handlers[type] ?? []).map((fn) => fn(event)));
    await settle();
  };
  const ask = async (text) => {
    el("question").value = text;
    await fire(el("form"), "submit");
  };
  const sourceButtons = () => walk(el("sources")).filter((n) => n.tag === "button");
  const categories = () => el("category").children.map((o) => o.value);
  await settle();
  return { ...page, el, elements, fire, ask, sourceButtons, categories };
}

test("the screen appears and a supported answer is shown as plain text with its sources", async () => {
  const hostile = "<img src=x onerror=alert(1)> Install the client.";
  const page = await openPage({ [ASK]: [reply(200, answered({ answer: hostile }))] });
  assert.equal(page.elements["#questions"].hidden, false);
  assert.equal(page.el("result").hidden, true);
  await page.ask("How do I set up the Campus VPN profile?");
  assert.equal(page.el("result").hidden, false);
  assert.equal(page.el("headline").textContent, "Answer");
  assert.equal(page.el("answer").hidden, false);
  assert.equal(page.el("answer").textContent, hostile);
  assert.equal(page.sourceButtons().length, 1);
  assert.equal(page.sourceButtons()[0].textContent, "VPN Setup Guide: Installing the client");
  assert.equal(page.el("sources-box").hidden, false);
  assert.equal(page.el("notice").hidden, true);
  assert.equal(page.el("offer").hidden, true);
  assert.equal(page.el("feedback").hidden, false);
  assert.equal(page.el("status").textContent, "Answer");
  assert.equal(page.el("submit").disabled, false);
});

test("opening a source fetches it, shows it in the page as plain text, and can be closed", async () => {
  const hostile = "<script>alert(1)</script> Step one.\nStep two.";
  const page = await openPage({
    [ASK]: [reply(200, answered())],
    [SOURCE]: [reply(200, section({ text: hostile }))],
  });
  await page.ask("vpn");
  await page.fire(page.sourceButtons()[0], "click", {});
  assert.equal(page.el("source-view").hidden, false);
  assert.equal(page.el("source-title").textContent, "VPN Setup Guide: Installing the client");
  assert.equal(page.el("source-text").textContent, hostile);
  assert.equal(page.ctx.assigned, undefined);
  assert.equal(count(page, SOURCE), 1);
  await page.fire(page.el("source-close"), "click", {});
  assert.equal(page.el("source-view").hidden, true);
  assert.equal(page.el("source-text").textContent, "");
});

test("a source that is no longer available says so and shows nothing", async () => {
  const page = await openPage({
    [ASK]: [reply(200, answered())],
    [SOURCE]: [error(404, "NOT_FOUND", "Not found.")],
  });
  await page.ask("vpn");
  await page.fire(page.sourceButtons()[0], "click", {});
  assert.equal(page.el("source-view").hidden, true);
  assert.equal(page.el("status").textContent, "This source is no longer available to you.");
});

test("an unverified section is not shown", async () => {
  const page = await openPage({
    [ASK]: [reply(200, answered())],
    [SOURCE]: [reply(200, section({ ref: { ...REF, section_id: "s9" } }))],
  });
  await page.ask("vpn");
  await page.fire(page.sourceButtons()[0], "click", {});
  assert.equal(page.el("source-view").hidden, true);
  assert.match(page.el("status").textContent, /could not verify this source/);
});

test("a source that arrives after another was requested or the result was cleared is dropped", async () => {
  const slow = deferred();
  const other = { ...REF, section_id: "s5" };
  const page = await openPage({
    [ASK]: [reply(200, answered({ sources: [source(), source({ ref: other, section_title: "Signing in" })] }))],
    [SOURCE]: [() => slow.promise],
    "GET /v1/sources/DOC-003/sections/s5?version=3": [
      reply(200, section({ ref: other, section_title: "Signing in", text: "Second." })),
    ],
  });
  await page.ask("vpn");
  const [first, second] = page.sourceButtons();
  page.fire(first, "click", {});
  await settle();
  await page.fire(second, "click", {});
  assert.equal(page.el("source-text").textContent, "Second.");
  slow.resolve(reply(200, section({ text: "First, late." })));
  await settle();
  assert.equal(page.el("source-text").textContent, "Second.");
  await page.fire(page.el("clear"), "click", {});
  assert.equal(page.el("source-view").hidden, true);
});

test("a question with no supported answer explains why and still offers feedback", async () => {
  const cases = [
    ["escalation_offered", "insufficient_evidence", /could not find a supported answer/, true],
    ["escalation_offered", "validation_failed", /could not confirm an answer/, true],
    ["temporarily_unavailable", "provider_failure", /could not prepare an answer right now/, true],
    ["temporarily_unavailable", "service_unavailable", /does not mean there is no answer/, true],
    ["escalation_offered", "human_requested", /asked to talk to a person/, true],
    ["escalation_offered", null, /could not answer this question/, true],
  ];
  for (const [status, reason, text, offered] of cases) {
    const page = await openPage({ [ASK]: [reply(200, unanswered(status, reason))] });
    await page.ask("Why can't I log in?");
    assert.equal(page.el("answer").hidden, true, reason);
    assert.equal(page.el("answer").textContent, "", reason);
    assert.equal(page.el("sources-box").hidden, true, reason);
    assert.equal(page.el("notice").hidden, false, reason);
    assert.match(page.el("notice").textContent, text, reason);
    assert.equal(page.el("offer").hidden, !offered, reason);
    assert.equal(page.el("feedback").hidden, false, reason);
    assert.equal(page.el("question").value, "Why can't I log in?", reason);
    // A normal "no answer" result is announced, but never styled like an error.
    assert.equal(page.el("status").className, "info", reason);
  }
});

test("headlines tell an unavailable service apart from an unsupported question", async () => {
  const down = await openPage({ [ASK]: [reply(200, unanswered("temporarily_unavailable", "provider_failure"))] });
  await down.ask("q");
  assert.equal(down.el("headline").textContent, "DeskGuide is unavailable right now");
  const none = await openPage({ [ASK]: [reply(200, unanswered("escalation_offered", "insufficient_evidence"))] });
  await none.ask("q");
  assert.equal(none.el("headline").textContent, "We could not answer this");
});

test("a clarification shows the server's prompt or a default, and offers no escalation", async () => {
  const withPrompt = await openPage({
    [ASK]: [reply(200, unanswered("clarification_requested", null, { clarification_prompt: "Which VPN client do you use?" }))],
  });
  await withPrompt.ask("vpn");
  assert.equal(withPrompt.el("headline").textContent, "We need a little more detail");
  assert.equal(withPrompt.el("notice").textContent, "Which VPN client do you use?");
  assert.equal(withPrompt.el("offer").hidden, true);
  assert.equal(withPrompt.el("feedback").hidden, false);
  const without = await openPage({ [ASK]: [reply(200, unanswered("clarification_requested", null))] });
  await without.ask("vpn");
  assert.match(without.el("notice").textContent, /add more detail/);
});

test("failures keep the question, show a message and never show a result or feedback", async () => {
  const page = await openPage({ [ASK]: [error(503, "SERVICE_BUSY", "DeskGuide is busy. Please try again shortly.", { "Retry-After": "1" })] });
  await page.ask("keep me");
  assert.equal(page.el("question").value, "keep me");
  assert.match(page.el("status").textContent, /DeskGuide is busy/);
  assert.equal(page.el("result").hidden, true);
  assert.equal(page.el("feedback").hidden, true);
  assert.equal(page.el("submit").disabled, false);

  const invalid = await openPage({ [ASK]: [reply(200, answered({ sources: [] }))] });
  await invalid.ask("keep me too");
  assert.equal(invalid.el("question").value, "keep me too");
  assert.match(invalid.el("status").textContent, /could not verify/);
  assert.equal(invalid.el("result").hidden, true);
  assert.equal(invalid.el("answer").textContent, "");
  assert.equal(invalid.el("feedback").hidden, true);
});

test("an invalid question never reaches the network", async () => {
  const page = await openPage({});
  await page.ask("   ");
  assert.equal(page.el("status").textContent, "Type your question.");
  await page.ask("😀".repeat(1001));
  assert.match(page.el("status").textContent, /1,000 characters/);
  assert.equal(page.keys().length, 0);
});

test("asking twice quickly sends one request and locks the form until it returns", async () => {
  const slow = deferred();
  const page = await openPage({ [ASK]: [() => slow.promise] });
  page.el("question").value = "vpn";
  page.fire(page.el("form"), "submit");
  await settle();
  assert.equal(page.el("submit").disabled, true);
  assert.equal(page.el("clear").disabled, true);
  await page.fire(page.el("form"), "submit");
  await page.fire(page.el("clear"), "click", {});
  assert.equal(count(page, ASK), 1);
  assert.equal(page.el("question").value, "vpn");
  slow.resolve(reply(200, answered()));
  await settle();
  assert.equal(page.el("submit").disabled, false);
  assert.equal(page.el("result").hidden, false);
});

test("an ended session sends the customer back to sign in", async () => {
  const atAsk = await openPage({ [ASK]: [error(401, "UNAUTHENTICATED")] });
  await atAsk.ask("q");
  assert.equal(atAsk.ctx.assigned, "/");
  const atSource = await openPage({ [ASK]: [reply(200, answered())], [SOURCE]: [error(401, "UNAUTHENTICATED")] });
  await atSource.ask("q");
  await atSource.fire(atSource.sourceButtons()[0], "click", {});
  assert.equal(atSource.ctx.assigned, "/");
  const atFeedback = await openPage({ [ASK]: [reply(200, answered())], [FEEDBACK]: [error(401, "UNAUTHENTICATED")] });
  await atFeedback.ask("q");
  atFeedback.el("rating").value = "helpful";
  await atFeedback.fire(atFeedback.el("feedback-form"), "submit");
  assert.equal(atFeedback.ctx.assigned, "/");
});

test("a new question replaces the old result, source and feedback", async () => {
  const page = await openPage({
    [ASK]: [reply(200, answered()), reply(200, unanswered("escalation_offered", "insufficient_evidence"))],
    [SOURCE]: [reply(200, section())],
    [FEEDBACK]: [reply(201, feedbackSaved())],
  });
  await page.ask("first");
  await page.fire(page.sourceButtons()[0], "click", {});
  page.el("rating").value = "helpful";
  await page.fire(page.el("feedback-form"), "submit");
  assert.equal(page.el("feedback-send").disabled, true);
  await page.ask("second");
  assert.equal(page.el("headline").textContent, "We could not answer this");
  assert.equal(page.el("source-view").hidden, true);
  assert.equal(page.el("answer").textContent, "");
  assert.equal(page.el("sources-box").hidden, true);
  assert.equal(page.el("rating").value, "");
  assert.equal(page.el("feedback-send").disabled, false);
  assert.equal(page.el("feedback-status").textContent, "");
});

test("Clear empties the question, result and feedback", async () => {
  const page = await openPage({ [ASK]: [reply(200, answered())] });
  await page.ask("first");
  await page.fire(page.el("clear"), "click", {});
  assert.equal(page.el("question").value, "");
  assert.equal(page.el("result").hidden, true);
  assert.equal(page.el("feedback").hidden, true);
  assert.equal(page.el("status").textContent, "");
});

/* ---------- feedback on the page ---------- */

test("feedback needs a rating, offers reasons only for not helpful, and sends the inquiry", async () => {
  const page = await openPage({
    [ASK]: [reply(200, answered())],
    [FEEDBACK]: [reply(201, feedbackSaved())],
  });
  await page.ask("vpn");
  await page.fire(page.el("feedback-form"), "submit");
  assert.match(page.el("feedback-status").textContent, /Choose whether/);
  assert.equal(count(page, FEEDBACK), 0);
  assert.equal(page.el("category-box").hidden, true);
  assert.deepEqual(page.categories(), ["", "incorrect", "incomplete", "wrong_source", "unclear", "other"]);

  page.el("rating").value = "not_helpful";
  await page.fire(page.el("rating"), "change", {});
  assert.equal(page.el("category-box").hidden, false);
  page.el("category").value = "wrong_source";
  page.el("comment").value = "The guide was for a different VPN.";
  await page.fire(page.el("feedback-form"), "submit");
  assert.deepEqual(plain(sentBody(page, FEEDBACK)), {
    inquiry_id: uid(1),
    rating: "not_helpful",
    category: "wrong_source",
    comment: "The guide was for a different VPN.",
  });
  assert.equal(page.el("feedback-status").textContent, "Thank you. Your feedback was saved for review.");
  assert.equal(page.el("feedback-status").className, "ok");
  assert.equal(page.el("feedback-send").disabled, true);
  assert.equal(page.el("rating").disabled, true);
  assert.equal(page.el("comment").readOnly, true);
  await page.fire(page.el("feedback-form"), "submit");
  assert.equal(count(page, FEEDBACK), 1);
});

test("changing the rating back to helpful clears the chosen reason", async () => {
  const page = await openPage({ [ASK]: [reply(200, answered())], [FEEDBACK]: [reply(201, feedbackSaved())] });
  await page.ask("vpn");
  page.el("rating").value = "not_helpful";
  await page.fire(page.el("rating"), "change", {});
  page.el("category").value = "incorrect";
  page.el("rating").value = "helpful";
  await page.fire(page.el("rating"), "change", {});
  assert.equal(page.el("category-box").hidden, true);
  assert.equal(page.el("category").value, "");
  await page.fire(page.el("feedback-form"), "submit");
  assert.deepEqual(plain(sentBody(page, FEEDBACK)), { inquiry_id: uid(1), rating: "helpful" });
});

test("feedback is tied to the customer's own inquiry even when there is no answer", async () => {
  const page = await openPage({
    [ASK]: [reply(200, unanswered("temporarily_unavailable", "provider_failure"))],
    [FEEDBACK]: [reply(201, feedbackSaved())],
  });
  await page.ask("How do I set up the VPN?");
  assert.deepEqual(page.categories(), ["", "too_much_escalation", "fallback_unhelpful", "unclear", "other"]);
  page.el("rating").value = "not_helpful";
  await page.fire(page.el("rating"), "change", {});
  page.el("category").value = "fallback_unhelpful";
  page.el("comment").value = "I only needed the VPN steps.";
  await page.fire(page.el("feedback-form"), "submit");
  assert.deepEqual(plain(sentBody(page, FEEDBACK)), {
    inquiry_id: uid(3),
    rating: "not_helpful",
    category: "fallback_unhelpful",
    comment: "I only needed the VPN steps.",
  });
  assert.equal(page.el("feedback-send").disabled, true);
});

test("an unknown feedback outcome can be sent again and a duplicate answer counts as recorded", async () => {
  const page = await openPage({
    [ASK]: [reply(200, answered())],
    [FEEDBACK]: [reply(500, undefined), error(409, "CONFLICT", "Already sent.")],
  });
  await page.ask("vpn");
  page.el("rating").value = "helpful";
  await page.fire(page.el("feedback-form"), "submit");
  assert.match(page.el("feedback-status").textContent, /will not be counted twice/);
  assert.equal(page.el("feedback-send").disabled, false);
  assert.equal(page.el("rating").disabled, true);
  await page.fire(page.el("feedback-form"), "submit");
  assert.equal(page.el("feedback-status").textContent, "Feedback for this question was already recorded. This attempt did not replace it.");
  assert.equal(page.el("feedback-send").disabled, true);
});

test("generic NOT_FOUND feedback stays available without claiming the question expired", async () => {
  const page = await openPage({ [ASK]: [reply(200, answered())], [FEEDBACK]: [error(404, "NOT_FOUND", "Not found.")] });
  await page.ask("vpn");
  page.el("rating").value = "helpful";
  await page.fire(page.el("feedback-form"), "submit");
  assert.equal(page.el("feedback-status").textContent, "Feedback is not available right now.");
  assert.equal(page.el("feedback-send").disabled, false);
  assert.equal(page.el("rating").disabled, false);
});

test("feedback that arrives after a new question was asked never touches the new result", async () => {
  const slow = deferred();
  const page = await openPage({
    [ASK]: [reply(200, answered()), reply(200, unanswered("escalation_offered", "insufficient_evidence"))],
    [FEEDBACK]: [() => slow.promise],
  });
  await page.ask("first");
  page.el("rating").value = "helpful";
  page.fire(page.el("feedback-form"), "submit");
  await settle();
  await page.ask("second");
  slow.resolve(reply(201, feedbackSaved()));
  await settle();
  assert.equal(page.el("feedback-status").textContent, "");
  assert.equal(page.el("feedback-send").disabled, false);
  assert.equal(page.el("rating").disabled, false);
});

/* ---------- hand-off to support ---------- */

test("Contact support reveals the form and offers the question without overwriting the customer's text", async () => {
  const page = await openPage({
    [ASK]: [reply(200, unanswered("escalation_offered", "insufficient_evidence"))],
  });
  await page.ask("Why can't I log in?");
  assert.equal(page.el("offer").hidden, false);
  await page.fire(page.el("contact"), "click", {});
  assert.equal(page.elements["#support"].hidden, false);
  assert.equal(page.elements["#support-content"].value, "Why can't I log in?");
  assert.equal(page.elements["#support-content"].focused, true);
  assert.equal(page.elements["#support"].scrolled, true);

  page.elements["#support-content"].value = "Already typed.";
  await page.fire(page.el("contact"), "click", {});
  assert.equal(page.elements["#support-content"].value, "Already typed.");
});

test("the question offered to support is the one that was asked, not text edited afterwards", async () => {
  const page = await openPage({
    [ASK]: [reply(200, unanswered("escalation_offered", "insufficient_evidence"))],
  });
  await page.ask("  Why can't\nI log in?  ");
  page.el("question").value = "Something else I started typing";
  await page.fire(page.el("contact"), "click", {});
  assert.equal(page.elements["#support-content"].value, "Why can't I log in?");
});

test("without a support section the offer to contact support is not shown", async () => {
  const page = await openPage(
    { [ASK]: [reply(200, unanswered("escalation_offered", "insufficient_evidence"))] },
    { support: false },
  );
  await page.ask("q");
  assert.equal(page.el("offer").hidden, true);
  assert.equal(page.el("notice").hidden, false);
});

/* ---------- the page template ---------- */

test("home.html carries every element the question screen uses and no HTML length limit", () => {
  const html = read("home.html", "templates");
  const ids = [...questionSource.matchAll(/\$\("([a-z-]+)"\)/g)].map((m) => m[1]);
  assert.ok(ids.length >= IDS.length);
  for (const id of ids) assert.match(html, new RegExp(`id="ask-${id}"`), `ask-${id}`);
  assert.match(html, /id="questions"/);
  assert.match(html, /question\.js/);
  const textarea = /<textarea[^>]*id="ask-(question|comment)"[^>]*>/g;
  for (const [tag] of html.matchAll(textarea)) assert.doesNotMatch(tag, /maxlength/);
  assert.deepEqual([...new Set(ids)].sort(), [...IDS].sort());
});

test("question.js shares no global names with the other screens", () => {
  const others = ["support.js", "agent.js", "conversation.js"].map((name) => read(name));
  const names = [...questionSource.matchAll(/^(?:async )?(?:function|const) ([A-Za-z_]\w*)/gm)].map(
    (m) => m[1],
  );
  assert.ok(names.length > 20);
  for (const name of names) {
    assert.match(name, /^(ask|ASK|initQuestionFlow)/, name);
    for (const source of others)
      assert.doesNotMatch(source, new RegExp(`^(?:async )?(?:function|const) ${name}\\b`, "m"), name);
  }
});

test("lost feedback retries the original payload and never claims later edits were saved", async () => {
  const page = await openPage({
    [ASK]: [reply(200, answered())],
    [FEEDBACK]: [new TypeError("response lost after commit"), error(409, "CONFLICT")],
  });
  await page.ask("vpn");
  page.el("rating").value = "helpful";
  page.el("comment").value = "first text";
  await page.fire(page.el("feedback-form"), "submit");
  assert.equal(page.el("rating").disabled, true);
  assert.equal(page.el("category").disabled, true);
  assert.equal(page.el("comment").readOnly, true);
  assert.equal(page.el("feedback-send").disabled, false);
  assert.match(page.el("feedback-status").textContent, /original feedback is locked/);
  // Even programmatic edits cannot change the retry.
  page.el("rating").value = "not_helpful";
  page.el("category").value = "incorrect";
  page.el("comment").value = "second text";
  await page.fire(page.el("feedback-form"), "submit");
  const bodies = page.calls.filter(c => c.key === FEEDBACK).map(c => JSON.parse(c.options.body));
  assert.deepEqual(bodies, [bodies[0], bodies[0]]);
  assert.equal(bodies[0].comment, "first text");
  assert.equal(page.el("comment").value, "first text");
  assert.equal(page.el("rating").value, "helpful");
  assert.match(page.el("feedback-status").textContent, /did not replace it/);
});

for (const phase of ["token-fetch", "token-body", "request-body"]) {
  test(`timeout covers ${phase} and unlocks Ask/Clear`, async () => {
    let timeout;
    let signal;
    let cleared = false;
    const hang = (s) => new Promise((_, reject) =>
      s.addEventListener("abort", () => reject(Object.assign(new Error("aborted"), { name: "AbortError" }))));
    const page = await openPage({}, { support: false, extra: {
      AbortController,
      setTimeout: (fn, ms) => { assert.equal(ms, 30000); timeout = fn; return 1; },
      clearTimeout: () => { cleared = true; },
      fetch: async (url, options) => {
        signal = options.signal;
        if (url === "/v1/session") {
          if (phase === "token-fetch") return hang(signal);
          if (phase === "token-body") return { ...reply(200, {}), json: () => hang(signal) };
          return reply(200, { csrf_token: "tok" });
        }
        return { ...reply(200, {}), json: () => hang(signal) };
      },
    } });
    await page.ask("keep me");
    assert.equal(page.el("submit").disabled, true);
    assert.equal(typeof timeout, "function");
    timeout();
    await settle();
    assert.equal(signal.aborted, true);
    assert.equal(cleared, true);
    assert.equal(page.el("submit").disabled, false);
    assert.equal(page.el("clear").disabled, false);
    assert.match(page.el("status").textContent, /Connection unavailable/);
    assert.equal(page.el("question").value, "keep me");
  });
}

const supportRegistration = () => reply(201, {
  submission_id: uid(70), operation: "escalation", registration_state: "unused",
  expires_at: "2026-11-11T00:00:00Z",
});
const supportSavedReply = () => reply(201, {
  submission_id: uid(70), request_id: uid(71), state: "queued",
  created_at: "2026-11-10T00:00:00Z",
});
async function reviewSupport(page, text) {
  page.elements["#support-content"].value = text;
  await page.fire(page.elements["#support-form"], "submit");
}
test("Contact after a completed support save opens a new editable draft with fresh consent", async () => {
  const page = await openPage({
    [ASK]: [reply(200, unanswered("escalation_offered", "human_requested"))],
    "POST /v1/escalations/submission-ids": supportRegistration(),
    "POST /v1/escalations": supportSavedReply(),
  });
  await reviewSupport(page, "old request");
  page.elements["#support-consent"].checked = true;
  await page.fire(page.elements["#support-send"], "click");
  assert.equal(page.elements["#support-done"].hidden, false);
  await page.ask("new question");
  await page.fire(page.el("contact"), "click");
  assert.equal(page.elements["#support-form"].hidden, false);
  assert.equal(page.elements["#support-done"].hidden, true);
  assert.equal(page.elements["#support-content"].value, "new question");
  assert.equal(page.elements["#support-consent"].checked, false);
  await page.fire(page.elements["#support-form"], "submit");
  await page.fire(page.elements["#support-send"], "click");
  assert.equal(count(page, "POST /v1/escalations"), 1);
});
for (const unresolved of [false, true]) {
  test(`Contact preserves existing support ${unresolved ? "recovery lock" : "review and consent"}`, async () => {
    const page = await openPage({
      [ASK]: [reply(200, unanswered("escalation_offered", "human_requested"))],
      "POST /v1/escalations/submission-ids": supportRegistration(),
      "POST /v1/escalations": new TypeError("lost"),
      [`GET /v1/escalations/${uid(70)}`]: reply(502, undefined),
    });
    await reviewSupport(page, "existing request");
    page.elements["#support-consent"].checked = true;
    if (unresolved) await page.fire(page.elements["#support-send"], "click");
    await page.ask("new question");
    await page.fire(page.el("contact"), "click");
    assert.equal(page.elements["#support-review"].hidden, false);
    assert.equal(page.elements["#support-form"].hidden, true);
    assert.equal(page.elements["#support-content"].value, "existing request");
    assert.equal(page.elements["#support-consent"].checked, true);
    assert.equal(page.elements["#support-edit"].disabled, unresolved);
    if (unresolved) {
      assert.equal(page.elements["#support-send"].textContent, "Check status");
      await page.fire(page.elements["#support-another"], "click");
      assert.equal(page.elements["#support-review"].hidden, false);
      assert.equal(count(page, "POST /v1/escalations"), 1);
    }
  });
}

test("a late feedback response cannot unlock feedback already sending on the next inquiry", async () => {
  const first = deferred();
  const second = deferred();
  const page = await openPage({
    [ASK]: [reply(200, answered()), reply(200, answered({ inquiry_id: uid(4) }))],
    [FEEDBACK]: [() => first.promise, () => second.promise],
  });
  await page.ask("first");
  page.el("rating").value = "helpful";
  await page.fire(page.el("feedback-form"), "submit");
  await page.ask("second");
  page.el("rating").value = "not_helpful";
  await page.fire(page.el("feedback-form"), "submit");
  first.resolve(reply(201, feedbackSaved()));
  await settle();
  assert.equal(page.el("feedback-send").disabled, true);
  await page.fire(page.el("feedback-form"), "submit");
  assert.equal(count(page, FEEDBACK), 2);
  second.resolve(reply(201, feedbackSaved()));
  await settle();
  assert.match(page.el("feedback-status").textContent, /saved for review/);
});

test("feedback token timeout allows retry without locking an unsent payload", async () => {
  let timeout;
  const page = await openPage({ [ASK]: reply(200, answered()) });
  await page.ask("vpn");
  page.ctx.AbortController = AbortController;
  page.ctx.setTimeout = fn => { timeout = fn; return 1; };
  page.ctx.clearTimeout = () => {};
  page.ctx.fetch = async (url, options) => new Promise((_, reject) =>
    options.signal.addEventListener("abort", () =>
      reject(Object.assign(new Error("aborted"), { name: "AbortError" }))));
  page.el("rating").value = "helpful";
  await page.fire(page.el("feedback-form"), "submit");
  assert.equal(page.el("feedback-send").disabled, true);
  timeout();
  await settle();
  assert.equal(page.el("feedback-send").disabled, false);
  assert.equal(page.el("rating").disabled, false);
  assert.equal(page.el("comment").readOnly, false);
  assert.match(page.el("feedback-status").textContent, /Connection unavailable/);
});
