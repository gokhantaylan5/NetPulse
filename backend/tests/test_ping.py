
from unittest.mock import patch
from subprocess import CompletedProcess
from app.monitoring.ping import measure_ping


from app.monitoring.ping import ping_host


def test_ping_success():
    fake_result = CompletedProcess(
        args=["ping"],
        returncode=0
    )

    with patch(
        "app.monitoring.ping.subprocess.run",
        return_value=fake_result
    ):
        result = ping_host("127.0.0.1")

    assert result is True


def test_ping_failure():
    fake_result = CompletedProcess(
        args=["ping"],
        returncode=1
    )

    with patch(
        "app.monitoring.ping.subprocess.run",
        return_value=fake_result
    ):
        result = ping_host("127.0.0.1")

    assert result is False


from app.monitoring.ping import parse_latency


def test_parse_latency_english():
    output = "Reply from 192.168.1.1: time=12ms TTL=64"

    assert parse_latency(output) == 12.0


def test_parse_latency_turkish():
    output = "Yanıt: Süre=8ms TTL=64"

    assert parse_latency(output) == 8.0


def test_parse_latency_missing():
    output = "Request timed out."

    assert parse_latency(output) is None



def test_measure_ping_success():
    fake_result = CompletedProcess(
        args=["ping"],
        returncode=0,
        stdout="Reply from 192.168.1.1: time=12ms TTL=64",
        stderr=""
    )

    with patch(
        "app.monitoring.ping.subprocess.run",
        return_value=fake_result
    ):
        result = measure_ping("192.168.1.1")

    assert result.host == "192.168.1.1"
    assert result.reachable is True
    assert result.latency_ms == 12.0


def test_measure_ping_failure():
    fake_result = CompletedProcess(
        args=["ping"],
        returncode=1,
        stdout="Request timed out.",
        stderr=""
    )

    with patch(
        "app.monitoring.ping.subprocess.run",
        return_value=fake_result
    ):
        result = measure_ping("192.168.1.1")

    assert result.reachable is False
    assert result.latency_ms is None
