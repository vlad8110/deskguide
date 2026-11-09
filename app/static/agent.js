/* Agent queue and request-detail flow (C5): claim, review, ask, resolve and release. */

"use strict";

const AGENT_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const AGENT_STATES = ["queued", "assigned", "in_review", "waiting_for_customer", "resolved"];
const AGENT_STATE_LABELS = {
  queued: "Waiting in the queue",
  assigned: "Assigned to you",
  in_review: "In review",
  waiting_for_customer: "Waiting for the customer",
  resolved: "Resolved",
};
const AGENT_MESSAGE_LABELS = {
  customer_reply: "Customer",
  message_to_customer: "You, to the customer",
  resolution_note: "Internal resolution note (never shown to the customer)",
};
const AGENT_CONTROL_CHARACTERS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/;
const AGENT_FIELDS = {
  waiting_for_customer: ["message_to_customer", 2000],
  resolved: ["resolution_note", 2000],
  queued: ["release_reason", 500],
};
const AGENT_SESSION_ENDED = "Your session has ended. Please sign in again.";

async function agentReadJson(response) {
  try {
    return await response.json();
  } catch {
    // Proxies may return an HTML error page instead of the application's JSON.
    return null;
  }
}

function agentNormalize(response, data, sent) {
  const error = data && typeof data.error === "object" && data.error ? data.error : {};
  return {
    ok: response.ok,
    status: response.status,
    data: data && typeof data === "object" ? data : {},
    code: typeof error.code === "string" ? error.code : null,
    message:
      typeof error.message === "string" && error.message.trim() ? error.message : null,
    network: false,
    sent,
  };
}

function agentFailure(network, sent) {
  return { ok: false, status: 0, data: {}, code: null, message: null, network, sent };
}

/*
 * One same-origin call. POSTs fetch the session CSRF token first. `sent` becomes true
 * once the real request leaves the browser, so a later failure means "outcome unknown".
 */
async function agentApi(method, path, body) {
  let sent = false;
  try {
    const headers = {};
    let payload;
    if (method !== "GET") {
      const tokenResponse = await fetch("/v1/session", { credentials: "same-origin" });
      const tokenData = await agentReadJson(tokenResponse);
      if (!tokenResponse.ok) return agentNormalize(tokenResponse, tokenData, false);
      if (typeof tokenData?.csrf_token !== "string" || !tokenData.csrf_token)
        return agentFailure(false, false);
      headers["X-CSRF-Token"] = tokenData.csrf_token;
      if (body !== undefined) {
        headers["Content-Type"] = "application/json";
        payload = JSON.stringify(body);
      }
    }
    sent = true;
    const response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers,
      body: payload,
    });
    return agentNormalize(response, await agentReadJson(response), true);
  } catch (error) {
    return agentFailure(error instanceof TypeError, sent);
  }
}

function agentDescribe(result) {
  if (result.network) return "Connection unavailable. Try again.";
  if (result.message) return result.message;
  return result.status >= 500 || result.status === 0
    ? "Service temporarily unavailable. Try again."
    : "The request could not be completed. Please try again.";
}

/* ---------- response validation: an HTTP success alone proves nothing ---------- */

function agentIsSummary(data) {
  return (
    !!data &&
    typeof data.request_id === "string" &&
    AGENT_UUID.test(data.request_id) &&
    AGENT_STATES.includes(data.state) &&
    Number.isInteger(data.version) &&
    data.version >= 1 &&
    (data.assigned_agent_id === null || typeof data.assigned_agent_id === "string")
  );
}

function agentIsListItem(item) {
  return agentIsSummary(item) && typeof item.content === "string" && typeof item.created_at === "string";
}

function agentIsDetail(data, requestId) {
  return (
    agentIsSummary(data) &&
    data.request_id === requestId &&
    typeof data.content === "string" &&
    (data.note === null || data.note === undefined || typeof data.note === "string") &&
    Array.isArray(data.messages) &&
    data.messages.every(
      (m) =>
        m &&
        typeof m.message_id === "string" &&
        typeof m.content === "string" &&
        Object.hasOwn(AGENT_MESSAGE_LABELS, m.kind),
    )
  );
}

