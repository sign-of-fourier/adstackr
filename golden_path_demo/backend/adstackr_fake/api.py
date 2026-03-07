from fastapi import APIRouter, HTTPException
from typing import Dict, List
import logging
import uuid
import random

import httpx

from .models import (
    state,
    ConnectorConfig,
    RunState,
    MappingOption,
    get_or_create_option_stats,
)
from .optimizer import optimize_run
from google_fake.models import state as google_state

logger = logging.getLogger("adstackr_fake")

router = APIRouter()



#from typing import Dict, List
#import logging

#import httpx

#from .models import (
#    state,
#
#)
from .optimizer import compute_ctr  # reuse the CTR helper from optimizer.py

#logger = logging.getLogger("adstackr_fake")

# in-memory store for last optimization decisions per tenant
last_decisions: Dict[str, List[Dict[str, str]]] = {}


@router.post("/optimize_now")
async def optimize_now(tenant_id: str):
    """Manual trigger: pull stats from Fake Google and choose templates per segment.

    This simulates AdStackr's async decision layer.
    """
    cfg = state.connector_configs.get(tenant_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Unknown tenant")

    async with httpx.AsyncClient() as client:
        base = "http://localhost:8000/google"
        logger.info(
            "AdStackr -> GoogleFake: GET /reporting",
            extra={"tenant_id": tenant_id},
        )
        resp = await client.get(f"{base}/reporting")
        resp.raise_for_status()
        rows = resp.json()

    # group by segment_id
    by_segment: Dict[str, List[Dict[str, int]]] = {}
    for row in rows:
        seg = row["segment_id"]
        by_segment.setdefault(seg, []).append(row)

    decisions: List[Dict[str, str]] = []

    for segment_id, options in by_segment.items():
        best_template_id = None
        best_ctr = -1.0

        for opt in options:
            imps = opt.get("impressions", 0)
            clicks = opt.get("clicks", 0)
            ctr = compute_ctr(clicks, imps)  # uses same smoothing as optimizer
            if ctr > best_ctr:
                best_ctr = ctr
                best_template_id = opt.get("template_id")

        if best_template_id is None and options:
            best_template_id = options[0].get("template_id")

        logger.info(
            "AdStackr optimize_now decision",
            extra={
                "tenant_id": tenant_id,
                "segment_id": segment_id,
                "template_id": best_template_id,
                "ctr": best_ctr,
            },
        )

        decisions.append(
            {
                "segment_id": segment_id,
                "template_id": best_template_id or "",
                "reason": "highest smoothed CTR",
            }
        )

    last_decisions[tenant_id] = decisions

    # Optionally, push to Fake Google Studio mappings endpoint if/when added
    # async with httpx.AsyncClient() as client:
    #     await client.post(
    #         f"{base}/studio/mappings",
    #         json=[{"segment_id": d["segment_id"], "template_id": d["template_id"]} for d in decisions],
    #     )

    return {"tenant_id": tenant_id, "decisions": decisions}


@router.get("/last_decisions")
async def get_last_decisions(tenant_id: str):
    """Return the last optimization decisions for this tenant."""
    decisions = last_decisions.get(tenant_id, [])
    return {"tenant_id": tenant_id, "decisions": decisions}


@router.get("/catalog")
async def catalog(tenant_id: str) -> Dict:
    cfg = state.connector_configs.get(tenant_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Unknown tenant")

    return {
        "campaigns": list(google_state.campaigns.values()),
        "line_items": list(google_state.line_items.values()),
        "creatives": list(google_state.creatives.values()),
        "templates": list(google_state.templates.values()),
        "feed_rows": list(google_state.feed_rows.values()),
    }




@router.post("/connect")
async def connect(cfg: ConnectorConfig):
    """Register connector config and fetch campaigns from Fake Google.

    Returns a payload suitable for the connector UI: status + campaigns list.
    """
    state.connector_configs[cfg.tenant_id] = cfg

    async with httpx.AsyncClient() as client:
        base = "http://localhost:8000/google"
        advertiser_id = cfg.dv360_credentials.get("advertiser_id", "12345")

        logger.info(
            "AdStackr -> GoogleFake: GET /dv360/campaigns",
            extra={"tenant_id": cfg.tenant_id, "advertiserId": advertiser_id},
        )
        campaigns_resp = await client.get(
            f"{base}/dv360/campaigns", params={"advertiserId": advertiser_id}
        )
        campaigns_resp.raise_for_status()
        campaigns = campaigns_resp.json()

    return {
        "tenant_id": cfg.tenant_id,
        "status": "ok",
        "campaigns": campaigns,
    }


@router.post("/select_campaign")
async def select_campaign(tenant_id: str, campaign_id: str):
    """Store which campaign this tenant wants AdStackr to optimize."""
    cfg = state.connector_configs.get(tenant_id)
    if not cfg:
        print("unknown tenant")
        raise HTTPException(status_code=404, detail="Unknown tenant")

    cfg.linked_campaign_id = campaign_id
    state.connector_configs[tenant_id] = cfg

    logger.info(
        "AdStackr select_campaign",
        extra={"tenant_id": tenant_id, "campaign_id": campaign_id},
    )

    return {"status": "ok", "tenant_id": tenant_id, "campaign_id": campaign_id}

