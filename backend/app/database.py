from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

DATABASE_URL = settings.secret("database_url") or "sqlite:///./events.db"

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def ensure_columns() -> None:
    inspector = inspect(engine)
    if "events" not in inspector.get_table_names():
        return
    cols = {col["name"] for col in inspector.get_columns("events")}
    if "estimated_fields" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE events ADD COLUMN estimated_fields TEXT DEFAULT '[]'"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
