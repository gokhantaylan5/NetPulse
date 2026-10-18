
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "netpulse.db"



def init_db(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
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



def add_target(name: str, address: str, db_path: Path = DB_PATH) -> int:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO targets (name, address)
            VALUES (?, ?)
            """,
            (name, address)
        )
        

        return cursor.lastrowid


def get_targets(db_path: Path = DB_PATH) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
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

    with sqlite3.connect(db_path) as conn:
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

    with sqlite3.connect(db_path) as conn:
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
