"""
schemas.py – Pydantic models for request bodies and response payloads.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ad serving
# ---------------------------------------------------------------------------

class AdResponse(BaseModel):
    """Returned by GET /ad."""
    decision_id: str
    placement_id: str
    user_id: str
    creative_id: str
    line_item_id: str
    served_at: str              # ISO-8601
    impression_url: str
    click_url: str


# ---------------------------------------------------------------------------
# Event tracking
# ---------------------------------------------------------------------------

class EventRequest(BaseModel):
    """Body for POST /event/impression and POST /event/click."""
    decision_id: str
    creative_id: str
    user_id: str
    timestamp: Optional[str] = None   # ISO-8601; defaults to now


class EventResponse(BaseModel):
    status: str = "ok"
    event_id: int


# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------

class DecisionDebug(BaseModel):
    id: str
    placement_id: str
    user_id: str
    creative_id: str
    line_item_id: str
    served_at: str


class EventDebug(BaseModel):
    id: int
    decision_id: str
    event_type: str
    creative_id: str
    user_id: str
    timestamp: str
