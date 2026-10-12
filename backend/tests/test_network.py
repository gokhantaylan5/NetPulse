
from app.monitoring.network import calculate_network


def test_calculate_home_network():
    result = calculate_network(
        "192.168.1.25",
        "255.255.255.0"
    )

    assert result == "192.168.1.0/24"


def test_calculate_large_network():
    result = calculate_network(
        "10.0.5.20",
        "255.255.0.0"
    )

    assert result == "10.0.0.0/16"


def test_invalid_netmask():
    result = calculate_network(
        "192.168.1.25",
        "invalid"
    )

    assert result is None


def test_ignore_loopback():
    result = calculate_network(
        "127.0.0.1",
        "255.0.0.0"
    )

    assert result is None
