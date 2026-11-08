/* Customer support-request flow (C4): review, confirm, retry and status recovery. */

"use strict";

const SUPPORT_CONTROL_CHARACTERS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/;
const SUPPORT_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SUPPORT_SAVED_TEXT = "Your request has been saved.";
// Codes the server only returns when it knows nothing was saved.
const SUPPORT_RETRYABLE_CODES = [
  "RATE_LIMITED",
  "SERVICE_BUSY",
  "DEPENDENCY_UNAVAILABLE",
  "CSRF_FAILED",
  "FORBIDDEN",
];

async function supportReadJson(response) {
  try {
    return await response.json();
  } catch {
    // Proxies may return an HTML error page instead of the application's JSON.
    return null;
  }
}

function supportNormalize(response, data, sent) {
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

function supportFailure(network, sent) {
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
async function apiRequest(method, path, body) {
  let sent = false;
  try {
    const headers = {};
    let payload;
    if (method !== "GET") {
      const tokenResponse = await fetch("/v1/session", { credentials: "same-origin" });
      const tokenData = await supportReadJson(tokenResponse);
      if (!tokenResponse.ok) return supportNormalize(tokenResponse, tokenData, false);
      if (typeof tokenData?.csrf_token !== "string" || !tokenData.csrf_token)
        return supportFailure(false, false);
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
    return supportNormalize(response, await supportReadJson(response), true);
  } catch (error) {
    return supportFailure(error instanceof TypeError, sent);
  }
}

function formatWait(seconds) {
  if (seconds < 90) return `about ${seconds} seconds`;
  if (seconds < 5400) return `about ${Math.ceil(seconds / 60)} minutes`;
  const hours = Math.ceil(seconds / 3600);
  return `about ${hours} ${hours === 1 ? "hour" : "hours"}`;
}

function describeFailure(result) {
  if (result.network) return "Connection unavailable. Your text is still here; try again.";
  if (result.message) {
    return result.status === 429 && result.retryAfter
      ? `${result.message} Try again in ${formatWait(result.retryAfter)}.`
      : result.message;
  }
  return result.status >= 500 || result.status === 0
    ? "Service temporarily unavailable. Try again."
    : "The request could not be completed. Please try again.";
}

/* Validate and canonicalize what the customer typed (the server stores NFC, trimmed). */
function buildSupportPayload(contentText, noteText) {
  const content = String(contentText ?? "").normalize("NFC").trim();
  const note = String(noteText ?? "").normalize("NFC").trim();
  if (!content) return { error: "Describe what you need help with." };
  if ([...content].length > 1000)
    return { error: "Please use 1,000 characters or fewer for the description." };
  if ([...note].length > 2000)
    return { error: "Please use 2,000 characters or fewer for the note." };
  if (SUPPORT_CONTROL_CHARACTERS.test(content + note))
    return { error: "Please remove special control characters from your text." };
  const payload = { reason: "human_requested", content };
  if (note) payload.note = note;
  return { payload };
}

/* A success status alone never proves a save: require the fields the contract promises. */
function validSaveResponse(result, submissionId) {
  const data = result.data;
  return (
    (result.status === 200 || result.status === 201) &&
    typeof data.request_id === "string" &&
    SUPPORT_UUID.test(data.request_id) &&
    data.submission_id === submissionId &&
    typeof data.state === "string" &&
    typeof data.created_at === "string"
  );
}

function validStatusResponse(result, submissionId) {
  const data = result.data;
  if (!result.ok || data.submission_id !== submissionId) return false;
  if (data.operation !== "escalation" || typeof data.saved !== "boolean") return false;
  if (!["unused", "completed", "expired"].includes(data.registration_state)) return false;
  if (data.saved)
    return (
      data.registration_state === "completed" &&
      typeof data.request_id === "string" &&
      SUPPORT_UUID.test(data.request_id)
    );
  return data.registration_state !== "completed";
}

function validRegistration(result) {
  const data = result.data;
  return (
    result.status === 201 &&
    typeof data.submission_id === "string" &&
    SUPPORT_UUID.test(data.submission_id) &&
    data.operation === "escalation" &&
    data.registration_state === "unused"
  );
}

function supportSaved(state, requestId, acknowledgement) {
  state.submissionId = null;
  state.unresolved = false;
  return {
    outcome: "saved",
    requestId,
    message:
      typeof acknowledgement === "string" && acknowledgement
        ? acknowledgement
        : SUPPORT_SAVED_TEXT,
  };
}

const SUPPORT_UNRESOLVED_MESSAGE =
  "We could not confirm whether this was saved. Your text is locked until it is checked. Choose Check status.";

/* Ask the server what happened to this ID. Never invents a new ID. */
async function recoverSupport(state, api) {
  const status = await api("GET", `/v1/escalations/${state.submissionId}`);
  if (status.status === 401) return { outcome: "redirect" };
  if (validStatusResponse(status, state.submissionId)) {
    if (status.data.saved) return supportSaved(state, status.data.request_id);
    state.unresolved = false;
    if (status.data.registration_state === "expired") {
      state.submissionId = null;
      return {
        outcome: "edit",
        message: "This form timed out before it was sent. Your text is still here.",
      };
    }
    return { outcome: "retry", message: "It was not saved. Send it again to retry." };
  }
  if (status.status === 404 && status.code === "NOT_FOUND") {
    state.submissionId = null;
    state.unresolved = false;
    return {
      outcome: "edit",
      message: "We could not find this submission. Your text is still here; review and send it again.",
    };
  }
  // Failed, malformed or contradictory status: stay locked on the original ID/payload.
  state.unresolved = true;
  return { outcome: "unresolved", message: SUPPORT_UNRESOLVED_MESSAGE };
}

/* A completed ID was resent with different text: show what was already saved first. */
async function resolveConflict(state, api) {
  const status = await api("GET", `/v1/escalations/${state.submissionId}`);
  if (status.status === 401) return { outcome: "redirect" };
  if (validStatusResponse(status, state.submissionId) && status.data.saved) {
    state.submissionId = null;
    state.unresolved = false;
    return {
      outcome: "conflict",
      requestId: status.data.request_id,
      message:
        "Your original request was already saved. The changed text was not sent. Start a new request to send it.",
    };
  }
  state.unresolved = true;
  return { outcome: "unresolved", message: SUPPORT_UNRESOLVED_MESSAGE };
}

/*
 * state = { payload, submissionId, unresolved }. The ID is registered only when the
 * customer confirms, then kept for every retry. Outcomes: saved, conflict, retry,
 * edit, unresolved or redirect. After any send that might have reached the server,
 * `unresolved` stays true until the status endpoint gives a valid answer.
 */
async function sendSupport(state, api = apiRequest) {
  if (state.unresolved) return recoverSupport(state, api);
  if (!state.submissionId) {
    const registered = await api("POST", "/v1/escalations/submission-ids", {
      operation: "escalation",
    });
    if (registered.status === 401) return { outcome: "redirect" };
    if (!validRegistration(registered))
      return { outcome: "retry", message: describeFailure(registered) };
    state.submissionId = registered.data.submission_id;
  }
  const result = await api("POST", "/v1/escalations", {
    submission_id: state.submissionId,
    ...state.payload,
  });
  if (result.status === 401) return { outcome: "redirect" };
  if (!result.sent) return { outcome: "retry", message: describeFailure(result) };
  if (result.ok && validSaveResponse(result, state.submissionId))
    return supportSaved(state, result.data.request_id, result.data.acknowledgement);
  if (!result.ok) {
    if (result.status === 409 && result.code === "CONFLICT")
      return resolveConflict(state, api);
    if (result.code === "SUBMISSION_ID_EXPIRED" || (result.status === 404 && result.code)) {
      state.submissionId = null;
      return { outcome: "edit", message: describeFailure(result) };
    }
    if (result.status === 400 && result.code)
      return { outcome: "edit", message: describeFailure(result) };
    if (SUPPORT_RETRYABLE_CODES.includes(result.code))
      return { outcome: "retry", message: describeFailure(result) };
  }
  // Network drop, proxy page, uncertain commit or malformed success: outcome unknown.
  state.unresolved = true;
  return recoverSupport(state, api);
}

function initSupportFlow() {
  const root = document.querySelector("#support");
  if (!root) return;
  const form = document.querySelector("#support-form");
  const review = document.querySelector("#support-review");
  const done = document.querySelector("#support-done");
  const status = document.querySelector("#support-status");
  const content = document.querySelector("#support-content");
  const note = document.querySelector("#support-note");
  const consent = document.querySelector("#support-consent");
  const edit = document.querySelector("#support-edit");
  const send = document.querySelector("#support-send");
  const another = document.querySelector("#support-another");
  const state = { payload: null, submissionId: null, unresolved: false };
  let busy = false;

  function say(text, good = false) {
    status.textContent = text;
    status.className = good ? "ok" : "";
  }
  function show(step) {
    form.hidden = step !== "form";
    review.hidden = step !== "review";
    done.hidden = step !== "done";
  }
  function resetSendButton() {
    send.textContent = "Send to support";
  }
  function showDone(text, requestId, buttonLabel) {
    const reference = requestId ? ` Reference: ${requestId.slice(0, 8)}.` : "";
    document.querySelector("#support-saved").textContent = text + reference;
    another.textContent = buttonLabel;
    show("done");
  }

  root.hidden = false;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (state.unresolved) return;
    const built = buildSupportPayload(content.value, note.value);
    if (built.error) {
      say(built.error);
      return;
    }
    state.payload = built.payload;
    document.querySelector("#support-preview-content").textContent = built.payload.content;
    document.querySelector("#support-preview-note").textContent =
      built.payload.note ?? "No additional note.";
    consent.checked = false; // fresh consent for the wording being reviewed
    resetSendButton();
    say("");
    show("review");
  });
  edit.addEventListener("click", () => {
    if (state.unresolved || busy) return;
    consent.checked = false;
    resetSendButton();
    say("");
    show("form");
  });
  send.addEventListener("click", async () => {
    if (busy) return;
    if (!state.unresolved) {
      if (!consent.checked) {
        say("Please confirm that you agree to share this with support.");
        return;
      }
      state.payload = { ...state.payload, consent_to_share: true };
    }
    busy = true;
    send.disabled = edit.disabled = true;
    say("Please wait…");
    let result;
    try {
      result = await sendSupport(state);
    } finally {
      busy = false;
      send.disabled = false;
      edit.disabled = state.unresolved;
    }
    if (result.outcome === "redirect") {
      window.location.assign("/");
    } else if (result.outcome === "saved") {
      content.value = "";
      note.value = "";
      consent.checked = false;
      resetSendButton();
      showDone(result.message, result.requestId, "Send another request");
      say("", true);
    } else if (result.outcome === "conflict") {
      consent.checked = false;
      resetSendButton();
      showDone(result.message, result.requestId, "Start new request");
      say("");
    } else if (result.outcome === "edit") {
      consent.checked = false;
      resetSendButton();
      show("form");
      say(result.message);
    } else if (result.outcome === "unresolved") {
      send.textContent = "Check status";
      say(result.message);
    } else {
      send.textContent = "Try again";
      say(result.message);
    }
  });
  another.addEventListener("click", () => {
    // A deliberate new request: the previous ID is already resolved as saved.
    state.payload = null;
    state.submissionId = null;
    state.unresolved = false;
    consent.checked = false;
    resetSendButton();
    say("");
    show("form");
  });
}

initSupportFlow();