/*
 * Customer conversation flow (C4g list, C4f detail, C4d/C4e reply): find your requests,
 * read the conversation, and send one reviewed reply. Self-contained: it shares no
 * helpers with support.js or agent.js, so every global here is prefixed `conv`.
 */

"use strict";

const CONV_STATE_LABELS = {
  queued: "Waiting for an agent",
  assigned: "An agent has picked this up",
  in_review: "Support is reviewing",
  waiting_for_customer: "Support is waiting for your reply",
  resolved: "Resolved",
};
const CONV_MESSAGE_LABELS = { customer_reply: "You", message_to_customer: "Support" };
const CONV_STATES = ["queued", "assigned", "in_review", "waiting_for_customer", "resolved"];
const CONV_CONTROL_CHARACTERS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/;
const CONV_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const CONV_TIMESTAMP = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?Z$/;
// Codes the server only returns when it knows nothing was saved.
const CONV_RETRYABLE_CODES = [
  "RATE_LIMITED",
  "SERVICE_BUSY",
  "DEPENDENCY_UNAVAILABLE",
  "CSRF_FAILED",
  "FORBIDDEN",
];

async function convReadJson(response) {
  try {
    return await response.json();
  } catch {
    // Proxies may return an HTML error page instead of the application's JSON.
    return null;
  }
}

function convNormalize(response, data, sent) {
  const error = data && typeof data.error === "object" && data.error ? data.error : {};
  const retryAfter = Number.parseInt(response.headers?.get?.("Retry-After") ?? "", 10);
  return {
    ok: response.ok,
    status: response.status,
    data: data && typeof data === "object" ? data : {},
    code: typeof error.code === "string" ? error.code : null,
    message:
      typeof error.message === "string" && error.message.trim() ? error.message : null,
    retryAfter: Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
    network: false,
    sent,
  };
}

function convFailure(network, sent) {
  return {
    ok: false,
    status: 0,
    data: {},
    code: null,
    message: null,
    retryAfter: null,
    network,
    sent,
  };
}

/*
 * One same-origin call. State-changing calls fetch the session CSRF token first.
 * `sent` is true once the real request has left the browser, so a later failure
 * means the outcome is unknown rather than "nothing happened".
 */
async function convApi(method, path, body) {
  let sent = false;
  try {
    const headers = {};
    let payload;
    if (method !== "GET") {
      const tokenResponse = await fetch("/v1/session", { credentials: "same-origin" });
      const tokenData = await convReadJson(tokenResponse);
      if (!tokenResponse.ok) return convNormalize(tokenResponse, tokenData, false);
      if (typeof tokenData?.csrf_token !== "string" || !tokenData.csrf_token)
        return convFailure(false, false);
      headers["Content-Type"] = "application/json";
      headers["X-CSRF-Token"] = tokenData.csrf_token;
      payload = JSON.stringify(body ?? {});
    }
    sent = true;
    const response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers,
      body: payload,
    });
    return convNormalize(response, await convReadJson(response), true);
  } catch (error) {
    return convFailure(error instanceof TypeError, sent);
  }
}

function convFormatWait(seconds) {
  if (seconds < 90) return `about ${seconds} seconds`;
  if (seconds < 5400) return `about ${Math.ceil(seconds / 60)} minutes`;
  const hours = Math.ceil(seconds / 3600);
  return `about ${hours} ${hours === 1 ? "hour" : "hours"}`;
}

/* Contract Timestamp: ISO 8601 UTC, and a real calendar date and time. */
function convValidTimestamp(value) {
  if (typeof value !== "string") return false;
  const match = CONV_TIMESTAMP.exec(value);
  if (!match) return false;
  const [year, month, day, hour, minute, second] = match.slice(1).map(Number);
  const date = new Date(Date.UTC(year, month - 1, day, hour, minute, second));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day &&
    date.getUTCHours() === hour &&
    date.getUTCMinutes() === minute &&
    date.getUTCSeconds() === second
  );
}

function convValidUuid(value) {
  return typeof value === "string" && CONV_UUID.test(value);
}

function convValidVersion(value) {
  return Number.isInteger(value) && value >= 1 && value <= 2147483647;
}

