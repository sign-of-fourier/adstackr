"""
models.py – SQLAlchemy ORM models and database engine/session setup.

Tables: placements, creatives, decisions, events.
Uses SQLite for zero-config local storage.

The engine and session factory live behind `get_engine()` / `get_session_factory()`
so tests can call `configure_engine(url)` before the app starts.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    ForeignKey,
    create_engine,
    Engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ---------------------------------------------------------------------------
# Configurable engine (default: file next to this module)
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ad_server.db")
_DEFAULT_URL = f"sqlite:///{_DEFAULT_DB_PATH}"

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def configure_engine(url: str = _DEFAULT_URL) -> None:
    """(Re)create the engine and session factory.  Call before first use."""
    global _engine, _SessionLocal
    _engine = create_engine(url, connect_args={"check_same_thread": False}, echo=False)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        configure_engine()
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        configure_engine()
    return _SessionLocal


Base = declarative_base()


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def get_db():
    """FastAPI dependency that yields a DB session and closes it after use."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class Placement(Base):
    __tablename__ = "placements"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)


class Creative(Base):
    __tablename__ = "creatives"

    id = Column(String, primary_key=True)
    placement_id = Column(String, ForeignKey("placements.id"), nullable=False)
    line_item_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    metadata_ = Column("metadata", Text, nullable=True)  # JSON string, opaque


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True)          # UUID4 as string
    placement_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    creative_id = Column(String, nullable=False)
    line_item_id = Column(String, nullable=False)
    served_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(String, ForeignKey("decisions.id"), nullable=False)
    event_type = Column(String, nullable=False)     # "impression" | "click"
    creative_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow)
