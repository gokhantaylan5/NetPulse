
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_monitoring_summary_api():
    fake_summary = {
        "total_targets": 3,
        "online_devices": 2,
        "offline_devices": 1,
        "unknown_devices": 0,
        "average_latency_ms": 14.0
    }

    with patch(
        "app.main.get_monitoring_summary",
        return_value=fake_summary
    ) as mock_summary:
        response = client.get("/api/monitor/summary")

    assert response.status_code == 200
    assert response.json() == fake_summary
    mock_summary.assert_called_once()