function agentFailed(result) {
  if (result.status === 401) return { outcome: "redirect" };
  if (result.status === 403)
    return { outcome: "forbidden", message: "You do not have access to the agent workspace." };
  return { outcome: "error", message: agentDescribe(result) };
}

/* ---------- operations (testable: the api function is injected) ---------- */

async function agentLoadQueue(api, { state = "", cursor = "" } = {}) {
  let path = "/v1/agent/escalations?limit=25";
  if (state) path += `&state=${encodeURIComponent(state)}`;
  if (cursor) path += `&cursor=${encodeURIComponent(cursor)}`;
  const result = await api("GET", path);
  if (!result.ok) return agentFailed(result);
  const { items, next_cursor: next } = result.data;
  if (
    !Array.isArray(items) ||
    !items.every(agentIsListItem) ||
    !(next === null || next === undefined || typeof next === "string")
  )
    return { outcome: "error", message: "The queue could not be read. Try again." };
  return { outcome: "ok", items, nextCursor: next ?? null };
}

async function agentLoadDetail(api, requestId) {
  const result = await api("GET", `/v1/agent/escalations/${requestId}`);
  if (result.status === 404)
    return {
      outcome: "gone",
      message: "This request was not found or is no longer assigned to you.",
    };
  if (!result.ok) return agentFailed(result);
  if (!agentIsDetail(result.data, requestId))
    return { outcome: "error", message: "The request could not be read. Try again." };
  return { outcome: "ok", detail: result.data };
}

const AGENT_UNKNOWN =
  "We could not confirm that update. Showing the latest saved state before you do anything else.";

async function agentClaim(api, requestId) {
  const result = await api("POST", `/v1/agent/escalations/${requestId}/claim`);
  if (result.status === 401) return { outcome: "redirect" };
  if (result.status === 403) return agentFailed(result);
  if (!result.sent) return { outcome: "error", message: agentDescribe(result) };
  if (result.ok) {
    return agentIsSummary(result.data) && result.data.request_id === requestId &&
      result.data.state === "assigned"
      ? { outcome: "claimed", summary: result.data }
      : { outcome: "unknown", message: AGENT_UNKNOWN };
  }
  if (result.status === 409)
    return {
      outcome: "lost",
      message: "Another agent has already taken this request, or it changed. The queue was refreshed.",
    };
  if (result.status === 404)
    return { outcome: "gone", message: "This request is no longer available." };
  if (result.status === 400) return { outcome: "error", message: agentDescribe(result) };
  return { outcome: "unknown", message: AGENT_UNKNOWN };
}

/* Trim, normalize and bound text the same way the server will. */
function agentText(value, limit, label) {
  const text = String(value ?? "").normalize("NFC").trim();
  if (!text) return { error: `Write the ${label} first.` };
  if ([...text].length > limit)
    return { error: `Use ${limit.toLocaleString("en-US")} characters or fewer for the ${label}.` };
  if (AGENT_CONTROL_CHARACTERS.test(text))
    return { error: "Please remove special control characters from your text." };
  return { text };
}

/* Move a request the agent owns. The version is the one the agent last saw. */
async function agentTransition(api, detail, target, text) {
  const body = { to_state: target, expected_version: detail.version };
  const field = AGENT_FIELDS[target];
  if (field) body[field[0]] = text;
  const result = await api("POST", `/v1/agent/escalations/${detail.request_id}/transition`, body);
  if (result.status === 401) return { outcome: "redirect" };
  if (result.status === 403) return agentFailed(result);
  if (!result.sent) return { outcome: "error", message: agentDescribe(result) };
  if (result.ok) {
    return agentIsSummary(result.data) &&
      result.data.request_id === detail.request_id &&
      result.data.state === target &&
      result.data.version > detail.version
      ? { outcome: "done", summary: result.data }
      : { outcome: "unknown", message: AGENT_UNKNOWN };
  }
  if (result.status === 409)
    return {
      outcome: "changed",
      message: "This request changed since you loaded it. Showing the latest version.",
    };
  if (result.status === 404)
    return {
      outcome: "gone",
      message: "This request was not found or is no longer assigned to you.",
    };
  if (result.status === 400) return { outcome: "invalid", message: agentDescribe(result) };
  return { outcome: "unknown", message: AGENT_UNKNOWN };
}

