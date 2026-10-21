from contextlib import contextmanager
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "netpulse.db"


@contextmanager
def db_connection(db_path: Path):
    conn = sqlite3.connect(db_path, timeout=5)

    try:
        conn.execute("PRAGMA foreign_keys = ON")

        with conn:
            yield conn

    finally:
        conn.close()




def init_db(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with db_connection(db_path) as conn:
        # Registered network targets
        conn.execute("""
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Historical monitoring results
        conn.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL,
                reachable INTEGER NOT NULL,
                latency_ms REAL,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (target_id)
                    REFERENCES targets(id)
            )
        """)


        conn.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_measurements_target_id_id
            ON measurements(target_id, id DESC)
        """)




def add_target(name: str, address: str, db_path: Path = DB_PATH) -> int:
    with db_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO targets (name, address)
            VALUES (?, ?)
            """,
            (name, address)
        )
        

        return cursor.lastrowid


def get_targets(db_path: Path = DB_PATH) -> list[dict]:
    with db_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """
            SELECT id, name, address, created_at
            FROM targets
            ORDER BY id
            """
        )

        return [dict(row) for row in cursor.fetchall()]



def add_measurement(
    target_id: int,
    reachable: bool,
    latency_ms: float | None,
    db_path: Path = DB_PATH
) -> int:

    with db_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO measurements (
                target_id,
                reachable,
                latency_ms
            )
            VALUES (?, ?, ?)
            """,
            (
                target_id,
                int(reachable),
                latency_ms
            )
        )

        return cursor.lastrowid



def get_measurements(
    target_id: int,
    limit: int = 100,
    db_path: Path = DB_PATH
) -> list[dict]:

    if not 1 <= limit <= 1000:
        raise ValueError("Limit must be between 1 and 1000.")

    with db_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """
            SELECT id, target_id, reachable,
                   latency_ms, timestamp
            FROM measurements
            WHERE target_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (target_id, limit)
        )

        return [dict(row) for row in cursor.fetchall()]



def get_monitoring_summary(
    db_path: Path = DB_PATH
) -> dict:
    """
    Calculate monitoring statistics using the latest
    measurement for each registered target.

    Measurements older than 45 seconds are considered stale.
    """

    with db_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute("""
            SELECT
                COUNT(*) AS total_targets,

                COALESCE(SUM(
                    CASE
                        WHEN m.timestamp >= datetime('now', '-45 seconds')
                             AND m.timestamp <= CURRENT_TIMESTAMP
                             AND m.reachable = 1
                        THEN 1 ELSE 0
                    END
                ), 0) AS online_devices,

                COALESCE(SUM(
                    CASE
                        WHEN m.timestamp >= datetime('now', '-45 seconds')
                             AND m.timestamp <= CURRENT_TIMESTAMP
                             AND m.reachable = 0
                        THEN 1 ELSE 0
                    END
                ), 0) AS offline_devices,

                ROUND(AVG(
                    CASE
                        WHEN m.timestamp >= datetime('now', '-45 seconds')
                             AND m.timestamp <= CURRENT_TIMESTAMP
                             AND m.reachable = 1
                        THEN m.latency_ms
                    END
                ), 1) AS average_latency_ms

            FROM targets t

            LEFT JOIN measurements m
                ON m.id = (
                    SELECT id
                    FROM measurements
                    WHERE target_id = t.id
                    ORDER BY id DESC
                    LIMIT 1
                )
        """).fetchone()

        result = dict(row)

        result["unknown_devices"] = (
            result["total_targets"]
            - result["online_devices"]
            - result["offline_devices"]
        )

        return result


def delete_target(
    target_id: int,
    db_path: Path = DB_PATH
) -> bool:
    """
    Delete a registered target and its measurement history.

    Returns True if deleted, False if target does not exist.
    """

    with db_connection(db_path) as conn:
        exists = conn.execute(
            "SELECT 1 FROM targets WHERE id = ?",
            (target_id,)
        ).fetchone()

        if exists is None:
            return False

        conn.execute(
            "DELETE FROM measurements WHERE target_id = ?",
            (target_id,)
        )

        conn.execute(
            "DELETE FROM targets WHERE id = ?",
            (target_id,)
        )

        return True
