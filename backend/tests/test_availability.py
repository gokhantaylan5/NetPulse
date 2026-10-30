
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.database import (
    add_target,
    db_connection,
    init_db,
)

from app.main import app
from app.monitoring.availability import (
    get_target_availability,
)


FIXED_NOW = datetime(
    2026, 10, 30, 12, 0, 0,
    tzinfo=timezone.utc
)


@pytest.fixture
def availability_db(tmp_path):
    db_path = tmp_path / "availability.db"
    init_db(db_path)

    target_id = add_target(
        "Test Router",
        "192.168.1.1",
        db_path
    )

    return db_path, target_id


def insert_measurement(
    db_path,
    target_id,
    seconds_before,
    reachable,
):
    timestamp = (
        FIXED_NOW - timedelta(seconds=seconds_before)
    ).strftime("%Y-%m-%d %H:%M:%S")

    with db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO measurements (
                target_id, reachable, latency_ms, timestamp
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                target_id,
                int(reachable),
                10.0 if reachable else None,
                timestamp
            )
        )


def test_no_measurements(availability_db):
    db_path, target_id = availability_db

    result = get_target_availability(
        target_id,
        hours=1,
        db_path=db_path,
        now=FIXED_NOW
    )

    assert result["total_checks"] == 0
    assert result["successful_checks"] == 0
    assert result["failed_checks"] == 0
    assert result["check_success_rate_percent"] is None
    assert result["measurement_coverage_percent"] == 0
    assert result["observed_seconds"] == 0


def test_check_success_rate(availability_db):
    db_path, target_id = availability_db

    insert_measurement(db_path, target_id, 30, True)
    insert_measurement(db_path, target_id, 20, False)
    insert_measurement(db_path, target_id, 10, True)

    result = get_target_availability(
        target_id,
        hours=1,
        db_path=db_path,
        now=FIXED_NOW
    )

    assert result["total_checks"] == 3
    assert result["successful_checks"] == 2
    assert result["failed_checks"] == 1
    assert result["check_success_rate_percent"] == 66.67

    # Two consecutive 10-second intervals.
    assert result["observed_seconds"] == 20
    assert result["measurement_coverage_percent"] == 0.56


def test_long_gap_is_not_counted_as_coverage(
    availability_db
):
    db_path, target_id = availability_db

    insert_measurement(db_path, target_id, 310, True)
    insert_measurement(db_path, target_id, 20, False)
    insert_measurement(db_path, target_id, 10, True)

    result = get_target_availability(
        target_id,
        hours=1,
        db_path=db_path,
        now=FIXED_NOW
    )

    assert result["total_checks"] == 3
    assert result["gaps_detected"] == 1

    # The 290-second gap is unknown, not online.
    assert result["observed_seconds"] == 10


def test_window_boundary_is_clipped(availability_db):
    db_path, target_id = availability_db

    # 10 seconds before the one-hour window.
    insert_measurement(db_path, target_id, 3610, True)

    # 10 seconds after the window begins.
    insert_measurement(db_path, target_id, 3590, True)

    result = get_target_availability(
        target_id,
        hours=1,
        db_path=db_path,
        now=FIXED_NOW
    )

    # Only the measurement inside the window counts.
    assert result["total_checks"] == 1

    # The 20-second interval overlaps the window by 10s.
    assert result["observed_seconds"] == 10


def test_unknown_target(availability_db):
    db_path, _ = availability_db

    result = get_target_availability(
        target_id=9999,
        db_path=db_path,
        now=FIXED_NOW
    )

    assert result is None


def test_invalid_hours(availability_db):
    db_path, target_id = availability_db

    with pytest.raises(ValueError):
        get_target_availability(
            target_id,
            hours=0,
            db_path=db_path
        )

    with pytest.raises(ValueError):
        get_target_availability(
            target_id,
            hours=169,
            db_path=db_path
        )


def test_availability_api(availability_db):
    db_path, target_id = availability_db

    with patch("app.main.DB_PATH", db_path):
        with TestClient(app) as client:
            response = client.get(
                f"/api/targets/{target_id}/availability?hours=24"
            )

            missing = client.get(
                "/api/targets/9999/availability"
            )

            invalid = client.get(
                f"/api/targets/{target_id}/availability?hours=0"
            )

    assert response.status_code == 200

    data = response.json()

    assert data["target_id"] == target_id
    assert data["window_hours"] == 24
    assert data["total_checks"] == 0
    assert data["check_success_rate_percent"] is None

    assert missing.status_code == 404
    assert invalid.status_code == 422
