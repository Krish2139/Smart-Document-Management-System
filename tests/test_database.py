from sqlalchemy import text
from backend.database.session import engine, check_db_connection, SessionLocal


def test_sqlite_connectivity():
    """Verify that SQLite connection check returns True."""
    assert check_db_connection() is True


def test_sqlite_query_execution():
    """Verify executing queries and session handling on SQLite."""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 42 as test_val")).fetchone()
        assert result is not None
        assert result[0] == 42
    finally:
        db.close()
