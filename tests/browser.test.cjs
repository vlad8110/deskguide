/* Browser session-action regressions using isolated fetch and DOM substitutes. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../app/static/workspace.js"),
  "utf8",
);

function jsonResponse(status, value) {
  return { status, ok: status >= 200 && status < 300, json: async () => value };
}

function htmlResponse(status) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => {
      throw new SyntaxError("Unexpected token '<', <html> is not valid JSON");
    },
  };
}

function browser(responses) {
  const status = { textContent: "" };
  const calls = [];
  const redirects = [];
  const context = {
    TypeError,
    document: { querySelector: (selector) => selector === "#status" ? status : null },
    window: { location: { assign: (destination) => redirects.push(destination) } },
    fetch: async (url, options) => {
      calls.push({ url, options });
      const response = responses.shift();
      if (response instanceof Error) throw response;
      return response;
    },
  };
  vm.runInNewContext(source, context, { filename: "workspace.js" });
  return { send: context.sendSessionAction, status, calls, redirects };
}

test("HTML proxy errors show a friendly service message", async () => {
  const page = browser([jsonResponse(200, { csrf_token: "test-token" }), htmlResponse(502)]);
  await page.send("/v1/session/login", {}, false);
  assert.equal(page.status.textContent, "Service temporarily unavailable. Try again.");
  assert.deepEqual(page.redirects, []);
});

test("safe API error messages remain usable", async () => {
  const page = browser([
    jsonResponse(200, { csrf_token: "test-token" }),
    jsonResponse(401, { error: { message: "Username or password is incorrect." } }),
  ]);
  await page.send("/v1/session/login", {}, false);
  assert.equal(page.status.textContent, "Username or password is incorrect.");
});

test("malformed JSON errors do not expose parser messages", async () => {
  const page = browser([jsonResponse(200, { csrf_token: "test-token" }), htmlResponse(400)]);
  await page.send("/v1/session/login", {}, false);
  assert.equal(page.status.textContent, "The request could not be completed. Please try again.");
});

test("unexpected error-envelope shapes use a safe fallback", async () => {
  const page = browser([
    jsonResponse(200, { csrf_token: "test-token" }),
    jsonResponse(400, { error: { message: { internal: "not public" } } }),
  ]);
  await page.send("/v1/session/login", {}, false);
  assert.equal(page.status.textContent, "The request could not be completed. Please try again.");
});

test("a non-JSON token response never submits a login", async () => {
  const page = browser([htmlResponse(200)]);
  await page.send("/v1/session/login", {}, false);
  assert.equal(page.calls.length, 1);
  assert.equal(page.status.textContent, "The request could not be completed. Refresh the page and try again.");
});

test("a missing CSRF token never submits a login", async () => {
  const page = browser([jsonResponse(200, {})]);
  await page.send("/v1/session/login", {}, false);
  assert.equal(page.calls.length, 1);
  assert.equal(page.status.textContent, "Please refresh the page and sign in again.");
});

test("network failures do not expose raw browser exception text", async () => {
  const page = browser([new TypeError("raw network implementation detail")]);
  await page.send("/v1/session/login", {}, false);
  assert.equal(page.status.textContent, "Connection unavailable. Try again.");
});

test("successful logout uses the session token and redirects", async () => {
  const page = browser([
    jsonResponse(200, { csrf_token: "test-token" }), jsonResponse(204),
  ]);
  await page.send("/v1/session/logout", {}, true);
  assert.equal(page.calls[0].url, "/v1/session");
  assert.equal(page.calls[1].options.headers["X-CSRF-Token"], "test-token");
  assert.equal(page.calls[1].options.credentials, "same-origin");
  assert.deepEqual(page.redirects, ["/"]);
});
