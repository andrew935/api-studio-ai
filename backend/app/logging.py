import json
import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import Request, Response

from backend.app.metrics import record_http_request


LOGGER_NAME = "backend.app"
REQUEST_LOGGER_NAME = f"{LOGGER_NAME}.http"
LOG_FIELDS = (
    "event",
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "error_type",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


async def log_http_request(request: Request, call_next) -> Response:
    request_id = uuid4().hex
    started_at = perf_counter()
    logger = logging.getLogger(REQUEST_LOGGER_NAME)

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_seconds = perf_counter() - started_at
        record_http_request(
            request=request,
            status_code=500,
            duration_seconds=duration_seconds,
        )
        logger.error(
            "HTTP request failed",
            extra={
                "event": "http_request_failed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": round(duration_seconds * 1000, 2),
                "error_type": type(exc).__name__,
            },
        )
        raise

    response.headers["X-Request-ID"] = request_id
    duration_seconds = perf_counter() - started_at
    record_http_request(
        request=request,
        status_code=response.status_code,
        duration_seconds=duration_seconds,
    )
    logger.info(
        "HTTP request completed",
        extra={
            "event": "http_request_completed",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_seconds * 1000, 2),
        },
    )
    return response
