from flask import Flask, request, jsonify, redirect, make_response
import uuid
from urllib.parse import urlencode

app = Flask(__name__)

# ... existing configs and mappings ...

FAKE_AUCTIONS = {}
FAKE_CREATIVES = {}
LINE_ITEM_TO_CREATIVES = {}

# Simple metrics store
METRICS = {
    # creative_id: {
    #   "impressions": 0,
    #   "clicks": 0,
    #   "conversions": 0,
    # }
}

# Helper to init metrics entry
def _ensure_metrics(creative_id):
    if creative_id not in METRICS:
        METRICS[creative_id] = {
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
        }



DV360_CAMPAIGN_CONFIG = {
    "campaign_id": "dv_campaign_001",
    "line_item_id": "dv_li_001",          # default; overridden per segment
    "creative_template_id": "tmpl_hero_banner",
    "base_creative_id": "cr_base_001",
}

CM360_CONFIG = {
    "cm_account_id": "cm_acct_123",
    "cm_campaign_id": "cm_campaign_789",
    "placement_id": "cm_placement_456",
}

FAKE_AUCTIONS = {}
FAKE_CREATIVES = {}
LINE_ITEM_TO_CREATIVES = {}

# Segment → line item mapping
SEGMENT_TO_LINE_ITEM = {
    "segment_A": "dv_li_001",
    "segment_B": "dv_li_002",
}

# =========================
# Pretend DV360 bid request
# =========================

@app.route("/dv360/bid_request", methods=["POST"])
def dv360_bid_request():
    payload = request.json or {}
    segment = payload.get("segment", "segment_A")

    dv_cfg = DV360_CAMPAIGN_CONFIG.copy()
    dv_cfg["line_item_id"] = SEGMENT_TO_LINE_ITEM.get(segment, "dv_li_001")

    auction_id = str(uuid.uuid4())
    FAKE_AUCTIONS[auction_id] = {
        "segment": segment,
        "dv360_config": dv_cfg,
        "status": "pending",
    }

    return jsonify({
        "auction_id": auction_id,
        "segment": segment,
        "next": f"/adstacker/handle_win/{auction_id}",
    })






# --- Pretend CM360 creative creation ---

def _cm360_set_creatives_internal(payload):
    variants = payload.get("variants", [])
    created = []
    for v in variants:
        creative_id = f"cm_creative_{payload['dv360_line_item_id']}_{v['variant_id']}"
        _ensure_metrics(creative_id)

        # Build click tracking URL (redirect)
        dest_url = v.get("final_url", "https://example.com/landing")
        click_qs = urlencode({
            "creative_id": creative_id,
            "line_item_id": payload["dv360_line_item_id"],
            "template_id": payload["creative_template_id"],
            "dest": dest_url,
        })
        click_url = f"{request.host_url.rstrip('/')}/track/click?{click_qs}"

        creative_record = {
            "creative_id": creative_id,
            "line_item_id": payload["dv360_line_item_id"],
            "data": v,
            "click_url": click_url,
        }
        FAKE_CREATIVES[creative_id] = creative_record
        created.append(creative_record)

    return {"status": "creatives_set", "creatives": created}




@app.route("/track/click", methods=["GET"])
def track_click():
    creative_id = request.args.get("creative_id")
    dest = request.args.get("dest", "https://example.com/landing")

    if creative_id:
        _ensure_metrics(creative_id)
        METRICS[creative_id]["clicks"] += 1

    # Here you could also log impression_id, template_id, etc.
    # For now just redirect.
    return redirect(dest, code=302)



# Simple 1x1 transparent GIF
PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00"
    b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;"
)

@app.route("/track/conversion", methods=["GET"])
def track_conversion():
    creative_id = request.args.get("creative_id")
    if creative_id:
        _ensure_metrics(creative_id)
        METRICS[creative_id]["conversions"] += 1

    # Return 1x1 gif
    resp = make_response(PIXEL_GIF)
    resp.headers["Content-Type"] = "image/gif"
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp



@app.route("/adstacker/handle_win/<auction_id>", methods=["POST"])
def handle_win(auction_id):
    auction = FAKE_AUCTIONS.get(auction_id)
    if not auction:
        return jsonify({"error": "auction not found"}), 404

    auction["status"] = "won"
    dv_cfg = auction["dv360_config"]
    line_item_id = dv_cfg["line_item_id"]

    creative_ids = LINE_ITEM_TO_CREATIVES.get(line_item_id, [])
    chosen_creative_id = creative_ids[0] if creative_ids else None

    if chosen_creative_id:
        _ensure_metrics(chosen_creative_id)
        METRICS[chosen_creative_id]["impressions"] += 1

    return jsonify({
        "auction_id": auction_id,
        "segment": auction["segment"],
        "line_item_id": line_item_id,
        "chosen_creative_id": chosen_creative_id,
        # include click_url so you can test it from the notebook
        "click_url": FAKE_CREATIVES.get(chosen_creative_id, {}).get("click_url"),
    })



# =========================
# AdStac.kr -> pretend CM360
# =========================

@app.route("/adstacker/generate_creatives", methods=["POST"])
def generate_creatives():
    payload = request.json or {}

    dv360_line_item_id = payload.get("dv360_line_item_id")
    template_id = payload.get("template_id")
    variants = payload.get("variants", [])

    cm_payload = {
        "cm_account_id": CM360_CONFIG["cm_account_id"],
        "cm_campaign_id": CM360_CONFIG["cm_campaign_id"],
        "placement_id": CM360_CONFIG["placement_id"],
        "dv360_line_item_id": dv360_line_item_id,
        "creative_template_id": template_id,
        "variants": variants,
    }

    result = _cm360_set_creatives_internal(cm_payload)

    # Overwrite mapping for this line item with the new creatives
    LINE_ITEM_TO_CREATIVES[dv360_line_item_id] = [
        c["creative_id"] for c in result["creatives"]
    ]

    return jsonify(result)







@app.route("/metrics", methods=["GET"])
def get_metrics():
    """
    Return metrics aggregated by creative_id.
    Optionally filter by creative_id, line_item_id, template_id via query params.
    """
    creative_id = request.args.get("creative_id")
    line_item_id = request.args.get("line_item_id")
    template_id = request.args.get("template_id")  # not used in store yet

    result = {}
    for cid, stats in METRICS.items():
        if creative_id and cid != creative_id:
            continue
        cr = FAKE_CREATIVES.get(cid, {})
        if line_item_id and cr.get("line_item_id") != line_item_id:
            continue
        result[cid] = {
            "creative_id": cid,
            "line_item_id": cr.get("line_item_id"),
            "impressions": stats["impressions"],
            "clicks": stats["clicks"],
            "conversions": stats["conversions"],
        }

    return jsonify(result)



