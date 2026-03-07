"""
test_ad_server.py – Pytest suite for the demo ad server.

Uses FastAPI's TestClient (no running server required).

Run:
    pip install pytest httpx
    cd ad-server && pytest test_ad_server.py -v
"""

import json
import os
import uuid

import pytest

# ---------------------------------------------------------------------------
# Configure a test DB BEFORE any app code touches the default engine.
# ---------------------------------------------------------------------------

TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_ad_server.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

import models  # noqa: E402
models.configure_engine(f"sqlite:///{TEST_DB}")

from seed import init_db  # noqa: E402
init_db()  # Create tables + seed data (lifespan won't fire with TestClient)

from main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_ad(placement_id: str = "homepage_hero", user_id: str = "test_user",
           context: dict = None) -> dict:
    params = {"placement_id": placement_id, "user_id": user_id}
    if context:
        params["context"] = json.dumps(context)
    r = client.get("/ad", params=params)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    return r.json()


# ═══════════════════════════════════════════════════════════════════════════
#  GET /ad
# ═══════════════════════════════════════════════════════════════════════════

class TestServeAd:

    def test_basic_ad_response_shape(self):
        data = get_ad()
        for key in ("decision_id", "placement_id", "user_id", "creative_id",
                     "line_item_id", "served_at", "impression_url", "click_url"):
            assert key in data

    def test_placement_id_echoed(self):
        data = get_ad(placement_id="sidebar_rect")
        assert data["placement_id"] == "sidebar_rect"

    def test_user_id_echoed(self):
        data = get_ad(user_id="u_42")
        assert data["user_id"] == "u_42"

    def test_decision_id_is_uuid(self):
        data = get_ad()
        uuid.UUID(data["decision_id"])

    def test_creative_belongs_to_placement(self):
        hero_creatives = {"acme_hero_beach", "acme_hero_mountain", "bolt_hero_launch"}
        for _ in range(20):
            data = get_ad(placement_id="homepage_hero")
            assert data["creative_id"] in hero_creatives

    def test_sidebar_creatives(self):
        sidebar_creatives = {"acme_side_retarget", "bolt_side_seasonal", "bolt_side_launch"}
        for _ in range(20):
            data = get_ad(placement_id="sidebar_rect")
            assert data["creative_id"] in sidebar_creatives

    def test_interstitial_creatives(self):
        inter_creatives = {"acme_inter_beach", "acme_inter_retarget",
                           "bolt_inter_launch", "bolt_inter_seasonal"}
        for _ in range(20):
            data = get_ad(placement_id="article_interstitial")
            assert data["creative_id"] in inter_creatives

    def test_tracking_urls_contain_decision_id(self):
        data = get_ad()
        assert data["decision_id"] in data["impression_url"]
        assert data["decision_id"] in data["click_url"]

    def test_tracking_urls_contain_creative_id(self):
        data = get_ad()
        assert data["creative_id"] in data["impression_url"]
        assert data["creative_id"] in data["click_url"]

    def test_context_accepted(self):
        data = get_ad(context={"page": "/sports", "device": "mobile"})
        assert data["creative_id"]

    def test_malformed_context_graceful(self):
        r = client.get("/ad", params={
            "placement_id": "homepage_hero",
            "user_id": "u",
            "context": "not{valid json",
        })
        assert r.status_code == 200

    def test_nonexistent_placement_404(self):
        r = client.get("/ad", params={"placement_id": "xyz", "user_id": "u"})
        assert r.status_code == 404
        assert "No creatives found" in r.json()["detail"]

    def test_missing_placement_id_422(self):
        r = client.get("/ad", params={"user_id": "u"})
        assert r.status_code == 422

    def test_missing_user_id_422(self):
        r = client.get("/ad", params={"placement_id": "homepage_hero"})
        assert r.status_code == 422

    def test_unique_decision_ids(self):
        ids = {get_ad()["decision_id"] for _ in range(10)}
        assert len(ids) == 10


# ═══════════════════════════════════════════════════════════════════════════
#  Impression & Click tracking (GET)
# ═══════════════════════════════════════════════════════════════════════════

