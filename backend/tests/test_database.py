
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
