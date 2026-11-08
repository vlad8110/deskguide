/* Customer support-request flow (C4): review, confirm, retry and status recovery. */

"use strict";

const SUPPORT_CONTROL_CHARACTERS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/;

async function supportReadJson(response) {
  try {
    return await response.json();
  } catch {
    // Proxies may return an HTML error page instead of the application's JSON.
    return null;
  }
}

function supportNormalize(response, data) {
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
  };
}

function supportFailure(network) {
  return {
    ok: false,
    status: 0,
    data: {},
    code: null,
    message: null,
    retryAfter: null,
    network,
  };
}

/* One same-origin call. State-changing calls fetch the session CSRF token first. */
async function apiRequest(method, path, body) {
  try {
    const headers = {};
    let payload;
    if (method !== "GET") {
      const tokenResponse = await fetch("/v1/session", { credentials: "same-origin" });
      const tokenData = await supportReadJson(tokenResponse);
      if (!tokenResponse.ok) return supportNormalize(tokenResponse, tokenData);
      if (typeof tokenData?.csrf_token !== "string" || !tokenData.csrf_token)
        return supportFailure(false);
      headers["Content-Type"] = "application/json";
      headers["X-CSRF-Token"] = tokenData.csrf_token;
      payload = JSON.stringify(body ?? {});
    }
    const response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers,
      body: payload,
    });
    return supportNormalize(response, await supportReadJson(response));
  } catch (error) {
    return supportFailure(error instanceof TypeError);
  }
}

function describeFailure(result) {
  if (result.network) return "Connection unavailable. Your text is still here; try again.";
  if (result.message) {
    return result.status === 429 && result.retryAfter
      ? `${result.message} Try again in about ${result.retryAfter} seconds.`
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

function supportSaved(result) {
  const text = result.data.acknowledgement;
  return {
    outcome: "saved",
    requestId: result.data.request_id ?? null,
    message: typeof text === "string" && text ? text : "Your request has been saved.",
  };
}

/* After an uncertain save, ask the server what happened. Never invent a new ID. */
async function checkSupportStatus(state, api) {
  const status = await api("GET", `/v1/escalations/${state.submissionId}`);
  if (status.status === 401) return { outcome: "redirect" };
  if (status.ok && status.data.saved === true) {
    state.submissionId = null;
    state.uncertain = false;
    return supportSaved({ data: { request_id: status.data.request_id } });
  }
  if (status.ok && status.data.registration_state === "expired") {
    state.submissionId = null;
    state.uncertain = false;
    return {
      outcome: "edit",
      message: "This form timed out before it was sent. Your text is still here.",
    };
  }
  if (status.ok) {
    state.uncertain = false;
    return { outcome: "retry", message: "It was not saved. Send it again to retry." };
  }
  return {
    outcome: "retry",
    message: "We could not confirm whether this was saved. Try again to check.",
  };
}

/*
 * state = { payload, submissionId, uncertain }. The ID is registered only when the
 * customer confirms, then kept for every retry. Outcomes: saved, retry, edit,
 * stop or redirect.
 */
async function sendSupport(state, api = apiRequest) {
  if (!state.submissionId) {
    const registered = await api("POST", "/v1/escalations/submission-ids", {
      operation: "escalation",
    });
    if (registered.status === 401) return { outcome: "redirect" };
    if (!registered.ok || typeof registered.data.submission_id !== "string")
      return { outcome: "retry", message: describeFailure(registered) };
    state.submissionId = registered.data.submission_id;
  }
  const result = await api("POST", "/v1/escalations", {
    submission_id: state.submissionId,
    ...state.payload,
  });
  if (result.status === 401) return { outcome: "redirect" };
  if (result.ok) {
    state.submissionId = null;
    state.uncertain = false;
    return supportSaved(result);
  }
  if (result.code === "SAVE_OUTCOME_UNCERTAIN") {
    state.uncertain = true;
    return checkSupportStatus(state, api);
  }
  if (result.code === "SUBMISSION_ID_EXPIRED" || result.status === 404) {
    state.submissionId = null;
    state.uncertain = false;
    return { outcome: "edit", message: describeFailure(result) };
  }
  if (result.status === 400) return { outcome: "edit", message: describeFailure(result) };
  if (result.code === "CONFLICT") return { outcome: "stop", message: describeFailure(result) };
  return { outcome: "retry", message: describeFailure(result) };
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
  const state = { payload: null, submissionId: null, uncertain: false };

  function say(text, good = false) {
    status.textContent = text;
    status.className = good ? "ok" : "";
  }
  function show(step) {
    form.hidden = step !== "form";
    review.hidden = step !== "review";
    done.hidden = step !== "done";
  }

  root.hidden = false;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const built = buildSupportPayload(content.value, note.value);
    if (built.error) {
      say(built.error);
      return;
    }
    state.payload = built.payload;
    document.querySelector("#support-preview-content").textContent = built.payload.content;
    document.querySelector("#support-preview-note").textContent =
      built.payload.note ?? "No additional note.";
    say("");
    show("review");
  });
  edit.addEventListener("click", () => {
    if (state.uncertain) return;
    say("");
    show("form");
  });
  send.addEventListener("click", async () => {
    if (!consent.checked) {
      say("Please confirm that you agree to share this with support.");
      return;
    }
    state.payload = { ...state.payload, consent_to_share: true };
    send.disabled = edit.disabled = true;
    say("Please wait…");
    const result = await sendSupport(state);
    send.disabled = false;
    edit.disabled = state.uncertain;
    if (result.outcome === "redirect") {
      window.location.assign("/");
    } else if (result.outcome === "saved") {
      document.querySelector("#support-saved").textContent = result.message;
      form.reset();
      consent.checked = false;
      show("done");
      say("", true);
    } else if (result.outcome === "edit") {
      show("form");
      say(result.message);
    } else if (result.outcome === "stop") {
      send.disabled = true;
      say(result.message);
    } else {
      send.textContent = "Try again";
      say(result.message);
    }
  });
  another.addEventListener("click", () => {
    send.textContent = "Send to support";
    say("");
    show("form");
  });
}

initSupportFlow();
