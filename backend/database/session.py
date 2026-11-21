from typing import Generator
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session

from backend.config.settings import settings
from backend.database.base import Base
from backend.models.category import Category
from backend.models.document import Document
from backend.models.activity import Activity
from backend.models.settings import SystemSetting
from backend.models.user import User
from backend.utils.logger import logger

# SQLite specific connect args: check_same_thread=False allows multiple threads
connect_args = {"check_same_thread": False, "timeout": 30} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Enable WAL (Write-Ahead Logging) and concurrency pragmas for SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Test connection to the database by executing a simple query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def init_db() -> None:
    """Initialize database tables and ensure schema consistency across versions."""
    try:
        Base.metadata.create_all(bind=engine)

        # Self-healing column migration for SQLite
        if engine.dialect.name == "sqlite":
            with engine.connect() as conn:
                # 1. documents table
                doc_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(documents)")).fetchall()]
                if doc_cols:
                    if "file_extension" not in doc_cols:
                        conn.execute(text("ALTER TABLE documents ADD COLUMN file_extension VARCHAR(20) DEFAULT ''"))
                        conn.commit()
                        logger.info("Migrated schema: Added 'file_extension' to 'documents' table.")
                    if "is_manually_categorized" not in doc_cols:
                        conn.execute(text("ALTER TABLE documents ADD COLUMN is_manually_categorized BOOLEAN DEFAULT 0"))
                        conn.commit()
                        logger.info("Migrated schema: Added 'is_manually_categorized' to 'documents' table.")
                    if "user_id" not in doc_cols:
                        conn.execute(text("ALTER TABLE documents ADD COLUMN user_id VARCHAR(36) DEFAULT NULL"))
                        conn.commit()
                        logger.info("Migrated schema: Added 'user_id' to 'documents' table.")
                    if "uploaded_by" not in doc_cols:
                        conn.execute(text("ALTER TABLE documents ADD COLUMN uploaded_by VARCHAR(100) DEFAULT 'Anonymous'"))
                        conn.commit()
                        logger.info("Migrated schema: Added 'uploaded_by' to 'documents' table.")

                # 2. activities table
                act_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(activities)")).fetchall()]
                if act_cols:
                    if "description" not in act_cols:
                        conn.execute(text("ALTER TABLE activities ADD COLUMN description TEXT DEFAULT ''"))
                        conn.commit()
                        logger.info("Migrated schema: Added 'description' to 'activities' table.")
                    if "document_id" not in act_cols:
                        conn.execute(text("ALTER TABLE activities ADD COLUMN document_id VARCHAR(36) DEFAULT NULL"))
                        conn.commit()
                        logger.info("Migrated schema: Added 'document_id' to 'activities' table.")
                    if "user_email" not in act_cols:
                        conn.execute(text("ALTER TABLE activities ADD COLUMN user_email VARCHAR(150) DEFAULT NULL"))
                        conn.commit()
                        logger.info("Migrated schema: Added 'user_email' to 'activities' table.")

                # Populate file_extension for any documents missing it
                conn.execute(text("""
                    UPDATE documents
                    SET file_extension = lower(substr(filename, instr(filename, '.') + 1))
                    WHERE (file_extension IS NULL OR file_extension = '') AND instr(filename, '.') > 0
                """))
                conn.commit()

        # Seed default admin user
        with SessionLocal() as db_session:
            from backend.services.auth_service import AuthService
            auth_svc = AuthService(db_session)
            auth_svc.seed_default_admin()

        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise
