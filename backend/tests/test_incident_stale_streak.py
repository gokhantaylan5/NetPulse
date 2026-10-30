import pytest

from app.database import (
    add_target,
    db_connection,
    get_incidents,
    init_db,
    record_monitoring_result,
)


@pytest.fixture
def target_db(tmp_path):
    db_path = tmp_path / "stale_streak.db"
    init_db(db_path)
    target_id = add_target("Test Router", "192.168.1.1", db_path)
    return db_path, target_id


def record_failure(db_path, target_id):
    return record_monitoring_result(target_id, False, None, db_path)


def test_three_fresh_failures_open_incident(target_db):
    db_path, target_id = target_db

    for _ in range(3):
        record_failure(db_path, target_id)

    assert len(get_incidents(status="open", db_path=db_path)) == 1


def test_old_failures_do_not_combine_with_new_ones(target_db):
    db_path, target_id = target_db

    record_failure(db_path, target_id)
    record_failure(db_path, target_id)

    with db_connection(db_path) as conn:
        conn.execute(
            "UPDATE measurements SET timestamp = datetime('now', '-1 hour') "
            "WHERE target_id = ?",
            (target_id,),
        )

    record_failure(db_path, target_id)
    assert get_incidents(db_path=db_path) == []

    record_failure(db_path, target_id)
    assert get_incidents(db_path=db_path) == []

    record_failure(db_path, target_id)
    assert len(get_incidents(status="open", db_path=db_path)) == 1


def test_failure_gap_over_threshold(target_db):
    db_path, target_id = target_db

    record_failure(db_path, target_id)
    record_failure(db_path, target_id)

    with db_connection(db_path) as conn:
        conn.execute(
            "UPDATE measurements SET timestamp = datetime('now', '-60 seconds') "
            "WHERE target_id = ?",
            (target_id,),
        )

    record_failure(db_path, target_id)
    assert get_incidents(status="open", db_path=db_path) == []
