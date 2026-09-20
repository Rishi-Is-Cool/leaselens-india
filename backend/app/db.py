from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def _connect_args(database_url: str) -> dict:
    parsed = urlsplit(database_url)
    host = parsed.hostname or ""
    args: dict = {}

    if "supabase" in host:
        args["sslmode"] = "require"

    # Supabase's transaction pooler (PgBouncer, :6543) cannot replay the server-side
    # prepared statements psycopg3 creates by default; reusing one across pooled
    # connections fails with "prepared statement already exists".
    if parsed.port == 6543 or "pooler.supabase.com" in host:
        args["prepare_threshold"] = None

    return args


_database_url = get_settings().database_url

# An unset DATABASE_URL must not crash the process at import: the API should still
# boot so /health can report the misconfiguration instead of the app failing opaquely.
engine = (
    create_engine(
        _database_url,
        pool_pre_ping=True,
        future=True,
        connect_args=_connect_args(_database_url),
    )
    if _database_url
    else None
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False) if engine else None


def get_session() -> Iterator["Session"]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_tables() -> None:
    from app.models import Base

    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    Base.metadata.create_all(engine)


@dataclass
class DatabaseStatus:
    connected: bool
    server_version: str | None = None
    error: str | None = None


def check_database() -> DatabaseStatus:
    if engine is None:
        return DatabaseStatus(connected=False, error="DATABASE_URL not set")
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SHOW server_version")).scalar_one()
        return DatabaseStatus(connected=True, server_version=str(version))
    except SQLAlchemyError as exc:
        # Exception type only: SQLAlchemy messages embed the DSN, including the password.
        return DatabaseStatus(connected=False, error=type(exc).__name__)