const CONV_REGISTRATION_STATES = ["unused", "completed", "expired"];
const CONV_NOT_WAITING_MESSAGE =
  "This request is no longer waiting for your reply. Your reply was not sent.";
const CONV_STALE_MESSAGE =
  "This request changed while you were writing. Read the latest messages, then review your reply again.";
const CONV_UNRESOLVED_MESSAGE =
  "We could not confirm whether this reply was saved. It is locked until it is checked. Choose Check status.";

function convDescribe(result) {
  if (result.network) return "Connection unavailable. Try again.";
  if (result.ok) return "The service gave an unexpected answer. Try again.";
  if (result.message) {
    return result.status === 429 && result.retryAfter
      ? `${result.message} Try again in ${convFormatWait(result.retryAfter)}.`
      : result.message;
  }
  return "Service temporarily unavailable. Try again.";
}

function convFormatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function convStateText(state) {
  return state === "resolved"
    ? "This request is resolved. It cannot be reopened."
    : `${CONV_STATE_LABELS[state]}.`;
}

/* ---------- response validation: success statuses alone prove nothing ---------- */

function convValidSummary(item) {
  return (
    Boolean(item) &&
    typeof item === "object" &&
    convValidUuid(item.request_id) &&
    CONV_STATES.includes(item.state) &&
    convValidVersion(item.version) &&
    convValidTimestamp(item.created_at)
  );
}

function convValidMessage(message) {
  return (
    Boolean(message) &&
    typeof message === "object" &&
    convValidUuid(message.message_id) &&
    Object.hasOwn(CONV_MESSAGE_LABELS, message.kind) &&
    typeof message.content === "string" &&
    convValidTimestamp(message.created_at) &&
    (message.version === null || convValidVersion(message.version))
  );
}

/* Returns only the fields the screen shows, or null when the response is not trustworthy. */
function convValidDetail(result, requestId) {
  const data = result.data;
  if (
    result.status !== 200 ||
    data.request_id !== requestId ||
    !CONV_STATES.includes(data.state) ||
    !convValidVersion(data.version) ||
    typeof data.content !== "string" ||
    !(data.note === null || typeof data.note === "string") ||
    !convValidTimestamp(data.created_at) ||
    !Array.isArray(data.messages) ||
    !data.messages.every(convValidMessage)
  )
    return null;
  return {
    request_id: data.request_id,
    state: data.state,
    version: data.version,
    content: data.content,
    note: data.note,
    created_at: data.created_at,
    messages: data.messages.map((m) => ({
      message_id: m.message_id,
      kind: m.kind,
      content: m.content,
      created_at: m.created_at,
    })),
  };
}

async function convLoadList(api = convApi) {
  const result = await api("GET", "/v1/escalations/requests");
  if (result.status === 401) return { outcome: "redirect" };
  const items = result.data.items;
  if (
    result.status === 200 &&
    Array.isArray(items) &&
    items.every(convValidSummary) &&
    new Set(items.map((item) => item.request_id)).size === items.length
  )
    return {
      outcome: "ok",
      items: items.map(({ request_id, state, version, created_at }) => ({
        request_id,
        state,
        version,
        created_at,
      })),
    };
  return { outcome: "error", message: convDescribe(result) };
}

async function convLoadDetail(api, requestId) {
  if (!convValidUuid(requestId)) return { outcome: "gone" };
  const result = await api("GET", `/v1/escalations/requests/${requestId}`);
  if (result.status === 401) return { outcome: "redirect" };
  if (result.status === 404 && result.code === "NOT_FOUND") return { outcome: "gone" };
  const detail = convValidDetail(result, requestId);
  if (detail) return { outcome: "ok", detail };
  return { outcome: "error", message: convDescribe(result) };
}

/* ---------- reply: review, register one ID, send once, recover on unknown outcomes ---------- */

function convBuildReply(text) {
  const message = String(text ?? "").normalize("NFC").trim();
  if (!message) return { error: "Write your reply first." };
  if ([...message].length > 2000)
    return { error: "Please use 2,000 characters or fewer for your reply." };
  if (CONV_CONTROL_CHARACTERS.test(message))
    return { error: "Please remove special control characters from your reply." };
  return { message };
}

