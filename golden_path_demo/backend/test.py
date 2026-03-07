import requests
import json
import random
from urllib.parse import urlparse, parse_qs

BASE_URL = "http://localhost:5000"

def generate_creatives(line_item_id, template_id, variants):
    url = f"{BASE_URL}/adstacker/generate_creatives"
    payload = {
        "dv360_line_item_id": line_item_id,
        "template_id": template_id,
        "variants": variants,
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    print("[generate_creatives]", line_item_id)
    print(json.dumps(data, indent=2))
    return data

def dv360_bid_and_win(segment):
    bid_url = f"{BASE_URL}/dv360/bid_request"
    bid_resp = requests.post(bid_url, json={"segment": segment})
    bid_resp.raise_for_status()
    bid_data = bid_resp.json()
    auction_id = bid_data["auction_id"]

    win_url = f"{BASE_URL}/adstacker/handle_win/{auction_id}"
    win_resp = requests.post(win_url)
    win_resp.raise_for_status()
    win_data = win_resp.json()
    print(f"[win] segment={segment}")
    print(json.dumps(win_data, indent=2))
    return win_data

def fire_click(click_url):
    """
    Simulate user click: call the click tracker URL and follow redirect.
    """
    resp = requests.get(click_url, allow_redirects=False)
    print("[click] status", resp.status_code, "Location:", resp.headers.get("Location"))
    return resp

def fire_conversion(creative_id):
    """
    Simulate a conversion pixel firing on vendor site.
    """
    url = f"{BASE_URL}/track/conversion"
    resp = requests.get(url, params={"creative_id": creative_id})
    print("[conversion] creative_id", creative_id, "status", resp.status_code)
    return resp

def get_metrics(creative_id=None, line_item_id=None):
    url = f"{BASE_URL}/metrics"
    params = {}
    if creative_id:
        params["creative_id"] = creative_id
    if line_item_id:
        params["line_item_id"] = line_item_id
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    print("[metrics]")
    print(json.dumps(data, indent=2))
    return data










# 1) Create creatives for two segments / line items
generate_creatives(
    line_item_id="dv_li_001",
    template_id="tmpl_hero_banner",
    variants=[
        {"variant_id": "a1", "headline": "SegA Headline", "bg_color": "#FFAAAA",
         "final_url": "https://example.com/segA"},
    ],
)

generate_creatives(
    line_item_id="dv_li_002",
    template_id="tmpl_hero_banner",
    variants=[
        {"variant_id": "b1", "headline": "SegB Headline", "bg_color": "#AAAFFF",
         "final_url": "https://example.com/segB"},
    ],
)

# 2) Generate a bunch of impressions, with random clicks/conversions
impressions = []
for i in range(50):
    seg = "segment_A" if random.random() < 0.5 else "segment_B"
    win = dv360_bid_and_win(seg)
    impressions.append(win)

    # 20% of impressions click
    if win["chosen_creative_id"] and random.random() < 0.2:
        click_url = win["click_url"]
        fire_click(click_url)

        # 50% of clickers convert
        if random.random() < 0.5:
            fire_conversion(win["chosen_creative_id"])

# 3) Inspect metrics
get_metrics()  # all creatives
get_metrics(line_item_id="dv_li_001")
get_metrics(line_item_id="dv_li_002")

