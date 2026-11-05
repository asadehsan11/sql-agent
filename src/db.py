"""SQLite log of every question the agent receives."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("data/query_log.db")


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS query_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            question TEXT NOT NULL,
            sql TEXT,
            row_count INTEGER,
            error TEXT,
            latency_sec REAL
        )"""
    )
    return conn


def log_query(question, sql, row_count, error, latency_sec):
    """Save one question and what happened."""
    conn = _connect()
    try:
        with conn:
            conn.execute(
                "INSERT INTO query_log "
                "(created_at, question, sql, row_count, error, latency_sec) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    question,
                    sql,
                    row_count,
                    error,
                    latency_sec,
                ),
            )
    finally:
        conn.close()


def get_history(limit=20):
    """Return the latest rows, newest first."""
    conn = _connect()
    try:
        return conn.execute(
            "SELECT created_at, question, sql, row_count, error, latency_sec "
            "FROM query_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()