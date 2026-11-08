"""Safe API errors and server-owned correlation IDs."""

from uuid import uuid4

from flask import g, jsonify

CONTRACT_VERSION = "0.3.3"


class ApiError(Exception):
    def __init__(self, status, code, message, *, retryable=False, retry_after=None):
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        self.retry_after = retry_after


def error_response(error):
    if not getattr(g, "correlation_id", None):
        g.correlation_id = str(uuid4())
    response = jsonify(
        contract_version=CONTRACT_VERSION,
        error={
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
            "correlation_id": g.correlation_id,
        },
    )
    response.status_code = error.status
    if error.retry_after is not None:
        response.headers["Retry-After"] = str(error.retry_after)
    return response