class TestTrackingGET:

    def test_impression_ok(self):
        ad = get_ad()
        r = client.get("/track/impression", params={
            "decision_id": ad["decision_id"],
            "creative_id": ad["creative_id"],
            "user_id": ad["user_id"],
        })
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_click_ok(self):
        ad = get_ad()
        r = client.get("/track/click", params={
            "decision_id": ad["decision_id"],
            "creative_id": ad["creative_id"],
            "user_id": ad["user_id"],
        })
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_impression_bad_decision_404(self):
        r = client.get("/track/impression", params={
            "decision_id": "nonexistent", "creative_id": "x", "user_id": "x",
        })
        assert r.status_code == 404

    def test_click_bad_decision_404(self):
        r = client.get("/track/click", params={
            "decision_id": "nonexistent", "creative_id": "x", "user_id": "x",
        })
        assert r.status_code == 404

    def test_impression_url_from_ad_response(self):
        ad = get_ad()
        r = client.get(ad["impression_url"])
        assert r.status_code == 200

    def test_click_url_from_ad_response(self):
        ad = get_ad()
        r = client.get(ad["click_url"])
        assert r.status_code == 200

    def test_multiple_impressions_same_decision(self):
        ad = get_ad()
        for _ in range(5):
            r = client.get("/track/impression", params={
                "decision_id": ad["decision_id"],
                "creative_id": ad["creative_id"],
                "user_id": ad["user_id"],
            })
            assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
#  Impression & Click tracking (POST)
# ═══════════════════════════════════════════════════════════════════════════

class TestTrackingPOST:

    def test_post_impression(self):
        ad = get_ad()
        r = client.post("/event/impression", json={
            "decision_id": ad["decision_id"],
            "creative_id": ad["creative_id"],
            "user_id": ad["user_id"],
        })
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert isinstance(body["event_id"], int)

    def test_post_click(self):
        ad = get_ad()
        r = client.post("/event/click", json={
            "decision_id": ad["decision_id"],
            "creative_id": ad["creative_id"],
            "user_id": ad["user_id"],
        })
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert isinstance(body["event_id"], int)

    def test_post_impression_with_timestamp(self):
        ad = get_ad()
        r = client.post("/event/impression", json={
            "decision_id": ad["decision_id"],
            "creative_id": ad["creative_id"],
            "user_id": ad["user_id"],
            "timestamp": "2026-01-15T12:00:00Z",
        })
        assert r.status_code == 200

    def test_post_impression_bad_decision_404(self):
        r = client.post("/event/impression", json={
            "decision_id": "fake", "creative_id": "x", "user_id": "x",
        })
        assert r.status_code == 404

    def test_post_click_bad_decision_404(self):
        r = client.post("/event/click", json={
            "decision_id": "fake", "creative_id": "x", "user_id": "x",
        })
        assert r.status_code == 404

    def test_post_impression_missing_fields_422(self):
        r = client.post("/event/impression", json={"decision_id": "x"})
        assert r.status_code == 422

    def test_event_ids_increment(self):
        ad = get_ad()
        ids = []
        for _ in range(3):
            r = client.post("/event/impression", json={
                "decision_id": ad["decision_id"],
                "creative_id": ad["creative_id"],
                "user_id": ad["user_id"],
            })
            ids.append(r.json()["event_id"])
        assert ids == sorted(ids)
        assert len(set(ids)) == 3


