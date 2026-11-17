import json
import logging
import re

from fastapi.testclient import TestClient

from backend.app.logging import JsonFormatter
from backend.app.main import app


def test_json_formatter_emits_machine_readable_fields():
    record = logging.LogRecord(
        name="backend.app.http",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="HTTP request completed",
        args=(),
        exc_info=None,
    )
    record.event = "http_request_completed"
    record.request_id = "req-123"
    record.status_code = 200

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["event"] == "http_request_completed"
    assert payload["request_id"] == "req-123"
    assert payload["status_code"] == 200
    assert "timestamp" in payload


def test_request_log_uses_safe_metadata_and_returns_request_id(capsys):
    with TestClient(app) as client:
        response = client.get(
            "/health/live?access_token=must-not-be-logged",
            headers={"Authorization": "Bearer must-not-be-logged"},
        )

    request_id = response.headers["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)

    records = [
        json.loads(line)
        for line in capsys.readouterr().err.splitlines()
        if line.startswith("{")
    ]
    request_record = next(
        record
        for record in records
        if record.get("event") == "http_request_completed"
    )

    assert request_record["request_id"] == request_id
    assert request_record["method"] == "GET"
    assert request_record["path"] == "/health/live"
    assert request_record["status_code"] == 200
    assert request_record["duration_ms"] >= 0
    assert "must-not-be-logged" not in json.dumps(request_record)
