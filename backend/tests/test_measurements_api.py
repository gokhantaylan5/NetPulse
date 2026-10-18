
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_measurements_api():
    fake_measurements = [
        {
            "id": 1,
            "target_id": 1,
            "reachable": 1,
            "latency_ms": 12.0,
            "timestamp": "2026-10-18 12:20:22"
        }
    ]

    with patch(
        "app.main.get_measurements",
        return_value=fake_measurements
    ) as mock_get:
        response = client.get(
            "/api/targets/1/measurements?limit=10"
        )

    assert response.status_code == 200
    assert response.json() == fake_measurements

    mock_get.assert_called_once_with(
        target_id=1,
        limit=10,
        db_path=mock_get.call_args.kwargs["db_path"]
    )


def test_get_measurements_empty():
    with patch(
        "app.main.get_measurements",
        return_value=[]
    ):
        response = client.get(
            "/api/targets/1/measurements"
        )

    assert response.status_code == 200
    assert response.json() == []


def test_invalid_measurement_limit():
    response = client.get(
        "/api/targets/1/measurements?limit=5000"
    )

    assert response.status_code == 422
