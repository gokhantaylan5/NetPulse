
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_network_interfaces():
    fake_networks = [
        {
            "interface": "Wi-Fi",
            "ip": "192.168.1.19",
            "netmask": "255.255.255.0",
            "network": "192.168.1.0/24",
            "is_primary": True
        }
    ]

    with patch(
        "app.main.detect_networks",
        return_value=fake_networks
    ):
        response = client.get("/api/network/interfaces")

    assert response.status_code == 200
    assert response.json() == fake_networks


def test_no_network_interfaces():
    with patch(
        "app.main.detect_networks",
        return_value=[]
    ):
        response = client.get("/api/network/interfaces")

    assert response.status_code == 200
    assert response.json() == []
