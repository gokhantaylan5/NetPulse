
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import (
    add_target,
    db_connection,
    get_incidents,
    init_db,
    open_incident,
    resolve_incident,
)

from app.main import app


def test_open_incident_duration(tmp_path):
    db_path = tmp_path / "duration.db"
    init_db(db_path)

    target_id = add_target(
        "Router", "192.168.1.1", db_path
    )

    incident_id = open_incident(target_id, db_path)

    with db_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE incidents
            SET opened_at = datetime('now', '-125 seconds')
            WHERE id = ?
            """,
            (incident_id,)
        )

    incident = get_incidents(
        status="open",
        db_path=db_path
    )[0]

    assert incident["status"] == "open"
    assert incident["duration_seconds"] >= 125
    assert incident["duration_seconds"] <= 127


def test_resolved_incident_duration(tmp_path):
    db_path = tmp_path / "duration.db"
    init_db(db_path)

    target_id = add_target(
        "DNS", "8.8.8.8", db_path
    )

    incident_id = open_incident(target_id, db_path)
    resolve_incident(target_id, db_path)

    with db_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE incidents
            SET opened_at = datetime('now', '-300 seconds'),
                resolved_at = datetime('now', '-60 seconds')
            WHERE id = ?
            """,
            (incident_id,)
        )

    incident = get_incidents(
        status="resolved",
        db_path=db_path
    )[0]

    assert incident["status"] == "resolved"
    assert incident["duration_seconds"] == 240


def test_incident_api_includes_duration(tmp_path):
    db_path = tmp_path / "duration_api.db"
    init_db(db_path)

    target_id = add_target(
        "Test Device", "192.168.1.50", db_path
    )

    open_incident(target_id, db_path)

    with patch("app.main.DB_PATH", db_path):
        with TestClient(app) as client:
            response = client.get("/api/incidents")

    assert response.status_code == 200

    incidents = response.json()

    assert len(incidents) == 1
    assert "duration_seconds" in incidents[0]
    assert isinstance(
        incidents[0]["duration_seconds"],
        int
    )
    assert incidents[0]["duration_seconds"] >= 0
