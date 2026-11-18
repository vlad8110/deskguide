/* Shared same-origin JSON requests for support and conversation screens. */

"use strict";

async function requestReadJson(response) {
  try {
    return await response.json();
  } catch {
    // Proxies may return an HTML error page instead of the application's JSON.
    return null;
  }
}

function requestNormalize(response, data, sent) {
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

function requestFailure(network, sent) {
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
      const tokenData = await requestReadJson(tokenResponse);
      if (!tokenResponse.ok) return requestNormalize(tokenResponse, tokenData, false);
      if (typeof tokenData?.csrf_token !== "string" || !tokenData.csrf_token)
        return requestFailure(false, false);
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
    return requestNormalize(response, await requestReadJson(response), true);
  } catch (error) {
    return requestFailure(error instanceof TypeError, sent);
  }
}
