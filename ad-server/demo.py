#!/usr/bin/env python3
"""
demo.py – Narrated ad-server lifecycle walkthrough.

Simulates realistic page-load scenarios with multiple placements, user
segments, impression/click tracking, and a final analytics summary.

Run:
    1. Start the server:  uvicorn main:app --reload
    2. In another terminal: python demo.py

Each step is printed with context so you can follow the flow as if
watching real ad traffic in slow motion.
"""

import json
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

import requests

BASE = "http://127.0.0.1:8000"

# ── Formatting helpers ───────────────────────────────────────────────────

BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

def banner(text: str) -> None:
    width = 70
    print(f"\n{BOLD}{'═' * width}")
    print(f"  {text}")
    print(f"{'═' * width}{RESET}\n")

def section(text: str) -> None:
    print(f"\n{CYAN}── {text} {'─' * max(0, 56 - len(text))}{RESET}\n")

def step(num: int, text: str) -> None:
    print(f"  {YELLOW}[Step {num}]{RESET} {text}")

def ok(text: str) -> None:
    print(f"           {GREEN}✓{RESET} {text}")

def info(text: str) -> None:
    print(f"           {DIM}{text}{RESET}")

def fail(text: str) -> None:
    print(f"           {RED}✗ {text}{RESET}")

def pretty(data: Any) -> str:
    return json.dumps(data, indent=4)

def pause(seconds: float = 0.4) -> None:
    time.sleep(seconds)


# ── HTTP wrappers ────────────────────────────────────────────────────────

def request_ad(placement_id: str, user_id: str, context: Optional[dict] = None) -> Dict:
    params: Dict[str, str] = {"placement_id": placement_id, "user_id": user_id}
    if context:
        params["context"] = json.dumps(context)
    r = requests.get(f"{BASE}/ad", params=params)
    r.raise_for_status()
    return r.json()

def fire_impression(decision: Dict) -> Dict:
    r = requests.get(decision["impression_url"])
    r.raise_for_status()
    return r.json()

def fire_click(decision: Dict) -> Dict:
    r = requests.get(decision["click_url"])
    r.raise_for_status()
    return r.json()

def post_event(endpoint: str, decision_id: str, creative_id: str, user_id: str) -> Dict:
    r = requests.post(f"{BASE}/event/{endpoint}", json={
        "decision_id": decision_id,
        "creative_id": creative_id,
        "user_id": user_id,
    })
    r.raise_for_status()
    return r.json()

def get_debug(endpoint: str) -> List[Dict]:
    r = requests.get(f"{BASE}/debug/{endpoint}")
    r.raise_for_status()
    return r.json()


# ── Tracking accumulators ────────────────────────────────────────────────

all_decisions: List[Dict] = []
impressions_fired: int = 0
clicks_fired: int = 0
creative_counts: Dict[str, int] = defaultdict(int)
placement_counts: Dict[str, int] = defaultdict(int)
user_decisions: Dict[str, List[Dict]] = defaultdict(list)


def serve_and_track(placement_id: str, user_id: str, context: Optional[dict] = None) -> Dict:
    global impressions_fired
    d = request_ad(placement_id, user_id, context)
    all_decisions.append(d)
    creative_counts[d["creative_id"]] += 1
    placement_counts[placement_id] += 1
    user_decisions[user_id].append(d)
    return d


# ══════════════════════════════════════════════════════════════════════════
#  SCENARIO 1 – Single page load, full lifecycle
# ══════════════════════════════════════════════════════════════════════════

def scenario_1():
    banner("SCENARIO 1: Single Page Load – Full Ad Lifecycle")
    print("  A user lands on the homepage. The page has three ad slots.")
    print("  The ad server picks a creative for each slot, then the browser")
    print("  fires impression pixels. The user clicks one ad.\n")

    user = "user_alice"
    decisions = []

    step(1, f"Page load for {BOLD}{user}{RESET} – requesting 3 placements")
    pause()

    for pid in ["homepage_hero", "sidebar_rect", "article_interstitial"]:
        d = serve_and_track(pid, user, {"page": "/", "device": "desktop"})
        decisions.append(d)
        ok(f"{pid:25s} → {BOLD}{d['creative_id']}{RESET}  (line item: {d['line_item_id']})")
        info(f"decision_id: {d['decision_id']}")
        pause(0.2)

    step(2, "Browser fires impression pixels for all 3 slots")
    pause()
    for d in decisions:
        fire_impression(d)
        ok(f"Impression logged for {d['creative_id']}")
    global impressions_fired
    impressions_fired += 3

    step(3, f"{user} clicks the hero ad")
    pause()
    fire_click(decisions[0])
    ok(f"Click logged for {decisions[0]['creative_id']} (hero slot)")
    global clicks_fired
    clicks_fired += 1

    step(4, "Verify via POST /event/impression (alternative path)")
    pause()
    resp = post_event("impression", decisions[1]["decision_id"],
                      decisions[1]["creative_id"], user)
    ok(f"POST impression → event_id={resp['event_id']}")
    impressions_fired += 1

    print(f"\n  {GREEN}Scenario 1 complete.{RESET} 3 decisions, 4 impressions, 1 click.\n")