function convValidRegistration(result, requestId) {
  const data = result.data;
  return (
    result.status === 201 &&
    convValidUuid(data.submission_id) &&
    data.operation === "reply" &&
    data.registration_state === "unused" &&
    convValidTimestamp(data.expires_at) &&
    data.request_id === requestId &&
    CONV_STATES.includes(data.state) &&
    convValidVersion(data.version)
  );
}

function convValidReplySave(result, state) {
  const data = result.data;
  if (
    !(result.status === 200 || result.status === 201) ||
    !convValidUuid(data.reply_id) ||
    data.request_id !== state.requestId ||
    !CONV_STATES.includes(data.state) ||
    !convValidVersion(data.version)
  )
    return false;
  // A first save moves the request to in_review exactly one version past the reviewed one.
  return result.status === 200 || (data.state === "in_review" && data.version === state.expectedVersion + 1);
}

function convValidReplyStatus(result, state) {
  const data = result.data;
  if (
    result.status !== 200 ||
    data.submission_id !== state.submissionId ||
    data.operation !== "reply" ||
    typeof data.saved !== "boolean" ||
    !CONV_REGISTRATION_STATES.includes(data.registration_state) ||
    data.request_id !== state.requestId ||
    !CONV_STATES.includes(data.state) ||
    !convValidVersion(data.version)
  )
    return false;
  if (data.saved)
    return (
      data.registration_state === "completed" &&
      convValidTimestamp(data.created_at) &&
      data.expires_at === null
    );
  return (
    data.registration_state !== "completed" &&
    data.created_at === null &&
    convValidTimestamp(data.expires_at)
  );
}

function convSaved(state, data) {
  state.submissionId = null;
  state.unresolved = false;
  return { outcome: "saved", state: data.state, version: data.version };
}

/* Ask the server what happened to this ID. Never invents a replacement ID. */
async function convRecoverReply(state, api) {
  const status = await api("GET", `/v1/escalations/${state.submissionId}`);
  if (status.status === 401) return { outcome: "redirect" };
  if (convValidReplyStatus(status, state)) {
    if (status.data.saved) return convSaved(state, status.data);
    state.unresolved = false;
    if (status.data.registration_state === "expired") {
      state.submissionId = null;
      return {
        outcome: "edit",
        message: "This reply form timed out before it was sent. Your text is still here.",
      };
    }
    return { outcome: "retry", message: "It was not saved. Send it again to retry." };
  }
  if (status.status === 404 && status.code === "NOT_FOUND") {
    state.submissionId = null;
    state.unresolved = false;
    return {
      outcome: "edit",
      message:
        "We could not find this reply. Your text is still here; reload the conversation, then review it again.",
    };
  }
  state.unresolved = true;
  return { outcome: "unresolved", message: CONV_UNRESOLVED_MESSAGE };
}

/* The ID was already used with a different reply: say what was saved, never overwrite it. */
async function convResolveConflict(state, api) {
  const status = await api("GET", `/v1/escalations/${state.submissionId}`);
  if (status.status === 401) return { outcome: "redirect" };
  if (convValidReplyStatus(status, state) && status.data.saved) {
    state.submissionId = null;
    state.unresolved = false;
    return {
      outcome: "conflict",
      message:
        "Your earlier reply was already saved. The changed text was not sent. Read the conversation, then write a new reply if you need to.",
    };
  }
  state.unresolved = true;
  return { outcome: "unresolved", message: CONV_UNRESOLVED_MESSAGE };
}

/*
 * state = { requestId, message, expectedVersion, submissionId, unresolved }.
 * expectedVersion is the version the customer just read. Outcomes: saved, changed, gone,
 * conflict, retry, edit, unresolved or redirect. A reply ID is registered only when the
 * customer confirms, reused for every retry, and never replaced while its outcome is unknown.
 */
