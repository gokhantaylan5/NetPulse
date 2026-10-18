
import pytest

from app.monitoring.discovery import discover_hosts
from app.monitoring.ping import PingResult


def test_discover_reachable_hosts():
    checked = []

    def fake_ping(host: str) -> PingResult:
        checked.append(host)

        reachable = host.endswith((".1", ".3"))

        return PingResult(
            host=host,
            reachable=reachable,
            latency_ms=5.0 if reachable else None
        )

    results = discover_hosts(
        "192.168.1.0/29",
        ping_fn=fake_ping
    )

    assert len(checked) == 6
    assert [result.host for result in results] == [
        "192.168.1.1",
        "192.168.1.3"
    ]


def test_reject_public_network():
    with pytest.raises(ValueError):
        discover_hosts("8.8.8.0/24")


def test_reject_large_network():
    with pytest.raises(ValueError):
        discover_hosts("192.168.0.0/16")


def test_reject_invalid_network():
    with pytest.raises(ValueError):
        discover_hosts("invalid-network")