/*
 * After an UNKNOWN outcome only: is there evidence this exact update was saved? A matching
 * state and newer version alone prove nothing (another tab may have got there first). Updates
 * that carry text are proven by the saved message with that text at the next version.
 * Updates without text (start, resume, release) can never be proven, so they are not claimed.
 */
function agentProvenSaved(before, target, text, after) {
  const field = AGENT_FIELDS[target];
  if (!field || target === "queued") return false;
  if (after.state !== target || after.version !== before.version + 1) return false;
  return after.messages.some(
    (m) => m.kind === field[0] && m.content === text && m.version === before.version + 1,
  );
}

/* Which controls the owner may use in each state. */
function agentActionsFor(state) {
  return {
    assigned: ["start", "release"],
    in_review: ["ask", "resolve", "release"],
    waiting_for_customer: ["resume", "release"],
  }[state] ?? [];
}

/* ---------- page ---------- */

function initAgentFlow() {
  const root = document.querySelector("#agent");
  if (!root) return;
  const $ = (id) => document.querySelector(`#${id}`);
  const queueView = $("agent-queue-view");
  const detailView = $("agent-detail-view");
  const list = $("agent-list");
  const empty = $("agent-empty");
  const more = $("agent-more");
  const filter = $("agent-filter");
  const refresh = $("agent-refresh");
  const retryQueue = $("agent-retry");
  const status = $("agent-status");
  const back = $("agent-back");
  const reload = $("agent-reload");
  const boxes = {
    start: $("agent-start-box"),
    ask: $("agent-ask-box"),
    resume: $("agent-resume-box"),
    resolve: $("agent-resolve-box"),
    release: $("agent-release-box"),
  };
  const buttons = {
    start: $("agent-start"),
    ask: $("agent-ask-send"),
    resume: $("agent-resume"),
    resolve: $("agent-resolve-send"),
    release: $("agent-release-send"),
  };
  const inputs = {
    ask: $("agent-ask"),
    resolve: $("agent-resolution"),
    release: $("agent-release-reason"),
  };
  const ui = {
    items: [],
    nextCursor: null,
    listFilter: "",
    loading: false,
    paging: false,
    detail: null,
    draftOwner: null,
    busy: false,
    locked: false,
    token: 0,
  };

  function say(text, good = false) {
    status.textContent = text;
    status.className = good ? "ok" : "";
  }
  function show(view) {
    queueView.hidden = view !== "queue";
    detailView.hidden = view !== "detail";
  }
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function endSession() {
    say(AGENT_SESSION_ENDED);
    window.location.assign("/");
  }
  function applyLock() {
    const disabled = ui.busy || ui.locked;
    Object.values(buttons).forEach((b) => (b.disabled = disabled));
    Object.values(inputs).forEach((i) => (i.disabled = disabled));
    back.disabled = ui.busy;
    reload.hidden = !ui.locked;
    reload.disabled = ui.busy;
  }

  /* Unsent text belongs to one request: never carry it to another. */
  function clearDrafts() {
    Object.values(inputs).forEach((i) => (i.value = ""));
    ui.draftOwner = null;
  }

  /* ----- queue ----- */
  function renderQueue() {
    const rows = ui.items.map((item) => {
      const row = el("li", "agent-row");
      const head = el("p", "agent-row-head", `Ref ${item.request_id.slice(0, 8)} · ${AGENT_STATE_LABELS[item.state]}`);
      const preview = [...item.content].slice(0, 200).join("");
      const text = el("p", "agent-row-text", preview + (item.content.length > 200 ? "…" : ""));
      const action = el(
        "button",
        item.state === "queued" ? "" : "secondary",
        item.state === "queued" ? "Claim" : "Open",
      );
      action.setAttribute("type", "button");
      action.addEventListener("click", () =>
        item.state === "queued" ? claim(item.request_id) : openDetail(item.request_id),
      );
      row.append(head, text, action);
      return row;
    });
    list.replaceChildren(...rows);
    empty.hidden = rows.length > 0 || ui.loading;
    more.hidden = !ui.nextCursor || ui.loading;
    more.disabled = ui.paging;
  }

  async function loadQueue({ append = false, keepMessage = false } = {}) {
    // A cursor only belongs to the filter that produced it.
    if (append && (!ui.nextCursor || filter.value !== ui.listFilter || ui.paging || ui.loading))
      return;
    const token = ++ui.token;
    retryQueue.hidden = true;
    if (append) {
      ui.paging = true;
    } else {
      ui.loading = true;
      ui.paging = false;
      ui.nextCursor = null;
      ui.items = [];
    }
    renderQueue();
    if (!keepMessage) say("Loading the queue…");
    const requested = filter.value;
    const result = await agentLoadQueue(agentApi, {
      state: requested,
      cursor: append ? ui.nextCursor : "",
    });
    if (token !== ui.token) return; // a newer load replaced this one
    ui.loading = false;
    ui.paging = false;
    if (result.outcome === "redirect") return endSession();
    if (result.outcome !== "ok") {
      say(result.message);
      retryQueue.hidden = result.outcome === "forbidden";
      renderQueue();
      return;
    }
    ui.listFilter = requested;
    ui.items = append ? ui.items.concat(result.items) : result.items;
    ui.nextCursor = result.nextCursor;
    renderQueue();
    if (!keepMessage) say("");
  }

  /* ----- detail ----- */
  function renderDetail() {
    const d = ui.detail;
    $("agent-detail-title").textContent = `Request ${d.request_id.slice(0, 8)}`;
    $("agent-detail-state").textContent = `${AGENT_STATE_LABELS[d.state]} · version ${d.version}`;
    $("agent-content").textContent = d.content;
    $("agent-note").textContent = d.note || "No additional note.";
    const messages = d.messages.map((m) => {
      const item = el("li", `agent-message ${m.kind === "resolution_note" ? "internal" : m.kind}`);
      item.append(el("strong", "", AGENT_MESSAGE_LABELS[m.kind]), el("p", "", m.content));
      return item;
    });
    $("agent-messages").replaceChildren(...messages);
    $("agent-no-messages").hidden = messages.length > 0;
    const allowed = agentActionsFor(d.state);
    Object.entries(boxes).forEach(([name, box]) => (box.hidden = !allowed.includes(name)));
    $("agent-resolved-box").hidden = d.state !== "resolved";
    applyLock();
  }

  async function openDetail(requestId, { keepMessage = false } = {}) {
    ui.busy = true;
    applyLock();
    if (!keepMessage) say("Loading the request…");
    const result = await agentLoadDetail(agentApi, requestId);
    ui.busy = false;
    if (result.outcome === "redirect") return endSession();
    if (result.outcome === "ok") {
      if (ui.draftOwner !== requestId) clearDrafts();
      ui.draftOwner = requestId;
      ui.detail = result.detail;
      ui.locked = false;
      show("detail");
      renderDetail();
      if (!keepMessage) say("");
      return true;
    }
    if (result.outcome === "gone") {
      ui.detail = null;
      ui.locked = false;
      if (ui.draftOwner === requestId) clearDrafts();
      show("queue");
      say(result.message);
      loadQueue({ keepMessage: true });
      return false;
    }
    // The latest state could not be read: keep every action locked until it can.
    if (ui.detail) {
      ui.locked = true;
      show("detail");
      renderDetail();
    }
    say(`${result.message} Actions stay locked until the request reloads.`);
    return false;
  }

  async function claim(requestId) {
    if (ui.busy) return;
    ui.busy = true;
    say("Claiming…");
    const result = await agentClaim(agentApi, requestId);
    ui.busy = false;
    if (result.outcome === "redirect") return endSession();
    if (result.outcome === "claimed") {
      ui.detail = null;
      if (await openDetail(requestId, { keepMessage: true })) say("You claimed this request.", true);
      else await loadQueue({ keepMessage: true });
      return;
    }
    if (result.outcome === "forbidden" || result.outcome === "error") {
      say(result.message);
      return;
    }
    // Lost the race, gone, or unknown: always reload the queue before acting again.
    say(result.message);
    await loadQueue({ keepMessage: true });
  }

  async function act(name) {
    if (ui.busy || ui.locked || !ui.detail) return;
    const before = ui.detail;
    const target = { start: "in_review", resume: "in_review", ask: "waiting_for_customer", resolve: "resolved", release: "queued" }[name];
    let text;
    if (AGENT_FIELDS[target]) {
      const [, limit] = AGENT_FIELDS[target];
      const label = { ask: "message to the customer", resolve: "resolution note", release: "release reason" }[name];
      const checked = agentText(inputs[name].value, limit, label);
      if (checked.error) {
        say(checked.error);
        return;
      }
      text = checked.text;
    }
    ui.busy = true;
    applyLock();
    say("Saving…");
    const result = await agentTransition(agentApi, before, target, text);
    ui.busy = false;
    if (result.outcome === "redirect") return endSession();
    if (result.outcome === "invalid" || result.outcome === "error" || result.outcome === "forbidden") {
      applyLock();
      say(result.message);
      return;
    }
    if (result.outcome === "gone") {
      ui.detail = null;
      clearDrafts();
      show("queue");
      say(result.message);
      await loadQueue({ keepMessage: true });
      return;
    }
    if (result.outcome === "done" && target === "queued") {
      clearDrafts();
      ui.detail = null;
      show("queue");
      say("Released to the queue.", true);
      await loadQueue({ keepMessage: true });
      return;
    }
    // Done, changed or unknown: reload the saved request before any further action.
    const reloaded = await agentLoadDetail(agentApi, before.request_id);
    if (reloaded.outcome === "redirect") return endSession();
    if (reloaded.outcome === "gone") {
      ui.detail = null;
      clearDrafts();
      show("queue");
      say(reloaded.message);
      await loadQueue({ keepMessage: true });
      return;
    }
    if (reloaded.outcome !== "ok") {
      ui.locked = true;
      renderDetail();
      say(`${AGENT_UNKNOWN} The latest state could not be loaded, so actions stay locked. Choose Reload.`);
      return;
    }
    ui.detail = reloaded.detail;
    ui.locked = false;
    renderDetail();
    if (result.outcome === "done") {
      if (inputs[name]) inputs[name].value = "";
      say("Saved.", true);
    } else if (result.outcome === "changed") {
      // A definite rejection is never reported as saved, even if the state now matches.
      if (agentActionsFor(reloaded.detail.state).includes(name))
        say(`${result.message} Your text is still here if you want to try again.`);
      else
        say(`${result.message} Your update was not sent, and this request is now ${AGENT_STATE_LABELS[reloaded.detail.state].toLowerCase()}.`);
    } else if (agentProvenSaved(before, target, text, reloaded.detail)) {
      if (inputs[name]) inputs[name].value = "";
      say("That update was saved. Showing the latest state.", true);
    } else if (reloaded.detail.version === before.version) {
      say("That update was not saved. Your text is still here; you can try again.");
    } else {
      say("The request changed and we could not tell whether your update was included. Review the latest state. Your text is still here.");
    }
  }

  root.hidden = false;
  show("queue");
  filter.addEventListener("change", () => {
    // Drop the old cursor and list at once; pagination stays off until the new list arrives.
    ui.nextCursor = null;
    ui.items = [];
    loadQueue();
  });
  refresh.addEventListener("click", () => loadQueue());
  retryQueue.addEventListener("click", () => loadQueue());
  more.addEventListener("click", () => loadQueue({ append: true }));
  back.addEventListener("click", () => {
    if (ui.busy) return;
    ui.detail = null;
    ui.locked = false;
    show("queue");
    say("");
    loadQueue();
  });
  reload.addEventListener("click", async () => {
    if (ui.busy || !ui.detail) return;
    const requestId = ui.detail.request_id;
    ui.locked = true;
    await openDetail(requestId);
  });
  Object.keys(buttons).forEach((name) => buttons[name].addEventListener("click", () => act(name)));
  loadQueue();
}

initAgentFlow();