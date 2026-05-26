import pytest
from fastapi.testclient import TestClient

pytest.importorskip("python_multipart")

import app.main as main_module
from app.main import app
from app.core.config import settings


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_root_health_returns_service_metadata(client: TestClient) -> None:
    response = client.get("/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["service"] == "Face Detector Backend"
    assert payload["embedding_provider"] == settings.embedding_provider
    assert payload["model_name"] == settings.model_name
    assert payload["model_version"] == settings.model_version
    assert payload["embedding_dimensions"] == settings.embedding_dimensions
    assert payload["match_threshold"] == settings.match_threshold


def test_admin_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/admin/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "admin"}


def test_vision_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/vision/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "vision"}


def test_readiness_returns_ready_when_dependencies_are_healthy(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "_check_database", lambda: True)
    monkeypatch.setattr(main_module, "_check_redis", lambda: True)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {"database": True, "redis": True},
    }


def test_readiness_returns_503_when_dependency_is_unhealthy(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "_check_database", lambda: True)
    monkeypatch.setattr(main_module, "_check_redis", lambda: False)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "dependencies": {"database": True, "redis": False},
    }


def test_metrics_endpoint_exposes_prometheus_series(client: TestClient) -> None:
    client.get("/api/admin/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "face_detector_http_requests_total" in response.text
    assert "face_detector_http_errors_total" in response.text
    assert "face_detector_http_request_duration_seconds_bucket" in response.text
    assert "face_detector_http_requests_in_progress" in response.text
    assert "face_detector_dependency_health_status" in response.text
