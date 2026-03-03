from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Recommendation:
    target_entity: str
    action: str
    proposed_value: float | str
    reason: str
    confidence: float


class Optimizer:
    """Rule-based optimization engine (MVP)."""

    def evaluate(
        self,
        ha_states: list[dict[str, Any]],
        current_price: float | None,
        upcoming_prices: list[float] | None,
    ) -> list[Recommendation]:
        # Placeholder logic: wire in actual rules from README roadmap.
        if not ha_states:
            return []

        recommendations: list[Recommendation] = []
        # Example stub: if price feed unavailable, do nothing.
        if current_price is None:
            return recommendations

        # Add real heuristics here.
        return recommendations
