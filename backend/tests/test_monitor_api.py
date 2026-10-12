
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.monitoring.ping import PingResult

client = TestClient(app)


def test_ping_api_success():
    fake_result = PingResult(
        host="8.8.8.8",
        reachable=True,
        latency_ms=25.0
    )

    with patch(
        "app.main.measure_ping",
        return_value=fake_result
    ):
        response = client.get(
            "/api/monitor/ping",
            params={"host": "8.8.8.8"}
        )

    assert response.status_code == 200
    assert response.json() == {
        "host": "8.8.8.8",
        "reachable": True,
        "latency_ms": 25.0
    }


def test_ping_api_invalid_ip():
    response = client.get(
        "/api/monitor/ping",
        params={"host": "invalid-host"}
    )

    assert response.status_code == 422
