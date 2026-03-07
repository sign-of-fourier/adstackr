from typing import Dict, List, Tuple
from pydantic import BaseModel
from dataclasses import dataclass, field


class Campaign(BaseModel):
    id: str
    name: str


class LineItem(BaseModel):
    id: str
    campaign_id: str
    name: str
    status: str = "active"
    targeting_segment_ids: List[str] = []


class Creative(BaseModel):
    id: str
    name: str
    type: str = "display"
    size: str = "300x250"
    landing_url: str
    template_id: str


class Template(BaseModel):
    id: str
    name: str
    component_keys: List[str]


class FeedRow(BaseModel):
    id: str
    segment_id: str
    data: Dict[str, str]


@dataclass
class StatsCounters:
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0


@dataclass
class GoogleFakeState:
    campaigns: Dict[str, Campaign] = field(default_factory=dict)
    line_items: Dict[str, LineItem] = field(default_factory=dict)
    creatives: Dict[str, Creative] = field(default_factory=dict)
    templates: Dict[str, Template] = field(default_factory=dict)
    feed_rows: Dict[str, FeedRow] = field(default_factory=dict)
    # key: (line_item_id, creative_id, template_id, segment_id)
    stats: Dict[Tuple[str, str, str, str], StatsCounters] = field(
        default_factory=dict
    )


state = GoogleFakeState()


def get_or_create_stats(
    line_item_id: str, creative_id: str, template_id: str, segment_id: str
) -> StatsCounters:
    key = (line_item_id, creative_id, template_id, segment_id)
    if key not in state.stats:
        state.stats[key] = StatsCounters()
    return state.stats[key]



# Temporary hard-coded demo data for 1.1 / 1.2

state.campaigns = {
    "12345-C1": Campaign(id="12345-C1", name="Demo Campaign 1"),
    "12345-C2": Campaign(id="12345-C2", name="Demo Campaign 2"),
}

state.line_items = {
    "LI_1": LineItem(id="LI_1", campaign_id="12345-C1", name="Line Item 1"),
    "LI_2": LineItem(id="LI_2", campaign_id="12345-C1", name="Line Item 2"),
}

state.creatives = {
    "CR_1": Creative(
        id="CR_1",
        name="Creative 1",
        landing_url="https://brand.example/1",
        template_id="T_1",
    ),
    "CR_2": Creative(
        id="CR_2",
        name="Creative 2",
        landing_url="https://brand.example/2",
        template_id="T_1",
    ),
}

state.templates = {
    "T_1": Template(id="T_1", name="Base Template", component_keys=["headline", "image"]),
}

state.feed_rows = {
    "row1": FeedRow(id="row1", segment_id="seg_A", data={"headline": "Buy shoes", "image": "img1.jpg"}),
    "row2": FeedRow(id="row2", segment_id="seg_B", data={"headline": "Buy hats", "image": "img2.jpg"}),
}




