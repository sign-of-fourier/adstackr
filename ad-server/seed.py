"""
seed.py – Create tables and insert sample data on first run.

Seed data models a realistic DCO scenario:
  - 3 placements across a publisher site (hero, sidebar, interstitial)
  - 2 advertisers, each with line items targeting different segments
  - 10 creatives spread across placements and line items

Idempotent: skips seeding if the homepage_hero placement already exists.
"""

from sqlalchemy.orm import Session

from models import Base, get_engine, get_session_factory, Placement, Creative


# ---------------------------------------------------------------------------
# Placements – positions on a publisher page
# ---------------------------------------------------------------------------

SEED_PLACEMENTS = [
    {"id": "homepage_hero",        "name": "Homepage Hero Banner (970x250)"},
    {"id": "sidebar_rect",         "name": "Sidebar Rectangle (300x250)"},
    {"id": "article_interstitial", "name": "Article Interstitial (640x480)"},
]


# ---------------------------------------------------------------------------
# Creatives – ads eligible for each placement
#
# Two advertisers:
#   Advertiser A  – "Acme Travel" (brand awareness + retargeting)
#   Advertiser B  – "Bolt Shoes"  (product launch + seasonal promo)
#
# Line items map to campaign objectives / audience segments:
#   li_acme_brand      -> broad reach, brand awareness
#   li_acme_retarget   -> users who visited acme site (retargeting)
#   li_bolt_launch     -> new product launch, high-intent users
#   li_bolt_seasonal   -> seasonal discount, broad audience
# ---------------------------------------------------------------------------

SEED_CREATIVES = [
    # -- Homepage Hero --
    {
        "id": "acme_hero_beach",
        "placement_id": "homepage_hero",
        "line_item_id": "li_acme_brand",
        "name": "Acme Travel - Beach Getaway",
        "metadata_": '{"advertiser":"Acme Travel","segment":"broad","format":"970x250","theme":"beach"}',
    },
    {
        "id": "acme_hero_mountain",
        "placement_id": "homepage_hero",
        "line_item_id": "li_acme_brand",
        "name": "Acme Travel - Mountain Adventure",
        "metadata_": '{"advertiser":"Acme Travel","segment":"broad","format":"970x250","theme":"mountain"}',
    },
    {
        "id": "bolt_hero_launch",
        "placement_id": "homepage_hero",
        "line_item_id": "li_bolt_launch",
        "name": "Bolt Shoes - AirStride Launch",
        "metadata_": '{"advertiser":"Bolt Shoes","segment":"high_intent","format":"970x250","product":"AirStride"}',
    },
    # -- Sidebar Rectangle --
    {
        "id": "acme_side_retarget",
        "placement_id": "sidebar_rect",
        "line_item_id": "li_acme_retarget",
        "name": "Acme Travel - Come Back & Book",
        "metadata_": '{"advertiser":"Acme Travel","segment":"retargeting","format":"300x250","cta":"Book Now"}',
    },
    {
        "id": "bolt_side_seasonal",
        "placement_id": "sidebar_rect",
        "line_item_id": "li_bolt_seasonal",
        "name": "Bolt Shoes - Summer Sale 30% Off",
        "metadata_": '{"advertiser":"Bolt Shoes","segment":"broad","format":"300x250","discount":"30%"}',
    },
    {
        "id": "bolt_side_launch",
        "placement_id": "sidebar_rect",
        "line_item_id": "li_bolt_launch",
        "name": "Bolt Shoes - AirStride Sidebar",
        "metadata_": '{"advertiser":"Bolt Shoes","segment":"high_intent","format":"300x250","product":"AirStride"}',
    },
    # -- Article Interstitial --
    {
        "id": "acme_inter_beach",
        "placement_id": "article_interstitial",
        "line_item_id": "li_acme_brand",
        "name": "Acme Travel - Beach Video Interstitial",
        "metadata_": '{"advertiser":"Acme Travel","segment":"broad","format":"640x480","type":"video"}',
    },
    {
        "id": "acme_inter_retarget",
        "placement_id": "article_interstitial",
        "line_item_id": "li_acme_retarget",
        "name": "Acme Travel - Your Trip Awaits",
        "metadata_": '{"advertiser":"Acme Travel","segment":"retargeting","format":"640x480","cta":"Resume Booking"}',
    },
    {
        "id": "bolt_inter_launch",
        "placement_id": "article_interstitial",
        "line_item_id": "li_bolt_launch",
        "name": "Bolt Shoes - AirStride Full-Screen",
        "metadata_": '{"advertiser":"Bolt Shoes","segment":"high_intent","format":"640x480","product":"AirStride"}',
    },
    {
        "id": "bolt_inter_seasonal",
        "placement_id": "article_interstitial",
        "line_item_id": "li_bolt_seasonal",
        "name": "Bolt Shoes - End of Season Blowout",
        "metadata_": '{"advertiser":"Bolt Shoes","segment":"broad","format":"640x480","discount":"50%"}',
    },
]


def create_tables() -> None:
    """Ensure all ORM tables exist in the database."""
    Base.metadata.create_all(bind=get_engine())


def seed_data() -> None:
    """Insert seed rows if they don't already exist."""
    db: Session = get_session_factory()()
    try:
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