# ═══════════════════════════════════════════════════════════════════════════
#  Debug endpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestDebugEndpoints:

    def test_debug_decisions_returns_list(self):
        r = client.get("/debug/decisions")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_debug_events_returns_list(self):
        r = client.get("/debug/events")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_debug_decisions_after_ad_request(self):
        ad = get_ad(user_id="debug_test_user")
        decisions = client.get("/debug/decisions").json()
        ids = [d["id"] for d in decisions]
        assert ad["decision_id"] in ids

    def test_debug_events_after_impression(self):
        ad = get_ad()
        client.get("/track/impression", params={
            "decision_id": ad["decision_id"],
            "creative_id": ad["creative_id"],
            "user_id": ad["user_id"],
        })
        events = client.get("/debug/events").json()
        decision_ids_in_events = [e["decision_id"] for e in events]
        assert ad["decision_id"] in decision_ids_in_events

    def test_debug_decisions_shape(self):
        get_ad()
        d = client.get("/debug/decisions").json()[0]
        for key in ("id", "placement_id", "user_id", "creative_id",
                     "line_item_id", "served_at"):
            assert key in d

    def test_debug_events_shape(self):
        ad = get_ad()
        client.get("/track/impression", params={
            "decision_id": ad["decision_id"],
            "creative_id": ad["creative_id"],
            "user_id": ad["user_id"],
        })
        e = client.get("/debug/events").json()[0]
        for key in ("id", "decision_id", "event_type", "creative_id",
                     "user_id", "timestamp"):
            assert key in e

    def test_debug_decisions_capped_at_20(self):
        for _ in range(25):
            get_ad()
        decisions = client.get("/debug/decisions").json()
        assert len(decisions) <= 20


# ═══════════════════════════════════════════════════════════════════════════
#  Full lifecycle integration
# ═══════════════════════════════════════════════════════════════════════════

class TestLifecycle:

    def test_full_lifecycle(self):
        ad = get_ad(placement_id="homepage_hero", user_id="lifecycle_user")
        decision_id = ad["decision_id"]

        r = client.get(ad["impression_url"])
        assert r.status_code == 200

        r = client.get(ad["click_url"])
        assert r.status_code == 200

        decisions = client.get("/debug/decisions").json()
        assert any(d["id"] == decision_id for d in decisions)

        events = client.get("/debug/events").json()
        matching = [e for e in events if e["decision_id"] == decision_id]
        types = {e["event_type"] for e in matching}
        assert "impression" in types
        assert "click" in types

    def test_multi_placement_page_load(self):
        user = "page_load_user"
        placements = ["homepage_hero", "sidebar_rect", "article_interstitial"]
        decisions = []

        for pid in placements:
            ad = get_ad(placement_id=pid, user_id=user)
            assert ad["placement_id"] == pid
            assert ad["user_id"] == user
            decisions.append(ad)

        for ad in decisions:
            r = client.get(ad["impression_url"])
            assert r.status_code == 200

        r = client.get(decisions[0]["click_url"])
        assert r.status_code == 200

        ids = [d["decision_id"] for d in decisions]
        assert len(set(ids)) == 3

    def test_concurrent_users(self):
        users = [f"concurrent_user_{i}" for i in range(5)]
        results = {}
        for u in users:
            results[u] = get_ad(user_id=u)

        ids = [r["decision_id"] for r in results.values()]
        assert len(set(ids)) == 5

        for u in users:
            assert results[u]["user_id"] == u


# ═══════════════════════════════════════════════════════════════════════════
#  Optimizer isolation
# ═══════════════════════════════════════════════════════════════════════════

class TestOptimizer:

    def test_select_creative_returns_candidate(self):
        from optimizer import select_creative
        candidates = [
            {"id": "a", "line_item_id": "li_1", "name": "A"},
            {"id": "b", "line_item_id": "li_2", "name": "B"},
        ]
        result = select_creative("test", "user", None, candidates)
        assert result in candidates

    def test_select_creative_empty_raises(self):
        from optimizer import select_creative
        with pytest.raises(ValueError, match="No eligible candidates"):
            select_creative("test", "user", None, [])

    def test_select_creative_single_candidate(self):
        from optimizer import select_creative
        candidates = [{"id": "only", "line_item_id": "li", "name": "Only"}]
        result = select_creative("test", "user", None, candidates)
        assert result["id"] == "only"

    def test_rotation_is_not_deterministic(self):
        from optimizer import select_creative
        candidates = [
            {"id": "a", "line_item_id": "li_1", "name": "A"},
            {"id": "b", "line_item_id": "li_2", "name": "B"},
            {"id": "c", "line_item_id": "li_3", "name": "C"},
        ]
        seen = set()
        for _ in range(50):
            r = select_creative("test", "user", None, candidates)
            seen.add(r["id"])
        assert len(seen) > 1


# ═══════════════════════════════════════════════════════════════════════════
#  Cleanup
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
