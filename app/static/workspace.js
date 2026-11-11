/* Same-origin login, session status and logout interactions. */

"use strict";

async function sessionErrorMessage(response) {
  try {
    const result = await response.json();
    if (typeof result?.error?.message === "string" && result.error.message.trim())
      return result.error.message;
  } catch {
    // Proxies may return an HTML error page instead of the application's JSON.
  }
  return response.status >= 500
    ? "Service temporarily unavailable. Try again."
    : "The request could not be completed. Please try again.";
}

async function sendSessionAction(path, body, authenticated) {
  const status = document.querySelector("#status");
  const endpoint = authenticated ? "/v1/session" : "/v1/session/login-token";
  status.textContent = "Please wait…";
  try {
    const tokenResponse = await fetch(endpoint, { credentials: "same-origin" });
    if (!tokenResponse.ok) {
      if (authenticated && tokenResponse.status === 401) {
        window.location.assign("/");
        return;
      }
      status.textContent = await sessionErrorMessage(tokenResponse);
      return;
    }
    const token = await tokenResponse.json();
    if (typeof token?.csrf_token !== "string" || !token.csrf_token) {
      status.textContent = "Please refresh the page and sign in again.";
      return;
    }
    const response = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": token.csrf_token },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      status.textContent = await sessionErrorMessage(response);
      return;
    }
    window.location.assign("/");
  } catch (error) {
    status.textContent =
      error instanceof TypeError
        ? "Connection unavailable. Try again."
        : "The request could not be completed. Refresh the page and try again.";
  }
}

const form = document.querySelector("#sign-in");
if (form) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button");
    button.disabled = true;
    await sendSessionAction(
      "/v1/session/login",
      {
        username: form.username.value,
        password: form.password.value,
      },
      false,
    );
    form.password.value = "";
    button.disabled = false;
  });
}
const signOut = document.querySelector("#sign-out");
if (signOut)
  signOut.addEventListener("click", () =>
    sendSessionAction("/v1/session/logout", {}, true),
  );
