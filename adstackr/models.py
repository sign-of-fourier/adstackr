from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel


class ConnectorConfig(BaseModel):
    tenant_id: str
    dv360_credentials: Dict
    cm360_credentials: Dict
    studio_credentials: Dict
    feed_rows: List[Dict[str, str]]
    linked_campaign_id: Optional[str] = None


class MappingOption(BaseModel):
    segment_id: str
    template_id: str
    component_variants: Dict[str, str]


@dataclass
class OptionStats:
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0


@dataclass
class RunState:
    run_id: str
    tenant_id: str
    # current_choice[segment_id] = option_key
    current_choice: Dict[str, str] = field(default_factory=dict)
    # candidates[segment_id] = list[option_key]
    candidates: Dict[str, List[str]] = field(default_factory=dict)
    # mapping_options[option_key] = MappingOption
    mapping_options: Dict[str, MappingOption] = field(default_factory=dict)
    # stats[(segment_id, option_key)] = OptionStats
    stats: Dict[Tuple[str, str], OptionStats] = field(default_factory=dict)


@dataclass
class AdStackrFakeState:
    connector_configs: Dict[str, ConnectorConfig] = field(default_factory=dict)
    runs: Dict[str, RunState] = field(default_factory=dict)


state = AdStackrFakeState()


def get_or_create_option_stats(run: RunState, segment_id: str, option_key: str) -> OptionStats:
    key = (segment_id, option_key)
    if key not in run.stats:
        run.stats[key] = OptionStats()
    return run.stats[key]
