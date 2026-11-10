/*
 * Customer question screen (C1 ask, C2b source view, C6a feedback). Ask a question, read a
 * validated answer with its sources, or see why there is no answer. Feedback is always tied
 * to the customer's own inquiry, including when no answer was produced.
 * Self-contained: it shares no helpers with the other screens, so every global is prefixed `ask`.
 */

"use strict";

const ASK_STATUSES = [
  "answered",
  "clarification_requested",
  "escalation_offered",
  "temporarily_unavailable",
];
const ASK_ROUTES = ["ai", "account_status", "human_requested"];
const ASK_REASONS = [
  "insufficient_evidence",
  "human_requested",
  "validation_failed",
  "provider_failure",
  "service_unavailable",
  "action_required",
];
const ASK_ORIGINS = ["ai_generated", "account_status"];
const ASK_RATINGS = ["helpful", "not_helpful"];
// Which feedback categories the server accepts for each recorded outcome (C6a).
const ASK_ANSWERED_CATEGORIES = ["incorrect", "incomplete", "wrong_source", "unclear", "other"];
const ASK_UNANSWERED_CATEGORIES = [
  "too_much_escalation",
  "fallback_unhelpful",
  "unclear",
  "other",
];
const ASK_CATEGORY_LABELS = {
  incorrect: "The answer was wrong",
  incomplete: "The answer was incomplete",
  wrong_source: "The guide it cited was not the right one",
  unclear: "It was unclear",
  too_much_escalation: "I should have been given an answer",
  fallback_unhelpful: "The suggestion to contact support did not help",
  other: "Something else",
};
const ASK_HEADLINES = {
  answered: "Answer",
  clarification_requested: "We need a little more detail",
  escalation_offered: "We could not answer this",
  temporarily_unavailable: "DeskGuide is unavailable right now",
};
const ASK_REASON_TEXT = {
  insufficient_evidence:
    "We could not find a supported answer to this in the DeskGuide guides. A support agent may be able to help.",
  validation_failed:
    "We could not confirm an answer we were confident in, so we are not showing one. A support agent may be able to help.",
  provider_failure:
    "DeskGuide could not prepare an answer right now. Your question is still here: you can ask again, or contact support.",
  service_unavailable:
    "DeskGuide could not look this up right now. That does not mean there is no answer. Ask again, or contact support.",
  human_requested: "You asked to talk to a person. You can contact support below.",
  action_required: "This needs action from support. You can contact support below.",
};
const ASK_DEFAULT_TEXT = "We could not answer this question. A support agent may be able to help.";
const ASK_CLARIFICATION_DEFAULT = "Please add more detail to your question and ask again.";
const ASK_INVALID_MESSAGE =
  "We received a reply we could not verify, so we are not showing it. Your question is still here; try again or contact support.";
const ASK_UNKNOWN_FEEDBACK =
  "We could not confirm that your feedback was saved. Your original feedback is locked while its outcome is uncertain. Send it again to retry; it will not be counted twice.";
const ASK_TIMEOUT_MS = 30000;

// Multi-line text may keep line breaks and tabs; single-line text may not.
const ASK_CONTROL_MULTILINE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/;
const ASK_CONTROL_SINGLE = /[\u0000-\u001F\u007F-\u009F]/;
const ASK_LONE_SURROGATE = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/;
const ASK_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

const askCount = (text) => [...text].length;
const askValidUuid = (value) => typeof value === "string" && ASK_UUID.test(value);
const askBadText = (text, multiline) =>
  (multiline ? ASK_CONTROL_MULTILINE : ASK_CONTROL_SINGLE).test(text) ||
  ASK_LONE_SURROGATE.test(text);

async function askReadJson(response) {
  try {
    return await response.json();
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    // Proxies may return an HTML error page instead of the application's JSON.
    return null;
  }
}

