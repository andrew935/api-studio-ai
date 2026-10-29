from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


DEMO_URL = "https://jsonplaceholder.typicode.com/users"
SAMPLE_USERS = [{"id": 1, "name": "Demo User"}]


@pytest.fixture(autouse=True)
def outbound(monkeypatch):
    """Replace outbound HTTP with an in-memory transport for every test."""
    state = SimpleNamespace(
        requests=[],
        response=httpx.Response(200, json=SAMPLE_USERS),
        error=None,
    )

    def handle_request(request):
        state.requests.append(request)
        assert request.method == "GET"
        assert str(request.url) == DEMO_URL
        if state.error is not None:
            raise state.error
        return state.response

    original_client = httpx.AsyncClient

    def create_client(*args, **kwargs):
        assert kwargs["timeout"] == 10.0
        return original_client(
            *args, transport=httpx.MockTransport(handle_request), **kwargs
        )

    monkeypatch.setattr(httpx, "AsyncClient", create_client)
    return state


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_home(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to API Studio AI"}


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_preview_echoes_input_without_sending(client, outbound, method):
    payload = {"url": "https://example.com/users?limit=2", "method": method}

    response = client.post("/api/v1/requests/preview", json=payload)

    assert response.status_code == 200
    assert response.json() == {**payload, "status": "ready"}
    assert outbound.requests == []


def test_preview_preserves_plain_string_validation(client, outbound):
    payload = {"url": "not a URL yet", "method": "custom-method"}

    response = client.post("/api/v1/requests/preview", json=payload)

    assert response.status_code == 200
    assert response.json() == {**payload, "status": "ready"}
    assert outbound.requests == []


@pytest.mark.parametrize(
    "payload",
    [{}, {"url": DEMO_URL}, {"method": "GET"}, {"url": 123, "method": "GET"}],
)
def test_preview_rejects_invalid_input(client, outbound, payload):
    response = client.post("/api/v1/requests/preview", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]
    assert outbound.requests == []


def test_demo_returns_status_and_json(client, outbound):
    response = client.get("/api/v1/requests/test")

    assert response.status_code == 200
    assert response.json() == {"status_code": 200, "data": SAMPLE_USERS}
    assert len(outbound.requests) == 1


@pytest.mark.parametrize("status_code", [404, 500])
def test_demo_preserves_http_error_response(client, outbound, status_code):
    outbound.response = httpx.Response(status_code)

    response = client.get("/api/v1/requests/test")

    assert response.status_code == 502
    assert set(response.json()) == {"detail"}
    assert str(status_code) in response.json()["detail"]
    assert DEMO_URL in response.json()["detail"]


@pytest.mark.parametrize(
    "error_type, expected_status",
    [
        (httpx.ReadTimeout, 504),
        (httpx.ConnectError, 502),
    ],
)
def test_demo_preserves_transport_error_response(
    client,
    outbound,
    error_type,
    expected_status,
):
    outbound.error = error_type("Demo request failed")

    response = client.get("/api/v1/requests/test")

    assert response.status_code == expected_status
    assert response.json() == {"detail": "Demo request failed"}
    


def test_swagger_docs_are_available(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text


def test_openapi_preserves_routes_and_schema(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    assert set(document["paths"]) == {
        "/",
        "/api/v1/ai/classify",
        "/api/v1/requests/preview",
        "/api/v1/requests/test",
    }
    schema = document["components"]["schemas"]["APIRequest"]
    assert set(schema["required"]) == {"url", "method"}
    assert schema["properties"]["url"]["type"] == "string"
    assert schema["properties"]["method"]["type"] == "string"