async function convSendReply(state, api = convApi) {
  if (state.unresolved) return convRecoverReply(state, api);
  if (!state.submissionId) {
    const registered = await api("POST", `/v1/escalations/${state.requestId}/reply-ids`, {
      operation: "reply",
    });
    if (registered.status === 401) return { outcome: "redirect" };
    if (registered.status === 409 && registered.code === "NOT_WAITING_FOR_CUSTOMER")
      return { outcome: "changed", message: CONV_NOT_WAITING_MESSAGE };
    if (registered.status === 404 && registered.code === "NOT_FOUND") return { outcome: "gone" };
    if (!convValidRegistration(registered, state.requestId))
      return { outcome: "retry", message: convDescribe(registered) };
    state.submissionId = registered.data.submission_id;
    // The conversation moved between reading it and registering: ask for a fresh review.
    if (registered.data.version !== state.expectedVersion)
      return { outcome: "changed", message: CONV_STALE_MESSAGE };
  }
  const result = await api("POST", `/v1/escalations/${state.requestId}/replies`, {
    submission_id: state.submissionId,
    message: state.message,
    expected_version: state.expectedVersion,
  });
  if (result.status === 401) return { outcome: "redirect" };
  if (!result.sent) return { outcome: "retry", message: convDescribe(result) };
  if (result.ok && convValidReplySave(result, state)) return convSaved(state, result.data);
  if (!result.ok) {
    if (result.status === 409 && result.code === "NOT_WAITING_FOR_CUSTOMER")
      return { outcome: "changed", message: CONV_NOT_WAITING_MESSAGE };
    if (result.status === 409 && result.code === "STALE_VERSION")
      return { outcome: "changed", message: CONV_STALE_MESSAGE };
    if (result.status === 409 && result.code === "CONFLICT")
      return convResolveConflict(state, api);
    if (result.code === "SUBMISSION_ID_EXPIRED") {
      state.submissionId = null;
      return {
        outcome: "edit",
        message: "This reply form timed out before it was sent. Your text is still here.",
      };
    }
    if (result.status === 404 && result.code === "NOT_FOUND") {
      state.submissionId = null;
      return {
        outcome: "edit",
        message:
          "We could not find this reply form. Your text is still here; reload the conversation, then review it again.",
      };
    }
    if (result.status === 400 && result.code) return { outcome: "edit", message: convDescribe(result) };
    if (CONV_RETRYABLE_CODES.includes(result.code))
      return { outcome: "retry", message: convDescribe(result) };
  }
  // Network drop, proxy page, uncertain commit or malformed success: outcome unknown.
  state.unresolved = true;
  return convRecoverReply(state, api);
}

/* ---------- page ---------- */

