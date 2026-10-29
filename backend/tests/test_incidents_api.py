
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

from app.database import (
    add_target,
    get_incidents,
    init_db,
    record_monitoring_result
)


client = TestClient(app)


def test_get_incidents_empty(tmp_path):
    db_path = tmp_path / "incidents_api.db"
    init_db(db_path)

    with patch("app.main.DB_PATH", db_path):
        response = client.get("/api/incidents")

    assert response.status_code == 200
    assert response.json() == []


def test_get_open_incidents_api(tmp_path):
    db_path = tmp_path / "incidents_api.db"
    init_db(db_path)

    target_id = add_target(
        "Home Router",
        "192.168.1.1",
        db_path
    )

    for _ in range(3):
        record_monitoring_result(
            target_id,
            False,
            None,
            db_path
        )

    with patch("app.main.DB_PATH", db_path):
        response = client.get(
            "/api/incidents?status=open"
        )

    assert response.status_code == 200

    incidents = response.json()

    assert len(incidents) == 1
    assert incidents[0]["target_id"] == target_id
    assert incidents[0]["target_name"] == "Home Router"
    assert incidents[0]["target_address"] == "192.168.1.1"
    assert incidents[0]["status"] == "open"
    assert incidents[0]["opened_at"] is not None
    assert incidents[0]["resolved_at"] is None


def test_get_resolved_incidents_api(tmp_path):
    db_path = tmp_path / "incidents_api.db"
    init_db(db_path)

    target_id = add_target(
        "Google DNS",
        "8.8.8.8",
        db_path
    )

    for _ in range(3):
        record_monitoring_result(
            target_id,
            False,
            None,
            db_path
        )

    record_monitoring_result(
        target_id,
        True,
        12.0,
        db_path
    )

    with patch("app.main.DB_PATH", db_path):
        open_response = client.get(
            "/api/incidents?status=open"
        )

        resolved_response = client.get(
            "/api/incidents?status=resolved"
        )

        all_response = client.get(
            "/api/incidents"
        )

    assert open_response.status_code == 200
    assert open_response.json() == []

    assert resolved_response.status_code == 200

    resolved = resolved_response.json()

    assert len(resolved) == 1
    assert resolved[0]["status"] == "resolved"
    assert resolved[0]["resolved_at"] is not None

    assert all_response.status_code == 200
    assert len(all_response.json()) == 1


def test_invalid_incident_status_api():
    response = client.get(
        "/api/incidents?status=invalid"
    )

    assert response.status_code == 422