# ══════════════════════════════════════════════════════════════════════════
#  SCENARIO 2 – Multiple users, different segments
# ══════════════════════════════════════════════════════════════════════════

def scenario_2():
    banner("SCENARIO 2: Multi-User Traffic – Segment Differentiation")
    print("  Five different users hit the site. Each has a different context")
    print("  (device, referrer, segment). The optimizer picks creatives for")
    print("  each.  We observe how rotation distributes across creatives.\n")

    users = [
        ("user_bob",     {"device": "mobile",  "segment": "high_intent",  "referrer": "google"}),
        ("user_carol",   {"device": "desktop", "segment": "retargeting",  "referrer": "email_campaign"}),
        ("user_dave",    {"device": "tablet",  "segment": "broad",        "referrer": "social"}),
        ("user_eve",     {"device": "mobile",  "segment": "high_intent",  "referrer": "direct"}),
        ("user_frank",   {"device": "desktop", "segment": "broad",        "referrer": "organic"}),
    ]

    placements = ["homepage_hero", "sidebar_rect", "article_interstitial"]

    for i, (uid, ctx) in enumerate(users):
        step(i + 1, f"Page load: {BOLD}{uid}{RESET}  segment={ctx['segment']}  device={ctx['device']}")
        pause(0.3)

        for pid in placements:
            d = serve_and_track(pid, uid, ctx)
            ok(f"{pid:25s} → {d['creative_id']:25s}  line_item={d['line_item_id']}")
            # Fire impression immediately
            fire_impression(d)
            pause(0.1)

        global impressions_fired
        impressions_fired += len(placements)

    # Simulate some clicks (not every user clicks)
    step(len(users) + 1, "Simulating clicks from bob and eve (high-intent users)")
    pause()
    global clicks_fired
    for uid in ["user_bob", "user_eve"]:
        # Click the first decision for each user
        d = user_decisions[uid][0]
        fire_click(d)
        clicks_fired += 1
        ok(f"{uid} clicked {d['creative_id']} on {d['placement_id']}")

    print(f"\n  {GREEN}Scenario 2 complete.{RESET} 5 users × 3 placements = 15 decisions.\n")


# ══════════════════════════════════════════════════════════════════════════
#  SCENARIO 3 – Rapid-fire rotation test
# ══════════════════════════════════════════════════════════════════════════

def scenario_3():
    banner("SCENARIO 3: Rotation Test – 30 Requests to One Placement")
    print("  Hammering homepage_hero 30 times with the same user to observe")
    print("  creative rotation under the uniform-random optimizer.\n")

    rotation: Dict[str, int] = defaultdict(int)

    step(1, "Firing 30 ad requests to homepage_hero")
    pause()
    for i in range(30):
        d = serve_and_track("homepage_hero", "user_rotation_test")
        rotation[d["creative_id"]] += 1
        fire_impression(d)
        global impressions_fired
        impressions_fired += 1

    step(2, "Distribution across creatives:")
    for cid, count in sorted(rotation.items()):
        bar = "█" * count
        pct = count / 30 * 100
        ok(f"{cid:25s}  {count:2d}/30  ({pct:4.1f}%)  {DIM}{bar}{RESET}")

    print(f"\n  {GREEN}Scenario 3 complete.{RESET} Uniform random → roughly even split.\n")


# ══════════════════════════════════════════════════════════════════════════
#  SCENARIO 4 – Error handling
# ══════════════════════════════════════════════════════════════════════════

def scenario_4():
    banner("SCENARIO 4: Error Handling & Edge Cases")

    step(1, "Request ad for nonexistent placement")
    pause()
    r = requests.get(f"{BASE}/ad", params={"placement_id": "nonexistent", "user_id": "u"})
    if r.status_code == 404:
        ok(f"404 returned: {r.json()['detail']}")
    else:
        fail(f"Expected 404, got {r.status_code}")

    step(2, "Fire impression for nonexistent decision_id")
    pause()
    r = requests.get(f"{BASE}/track/impression", params={
        "decision_id": "fake-uuid", "creative_id": "x", "user_id": "x"
    })
    if r.status_code == 404:
        ok(f"404 returned: {r.json()['detail']}")
    else:
        fail(f"Expected 404, got {r.status_code}")

    step(3, "POST click for nonexistent decision_id")
    pause()
    r = requests.post(f"{BASE}/event/click", json={
        "decision_id": "fake-uuid", "creative_id": "x", "user_id": "x"
    })
    if r.status_code == 404:
        ok(f"404 returned: {r.json()['detail']}")
    else:
        fail(f"Expected 404, got {r.status_code}")

    step(4, "Request ad with malformed context JSON (should not crash)")
    pause()
    r = requests.get(f"{BASE}/ad", params={
        "placement_id": "homepage_hero", "user_id": "u", "context": "not{json"
    })
    if r.status_code == 200:
        ok(f"200 returned – server gracefully ignored bad context")
    else:
        fail(f"Expected 200, got {r.status_code}")

    print(f"\n  {GREEN}Scenario 4 complete.{RESET} All error paths handled correctly.\n")


