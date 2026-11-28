from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.config import Settings

__all__ = [
    "REDACTED",
    "SAFE_MESSAGES",
    "error_report_options",
    "safe_text",
    "scrub_breadcrumb",
    "scrub_event",
    "start_error_reports",
]

REDACTED = "[redacted]"
SAFE_MESSAGES = frozenset(
    {
        "Exception in ASGI application\n",
        "%s failed",
        "analysis %s failed unexpectedly",
        "provider reminders failed",
        "queue metrics failed",
        "access log purge failed",
        "email intake message %s failed",
        "intake needs a session bound to an engine",
        "the sweep needs a session bound to an engine",
        "email intake needs a session bound to an engine",
        "now needs a time zone",
    }
)
KEPT_EVENT_KEYS = ("event_id", "timestamp", "level", "platform", "release", "environment", "logger", "server_name")
KEPT_SDK_KEYS = ("name", "version")
KEPT_FRAME_KEYS = ("filename", "module", "function", "lineno", "colno", "in_app")
KEPT_CRUMB_KEYS = ("type", "category", "level", "timestamp")
KEPT_TRACE_KEYS = ("trace_id", "span_id")
KEPT_RUNTIME_KEYS = ("name", "version")
KEPT_TAGS = ("process",)
NOTHING = {"mode": "off"}
DATA_COLLECTION = {
    "user_info": False,
    "cookies": NOTHING,
    "http_headers": {"request": NOTHING},
    "http_bodies": [],
    "url_query_params": NOTHING,
    "graphql": {"document": False, "variables": False},
    "gen_ai": {"inputs": False, "outputs": False},
    "mcp": {"inputs": False, "outputs": False},
    "database_query_data": False,
    "queues": False,
    "stack_frame_variables": False,
    "frame_context_lines": 0,
}


def start_error_reports(settings: Settings, *, process: str) -> bool:
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(**error_report_options(settings, process=process))
    sentry_sdk.set_tag("process", process)
    return True


def error_report_options(settings: Settings, *, process: str) -> dict[str, Any]:
    return {
        "dsn": settings.sentry_dsn,
        "release": settings.app_version,
        "environment": settings.app_environment,
        "server_name": process,
        "data_collection": DATA_COLLECTION,
        "max_request_body_size": "never",
        "attach_stacktrace": False,
        "auto_enabling_integrations": False,
        "integrations": [LoggingIntegration(level=None, event_level=logging.ERROR, breadcrumb_level=None)],
        "auto_session_tracking": False,
        "send_client_reports": False,
        "before_send": scrub_event,
        "before_breadcrumb": scrub_breadcrumb,
        "in_app_include": ["app"],
    }


def scrub_event(event: Mapping[str, Any], hint: Mapping[str, Any] | None = None) -> dict[str, Any]:
    kept: dict[str, Any] = {key: event[key] for key in KEPT_EVENT_KEYS if key in event}
    if isinstance(event.get("sdk"), Mapping):
        kept["sdk"] = _picked(event["sdk"], KEPT_SDK_KEYS)
    values = (event.get("exception") or {}).get("values") or []
    if values:
        kept["exception"] = {"values": [_exception(value) for value in values]}
    template = _message_template(event)
    if template is not None:
        kept["logentry"] = {"message": safe_text(template)}
    tags = {name: value for name, value in dict(event.get("tags") or {}).items() if name in KEPT_TAGS}
    if tags:
        kept["tags"] = tags
    contexts = _contexts(event.get("contexts") or {})
    if contexts:
        kept["contexts"] = contexts
    crumbs = [scrub_breadcrumb(crumb) for crumb in (event.get("breadcrumbs") or {}).get("values") or []]
    if crumbs:
        kept["breadcrumbs"] = {"values": crumbs}
    return kept


def scrub_breadcrumb(crumb: Mapping[str, Any], hint: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return _picked(crumb, KEPT_CRUMB_KEYS)


def safe_text(text: str) -> str:
    return text if text in SAFE_MESSAGES else REDACTED


def _picked(source: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: source[key] for key in keys if key in source}


def _exception(value: Mapping[str, Any]) -> dict[str, Any]:
    kept = _picked(value, ("type", "module"))
    if isinstance(value.get("value"), str):
        kept["value"] = safe_text(value["value"])
    if isinstance(value.get("mechanism"), Mapping):
        kept["mechanism"] = _picked(value["mechanism"], ("type", "handled"))
    frames = (value.get("stacktrace") or {}).get("frames") or []
    if frames:
        kept["stacktrace"] = {"frames": [_picked(frame, KEPT_FRAME_KEYS) for frame in frames]}
    return kept


def _message_template(event: Mapping[str, Any]) -> str | None:
    entry = event.get("logentry")
    if isinstance(entry, Mapping) and isinstance(entry.get("message"), str):
        return entry["message"]
    message = event.get("message")
    return message if isinstance(message, str) else None


def _contexts(contexts: Mapping[str, Any]) -> dict[str, Any]:
    kept: dict[str, Any] = {}
    if isinstance(contexts.get("runtime"), Mapping):
        kept["runtime"] = _picked(contexts["runtime"], KEPT_RUNTIME_KEYS)
    if isinstance(contexts.get("trace"), Mapping):
        kept["trace"] = _picked(contexts["trace"], KEPT_TRACE_KEYS)
    return kept
