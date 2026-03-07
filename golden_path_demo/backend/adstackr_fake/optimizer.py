import math
import random
from typing import Dict

from adstackr_fake.models import RunState, get_or_create_option_stats


def compute_ctr(clicks: int, impressions: int, alpha: float = 1.0, beta: float = 1.0) -> float:
    # simple smoothed CTR estimate
    return (clicks + alpha) / (impressions + alpha + beta)


def optimize_run(run: RunState, epsilon: float = 0.1) -> Dict[str, str]:
    """Semi-realistic per-segment optimizer using epsilon-greedy on CTR.

    Returns a dict of segment_id -> chosen_option_key.
    """
    new_choices: Dict[str, str] = {}

    for segment_id, option_keys in run.candidates.items():
        if not option_keys:
            continue

        # compute CTR per option
        ctrs = []
        for ok in option_keys:
            stats = get_or_create_option_stats(run, segment_id, ok)
            ctr = compute_ctr(stats.clicks, stats.impressions)
            ctrs.append((ok, ctr))

        # exploration vs exploitation
        if random.random() < epsilon:
            # explore: pick random option
            chosen_key = random.choice(option_keys)
        else:
            # exploit: pick option with highest CTR
            chosen_key = max(ctrs, key=lambda t: t[1])[0]

        run.current_choice[segment_id] = chosen_key
        new_choices[segment_id] = chosen_key

    return new_choices
