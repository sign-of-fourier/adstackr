from fastapi import APIRouter, Response, Query
from typing import List, Dict
import logging

from .models import (
    state,
    Campaign,
    LineItem,
    Creative,
    Template,
    FeedRow,
    get_or_create_stats,
)

logger = logging.getLogger("google_fake")

router = APIRouter()


@router.get("/dv360/campaigns", response_model=List[Campaign])
async def list_campaigns(advertiserId: str | None = None) -> List[Campaign]:
    """List campaigns for an advertiser (advertiserId is ignored but logged)."""
    logger.info(
        "GoogleFake DV360: list campaigns",
        extra={"advertiserId": advertiserId},
    )
    return list(state.campaigns.values())


@router.get("/dv360/lineItems", response_model=List[LineItem])
async def list_line_items() -> List[LineItem]:
    logger.info("GoogleFake DV360: list line items")
    return list(state.line_items.values())


@router.get("/dv360/creatives", response_model=List[Creative])
async def list_creatives() -> List[Creative]:
    logger.info("GoogleFake DV360: list creatives")
    return list(state.creatives.values())


@router.get("/studio/templates", response_model=List[Template])
async def list_templates() -> List[Template]:
    logger.info("GoogleFake Studio: list templates")
    return list(state.templates.values())


@router.get("/studio/feeds", response_model=List[FeedRow])
async def list_feeds() -> List[FeedRow]:
    logger.info("GoogleFake Studio: list feeds")
    return list(state.feed_rows.values())


@router.get("/cm360/click")
async def click(
    line_item_id: str,
    creative_id: str,
    template_id: str,
    segment_id: str,
    target: str = "http://example.com",
):
    logger.info(
        "GoogleFake CM360: click",
        extra={
            "line_item_id": line_item_id,
            "creative_id": creative_id,
            "template_id": template_id,
            "segment_id": segment_id,
        },
    )
    stats = get_or_create_stats(line_item_id, creative_id, template_id, segment_id)
    stats.clicks += 1
    return Response(status_code=302, headers={"Location": target})


@router.get("/cm360/pixel")
async def pixel(
    line_item_id: str, creative_id: str, template_id: str, segment_id: str
):
    logger.info(
        "GoogleFake CM360: conversion pixel",
        extra={
            "line_item_id": line_item_id,
            "creative_id": creative_id,
            "template_id": template_id,
            "segment_id": segment_id,
        },
    )
    stats = get_or_create_stats(line_item_id, creative_id, template_id, segment_id)
    stats.conversions += 1
    return {"status": "ok"}


@router.get("/render")
async def render(
    line_item_id: str = Query(...),
    creative_id: str = Query(...),
    segment_id: str = Query(...),
):
    """Simulate an ad render after an auction win.

    - Increments impressions for (line_item, creative, template, segment)
    - Returns template info plus click and conversion URLs.
    """
    template_ids = list(state.templates.keys())
    template_id = template_ids[0] if template_ids else "T_DEFAULT"

    stats = get_or_create_stats(line_item_id, creative_id, template_id, segment_id)
    stats.impressions += 1

    click_url = (
        f"/google/cm360/click"
        f"?line_item_id={line_item_id}"
        f"&creative_id={creative_id}"
        f"&template_id={template_id}"
        f"&segment_id={segment_id}"
    )

    conversion_url = (
        f"/google/cm360/pixel"
        f"?line_item_id={line_item_id}"
        f"&creative_id={creative_id}"
        f"&template_id={template_id}"
        f"&segment_id={segment_id}"
    )

    logger.info(
        "GoogleFake render",
        extra={
            "line_item_id": line_item_id,
            "creative_id": creative_id,
            "template_id": template_id,
            "segment_id": segment_id,
        },
    )

    return {
        "line_item_id": line_item_id,
        "creative_id": creative_id,
        "segment_id": segment_id,
        "template_id": template_id,
        "click_url": click_url,
        "conversion_url": conversion_url,
    }


@router.get("/reporting")
async def reporting():
    """Aggregate stats per (segment_id, template_id)."""
    agg: Dict[tuple, Dict[str, int]] = {}

    for (li_id, cr_id, template_id, segment_id), counters in state.stats.items():
        key = (segment_id, template_id)
        if key not in agg:
            agg[key] = {"impressions": 0, "clicks": 0, "conversions": 0}
        agg[key]["impressions"] += counters.impressions
        agg[key]["clicks"] += counters.clicks
        agg[key]["conversions"] += counters.conversions

    rows = []
    for (segment_id, template_id), m in agg.items():
        rows.append(
            {
                "segment_id": segment_id,
                "template_id": template_id,
                "impressions": m["impressions"],
                "clicks": m["clicks"],
                "conversions": m["conversions"],
            }
        )
    logger.info("GoogleFake reporting", extra={"rows": len(rows)})
    return rows

