import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "feedback.db"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT    DEFAULT (datetime('now')),
                rating       INTEGER NOT NULL,
                comment      TEXT,
                origin       TEXT,
                destination  TEXT,
                car_category TEXT
            )
        """)
        con.commit()


def store_feedback(
    rating: int,
    comment: str | None,
    origin: str | None,
    destination: str | None,
    car_category: str | None,
) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO feedback (rating, comment, origin, destination, car_category) VALUES (?, ?, ?, ?, ?)",
            (rating, comment, origin, destination, car_category),
        )
        con.commit()
