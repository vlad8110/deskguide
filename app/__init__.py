"""Application factory, secure configuration and shared request handling."""

import json
import os
import secrets
import sqlite3
import time
from datetime import timedelta
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

from flask import Flask, g, jsonify, render_template, request
from flask_session import Session
from flask_session.base import Serializer, ServerSideSession, ServerSideSessionInterface
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash

from . import accounts, auth, db
from .errors import CONTRACT_VERSION, ApiError, error_response


class JsonSessionSerializer(Serializer):
    """Use only JSON for the fresh local store; never deserialize legacy pickle."""

    def encode(self, session: ServerSideSession) -> bytes:
        return json.dumps(dict(session), separators=(",", ":")).encode("utf-8")

    def decode(self, serialized_data: bytes) -> dict:
        decoded = json.loads(serialized_data)
        if not isinstance(decoded, dict):
            raise ValueError("Invalid session record")
        return decoded


class _ConfigurableSessionInterface(Protocol):
    """Describe Flask-Session's replaceable serializer extension point."""

    serializer: Serializer


def _stateless_health(application):
    """Keep cookie-backed session loading from blocking the readiness route."""

    def dispatch(environ, start_response):
        if environ.get("PATH_INFO") == "/health":
            environ = environ.copy()
            environ.pop("HTTP_COOKIE", None)
        return application(environ, start_response)

    return dispatch


