
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.database import DB_PATH, db_connection


MAX_GAP_SECONDS = 30


def _parse_timestamp(value: str) -> datetime:
    """SQLite timestamps are stored in UTC."""
    return datetime.fromisoformat(value).replace(
        tzinfo=timezone.utc
    )


def _format_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def get_target_availability(
    target_id: int,
    hours: int = 24,
    db_path: Path = DB_PATH,
    now: datetime | None = None,
) -> dict | None:
    """
    Calculate observed monitoring availability.

    Check success rate is based on recorded measurements.

    Coverage includes only intervals between consecutive
    measurements separated by at most MAX_GAP_SECONDS.

    Gaps are not automatically considered online or offline.
    """

    if not 1 <= hours <= 168:
        raise ValueError("Hours must be between 1 and 168.")

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware.")

    now = now.astimezone(timezone.utc)
    start = now - timedelta(hours=hours)

    start_text = _format_timestamp(start)
    end_text = _format_timestamp(now)

    with db_connection(db_path) as conn:

        target = conn.execute(
            """
            SELECT id, name, address
            FROM targets
            WHERE id = ?
            """,
            (target_id,)
        ).fetchone()

        if target is None:
            return None

        # Measurements inside the requested window.
        measurements = conn.execute(
            """
            SELECT id, reachable, timestamp
            FROM measurements
            WHERE target_id = ?
              AND timestamp >= ?
              AND timestamp <= ?
            ORDER BY timestamp ASC, id ASC
            """,
            (target_id, start_text, end_text)
        ).fetchall()

        # One measurement before the window is used only
        # to calculate coverage at the left boundary.
        previous = conn.execute(
            """
            SELECT id, reachable, timestamp
            FROM measurements
            WHERE target_id = ?
              AND timestamp < ?
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
            """,
            (target_id, start_text)
        ).fetchone()

    total_checks = len(measurements)

    successful_checks = sum(
        1 for row in measurements if row[1] == 1
    )

    failed_checks = total_checks - successful_checks

    success_rate = (
        round(successful_checks / total_checks * 100, 2)
        if total_checks > 0
        else None
    )

    timeline = (
        [previous] if previous is not None else []
    ) + list(measurements)

    observed_seconds = 0.0
    gaps_detected = 0

    for left, right in zip(timeline, timeline[1:]):

        left_time = _parse_timestamp(left[2])
        right_time = _parse_timestamp(right[2])

        gap_seconds = (
            right_time - left_time
        ).total_seconds()

        if gap_seconds <= 0:
            continue

        if gap_seconds > MAX_GAP_SECONDS:
            gaps_detected += 1
            continue

        # Clip the observed interval to the selected window.
        interval_start = max(left_time, start)
        interval_end = min(right_time, now)

        if interval_end > interval_start:
            observed_seconds += (
                interval_end - interval_start
            ).total_seconds()

    window_seconds = hours * 3600

    observed_seconds = min(
        window_seconds,
        round(observed_seconds)
    )

    unknown_seconds = (
        window_seconds - observed_seconds
    )

    coverage_percent = round(
        observed_seconds / window_seconds * 100,
        2
    )

    return {
        "target_id": target[0],
        "target_name": target[1],
        "target_address": target[2],

        "window_hours": hours,
        "window_start": start.isoformat(),
        "window_end": now.isoformat(),

        "total_checks": total_checks,
        "successful_checks": successful_checks,
        "failed_checks": failed_checks,

        "check_success_rate_percent": success_rate,
        "measurement_coverage_percent": coverage_percent,

        "observed_seconds": observed_seconds,
        "unknown_seconds": unknown_seconds,

        "gaps_detected": gaps_detected,
        "max_gap_seconds": MAX_GAP_SECONDS
    }
