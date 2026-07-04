from __future__ import annotations

from flask.testing import FlaskClient


def test_health_returns_json_with_expected_keys(client: FlaskClient) -> None:
    response = client.get("/api/health")
    body = response.get_json()

    assert body["service"] == "barcodelabelgen-backend"
    # Version comes from installed package metadata ("dev" in a bare checkout)
    assert body["version"]
    assert "checks" in body
    assert "database" in body["checks"]
    assert "redis" in body["checks"]


def test_health_reports_degraded_when_dependencies_unreachable(client: FlaskClient) -> None:
    response = client.get("/api/health")
    body = response.get_json()

    assert response.status_code == 503
    assert body["status"] == "degraded"
    assert body["checks"]["database"]["ok"] is False
    assert body["checks"]["redis"]["ok"] is False