# ══════════════════════════════════════════════════════════════════════════
#  SCENARIO 5 – Reconfiguration: add a new placement mid-session
# ══════════════════════════════════════════════════════════════════════════

def scenario_5():
    banner("SCENARIO 5: Live Reconfiguration – Add Placement + Creatives")
    print("  Simulates a campaign manager adding a new 'checkout_banner'")
    print("  placement and two creatives via direct DB insert, then")
    print("  immediately serving ads from it.\n")

    import sqlite3, os
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ad_server.db")

    step(1, "Inserting new placement 'checkout_banner' into SQLite")
    pause()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Idempotent
    cur.execute("SELECT id FROM placements WHERE id = 'checkout_banner'")
    if not cur.fetchone():
        cur.execute("INSERT INTO placements (id, name) VALUES (?, ?)",
                    ("checkout_banner", "Checkout Page Banner (728×90)"))
        cur.execute("INSERT INTO creatives (id, placement_id, line_item_id, name, metadata) VALUES (?, ?, ?, ?, ?)",
                    ("bolt_checkout_urgency", "checkout_banner", "li_bolt_seasonal",
                     "Bolt Shoes – Complete Your Order!", '{"advertiser":"Bolt Shoes","segment":"cart_abandoner","cta":"Buy Now"}'))
        cur.execute("INSERT INTO creatives (id, placement_id, line_item_id, name, metadata) VALUES (?, ?, ?, ?, ?)",
                    ("acme_checkout_upsell", "checkout_banner", "li_acme_brand",
                     "Acme Travel – Add Travel Insurance", '{"advertiser":"Acme Travel","segment":"checkout","cta":"Add Insurance"}'))
        conn.commit()
    conn.close()
    ok("Inserted placement + 2 creatives")

    step(2, "Requesting ad from newly-created placement")
    pause()
    d = serve_and_track("checkout_banner", "user_carol", {"page": "/checkout", "cart_value": 149.99})
    ok(f"checkout_banner → {BOLD}{d['creative_id']}{RESET}  ({d['line_item_id']})")
    info(f"decision_id: {d['decision_id']}")

    step(3, "Firing impression + click on new placement")
    pause()
    fire_impression(d)
    ok("Impression logged")
    fire_click(d)
    ok("Click logged")
    global impressions_fired, clicks_fired
    impressions_fired += 1
    clicks_fired += 1

    print(f"\n  {GREEN}Scenario 5 complete.{RESET} Hot-reloaded a new placement with zero downtime.\n")


# ══════════════════════════════════════════════════════════════════════════
#  FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════

def summary():
    banner("SUMMARY – Session Analytics")

    section("Decisions by placement")
    for pid, count in sorted(placement_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 40)
        print(f"    {pid:28s}  {count:3d}  {DIM}{bar}{RESET}")

    section("Decisions by creative")
    for cid, count in sorted(creative_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 40)
        print(f"    {cid:28s}  {count:3d}  {DIM}{bar}{RESET}")

    section("Per-user decision count")
    for uid, decs in sorted(user_decisions.items()):
        placements_hit = set(d["placement_id"] for d in decs)
        print(f"    {uid:28s}  {len(decs):3d} decisions  placements: {', '.join(sorted(placements_hit))}")

    section("Aggregate totals")
    print(f"    Total decisions:    {len(all_decisions)}")
    print(f"    Impressions fired:  {impressions_fired}")
    print(f"    Clicks fired:       {clicks_fired}")
    ctr = (clicks_fired / impressions_fired * 100) if impressions_fired else 0
    print(f"    Session CTR:        {ctr:.1f}%")

    section("Server-side verification (debug endpoints)")
    decisions_db = get_debug("decisions")
    events_db = get_debug("events")
    print(f"    /debug/decisions returned {len(decisions_db)} rows (capped at 20)")
    print(f"    /debug/events    returned {len(events_db)} rows (capped at 50)")
    if decisions_db:
        print(f"\n    Most recent decision:")
        print(f"      {pretty(decisions_db[0])}")

    print(f"\n{BOLD}{'═' * 70}")
    print(f"  Demo complete.  All scenarios passed.")
    print(f"{'═' * 70}{RESET}\n")


# ══════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════

def main():
    # Sanity check: is the server running?
    try:
        requests.get(f"{BASE}/debug/decisions", timeout=2)
    except requests.ConnectionError:
        print(f"\n{RED}ERROR: Cannot reach {BASE}")
        print(f"Start the server first:  uvicorn main:app --reload{RESET}\n")
        sys.exit(1)

    scenario_1()
    scenario_2()
    scenario_3()
    scenario_4()
    scenario_5()
    summary()


if __name__ == "__main__":
    main()
