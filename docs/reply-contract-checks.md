# Customer reply contract checks

Run `python -m pytest -q tests/test_reply_contract.py` with Python dependencies and Node 24 installed. GitHub Actions runs this as **Check customer reply contracts**, separately from the remaining tests.

1. **Response fields:** real customer detail, submission status and reply-ID registration responses expose the agreed integer version, request identity, state and contract version. Registration preserves its operation and unused state.
2. **Error behavior:** stale versions, requests no longer waiting for a reply and changed retry payloads return distinct 409 codes. Repeating the original payload returns the saved result without a duplicate reply.
3. **Connected browser/backend flow:** the actual `conversation.js` operations log in with a fictional account, read a request from an isolated Flask HTTP server, register an ID, send the read version with a reply, and reload the persisted conversation. Missing-version fault cases must stop before any reply write.

These checks use a temporary SQLite database, an ephemeral loopback port and synthetic test data. No hosted AI, external account or working development database is used. Node executes the browser's request/response functions; this is not a rendered-browser layout or click test. Existing browser tests continue to cover the UI behavior separately.
