"""
main.py – FastAPI ad-server demo.

Endpoints
---------
GET  /ad                     – Serve an ad decision
POST /event/impression       – Log impression event
POST /event/click            – Log click event
GET  /track/impression       – Tracking-pixel-style impression
GET  /track/click            – Tracking-pixel-style click
GET  /debug/decisions        – Last 20 decisions
GET  /debug/events           – Last 50 events

Run:
    uvicorn main:app --reload
"""

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from sqlalchemy.orm import Session

from models import Creative, Decision, Event, get_db, utcnow
from optimizer import select_creative
from schemas import (
    AdResponse,
    DecisionDebug,
    EventDebug,
    EventRequest,
    EventResponse,
)
from seed import init_db


# ---------------------------------------------------------------------------
# App lifespan – init DB + seed on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AdStackr Demo Ad Server",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_url(request: Request) -> str:
    """Derive the external base URL from the incoming request."""
    return str(request.base_url).rstrip("/")


def _parse_ts(raw: Optional[str]) -> datetime:
    """Parse an ISO-8601 string or return UTC now."""
    if raw is None:
        return utcnow()
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return utcnow()


def _record_event(
    db: Session,
    decision_id: str,
    event_type: str,
    creative_id: str,
    user_id: str,
    timestamp: Optional[str] = None,
) -> Event:
    """Validate the decision exists, then insert an Event row."""
    decision = db.query(Decision).filter_by(id=decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")

    event = Event(
        decision_id=decision_id,
        event_type=event_type,
        creative_id=creative_id,
        user_id=user_id,
        timestamp=_parse_ts(timestamp),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# ---------------------------------------------------------------------------
# GET /ad – serve an ad decision
# ---------------------------------------------------------------------------

@app.get("/ad", response_model=AdResponse)
def serve_ad(
    request: Request,
    placement_id: str = Query(..., description="Placement requesting an ad"),
    user_id: str = Query(..., description="Opaque user identifier"),
    context: Optional[str] = Query(None, description="JSON-encoded context (opaque)"),
    db: Session = Depends(get_db),
):
    # 1. Look up eligible creatives
    candidates: List[Creative] = (
        db.query(Creative).filter_by(placement_id=placement_id).all()
    )
    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No creatives found for placement '{placement_id}'",
        )

    candidate_dicts = [
        {
            "id": c.id,
            "placement_id": c.placement_id,
            "line_item_id": c.line_item_id,
            "name": c.name,
            "metadata": c.metadata_,
        }
        for c in candidates
    ]

    # 2. Parse context (treat as opaque dict)
    ctx = None
    if context:
        try:
            ctx = json.loads(context)
        except json.JSONDecodeError:
            ctx = None

    # 3. Call decision function
    chosen = select_creative(placement_id, user_id, ctx, candidate_dicts)

    # 4. Persist the decision
    decision_id = str(uuid.uuid4())
    now = utcnow()

    decision = Decision(
        id=decision_id,
        placement_id=placement_id,
        user_id=user_id,
        creative_id=chosen["id"],
        line_item_id=chosen["line_item_id"],
        served_at=now,
    )
    db.add(decision)
    db.commit()

    # 5. Build tracking URLs
    base = _base_url(request)
    impression_url = (
        f"{base}/track/impression"
        f"?decision_id={decision_id}"
        f"&creative_id={chosen['id']}"
        f"&user_id={user_id}"
    )
    click_url = (
        f"{base}/track/click"
        f"?decision_id={decision_id}"
        f"&creative_id={chosen['id']}"
        f"&user_id={user_id}"
    )

    return AdResponse(
        decision_id=decision_id,
        placement_id=placement_id,
        user_id=user_id,
        creative_id=chosen["id"],
        line_item_id=chosen["line_item_id"],
        served_at=now.isoformat(),
        impression_url=impression_url,
        click_url=click_url,
    )


# ---------------------------------------------------------------------------
# POST /event/impression
# ---------------------------------------------------------------------------

@app.post("/event/impression", response_model=EventResponse)
def post_impression(body: EventRequest, db: Session = Depends(get_db)):
    event = _record_event(
        db,
        decision_id=body.decision_id,
        event_type="impression",
        creative_id=body.creative_id,
        user_id=body.user_id,
        timestamp=body.timestamp,
    )
    return EventResponse(event_id=event.id)


# ---------------------------------------------------------------------------
# POST /event/click
# ---------------------------------------------------------------------------

@app.post("/event/click", response_model=EventResponse)
def post_click(body: EventRequest, db: Session = Depends(get_db)):
    event = _record_event(
        db,
        decision_id=body.decision_id,
        event_type="click",
        creative_id=body.creative_id,
        user_id=body.user_id,
        timestamp=body.timestamp,
    )
    return EventResponse(event_id=event.id)


# ---------------------------------------------------------------------------
# GET /track/impression  – tracking-pixel shortcut
# ---------------------------------------------------------------------------

@app.get("/track/impression")
def track_impression(
    decision_id: str = Query(...),
    creative_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db),
):
    _record_event(db, decision_id, "impression", creative_id, user_id)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /track/click  – tracking-pixel shortcut
# ---------------------------------------------------------------------------

@app.get("/track/click")
def track_click(
    decision_id: str = Query(...),
    creative_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db),
):
    _record_event(db, decision_id, "click", creative_id, user_id)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Debug endpoints
# ---------------------------------------------------------------------------

@app.get("/debug/decisions", response_model=List[DecisionDebug])
def debug_decisions(db: Session = Depends(get_db)):
    """Return the 20 most recent decisions."""
    rows = (
        db.query(Decision)
        .order_by(Decision.served_at.desc())
        .limit(20)
        .all()
    )
    return [
        DecisionDebug(
            id=d.id,
            placement_id=d.placement_id,
            user_id=d.user_id,
            creative_id=d.creative_id,
            line_item_id=d.line_item_id,
            served_at=d.served_at.isoformat() if d.served_at else "",
        )
        for d in rows
    ]


@app.get("/debug/events", response_model=List[EventDebug])
def debug_events(db: Session = Depends(get_db)):
    """Return the 50 most recent events."""
    rows = (
        db.query(Event)
        .order_by(Event.timestamp.desc())
        .limit(50)
        .all()
    )
    return [
        EventDebug(
            id=e.id,
            decision_id=e.decision_id,
            event_type=e.event_type,
            creative_id=e.creative_id,
            user_id=e.user_id,
            timestamp=e.timestamp.isoformat() if e.timestamp else "",
        )
        for e in rows
    ]


# ---------------------------------------------------------------------------
# Entrypoint (python main.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