def create_app(test_config=None):
    default_instance = Path(__file__).resolve().parent.parent / "instance"
    instance = Path(
        os.environ.get("DESKGUIDE_INSTANCE_PATH", str(default_instance))
    ).resolve()
    app = Flask(__name__, instance_path=str(instance), instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        LOCAL_HTTP=os.environ.get("DESKGUIDE_LOCAL_HTTP") == "1",
        PROXY_X_FOR=os.environ.get("DESKGUIDE_PROXY_X_FOR", "0"),
        PROXY_X_PROTO=os.environ.get("DESKGUIDE_PROXY_X_PROTO", "0"),
        DATABASE=str(instance / "deskguide.sqlite3"),
        SESSION_TYPE="sqlalchemy",
        SESSION_SQLALCHEMY_TABLE="http_sessions",
        SESSION_COOKIE_NAME="deskguide_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=True,
        SESSION_PERMANENT=True,
        SESSION_REFRESH_EACH_REQUEST=False,
        SESSION_CLEANUP_N_REQUESTS=100,
        SESSION_ACTIVITY_REFRESH_SECONDS=60,
        SESSION_ID_LENGTH=32,
        SESSION_KEY_PREFIX="deskguide:",
        IDLE_SESSION_SECONDS=1800,
        ABSOLUTE_SESSION_SECONDS=28800,
        LOGIN_USER_LIMIT=5,
        LOGIN_ADDRESS_LIMIT=30,
        LOGIN_WINDOW_SECONDS=900,
        MAX_CONTENT_LENGTH=16 * 1024,
        TIME_PROVIDER=time.time,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "connect_args": {"timeout": 5},
            "hide_parameters": True,
        },
        DUMMY_PASSWORD_HASH=generate_password_hash(secrets.token_urlsafe(32)),
    )
    # Explicit local profile; secure cookies remain the default for other deployments.
    app.config["SESSION_COOKIE_SECURE"] = not app.config["LOCAL_HTTP"]
    if not app.config["SESSION_COOKIE_SECURE"]:
        app.config["TRUSTED_HOSTS"] = ["localhost", "127.0.0.1", "[::1]"]
    if test_config:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        if not (app.testing or app.config["LOCAL_HTTP"]):
            raise RuntimeError("SECRET_KEY is required outside local development.")
        app.config["SECRET_KEY"] = secrets.token_hex(32)
    for setting in ("PROXY_X_FOR", "PROXY_X_PROTO"):
        try:
            hops = int(app.config[setting])
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"{setting} must be a nonnegative proxy count."
            ) from error
        if hops < 0:
            raise RuntimeError(f"{setting} must be a nonnegative proxy count.")
        app.config[setting] = hops
    if app.config["PROXY_X_FOR"] or app.config["PROXY_X_PROTO"]:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config["PROXY_X_FOR"],
            x_proto=app.config["PROXY_X_PROTO"],
            x_host=0,
            x_port=0,
            x_prefix=0,
        )
    app.wsgi_app = _stateless_health(app.wsgi_app)
    database = Path(app.config["DATABASE"]).resolve()
    database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    app.config["DATABASE"] = str(database)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(database)
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        seconds=app.config["IDLE_SESSION_SECONDS"]
    )
    session_db = SQLAlchemy(app)
    app.config["SESSION_SQLALCHEMY"] = session_db
    Session(app)
    session_interface = app.session_interface
    if not isinstance(session_interface, ServerSideSessionInterface):
        raise RuntimeError("Server-side session initialization is required.")
    # The library infers its default concrete serializer rather than its interface.
    cast(
        _ConfigurableSessionInterface, session_interface
    ).serializer = JsonSessionSerializer()
    db.init_app(app)
    accounts.init_app(app)
    app.register_blueprint(auth.bp)

    @app.before_request
    def prepare_request():
        g.correlation_id = str(uuid4())
        g.access = None
        g.account = None
        # Preserve routing errors and do not count monitoring/assets as activity.
        if request.routing_exception is not None:
            return
        if request.endpoint in {"health", "static"}:
            return
        auth.load_access()
        auth.enforce_csrf()

    @app.after_request
    def response_headers(response):
        if not getattr(g, "correlation_id", None):
            g.correlation_id = str(uuid4())
        response.headers["X-Correlation-ID"] = g.correlation_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; object-src 'none'; base-uri 'self'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @app.get("/health")
    def health():
        if not db.is_schema_ready():
            raise ApiError(
                503,
                "DEPENDENCY_UNAVAILABLE",
                "Workspace setup is incomplete.",
                retryable=True,
            )
        return jsonify(
            status="ok",
            contract_version=CONTRACT_VERSION,
            correlation_id=g.correlation_id,
        )

    @app.get("/")
    def home():
        account = (
            {"username": g.account["username"], "role": g.account["role"]}
            if g.account is not None
            else None
        )
        return render_template(
            "home.html",
            account=account,
            local_http=not app.config["SESSION_COOKIE_SECURE"],
        )

    app.register_error_handler(ApiError, error_response)

    @app.errorhandler(HTTPException)
    def http_error(error):
        codes = {
            400: "VALIDATION_FAILED",
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            413: "VALIDATION_FAILED",
            415: "UNSUPPORTED_MEDIA_TYPE",
            429: "RATE_LIMITED",
        }
        status = error.code or 500
        body = error_response(
            ApiError(
                status,
                codes.get(
                    status, "REQUEST_FAILED" if status < 500 else "INTERNAL_ERROR"
                ),
                "The request could not be completed.",
                retryable=status == 429,
            )
        )
        # Retain protocol headers such as Allow, WWW-Authenticate and Retry-After.
        response = error.get_response()
        response.set_data(body.get_data())
        response.content_type = "application/json"
        return response

    def storage_error(_error):
        app.logger.exception(
            "storage_unavailable correlation_id=%s",
            getattr(g, "correlation_id", "unavailable"),
        )
        return error_response(
            ApiError(
                503,
                "DEPENDENCY_UNAVAILABLE",
                "The workspace is temporarily unavailable.",
                retryable=True,
            )
        )

    app.register_error_handler(sqlite3.Error, storage_error)
    app.register_error_handler(SQLAlchemyError, storage_error)

    @app.errorhandler(Exception)
    def unexpected_error(_error):
        app.logger.exception(
            "internal_error correlation_id=%s",
            getattr(g, "correlation_id", "unavailable"),
        )
        return error_response(
            ApiError(500, "INTERNAL_ERROR", "Please try again later.", retryable=True)
        )

    return app
