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


        # Network availability incidents
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,

                FOREIGN KEY (target_id)
                    REFERENCES targets(id)
                    ON DELETE CASCADE,

                CHECK (status IN ('open', 'resolved')),

                CHECK (
                    (status = 'open' AND resolved_at IS NULL)
                    OR
                    (status = 'resolved' AND resolved_at IS NOT NULL)
                )
            )
        """)

        # Only one open incident per target.
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_incidents_one_open_per_target
            ON incidents(target_id)
            WHERE status = 'open'
        """)

        # Speed up incident history queries.
        conn.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_incidents_status_opened
            ON incidents(status, opened_at DESC)
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



def open_incident(
    target_id: int,
    db_path: Path = DB_PATH
) -> int:
    """
    Open an incident for a target.

    If an open incident already exists, return its ID.
    """

    with db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO incidents (target_id, status)
            VALUES (?, 'open')
            ON CONFLICT DO NOTHING
            """,
            (target_id,)
        )

        row = conn.execute(
            """
            SELECT id
            FROM incidents
            WHERE target_id = ?
              AND status = 'open'
            """,
            (target_id,)
        ).fetchone()

        if row is None:
            raise RuntimeError(
                "Failed to retrieve open incident."
            )

        return int(row[0])


def resolve_incident(
    target_id: int,
    db_path: Path = DB_PATH
) -> bool:
    """
    Resolve the open incident for a target.

    Returns True if an incident was resolved.
    Returns False if no open incident exists.
    """

    with db_connection(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE incidents
            SET status = 'resolved',
                resolved_at = CURRENT_TIMESTAMP
            WHERE target_id = ?
              AND status = 'open'
            """,
            (target_id,)
        )

        return cursor.rowcount > 0



def get_incidents(
    status: str | None = None,
    db_path: Path = DB_PATH
) -> list[dict]:
    """
    Retrieve monitoring incidents with duration.

    Duration is measured from incident opening:
    - Open: opened_at -> current time
    - Resolved: opened_at -> resolved_at

    duration_seconds represents incident lifetime,
    not necessarily the full network outage duration.
    """

    if status not in (None, "open", "resolved"):
        raise ValueError("Invalid incident status.")

    with db_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row

        query = """
            SELECT
                i.id,
                i.target_id,
                t.name AS target_name,
                t.address AS target_address,
                i.status,
                i.opened_at,
                i.resolved_at,

                CAST(
                    MAX(
                        0,
                        ROUND(
                            (
                                julianday(
                                    COALESCE(
                                        i.resolved_at,
                                        CURRENT_TIMESTAMP
                                    )
                                )
                                - julianday(i.opened_at)
                            ) * 86400
                        )
                    ) AS INTEGER
                ) AS duration_seconds

            FROM incidents i

            JOIN targets t
                ON t.id = i.target_id
        """

        parameters = ()

        if status is not None:
            query += " WHERE i.status = ?"
            parameters = (status,)

        query += " ORDER BY i.opened_at DESC, i.id DESC"

        rows = conn.execute(
            query,
            parameters
        ).fetchall()

        return [dict(row) for row in rows]



def record_monitoring_result(
    target_id: int,
    reachable: bool,
    latency_ms: float | None,
    db_path: Path = DB_PATH
) -> int:
    """
    Save a monitoring result and update its incident state.

    Rules:
    - 3 consecutive failed measurements open an incident.
    - Further failures keep the existing incident open.
    - A successful measurement resolves an open incident.

    The measurement and incident update are atomic.
    """

    with db_connection(db_path) as conn:

        # 1. Save the measurement.
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

        measurement_id = cursor.lastrowid

        # 2. Successful ping: resolve any open incident.
        if reachable:
            conn.execute(
                """
                UPDATE incidents
                SET status = 'resolved',
                    resolved_at = CURRENT_TIMESTAMP
                WHERE target_id = ?
                  AND status = 'open'
                """,
                (target_id,)
            )

        else:
            # 3. Check the last three recorded results.
            recent = conn.execute(
                """
                SELECT reachable
                FROM measurements
                WHERE target_id = ?
                ORDER BY id DESC
                LIMIT 3
                """,
                (target_id,)
            ).fetchall()

            # 4. Open an incident after three failures.
            if (
                len(recent) == 3
                and all(row[0] == 0 for row in recent)
            ):
                conn.execute(
                    """
                    INSERT INTO incidents (
                        target_id,
                        status
                    )
                    VALUES (?, 'open')
                    ON CONFLICT DO NOTHING
                    """,
                    (target_id,)
                )

        return int(measurement_id)
