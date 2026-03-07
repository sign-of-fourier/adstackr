"""
optimizer.py – Creative selection logic.

V0: uniform random selection from eligible candidates.

This module is intentionally isolated so the decision strategy can be
swapped later for:
  - A call to an external HTTP optimizer service
  - A local Thompson-sampling / contextual-bandit model
  - Any pure function with the same signature
"""

import random
from typing import Any, Dict, List, Optional


def select_creative(
    placement_id: str,
    user_id: str,
    context: Optional[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Pick one creative from *candidates*.

    Parameters
    ----------
    placement_id : str
        The placement requesting an ad.
    user_id : str
        Opaque user identifier from the ad request.
    context : dict | None
        Arbitrary context forwarded from the request (page URL, device
        info, etc.).  Ignored in V0.
    candidates : list[dict]
        Each dict has at least ``id``, ``line_item_id``, ``name``.

    Returns
    -------
    dict
        The chosen candidate dictionary.

    Raises
    ------
    ValueError
        If *candidates* is empty.
    """
    if not candidates:
        raise ValueError("No eligible candidates for placement")

    # --- V0: uniform random ---
    return random.choice(candidates)
