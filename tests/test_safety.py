"""Safety checks: the agent must never be able to change the database."""
import sqlite3

from src.sql_agent import run_query, validate_sql


def blocked(func, *args):
    try:
        func(*args)
    except (ValueError, sqlite3.Error):
        return True
    return False


def test_validator_blocks_writes():
    for bad in [
        "DROP TABLE Track",
        "DELETE FROM Track",
        "UPDATE Track SET Name = 'x'",
        "SELECT 1; DROP TABLE Track",
        "PRAGMA table_info(Track)",
    ]:
        assert blocked(validate_sql, bad), f"not blocked: {bad}"


def test_validator_allows_keywords_inside_text():
    validate_sql("SELECT * FROM Track WHERE Name LIKE '%update%'")


def test_database_is_read_only_even_without_validator():
    assert blocked(run_query, "INSERT INTO Genre (Name) VALUES ('Test')")


def test_row_limit():
    columns, rows = run_query("SELECT * FROM Track")
    assert len(rows) == 100


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_"):
            func()
            print("OK:", name)