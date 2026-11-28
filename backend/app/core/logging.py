from __future__ import annotations

import json
import logging
import re
import sys
import time
import traceback
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

__all__ = [
    "ACCESS_LOGGER",
    "METRICS_NAMESPACE",
    "QUEUED_METRIC",
    "REQUEST_ID_HEADER",
    "RUNNING_METRIC",
    "JsonFormatter",
    "RequestLog",
    "configure_logging",
    "log_queue_metrics",
]

ACCESS_LOGGER = "bodha.access"
REQUEST_ID_HEADER = "X-Request-ID"
METRICS_NAMESPACE = "BodhaCoder"
QUEUED_METRIC = "QueuedAnalyses"
RUNNING_METRIC = "RunningAnalyses"
UNMATCHED_ROUTE = "unmatched"
LOG_LEVEL = logging.INFO
MAX_FRAMES = 20
MAX_CAUSES = 5
INCOMING_REQUEST_ID = re.compile(r"[0-9A-Fa-f-]{16,64}")
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error")
UVICORN_ACCESS_LOGGER = "uvicorn.access"
QUIET_LOGGERS = (
    "httpx",
    "httpcore",
    "botocore",
    "boto3",
    "s3transfer",
    "urllib3",
    "google_genai",
    "google.auth",
    "signxml",
)

_request_id: ContextVar[str | None] = ContextVar("bodha_request_id", default=None)
_access = logging.getLogger(ACCESS_LOGGER)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = _request_id.get()
        if request_id is not None:
            entry["request_id"] = request_id
        entry.update(getattr(record, "fields", {}))
        if record.exc_info and record.exc_info[1] is not None:
            entry["error"] = _error_summary(record.exc_info[1])
        return json.dumps(entry, default=str, separators=(",", ":"))


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(LOG_LEVEL)
    for name in UVICORN_LOGGERS:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    uvicorn_access = logging.getLogger(UVICORN_ACCESS_LOGGER)
    uvicorn_access.handlers, uvicorn_access.propagate, uvicorn_access.disabled = [], False, True
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.captureWarnings(True)


class RequestLog:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        request_id = _incoming_request_id(scope) or uuid4().hex
        token = _request_id.set(request_id)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self._app(scope, receive, send_with_id)
        finally:
            _log_request(scope, status, time.perf_counter() - started, request_id)
            _request_id.reset(token)


def log_queue_metrics(logger: logging.Logger, *, queued: int, running: int, at: datetime) -> None:
    if at.tzinfo is None:
        raise ValueError("queue metrics need a timezone-aware time")
    directive = {
        "Namespace": METRICS_NAMESPACE,
        "Dimensions": [[]],
        "Metrics": [{"Name": QUEUED_METRIC, "Unit": "Count"}, {"Name": RUNNING_METRIC, "Unit": "Count"}],
    }
    fields = {
        "_aws": {"Timestamp": int(at.timestamp() * 1000), "CloudWatchMetrics": [directive]},
        QUEUED_METRIC: queued,
        RUNNING_METRIC: running,
    }
    logger.info("analysis queue", extra={"fields": fields})


def _incoming_request_id(scope: Scope) -> str | None:
    for name, value in scope["headers"]:
        if name == b"x-request-id":
            text = value.decode("latin-1")
            return text if INCOMING_REQUEST_ID.fullmatch(text) else None
    return None


def route_template(path: str, route_path: str | None) -> str:
    if not route_path:
        return UNMATCHED_ROUTE
    parts, template = path.rstrip("/").split("/"), route_path.rstrip("/").split("/")
    prefix = parts[: max(1, len(parts) - len(template) + 1)]
    return "/".join(prefix + template[1:]) or "/"


def _log_request(scope: Scope, status: int, seconds: float, request_id: str) -> None:
    route = scope.get("route")
    fields = {
        "method": scope["method"],
        "route": route_template(scope["path"], getattr(route, "path", None)),
        "status": status,
        "duration_ms": round(seconds * 1000, 1),
        "request_id": request_id,
    }
    _access.info("request", extra={"fields": fields})


def _error_summary(error: BaseException) -> dict[str, Any]:
    frames = traceback.extract_tb(error.__traceback__)[-MAX_FRAMES:]
    return {
        "type": _type_name(error),
        "frames": [f"{frame.filename}:{frame.lineno} {frame.name}" for frame in frames],
        "causes": [_type_name(cause) for cause in _causes(error)],
    }


def _causes(error: BaseException) -> list[BaseException]:
    found: list[BaseException] = []
    current = _cause_of(error)
    while current is not None and len(found) < MAX_CAUSES and all(current is not seen for seen in found):
        found.append(current)
        current = _cause_of(current)
    return found


def _cause_of(error: BaseException) -> BaseException | None:
    if error.__cause__ is not None:
        return error.__cause__
    return None if error.__suppress_context__ else error.__context__


def _type_name(error: BaseException) -> str:
    kind = type(error)
    return f"{kind.__module__}.{kind.__qualname__}"
