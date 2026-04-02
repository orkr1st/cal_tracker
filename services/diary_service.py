"""SQLite food diary."""

import sqlite3
from contextlib import contextmanager
from datetime import date

import config


def init_db() -> None:
    """Create diary table if it does not exist."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS diary (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                date        TEXT    NOT NULL,
                name        TEXT    NOT NULL,
                quantity    TEXT,
                calories    REAL,
                protein_g   REAL,
                carbs_g     REAL,
                fat_g       REAL,
                estimated   INTEGER NOT NULL DEFAULT 0
            )
        """)


@contextmanager
def _conn():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def add_entry(
    name: str,
    quantity: str | None,
    calories: float | None,
    protein_g: float | None,
    carbs_g: float | None,
    fat_g: float | None,
    estimated: bool = False,
) -> int:
    """Insert a diary entry and return its id."""
    today = date.today().isoformat()
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO diary
                   (date, name, quantity, calories, protein_g, carbs_g, fat_g, estimated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (today, name, quantity, calories, protein_g, carbs_g, fat_g, int(estimated)),
        )
        return cur.lastrowid


def get_entries(for_date: str | None = None) -> list[dict]:
    """Return all diary entries for *for_date* (ISO string, defaults to today)."""
    if for_date is None:
        for_date = date.today().isoformat()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM diary WHERE date = ? ORDER BY logged_at",
            (for_date,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_entry(entry_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM diary WHERE id = ?", (entry_id,))


def get_history(days: int = 30) -> list[dict]:
    """Return per-day aggregated totals for the last *days* days.

    Only days that have at least one entry are included.
    Results are ordered oldest → newest.
    """
    from datetime import timedelta

    end = date.today()
    start = end - timedelta(days=days - 1)
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT date,
                   COALESCE(SUM(calories), 0)  AS calories,
                   COALESCE(SUM(protein_g), 0) AS protein_g,
                   COALESCE(SUM(carbs_g), 0)   AS carbs_g,
                   COALESCE(SUM(fat_g), 0)     AS fat_g,
                   COUNT(*)                     AS entry_count
            FROM   diary
            WHERE  date BETWEEN ? AND ?
            GROUP  BY date
            ORDER  BY date
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    return [dict(r) for r in rows]
