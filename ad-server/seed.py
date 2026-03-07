"""
seed.py – Create tables and insert sample data on first run.

Idempotent: skips seeding if the placement already exists.
"""

from sqlalchemy.orm import Session

from models import Base, engine, SessionLocal, Placement, Creative


SEED_PLACEMENTS = [
    {"id": "homepage_hero", "name": "Homepage Hero Banner"},
]

SEED_CREATIVES = [
    {
        "id": "creative_1",
        "placement_id": "homepage_hero",
        "line_item_id": "li_brand_awareness",
        "name": "Summer Sale – Blue",
    },
    {
        "id": "creative_2",
        "placement_id": "homepage_hero",
        "line_item_id": "li_brand_awareness",
        "name": "Summer Sale – Green",
    },
    {
        "id": "creative_3",
        "placement_id": "homepage_hero",
        "line_item_id": "li_retargeting",
        "name": "Retargeting – Product Grid",
    },
]


def create_tables() -> None:
    """Ensure all ORM tables exist in the database."""
    Base.metadata.create_all(bind=engine)


def seed_data() -> None:
    """Insert seed rows if they don't already exist."""
    db: Session = SessionLocal()
    try:
        # Guard: skip if already seeded
        if db.query(Placement).filter_by(id="homepage_hero").first():
            return

        for p in SEED_PLACEMENTS:
            db.add(Placement(**p))

        for c in SEED_CREATIVES:
            db.add(Creative(**c))

        db.commit()
    finally:
        db.close()


def init_db() -> None:
    """One-shot helper called from the FastAPI lifespan hook."""
    create_tables()
    seed_data()
