from fastapi.testclient import TestClient

from backend.app.main import app


def test_metrics_expose_request_count_and_duration():
    with TestClient(app) as client:
        response = client.get("/health/live")
        metrics = client.get("/metrics/")

    assert response.status_code == 200
    assert metrics.status_code == 200
    assert "api_studio_http_requests_total" in metrics.text
    assert "api_studio_http_request_duration_seconds" in metrics.text
    assert 'method="GET",route="/health/live",status_class="2xx"' in metrics.text


def test_metrics_use_route_template_instead_of_dynamic_id():
    with TestClient(app) as client:
        response = client.post("/api/v1/upload-requests/987654/activate")
        metrics = client.get("/metrics/")

    assert response.status_code == 401
    assert (
        'route="/api/v1/upload-requests/{upload_request_id}/activate"'
        in metrics.text
    )
    assert 'route="/api/v1/upload-requests/987654/activate"' not in metrics.text
