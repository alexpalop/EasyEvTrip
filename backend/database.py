import os
import psycopg2
from psycopg2.extras import RealDictCursor

_DATABASE_URL = os.environ.get("DATABASE_URL", "")


def _conn():
    url = _DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)


def init_db() -> None:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id           SERIAL PRIMARY KEY,
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
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
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (rating, comment, origin, destination, car_category) "
                "VALUES (%s, %s, %s, %s, %s)",
                (rating, comment, origin, destination, car_category),
            )
        con.commit()


def get_all_feedback() -> list[dict]:
    with _conn() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM feedback ORDER BY created_at DESC")
            return [dict(row) for row in cur.fetchall()]
