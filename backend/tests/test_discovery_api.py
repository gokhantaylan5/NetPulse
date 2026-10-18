
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.monitoring.ping import PingResult


client = TestClient(app)

FAKE_NETWORKS = [
    {
        "interface": "Wi-Fi",
        "ip": "192.168.1.19",
        "netmask": "255.255.255.0",
        "network": "192.168.1.0/24",
        "is_primary": True
    }
]


def test_discovery_success():
    fake_devices = [
        PingResult("192.168.1.1", True, 4.0),
        PingResult("192.168.1.19", True, None)
    ]

    with (
        patch(
            "app.main.detect_networks",
            return_value=FAKE_NETWORKS
        ),
        patch(
            "app.main.discover_hosts",
            return_value=fake_devices
        ) as mock_scan
    ):
        response = client.post(
            "/api/network/discover",
            json={"network": "192.168.1.0/24"}
        )

    assert response.status_code == 200

    data = response.json()
    assert data["discovered_count"] == 2
    assert len(data["devices"]) == 2
    assert data["devices"][0]["ip"] == "192.168.1.1"

    mock_scan.assert_called_once_with(
        "192.168.1.0/24"
    )


def test_discovery_rejects_unrelated_network():
    with (
        patch(
            "app.main.detect_networks",
            return_value=FAKE_NETWORKS
        ),
        patch("app.main.discover_hosts") as mock_scan
    ):
        response = client.post(
            "/api/network/discover",
            json={"network": "192.168.2.0/24"}
        )

    assert response.status_code == 403
    mock_scan.assert_not_called()


def test_discovery_rejects_large_network():
    response = client.post(
        "/api/network/discover",
        json={"network": "192.168.0.0/16"}
    )

    assert response.status_code == 400


def test_discovery_rejects_public_network():
    response = client.post(
        "/api/network/discover",
        json={"network": "8.8.8.0/24"}
    )

    assert response.status_code == 403


def test_discovery_rejects_invalid_cidr():
    response = client.post(
        "/api/network/discover",
        json={"network": "invalid-network"}
    )

    assert response.status_code == 422
