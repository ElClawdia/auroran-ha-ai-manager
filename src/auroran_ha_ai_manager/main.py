from __future__ import annotations

import argparse
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from auroran_ha_ai_manager.alerts import AlertEngine, Notifier
from auroran_ha_ai_manager.config import Settings
from auroran_ha_ai_manager.ha_client import HomeAssistantClient
from auroran_ha_ai_manager.influx_memory import InfluxMemoryWriter
from auroran_ha_ai_manager.mqtt_client import MqttIngestor
from auroran_ha_ai_manager.optimizer import Optimizer


def _in_bedroom_off_window(settings: Settings) -> bool:
    tz = ZoneInfo(settings.local_timezone)
    h = datetime.now(tz).hour
    start = settings.bedroom_hp_off_start_hour
    end = settings.bedroom_hp_off_end_hour
    if start <= end:
        return start <= h < end
    return h >= start or h < end


def _healthcheck(settings: Settings) -> int:
    ha = HomeAssistantClient(settings.ha_base_url, settings.ha_token)
    try:
        status = ha.healthcheck()
        print(f"HA healthcheck OK: {status}")
        return 0
    finally:
        ha.close()


def _inventory(settings: Settings) -> int:
    ha = HomeAssistantClient(settings.ha_base_url, settings.ha_token)
    try:
        inventory = ha.inventory_by_domain()
        print("HA entity inventory by domain:")
        for domain, count in inventory.items():
            print(f"- {domain}: {count}")
        return 0
    finally:
        ha.close()


def _get_float_state(by_id: dict[str, dict], entity_id: str) -> float | None:
    try:
        return float(by_id.get(entity_id, {}).get("state"))
    except Exception:
        return None


