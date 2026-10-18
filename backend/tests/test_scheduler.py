
import pytest

from threading import Event

from app.monitoring.scheduler import MonitoringScheduler
from app.monitoring.ping import PingResult


def test_scheduler_run_once():
    targets = [
        {"address": "192.168.1.1"},
        {"address": "8.8.8.8"}
    ]

    checked = []

    def fake_ping(host):
        checked.append(host)

        return PingResult(
            host=host,
            reachable=True,
            latency_ms=5.0
        )

    scheduler = MonitoringScheduler(
        target_provider=lambda: targets,
        ping_fn=fake_ping
    )

    results = scheduler.run_once()

    assert checked == ["192.168.1.1", "8.8.8.8"]
    assert len(results) == 2
    assert all(result.reachable for result in results)


def test_scheduler_with_no_targets():
    scheduler = MonitoringScheduler(
        target_provider=lambda: [],
        ping_fn=lambda host: None
    )

    assert scheduler.run_once() == []


def test_scheduler_stops():
    stop_event = Event()
    received = []

    def fake_ping(host):
        return PingResult(host, True, 4.0)

    scheduler = MonitoringScheduler(
        interval_seconds=10,
        target_provider=lambda: [{"address": "8.8.8.8"}],
        ping_fn=fake_ping
    )

    def collect_results(results):
        received.extend(results)
        stop_event.set()

    scheduler.run(stop_event, collect_results)

    assert len(received) == 1
    assert stop_event.is_set()


def test_invalid_interval():
    with pytest.raises(ValueError):
        MonitoringScheduler(interval_seconds=0)



import sqlite3

from app.database import (
    init_db,
    add_target,
    get_targets,
    add_measurement
)


def test_scheduler_saves_measurement(tmp_path):
    db_path = tmp_path / "scheduler_test.db"
    init_db(db_path)

    target_id = add_target(
        "Google DNS",
        "8.8.8.8",
        db_path
    )

    def fake_ping(host):
        return PingResult(
            host=host,
            reachable=True,
            latency_ms=12.5
        )

    def save_measurement(target_id, reachable, latency):
        return add_measurement(
            target_id,
            reachable,
            latency,
            db_path=db_path
        )

    scheduler = MonitoringScheduler(
        target_provider=lambda: get_targets(db_path),
        ping_fn=fake_ping,
        measurement_writer=save_measurement
    )

    scheduler.run_once()

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT target_id, reachable, latency_ms
            FROM measurements
            """
        ).fetchone()

    assert row == (target_id, 1, 12.5)
