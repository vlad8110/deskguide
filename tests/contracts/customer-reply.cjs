/* Real conversation.js operations against an isolated Flask HTTP server. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const config = JSON.parse(fs.readFileSync(0, "utf8"));
let cookie = "";
let replyWrites = 0;
async function transport(url, options = {}) {
  const response = await fetch(new URL(url, config.base), {
    ...options,
    headers: { ...options.headers, ...(cookie ? { Cookie: cookie } : {}) },
    redirect: "error",
  });
  for (const value of response.headers.getSetCookie()) cookie = value.split(";")[0];
  if (url.endsWith("/replies") && options.method === "POST") replyWrites++;
  // Remove a required field from a real response to prove the client fails closed.
  const omit = (config.omit === "detail" && url.includes("/requests/")) ||
    (config.omit === "registration" && url.endsWith("/reply-ids"));
  if (!omit || !response.ok) return response;
  const data = await response.json();
  delete data.version;
  return new Response(JSON.stringify(data), { status: response.status, headers: response.headers });
}
async function main() {
  const token = await (await transport("/v1/session/login-token")).json();
  const login = await transport("/v1/session/login", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": token.csrf_token },
    body: JSON.stringify({ username: "customer-one", password: "Test-only-passphrase-12!" }),
  });
  assert.equal(login.status, 200);
  const context = vm.createContext({
    fetch: transport, TypeError, document: { querySelector: () => null },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../../app/static/conversation.js"), "utf8"), context);
  const loaded = await context.convLoadDetail(context.convApi, config.requestId);
  if (config.omit === "detail") {
    assert.equal(loaded.outcome, "error");
    assert.equal(replyWrites, 0);
    return;
  }
  assert.equal(loaded.outcome, "ok");
  assert.equal(loaded.detail.version, 4);
  const state = { requestId: config.requestId, message: "Reviewed contract reply",
    expectedVersion: loaded.detail.version, submissionId: null, unresolved: false };
  const saved = await context.convSendReply(state);
  if (config.omit === "registration") {
    assert.equal(saved.outcome, "retry");
    assert.equal(replyWrites, 0);
    return;
  }
  assert.equal(saved.outcome, "saved");
  assert.equal(saved.version, 5);
  assert.equal(saved.state, "in_review");
  assert.equal(replyWrites, 1);
  const reloaded = await context.convLoadDetail(context.convApi, config.requestId);
  assert.equal(reloaded.outcome, "ok");
  assert.equal(reloaded.detail.version, 5);
  assert.equal(reloaded.detail.messages.filter(m => m.content === state.message).length, 1);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