function askNormalize(response, data, sent) {
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

function askFailure(network, sent) {
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
 * One same-origin call. State-changing calls fetch the session CSRF token first. `sent` is
 * true once the real request has left the browser. A call that takes longer than
 * ASK_TIMEOUT_MS is abandoned so the screen never stays locked.
 */
async function askApi(method, path, body) {
  let sent = false;
  let timer = null;
  try {
    const controller = typeof AbortController === "function" ? new AbortController() : null;
    if (controller && typeof setTimeout === "function")
      timer = setTimeout(() => controller.abort(), ASK_TIMEOUT_MS);
    const signal = controller?.signal;
    const headers = {};
    let payload;
    if (method !== "GET") {
      const tokenResponse = await fetch("/v1/session", { credentials: "same-origin", signal });
      const tokenData = await askReadJson(tokenResponse);
      if (!tokenResponse.ok) return askNormalize(tokenResponse, tokenData, false);
      if (typeof tokenData?.csrf_token !== "string" || !tokenData.csrf_token)
        return askFailure(false, false);
      headers["Content-Type"] = "application/json";
      headers["X-CSRF-Token"] = tokenData.csrf_token;
      payload = JSON.stringify(body ?? {});
    }
    const options = { method, credentials: "same-origin", headers, body: payload, signal };
    sent = true;
    const response = await fetch(path, options);
    return askNormalize(response, await askReadJson(response), true);
  } catch (error) {
    // An aborted call is reported like a dropped connection.
    return askFailure(true, sent);
  } finally {
    if (timer !== null) clearTimeout(timer);
  }
}

function askFormatWait(seconds) {
  if (seconds < 90) return `about ${seconds} seconds`;
  if (seconds < 5400) return `about ${Math.ceil(seconds / 60)} minutes`;
  const hours = Math.ceil(seconds / 3600);
  return `about ${hours} ${hours === 1 ? "hour" : "hours"}`;
}

function askDescribeFailure(result, kept) {
  if (result.network) return `Connection unavailable. ${kept}Try again.`;
  if (result.message) {
    return result.retryAfter && (result.status === 429 || result.status === 503)
      ? `${result.message} Try again in ${askFormatWait(result.retryAfter)}.`
      : result.message;
  }
  return result.status >= 500 || result.status === 0
    ? `DeskGuide is unavailable right now. ${kept}Try again.`
    : `That could not be completed. ${kept}Try again.`;
}

/* ---------- question ---------- */

/*
 * What the server stores: trimmed, NFC, 1-1,000 characters, no control characters. The server
 * rejects line breaks, so they become spaces here rather than failing the request.
 */
function askBuildQuestion(raw) {
  const question = String(raw ?? "")
    .replace(/[\r\n\t]+/g, " ")
    .normalize("NFC")
    .trim();
  if (!question) return { error: "Type your question." };
  if (askCount(question) > 1000) return { error: "Please use 1,000 characters or fewer." };
  if (askBadText(question, false))
    return { error: "Please remove special control characters from your question." };
  return { question };
}

function askValidSource(source) {
  if (!source || typeof source !== "object" || !source.ref || typeof source.ref !== "object")
    return null;
  const { source_id: sourceId, section_id: sectionId, source_version: version } = source.ref;
  const identifiers = [sourceId, sectionId, version];
  const labels = [source.title, source.section_title];
  const wellFormed = (value) =>
    typeof value === "string" &&
    value.length >= 1 &&
    askCount(value) <= 200 &&
    !askBadText(value, false);
  if (!identifiers.every(wellFormed) || !labels.every(wellFormed)) return null;
  return {
    ref: { source_id: sourceId, section_id: sectionId, source_version: version },
    title: source.title,
    sectionTitle: source.section_title,
  };
}

/*
 * Accept an inquiry result only when every field is consistent with the contract. A result
 * that fails any check is never shown as an answer.
 */
function askValidInquiry(data) {
  if (!data || typeof data !== "object") return null;
  const { status } = data;
  if (!askValidUuid(data.inquiry_id)) return null;
  if (!ASK_STATUSES.includes(status) || !ASK_ROUTES.includes(data.route)) return null;
  const offered = status === "escalation_offered" || status === "temporarily_unavailable";
  if (data.escalation_offered !== offered) return null;
  if (data.suggested_reason !== null && !ASK_REASONS.includes(data.suggested_reason))
    return null;
  if (!Array.isArray(data.sources) || data.sources.length > 8) return null;

  const result = {
    inquiryId: data.inquiry_id,
    status,
    route: data.route,
    origin: null,
    answer: null,
    sources: [],
    prompt: null,
    reason: data.suggested_reason,
    offered,
  };

  if (status === "answered") {
    if (!ASK_ORIGINS.includes(data.answer_origin) || !askValidUuid(data.answer_id)) return null;
    if (
      typeof data.answer !== "string" ||
      !data.answer.trim() ||
      askCount(data.answer) > 4000 ||
      askBadText(data.answer, true)
    )
      return null;
    if ((data.answer_origin === "account_status") !== (data.route === "account_status"))
      return null;
    if (data.clarification_prompt !== null) return null;
    const sources = data.sources.map(askValidSource);
    if (sources.some((source) => source === null)) return null;
    const keys = new Set(
      sources.map((s) => `${s.ref.source_id}\u0000${s.ref.section_id}\u0000${s.ref.source_version}`),
    );
    if (keys.size !== sources.length) return null;
    // An AI answer without a citation is never shown; account-status answers have none.
    if (data.answer_origin === "ai_generated" && sources.length === 0) return null;
    if (data.answer_origin === "account_status" && sources.length > 0) return null;
    result.origin = data.answer_origin;
    result.answer = data.answer;
    result.sources = sources;
    return result;
  }

  if (data.answer !== null || data.answer_id !== null || data.answer_origin !== null) return null;
  if (data.sources.length > 0) return null;
  if (status === "clarification_requested") {
    const prompt = data.clarification_prompt;
    if (prompt !== null) {
      if (
        typeof prompt !== "string" ||
        !prompt.trim() ||
        askCount(prompt) > 1000 ||
        askBadText(prompt, true)
      )
        return null;
      result.prompt = prompt;
    }
  } else if (data.clarification_prompt !== null) {
    return null;
  }
  return result;
}

async function askSubmitQuestion(question, api = askApi) {
  const result = await api("POST", "/v1/inquiries", {
    requested_operation: "ask_question",
    question,
  });
  if (result.status === 401) return { outcome: "redirect" };
  if (result.status === 200) {
    const inquiry = askValidInquiry(result.data);
    return inquiry
      ? { outcome: "ok", inquiry }
      : { outcome: "invalid", message: ASK_INVALID_MESSAGE };
  }
  if (result.ok) return { outcome: "invalid", message: ASK_INVALID_MESSAGE };
  return {
    outcome: "error",
    message: askDescribeFailure(result, "Your question is still here. "),
  };
}

/* ---------- source view ---------- */

/* Built from the structured reference, never from a server-supplied address. */
function askSourceUrl(ref) {
  return (
    `/v1/sources/${encodeURIComponent(ref.source_id)}` +
    `/sections/${encodeURIComponent(ref.section_id)}` +
    `?version=${encodeURIComponent(ref.source_version)}`
  );
}

function askValidSection(data, ref) {
  if (!data || typeof data !== "object" || !data.ref || typeof data.ref !== "object")
    return null;
  if (
    data.ref.source_id !== ref.source_id ||
    data.ref.section_id !== ref.section_id ||
    data.ref.source_version !== ref.source_version
  )
    return null;
  const text = (value) => typeof value === "string" && value.trim().length > 0;
  if (!text(data.document_title) || !text(data.section_title) || !text(data.text)) return null;
  return {
    documentTitle: data.document_title,
    sectionTitle: data.section_title,
    text: data.text,
  };
}

async function askLoadSource(ref, api = askApi) {
  const result = await api("GET", askSourceUrl(ref));
  if (result.status === 401) return { outcome: "redirect" };
  // Missing, removed and no-longer-permitted sources look the same on purpose.
  if (result.status === 404)
    return { outcome: "gone", message: "This source is no longer available to you." };
  if (result.status === 200) {
    const section = askValidSection(result.data, ref);
    return section
      ? { outcome: "ok", section }
      : { outcome: "invalid", message: "We could not verify this source, so it is not shown." };
  }
  return { outcome: "error", message: askDescribeFailure(result, "") };
}

/* ---------- feedback ---------- */

function askCategoriesFor(status) {
  return status === "answered" ? ASK_ANSWERED_CATEGORIES : ASK_UNANSWERED_CATEGORIES;
}

/* Feedback needs the inquiry, a rating and optionally a category and comment (never an answer ID). */
function askBuildFeedback(inquiry, input) {
  if (!ASK_RATINGS.includes(input.rating))
    return { error: "Choose whether this was helpful." };
  const payload = { inquiry_id: inquiry.inquiryId, rating: input.rating };
  if (input.rating === "not_helpful" && input.category) {
    if (!askCategoriesFor(inquiry.status).includes(input.category))
      return { error: "Choose one of the listed reasons." };
    payload.category = input.category;
  }
  const comment = String(input.comment ?? "").normalize("NFC").trim();
  if (askCount(comment) > 500) return { error: "Please use 500 characters or fewer." };
  if (askBadText(comment, true))
    return { error: "Please remove special control characters from your comment." };
  if (comment) payload.comment = comment;
  return { payload };
}

/*
 * A duplicate answer (409) means the feedback already exists, so sending again after an
 * unknown outcome is always safe and never counts twice.
 */
async function askSendFeedback(payload, api = askApi) {
  const result = await api("POST", "/v1/feedback", payload);
  if (result.status === 401) return { outcome: "redirect" };
  if (!result.sent) return { outcome: "error", message: askDescribeFailure(result, "") };
  if (result.status === 201) {
    const data = result.data;
    return askValidUuid(data.feedback_id) && data.state === "pending_review"
      ? { outcome: "saved" }
      : { outcome: "unknown", message: ASK_UNKNOWN_FEEDBACK };
  }
  if (result.status === 409) return { outcome: "recorded" };
  if (result.status === 404)
    return { outcome: "unavailable", message: "Feedback is not available right now." };
  if (
    result.status === 400 ||
    result.status === 403 ||
    result.status === 429 ||
    result.code === "SERVICE_BUSY" ||
    result.code === "DEPENDENCY_UNAVAILABLE"
  )
    return { outcome: "error", message: askDescribeFailure(result, "") };
  return { outcome: "unknown", message: ASK_UNKNOWN_FEEDBACK };
}

/* ---------- page ---------- */

function initQuestionFlow() {
  const root = document.querySelector("#questions");
  if (!root) return;
  const $ = (name) => document.querySelector(`#ask-${name}`);
  const el = {
    form: $("form"),
    question: $("question"),
    submit: $("submit"),
    clear: $("clear"),
    result: $("result"),
    headline: $("headline"),
    answer: $("answer"),
    sourcesBox: $("sources-box"),
    sources: $("sources"),
    sourceView: $("source-view"),
    sourceTitle: $("source-title"),
    sourceText: $("source-text"),
    sourceClose: $("source-close"),
    notice: $("notice"),
    offer: $("offer"),
    contact: $("contact"),
    feedback: $("feedback"),
    feedbackForm: $("feedback-form"),
    rating: $("rating"),
    categoryBox: $("category-box"),
    category: $("category"),
    comment: $("comment"),
    feedbackSend: $("feedback-send"),
    feedbackStatus: $("feedback-status"),
    status: $("status"),
  };
  const ui = {
    busy: false,
    token: 0,
    inquiry: null,
    sourceToken: 0,
    asked: "", // the question exactly as it was sent
    feedbackBusy: false,
    feedbackDone: false,
    feedbackPending: null,
  };

  function say(text, tone = false) {
    el.status.textContent = text;
    el.status.className = tone === true ? "ok" : tone || "";
  }
  function sayFeedback(text, good = false) {
    el.feedbackStatus.textContent = text;
    el.feedbackStatus.className = good ? "ok" : "";
  }
  function endSession() {
    window.location.assign("/");
  }
  function refreshControls() {
    el.submit.disabled = ui.busy;
    el.clear.disabled = ui.busy;
    const frozen = ui.feedbackBusy || ui.feedbackDone || !!ui.feedbackPending;
    el.rating.disabled = frozen;
    el.category.disabled = frozen;
    el.comment.readOnly = frozen;
    el.feedbackSend.disabled = ui.feedbackBusy || ui.feedbackDone;
  }
  function closeSource() {
    ui.sourceToken += 1;
    el.sourceView.hidden = true;
    el.sourceTitle.textContent = "";
    el.sourceText.textContent = "";
  }
  function hideResult() {
    ui.inquiry = null;
    closeSource();
    el.result.hidden = true;
    el.answer.hidden = true;
    el.answer.textContent = "";
    el.sourcesBox.hidden = true;
    el.sources.replaceChildren();
    el.notice.hidden = true;
    el.notice.textContent = "";
    el.offer.hidden = true;
    el.feedback.hidden = true;
    sayFeedback("");
  }

  /* ----- sources ----- */
  function makeSourceRow(source) {
    const row = document.createElement("li");
    const open = document.createElement("button");
    open.type = "button";
    open.className = "secondary";
    open.textContent = `${source.title}: ${source.sectionTitle}`;
    open.setAttribute("aria-label", `Open source ${source.title}, ${source.sectionTitle}`);
    open.addEventListener("click", () => showSource(source));
    row.append(open);
    return row;
  }

  async function showSource(source) {
    const token = ++ui.sourceToken;
    el.sourceView.hidden = true;
    say("Opening the source…");
    const result = await askLoadSource(source.ref);
    if (token !== ui.sourceToken) return; // closed, replaced or a new question was asked
    if (result.outcome === "redirect") return endSession();
    if (result.outcome === "ok") {
      el.sourceTitle.textContent = `${result.section.documentTitle}: ${result.section.sectionTitle}`;
      el.sourceText.textContent = result.section.text;
      el.sourceView.hidden = false;
      say("");
    } else {
      say(result.message);
    }
  }

  /* ----- result ----- */
  function resetFeedback(inquiry) {
    ui.feedbackBusy = false;
    ui.feedbackDone = false;
    ui.feedbackPending = null;
    el.rating.value = "";
    el.comment.value = "";
    const options = [{ value: "", label: "Choose a reason (optional)" }].concat(
      askCategoriesFor(inquiry.status).map((value) => ({
        value,
        label: ASK_CATEGORY_LABELS[value],
      })),
    );
    el.category.replaceChildren(
      ...options.map((entry) => {
        const option = document.createElement("option");
        option.value = entry.value;
        option.textContent = entry.label;
        return option;
      }),
    );
    el.category.value = "";
    el.categoryBox.hidden = true;
    sayFeedback("");
    refreshControls();
  }

  function renderResult(inquiry) {
    ui.inquiry = inquiry;
    closeSource();
    el.headline.textContent = ASK_HEADLINES[inquiry.status];
    el.answer.hidden = inquiry.status !== "answered";
    el.answer.textContent = inquiry.answer ?? "";
    el.sourcesBox.hidden = inquiry.sources.length === 0;
    el.sources.replaceChildren(...inquiry.sources.map(makeSourceRow));
    if (inquiry.status === "answered") {
      el.notice.hidden = true;
      el.notice.textContent = "";
    } else {
      el.notice.hidden = false;
      el.notice.textContent =
        inquiry.status === "clarification_requested"
          ? (inquiry.prompt ?? ASK_CLARIFICATION_DEFAULT)
          : (ASK_REASON_TEXT[inquiry.reason] ?? ASK_DEFAULT_TEXT);
    }
    el.offer.hidden = !(inquiry.offered && document.querySelector("#support"));
    el.result.hidden = false;
    // Feedback is offered for every outcome, tied to this inquiry.
    el.feedback.hidden = false;
    resetFeedback(inquiry);
    // Announce the outcome without styling a normal "no answer" result like an error.
    say(ASK_HEADLINES[inquiry.status], inquiry.status === "answered" ? true : "info");
  }

  async function ask() {
    if (ui.busy) return;
    const built = askBuildQuestion(el.question.value);
    if (built.error) return say(built.error);
    const token = ++ui.token;
    hideResult();
    ui.asked = built.question;
    ui.busy = true;
    refreshControls();
    say("Looking in the guides…");
    let outcome;
    try {
      outcome = await askSubmitQuestion(built.question);
    } finally {
      ui.busy = false;
      refreshControls();
    }
    if (token !== ui.token) return;
    if (outcome.outcome === "redirect") return endSession();
    if (outcome.outcome === "ok") return renderResult(outcome.inquiry);
    say(outcome.message);
  }

  /* ----- hand off to support ----- */
  function contactSupport() {
    const section = document.querySelector("#support");
    if (!section) return;
    section.dispatchEvent(new CustomEvent("deskguide:support-open", {
      detail: { question: ui.asked },
    }));
  }

  /* ----- feedback ----- */
  async function sendFeedback() {
    if (!ui.inquiry || ui.feedbackBusy || ui.feedbackDone) return;
    const inquiry = ui.inquiry;
    const built = ui.feedbackPending
      ? { payload: ui.feedbackPending }
      : askBuildFeedback(inquiry, {
          rating: el.rating.value,
          category: el.category.value,
          comment: el.comment.value,
        });
    if (built.error) return sayFeedback(built.error);
    // Retries must use exactly the first uncertain submission, not newly edited text.
    const payload = built.payload;
    el.rating.value = payload.rating;
    el.category.value = payload.category ?? "";
    el.comment.value = payload.comment ?? "";
    el.categoryBox.hidden = payload.rating !== "not_helpful";
    ui.feedbackBusy = true;
    refreshControls();
    sayFeedback("Sending your feedback…");
    let outcome;
    try {
      outcome = await askSendFeedback(payload);
    } finally {
      if (ui.inquiry === inquiry) ui.feedbackBusy = false;
    }
    // A late answer for an earlier question never touches the current one.
    if (ui.inquiry?.inquiryId !== inquiry.inquiryId) return;
    if (outcome.outcome === "redirect") return endSession();
    if (outcome.outcome === "saved" || outcome.outcome === "recorded") {
      ui.feedbackDone = true;
      sayFeedback(
        outcome.outcome === "saved"
          ? "Thank you. Your feedback was saved for review."
          : "Feedback for this question was already recorded. This attempt did not replace it.",
        true,
      );
    } else {
      if (outcome.outcome === "unknown") ui.feedbackPending = payload;
      sayFeedback(outcome.message);
    }
    refreshControls();
  }

  el.form.addEventListener("submit", (event) => {
    event.preventDefault();
    ask();
  });
  el.clear.addEventListener("click", () => {
    if (ui.busy) return;
    ui.token += 1;
    el.question.value = "";
    hideResult();
    say("");
  });
  el.sourceClose.addEventListener("click", closeSource);
  el.contact.addEventListener("click", contactSupport);
  el.rating.addEventListener("change", () => {
    el.categoryBox.hidden = el.rating.value !== "not_helpful";
    if (el.rating.value !== "not_helpful") el.category.value = "";
  });
  el.feedbackForm.addEventListener("submit", (event) => {
    event.preventDefault();
    sendFeedback();
  });

  root.hidden = false;
}

initQuestionFlow();