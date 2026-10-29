
import sqlite3

import pytest

from app.database import (
    add_target,
    delete_target,
    get_incidents,
    init_db,
    open_incident,
    resolve_incident,
)


def test_incidents_table_initialized(tmp_path):
    db_path = tmp_path / "incidents.db"
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        table = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'incidents'
            """
        ).fetchone()

        indexes = conn.execute(
            "PRAGMA index_list('incidents')"
        ).fetchall()

    assert table is not None

    index_names = [row[1] for row in indexes]

    assert "idx_incidents_one_open_per_target" in index_names


def test_open_incident(tmp_path):
    db_path = tmp_path / "incidents.db"
    init_db(db_path)

    target_id = add_target(
        "Home Router",
        "192.168.1.1",
        db_path
    )

    incident_id = open_incident(target_id, db_path)

    incidents = get_incidents(
        status="open",
        db_path=db_path
    )

    assert incident_id > 0
    assert len(incidents) == 1

    incident = incidents[0]

    assert incident["id"] == incident_id
    assert incident["target_id"] == target_id
    assert incident["target_name"] == "Home Router"
    assert incident["status"] == "open"
    assert incident["opened_at"] is not None
    assert incident["resolved_at"] is None


def test_duplicate_open_incident_prevented(tmp_path):
    db_path = tmp_path / "incidents.db"
    init_db(db_path)

    target_id = add_target(
        "Router",
        "192.168.1.1",
        db_path
    )

    first_id = open_incident(target_id, db_path)
    second_id = open_incident(target_id, db_path)

    assert first_id == second_id

    incidents = get_incidents(
        status="open",
        db_path=db_path
    )

    assert len(incidents) == 1


def test_resolve_incident(tmp_path):
    db_path = tmp_path / "incidents.db"
    init_db(db_path)

    target_id = add_target(
        "Google DNS",
        "8.8.8.8",
        db_path
    )

    incident_id = open_incident(target_id, db_path)

    assert resolve_incident(target_id, db_path) is True
    assert resolve_incident(target_id, db_path) is False

    active = get_incidents(
        status="open",
        db_path=db_path
    )

    resolved = get_incidents(
        status="resolved",
        db_path=db_path
    )

    assert active == []
    assert len(resolved) == 1
    assert resolved[0]["id"] == incident_id
    assert resolved[0]["status"] == "resolved"
    assert resolved[0]["resolved_at"] is not None


def test_incident_can_reopen_after_resolution(tmp_path):
    db_path = tmp_path / "incidents.db"
    init_db(db_path)

    target_id = add_target(
        "Router",
        "192.168.1.1",
        db_path
    )

    first_id = open_incident(target_id, db_path)

    assert resolve_incident(target_id, db_path)

    second_id = open_incident(target_id, db_path)

    assert second_id != first_id

    all_incidents = get_incidents(db_path=db_path)
    active = get_incidents(
        status="open",
        db_path=db_path
    )

    assert len(all_incidents) == 2
    assert len(active) == 1
    assert active[0]["id"] == second_id


def test_delete_target_cascades_incidents(tmp_path):
    db_path = tmp_path / "incidents.db"
    init_db(db_path)

    target_id = add_target(
        "Old Device",
        "192.168.1.50",
        db_path
    )

    open_incident(target_id, db_path)

    assert delete_target(target_id, db_path) is True

    assert get_incidents(db_path=db_path) == []


def test_incident_foreign_key_and_status_validation(tmp_path):
    db_path = tmp_path / "incidents.db"
    init_db(db_path)

    with pytest.raises(sqlite3.IntegrityError):
        open_incident(9999, db_path)

    target_id = add_target(
        "Test Device",
        "192.168.1.80",
        db_path
    )

    with sqlite3.connect(db_path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO incidents (
                    target_id,
                    status
                )
                VALUES (?, 'invalid')
                """,
                (target_id,)
            )
