
import sqlite3

import pytest

from app.database import (
    add_target,
    get_incidents,
    get_measurements,
    get_targets,
    init_db,
    record_monitoring_result
)

from app.monitoring.scheduler import MonitoringScheduler
from app.monitoring.ping import PingResult


@pytest.fixture
def target_db(tmp_path):
    db_path = tmp_path / "monitoring.db"
    init_db(db_path)

    target_id = add_target(
        "Home Router",
        "192.168.1.1",
        db_path
    )

    return db_path, target_id


def test_incident_opens_after_three_failures(target_db):
    db_path, target_id = target_db

    for _ in range(2):
        record_monitoring_result(
            target_id, False, None, db_path
        )

    assert get_incidents(db_path=db_path) == []

    record_monitoring_result(
        target_id, False, None, db_path
    )

    incidents = get_incidents(
        status="open",
        db_path=db_path
    )

    assert len(incidents) == 1
    assert incidents[0]["target_id"] == target_id


def test_extended_outage_does_not_duplicate_incidents(target_db):
    db_path, target_id = target_db

    for _ in range(8):
        record_monitoring_result(
            target_id, False, None, db_path
        )

    incidents = get_incidents(db_path=db_path)

    assert len(incidents) == 1
    assert incidents[0]["status"] == "open"


def test_success_resolves_incident(target_db):
    db_path, target_id = target_db

    for _ in range(3):
        record_monitoring_result(
            target_id, False, None, db_path
        )

    record_monitoring_result(
        target_id, True, 12.5, db_path
    )

    assert get_incidents(
        status="open",
        db_path=db_path
    ) == []

    resolved = get_incidents(
        status="resolved",
        db_path=db_path
    )

    assert len(resolved) == 1
    assert resolved[0]["resolved_at"] is not None


def test_success_resets_failure_streak(target_db):
    db_path, target_id = target_db

    for _ in range(2):
        record_monitoring_result(
            target_id, False, None, db_path
        )

    record_monitoring_result(
        target_id, True, 10.0, db_path
    )

    for _ in range(2):
        record_monitoring_result(
            target_id, False, None, db_path
        )

    assert get_incidents(db_path=db_path) == []

    record_monitoring_result(
        target_id, False, None, db_path
    )

    assert len(get_incidents(db_path=db_path)) == 1


def test_new_incident_after_recovery(target_db):
    db_path, target_id = target_db

    for _ in range(3):
        record_monitoring_result(
            target_id, False, None, db_path
        )

    first = get_incidents(db_path=db_path)[0]["id"]

    record_monitoring_result(
        target_id, True, 8.5, db_path
    )

    for _ in range(3):
        record_monitoring_result(
            target_id, False, None, db_path
        )

    incidents = get_incidents(db_path=db_path)

    assert len(incidents) == 2

    active = get_incidents(
        status="open",
        db_path=db_path
    )

    assert len(active) == 1
    assert active[0]["id"] != first


def test_failure_streak_survives_scheduler_restart(target_db):
    db_path, target_id = target_db

    def make_scheduler():
        def fake_ping(host):
            return PingResult(
                host=host,
                reachable=False,
                latency_ms=None
            )

        def writer(target_id, reachable, latency):
            return record_monitoring_result(
                target_id,
                reachable,
                latency,
                db_path
            )

        return MonitoringScheduler(
            target_provider=lambda: get_targets(db_path),
            ping_fn=fake_ping,
            measurement_writer=writer
        )

    first_scheduler = make_scheduler()

    first_scheduler.run_once()
    first_scheduler.run_once()

    assert get_incidents(db_path=db_path) == []

    # Simulate restarting the scheduler process.
    restarted_scheduler = make_scheduler()
    restarted_scheduler.run_once()

    incidents = get_incidents(
        status="open",
        db_path=db_path
    )

    assert len(incidents) == 1
    assert incidents[0]["target_id"] == target_id


def test_failure_streaks_are_independent(tmp_path):
    db_path = tmp_path / "independent.db"
    init_db(db_path)

    router = add_target(
        "Router", "192.168.1.1", db_path
    )

    dns = add_target(
        "DNS", "8.8.8.8", db_path
    )

    for _ in range(2):
        record_monitoring_result(
            router, False, None, db_path
        )
        record_monitoring_result(
            dns, False, None, db_path
        )

    record_monitoring_result(
        router, False, None, db_path
    )

    incidents = get_incidents(
        status="open",
        db_path=db_path
    )

    assert len(incidents) == 1
    assert incidents[0]["target_id"] == router

    record_monitoring_result(
        dns, False, None, db_path
    )

    incidents = get_incidents(
        status="open",
        db_path=db_path
    )

    assert len(incidents) == 2


def test_measurement_rolls_back_if_incident_update_fails(
    target_db
):
    db_path, target_id = target_db

    # Simulate a database schema failure.
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE incidents")

    with pytest.raises(sqlite3.OperationalError):
        record_monitoring_result(
            target_id,
            True,
            10.0,
            db_path
        )

    # Measurement must not be stored alone.
    measurements = get_measurements(
        target_id,
        db_path=db_path
    )

    assert measurements == []
