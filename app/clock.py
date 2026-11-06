"""Shared injectable application time and UTC API timestamps."""

from datetime import datetime, timezone

from flask import current_app


def now():
    return int(current_app.config["TIME_PROVIDER"]())


def timestamp(seconds):
    return (
        datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")
    )
