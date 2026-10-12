
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db

client = TestClient(app)


def test_create_target(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with patch("app.main.DB_PATH", db_path):
        response = client.post(
            "/api/targets",
            json={
                "name": "Home Router",
                "address": "192.168.1.1"
            }
        )

    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["name"] == "Home Router"
    assert response.json()["address"] == "192.168.1.1"


def test_duplicate_target(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with patch("app.main.DB_PATH", db_path):
        payload = {
            "name": "Home Router",
            "address": "192.168.1.1"
        }

        first = client.post("/api/targets", json=payload)
        second = client.post("/api/targets", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_invalid_target():
    response = client.post(
        "/api/targets",
        json={
            "name": "Invalid Device",
            "address": "not-an-ip"
        }
    )

    assert response.status_code == 422



def test_get_targets_empty(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with patch("app.main.DB_PATH", db_path):
        response = client.get("/api/targets")

    assert response.status_code == 200
    assert response.json() == []


def test_get_targets_with_data(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with patch("app.main.DB_PATH", db_path):
        client.post(
            "/api/targets",
            json={
                "name": "Home Router",
                "address": "192.168.1.1"
            }
        )

        response = client.get("/api/targets")

    assert response.status_code == 200

    targets = response.json()

    assert len(targets) == 1
    assert targets[0]["name"] == "Home Router"
    assert targets[0]["address"] == "192.168.1.1"
    assert targets[0]["id"] == 1
    assert "created_at" in targets[0]
