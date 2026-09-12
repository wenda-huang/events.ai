from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _database_url() -> str:
    url = (settings.secret("database_url") or "").strip()
    if not url:
        raise RuntimeError(
            "Database URL missing. Set [database] url in config.ini or DATABASE_URL in the environment."
        )
    if url.startswith("sqlite"):
        raise RuntimeError("SQLite is no longer supported. Set [database] url or DATABASE_URL to Postgres.")
    return url


DATABASE_URL = _database_url()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def _exec_ignore_duplicate(conn, statement: str) -> None:
    try:
        conn.execute(text(statement))
    except (ProgrammingError, OperationalError):
        pass


def ensure_columns() -> None:
    inspector = inspect(engine)
    names = inspector.get_table_names()
    with engine.begin() as conn:
        if "events" in names:
            cols = {col["name"] for col in inspector.get_columns("events")}
            if "estimated_fields" not in cols:
                _exec_ignore_duplicate(conn, "ALTER TABLE events ADD COLUMN estimated_fields TEXT DEFAULT '[]'")
            if "city_id" not in cols:
                _exec_ignore_duplicate(conn, "ALTER TABLE events ADD COLUMN city_id INTEGER")
            _exec_ignore_duplicate(conn, "CREATE INDEX IF NOT EXISTS ix_events_city_id ON events (city_id)")
        if "users" in names:
            user_cols = {col["name"] for col in inspector.get_columns("users")}
            if "notifications_enabled" not in user_cols:
                _exec_ignore_duplicate(
                    conn, "ALTER TABLE users ADD COLUMN notifications_enabled BOOLEAN DEFAULT TRUE"
                )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