function initConversationFlow() {
  const root = document.querySelector("#conversations");
  if (!root) return;
  const $ = (name) => document.querySelector(`#conv-${name}`);
  const el = {
    listView: $("list-view"),
    detailView: $("detail-view"),
    list: $("list"),
    empty: $("empty"),
    refresh: $("refresh"),
    retry: $("retry"),
    back: $("back"),
    reload: $("reload"),
    title: $("detail-title"),
    stateText: $("detail-state"),
    content: $("content"),
    note: $("note"),
    messages: $("messages"),
    noMessages: $("no-messages"),
    hint: $("hint"),
    replyBox: $("reply-box"),
    replyForm: $("reply-form"),
    replyInput: $("reply"),
    review: $("review"),
    preview: $("preview"),
    send: $("send"),
    edit: $("edit"),
    status: $("status"),
  };
  const ui = {
    currentId: null,
    detail: null,
    reply: null,
    reviewing: false,
    busy: false,
    token: 0,
    drafts: new Map(),
    ids: new Map(),
  };
  const locked = () => Boolean(ui.reply?.unresolved);

  function say(text, good = false) {
    el.status.textContent = text;
    el.status.className = good ? "ok" : "";
  }
  function refreshControls() {
    const frozen = locked() || ui.busy;
    el.back.disabled = frozen;
    el.reload.disabled = frozen;
    el.refresh.disabled = ui.busy;
    el.edit.disabled = frozen;
    el.send.disabled = ui.busy;
    el.replyInput.readOnly = locked();
  }
  function setBusy(value) {
    ui.busy = value;
    refreshControls();
  }
  function show(view) {
    el.listView.hidden = view !== "list";
    el.detailView.hidden = view !== "detail";
  }
  function applyReplyVisibility() {
    const waiting = ui.detail?.state === "waiting_for_customer";
    el.replyBox.hidden = !waiting || ui.reviewing;
    el.review.hidden = !waiting || !ui.reviewing;
    refreshControls();
  }
  function endSession() {
    window.location.assign("/");
  }

  /* ----- list ----- */
  function makeRow(item) {
    const row = document.createElement("li");
    row.className = "conv-row";
    const head = document.createElement("p");
    head.className = "conv-row-head";
    head.textContent = `Request ${item.request_id.slice(0, 8)} · ${CONV_STATE_LABELS[item.state]}`;
    const when = document.createElement("p");
    when.textContent = `Sent ${convFormatTime(item.created_at)}`;
    const open = document.createElement("button");
    open.type = "button";
    open.className = "secondary";
    open.textContent = "Open";
    open.setAttribute("aria-label", `Open request ${item.request_id.slice(0, 8)}`);
    open.addEventListener("click", () => showRequest(item.request_id));
    row.append(head, when, open);
    return row;
  }

  async function loadList(note = "") {
    const token = ++ui.token;
    ui.currentId = null;
    ui.detail = null;
    ui.reply = null;
    ui.reviewing = false;
    show("list");
    el.retry.hidden = true;
    el.empty.hidden = true;
    el.list.replaceChildren();
    say(note || "Loading your requests…");
    setBusy(true);
    let result;
    try {
      result = await convLoadList();
    } finally {
      setBusy(false);
    }
    if (token !== ui.token) return;
    if (result.outcome === "redirect") return endSession();
    if (result.outcome === "ok") {
      el.list.replaceChildren(...result.items.map(makeRow));
      el.empty.hidden = result.items.length > 0;
      say(note);
    } else {
      el.retry.hidden = false;
      say(result.message);
    }
  }

  /* ----- detail ----- */
  function renderDetail(detail) {
    ui.detail = detail;
    ui.reviewing = false;
    el.title.textContent = `Request ${detail.request_id.slice(0, 8)}`;
    el.stateText.textContent = convStateText(detail.state);
    el.content.textContent = detail.content;
    el.note.textContent = detail.note ?? "No additional note.";
    const items = detail.messages.map((message) => {
      const item = document.createElement("li");
      item.className = `conv-message ${message.kind}`;
      const head = document.createElement("p");
      head.className = "conv-row-head";
      head.textContent = `${CONV_MESSAGE_LABELS[message.kind]} · ${convFormatTime(message.created_at)}`;
      const body = document.createElement("p");
      body.textContent = message.content;
      item.append(head, body);
      return item;
    });
    el.messages.replaceChildren(...items);
    el.noMessages.hidden = items.length > 0;
    el.hint.hidden = detail.state === "waiting_for_customer" || detail.state === "resolved";
    applyReplyVisibility();
  }

  /* Returns true when fresh detail is on screen; otherwise it has already told the customer why. */
  function acceptDetail(result, requestId) {
    if (result.outcome === "redirect") {
      endSession();
      return false;
    }
    if (result.outcome === "gone") {
      ui.drafts.delete(requestId);
      ui.ids.delete(requestId);
      loadList("That request is no longer available.");
      return false;
    }
    if (result.outcome === "ok") {
      renderDetail(result.detail);
      return true;
    }
    say(result.message);
    return false;
  }

  async function showRequest(requestId) {
    const token = ++ui.token;
    const sameRequest = ui.currentId === requestId && ui.detail;
    ui.currentId = requestId;
    show("detail");
    if (!sameRequest) {
      ui.detail = null;
      ui.reply = null;
      ui.reviewing = false;
      el.title.textContent = `Request ${requestId.slice(0, 8)}`;
      el.stateText.textContent = "";
      el.content.textContent = "";
      el.note.textContent = "";
      el.messages.replaceChildren();
      el.noMessages.hidden = true;
      el.hint.hidden = true;
      el.replyInput.value = ui.drafts.get(requestId) ?? "";
      applyReplyVisibility();
    }
    say("Loading the conversation…");
    setBusy(true);
    let result;
    try {
      result = await convLoadDetail(convApi, requestId);
    } finally {
      setBusy(false);
    }
    if (token !== ui.token) return;
    if (acceptDetail(result, requestId)) say("");
  }

  /* ----- reply: read the latest conversation, then review, then send ----- */
  el.replyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (ui.busy || locked() || !ui.detail) return;
    const built = convBuildReply(el.replyInput.value);
    if (built.error) {
      say(built.error);
      return;
    }
    const shown = ui.detail;
    say("Checking for new messages…");
    setBusy(true);
    let result;
    try {
      result = await convLoadDetail(convApi, shown.request_id);
    } finally {
      setBusy(false);
    }
    if (!acceptDetail(result, shown.request_id)) return;
    const latest = ui.detail;
    if (latest.state !== "waiting_for_customer") {
      say("This request changed and is no longer waiting for your reply. Your reply was not sent.");
      return;
    }
    if (latest.version !== shown.version) {
      say("Support's latest messages are shown above. Read them, then review your reply again.");
      return;
    }
    ui.drafts.set(latest.request_id, el.replyInput.value);
    ui.reply = {
      requestId: latest.request_id,
      message: built.message,
      expectedVersion: latest.version,
      submissionId: ui.ids.get(latest.request_id) ?? null,
      unresolved: false,
    };
    el.preview.textContent = built.message;
    el.send.textContent = "Send reply";
    ui.reviewing = true;
    applyReplyVisibility();
    say("");
  });

  el.edit.addEventListener("click", () => {
    if (ui.busy || locked()) return;
    ui.reviewing = false;
    ui.reply = null;
    applyReplyVisibility();
    say("");
  });

  el.send.addEventListener("click", async () => {
    if (ui.busy || !ui.reply) return;
    const reply = ui.reply;
    say("Please wait…");
    setBusy(true);
    let result;
    try {
      result = await convSendReply(reply);
    } finally {
      setBusy(false);
    }
    if (reply.submissionId) ui.ids.set(reply.requestId, reply.submissionId);
    else ui.ids.delete(reply.requestId);
    if (result.outcome === "redirect") {
      endSession();
    } else if (result.outcome === "saved") {
      await afterSaved(reply, result);
    } else if (result.outcome === "gone") {
      ui.drafts.delete(reply.requestId);
      ui.ids.delete(reply.requestId);
      loadList("That request is no longer available.");
    } else if (result.outcome === "unresolved") {
      el.send.textContent = "Check status";
      refreshControls();
      say(result.message);
    } else if (result.outcome === "retry") {
      el.send.textContent = "Try again";
      say(result.message);
    } else if (result.outcome === "edit") {
      ui.reply = null;
      ui.reviewing = false;
      applyReplyVisibility();
      say(result.message);
    } else {
      // changed or conflict: nothing was sent. Show what is true now and require a fresh review.
      ui.reply = null;
      const reloaded = await convLoadDetail(convApi, reply.requestId);
      if (acceptDetail(reloaded, reply.requestId)) say(result.message);
    }
  });

  async function afterSaved(reply, result) {
    ui.reply = null;
    ui.reviewing = false;
    ui.drafts.delete(reply.requestId);
    ui.ids.delete(reply.requestId);
    el.replyInput.value = "";
    const note =
      "Your reply was saved. Support has not read it yet, and we cannot promise a response time.";
    const reloaded = await convLoadDetail(convApi, reply.requestId);
    if (reloaded.outcome === "redirect") return endSession();
    if (reloaded.outcome === "ok") {
      renderDetail(reloaded.detail);
      say(note, true);
      return;
    }
    // Keep a stale reply box from inviting a second reply while the reload is unavailable.
    renderDetail({ ...ui.detail, state: result.state, version: result.version });
    say(`${note} We could not reload the conversation; choose Reload.`, true);
  }

  el.reload.addEventListener("click", () => {
    if (ui.busy || locked() || !ui.currentId) return;
    ui.reviewing = false;
    ui.reply = null;
    showRequest(ui.currentId);
  });
  el.back.addEventListener("click", () => {
    if (ui.busy || locked()) return;
    if (ui.currentId) {
      if (el.replyInput.value.trim()) ui.drafts.set(ui.currentId, el.replyInput.value);
      else ui.drafts.delete(ui.currentId);
    }
    loadList();
  });
  el.refresh.addEventListener("click", () => {
    if (!ui.busy) loadList();
  });
  el.retry.addEventListener("click", () => {
    if (!ui.busy) loadList();
  });

  root.hidden = false;
  loadList();
}

initConversationFlow();