
import sqlite3
import pytest
from app.database import add_target, get_targets
from app.database import init_db
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app


def test_database_initialization(tmp_path):
    db_path = tmp_path / "test.db"

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        result = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='targets'"
        ).fetchone()

    assert db_path.exists()
    assert result is not None
    assert result[0] == "targets"



def test_add_and_get_target(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    target_id = add_target(
        name="Home Router",
        address="192.168.1.1",
        db_path=db_path
    )

    targets = get_targets(db_path)

    assert target_id == 1
    assert len(targets) == 1
    assert targets[0]["name"] == "Home Router"
    assert targets[0]["address"] == "192.168.1.1"


def test_duplicate_address(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    add_target("Router", "192.168.1.1", db_path)

    with pytest.raises(sqlite3.IntegrityError):
        add_target("Another Router", "192.168.1.1", db_path)


def test_database_initialized_on_startup(tmp_path):
    db_path = tmp_path / "startup_test.db"

    with patch("app.main.DB_PATH", db_path):
        with TestClient(app):
            assert db_path.exists()

            with sqlite3.connect(db_path) as conn:
                result = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='targets'"
                ).fetchone()

            assert result is not None


from app.database import add_measurement


def test_add_measurement(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    target_id = add_target(
        "Google DNS",
        "8.8.8.8",
        db_path
    )

    measurement_id = add_measurement(
        target_id=target_id,
        reachable=True,
        latency_ms=12.0,
        db_path=db_path
    )

    with sqlite3.connect(db_path) as conn:
        result = conn.execute(
            """
            SELECT target_id, reachable, latency_ms
            FROM measurements
            WHERE id = ?
            """,
            (measurement_id,)
        ).fetchone()

    assert result == (target_id, 1, 12.0)


from app.database import get_measurements


def test_get_measurements(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    target_id = add_target(
        "Google DNS",
        "8.8.8.8",
        db_path
    )

    add_measurement(target_id, True, 12.0, db_path)
    add_measurement(target_id, True, 15.0, db_path)

    measurements = get_measurements(
        target_id,
        db_path=db_path
    )

    assert len(measurements) == 2
    assert measurements[0]["latency_ms"] == 15.0
    assert measurements[1]["latency_ms"] == 12.0
    assert measurements[0]["target_id"] == target_id



def test_measurement_foreign_key(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with pytest.raises(sqlite3.IntegrityError):
        add_measurement(
            target_id=999,
            reachable=True,
            latency_ms=12.0,
            db_path=db_path
        )


def test_measurements_index_created(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        indexes = conn.execute(
            "PRAGMA index_list('measurements')"
        ).fetchall()

    index_names = [row[1] for row in indexes]

    assert (
        "idx_measurements_target_id_id"
        in index_names
    )