def _run_cycle(settings: Settings) -> int:
    notifier = Notifier()
    ha = HomeAssistantClient(settings.ha_base_url, settings.ha_token)

    memory: InfluxMemoryWriter | None = None
    if settings.influxdb_url and settings.influxdb_token:
        memory = InfluxMemoryWriter(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
            bucket=settings.influxdb_ai_memory_bucket,
        )

    mqtt_ingestor: MqttIngestor | None = None
    mqtt_topics: list[str] = []
    if settings.mqtt_topics:
        mqtt_topics = [t.strip() for t in settings.mqtt_topics.split(",") if t.strip()]

    try:
        if settings.mqtt_host and mqtt_topics:
            mqtt_ingestor = MqttIngestor(
                host=settings.mqtt_host,
                port=settings.mqtt_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
            )
            mqtt_ingestor.connect_and_subscribe(mqtt_topics)
            # Short warm-up so we have initial samples.
            time.sleep(1.5)

        states = ha.get_states()
        by_id = {e.get("entity_id"): e for e in states if e.get("entity_id")}

        # Price + weather context from HA entities.
        current_price = _get_float_state(by_id, "sensor.electricity_cost_in_cents_per_kwh")
        if current_price is None:
            current_price = _get_float_state(by_id, "sensor.energy_spot_price")
        outdoor_temp = _get_float_state(by_id, "sensor.openweathermap_temperature")

        # Hard policy: bedroom heat pump OFF between 19:00-09:00 Helsinki.
        if _in_bedroom_off_window(settings):
            bedroom = by_id.get(settings.bedroom_hp_entity)
            if bedroom and bedroom.get("state") != "off":
                ha.call_service("climate", "set_hvac_mode", {"entity_id": settings.bedroom_hp_entity, "hvac_mode": "off"})
                notifier.send(
                    f"Policy enforced: {settings.bedroom_hp_entity} turned OFF "
                    f"for quiet window {settings.bedroom_hp_off_start_hour}:00-{settings.bedroom_hp_off_end_hour}:00 "
                    f"({settings.local_timezone})."
                )
                if memory:
                    memory.write_action(
                        service="climate.set_hvac_mode",
                        entity_id=settings.bedroom_hp_entity,
                        result="off",
                        reason="bedroom_off_window_policy",
                    )

        # Temperature policy: if room temperatures are above threshold, keep both heat pumps off.
        indoor_sensor_ids = [x.strip() for x in settings.indoor_temp_sensor_ids.split(",") if x.strip()]
        indoor_refs = [_get_float_state(by_id, eid) for eid in indoor_sensor_ids]
        indoor_vals = [v for v in indoor_refs if v is not None]
        indoor_max = max(indoor_vals) if indoor_vals else None

        for hp_entity in [settings.bedroom_hp_entity, settings.hallway_hp_entity]:
            hp = by_id.get(hp_entity)
            if not hp:
                continue
            if indoor_max is not None and indoor_max > settings.comfort_temp_high_c and hp.get("state") != "off":
                ha.call_service("climate", "set_hvac_mode", {"entity_id": hp_entity, "hvac_mode": "off"})
                if memory:
                    memory.write_action("climate.set_hvac_mode", hp_entity, "off", "indoor_above_21_policy")

        # Expensive electricity policy:
        # - target comfort floor 20C
        # - avoid bedroom heat pump entirely
        if current_price is not None and current_price >= settings.expensive_price_c_per_kwh:
            bedroom = by_id.get(settings.bedroom_hp_entity)
            if bedroom and bedroom.get("state") != "off":
                ha.call_service("climate", "set_hvac_mode", {"entity_id": settings.bedroom_hp_entity, "hvac_mode": "off"})
                if memory:
                    memory.write_action("climate.set_hvac_mode", settings.bedroom_hp_entity, "off", "expensive_price_policy")

            hallway = by_id.get(settings.hallway_hp_entity)
            representative_temp = min(indoor_vals) if indoor_vals else None
            if hallway and representative_temp is not None:
                if representative_temp < settings.comfort_temp_low_c:
                    ha.call_service("climate", "set_hvac_mode", {"entity_id": settings.hallway_hp_entity, "hvac_mode": "heat"})
                    ha.call_service("climate", "set_temperature", {"entity_id": settings.hallway_hp_entity, "temperature": settings.comfort_temp_low_c})
                    if memory:
                        memory.write_action("climate.set_temperature", settings.hallway_hp_entity, str(settings.comfort_temp_low_c), "expensive_price_floor_20")
                elif hallway.get("state") != "off":
                    ha.call_service("climate", "set_hvac_mode", {"entity_id": settings.hallway_hp_entity, "hvac_mode": "off"})
                    if memory:
                        memory.write_action("climate.set_hvac_mode", settings.hallway_hp_entity, "off", "expensive_price_above_floor")

        # Miner heat note: above 0C outside, prefer relying on miner heat before enabling extra HP heating.
        if outdoor_temp is not None and outdoor_temp >= 0 and current_price is not None and current_price >= settings.expensive_price_c_per_kwh:
            notifier.send("Context: Outside >=0C and electricity expensive; prefer miner heat and minimal heat pump usage.")

        upcoming_prices: list[float] | None = None

        recommendations = Optimizer().evaluate(states, current_price=current_price, upcoming_prices=upcoming_prices)
        alerts = AlertEngine().detect()

        if mqtt_ingestor:
            recent = mqtt_ingestor.recent_messages(limit=8)
            notifier.send(f"MQTT ingestion active: {len(recent)} recent messages buffered.")

        if recommendations:
            for rec in recommendations:
                notifier.send(
                    f"RECOMMENDATION (advice-only): {rec.target_entity} -> {rec.proposed_value} "
                    f"[{rec.action}] because {rec.reason} (confidence={rec.confidence:.2f})"
                )
                if memory:
                    memory.write_recommendation(
                        {
                            "action": rec.action,
                            "target_entity": rec.target_entity,
                            "reason": rec.reason,
                            "confidence": rec.confidence,
                        }
                    )

        if alerts:
            for alert in alerts:
                notifier.send(f"[{alert.severity.upper()}] {alert.message}")

        if not recommendations and not alerts:
            notifier.send("Auroran HA AI Manager: cycle complete, no actions.")

        # Persist episodic snapshot for ML/features.
        if memory:
            memory.write_entity_snapshot(states)
            try:
                hashrate = float(by_id.get("sensor.miner_hashrate_gh", {}).get("state"))
            except Exception:
                hashrate = None
            try:
                cost_h = float(by_id.get("sensor.mining_hourly_cost", {}).get("state"))
            except Exception:
                cost_h = None
            try:
                revenue_h = float(by_id.get("sensor.miner_rewards_hourly", {}).get("state"))
            except Exception:
                revenue_h = None
            memory.write_profitability(hashrate_gh=hashrate, revenue_h=revenue_h, cost_h=cost_h)

        return 0
    finally:
        if mqtt_ingestor:
            mqtt_ingestor.close()
        ha.close()


def run() -> None:
    parser = argparse.ArgumentParser(description="Auroran HA AI Manager")
    parser.add_argument("command", nargs="?", default="cycle", choices=["healthcheck", "inventory", "cycle"])
    args = parser.parse_args()

    settings = Settings()

    if args.command == "healthcheck":
        raise SystemExit(_healthcheck(settings))
    if args.command == "inventory":
        raise SystemExit(_inventory(settings))

    raise SystemExit(_run_cycle(settings))


if __name__ == "__main__":
    run()
