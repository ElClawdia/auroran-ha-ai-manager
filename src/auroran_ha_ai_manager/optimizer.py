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
    """Rule-based optimization engine (MVP).

    Advice-only by default. Real write actions are guarded elsewhere.
    """

    def evaluate(
        self,
        ha_states: list[dict[str, Any]],
        current_price: float | None,
        upcoming_prices: list[float] | None,
    ) -> list[Recommendation]:
        if not ha_states:
            return []

        recommendations: list[Recommendation] = []

        climate_entities = [s for s in ha_states if str(s.get("entity_id", "")).startswith("climate.")]
        low_temp_sensors = []
        for state in ha_states:
            entity_id = str(state.get("entity_id", ""))
            if not entity_id.startswith("sensor."):
                continue
            try:
                temp = float(state.get("state"))
            except (TypeError, ValueError):
                continue
            unit = str(state.get("attributes", {}).get("unit_of_measurement", ""))
            fname = str(state.get("attributes", {}).get("friendly_name", "")).lower()
            is_outdoor = any(k in entity_id for k in ["openweathermap", "outdoor", "outside", "weather"])
            looks_room_temp = (
                entity_id.startswith("sensor.temperature_")
                or ("temperature" in entity_id and "miner" not in entity_id and "inlet" not in entity_id and "outlet" not in entity_id)
                or ("temperature" in fname and "miner" not in fname)
            )
            if unit in {"°C", "C", "celsius"} and temp < 19.5 and not is_outdoor and looks_room_temp:
                low_temp_sensors.append((entity_id, temp))

        if current_price is not None and upcoming_prices:
            future_avg = sum(upcoming_prices) / len(upcoming_prices)
            if future_avg > current_price * 1.15 and climate_entities:
                recommendations.append(
                    Recommendation(
                        target_entity=climate_entities[0]["entity_id"],
                        action="suggest_preheat",
                        proposed_value="+0.5°C setpoint",
                        reason="Upcoming prices appear higher than current price window.",
                        confidence=0.62,
                    )
                )

        if low_temp_sensors and climate_entities:
            coldest = min(low_temp_sensors, key=lambda x: x[1])
            recommendations.append(
                Recommendation(
                    target_entity=climate_entities[0]["entity_id"],
                    action="suggest_heat_increase",
                    proposed_value="+0.5°C setpoint",
                    reason=f"Low indoor temperature detected at {coldest[0]} ({coldest[1]:.1f}°C).",
                    confidence=0.71,
                )
            )

        return recommendations
