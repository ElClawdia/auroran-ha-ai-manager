from __future__ import annotations

import argparse
import time

from auroran_ha_ai_manager.alerts import AlertEngine, Notifier
from auroran_ha_ai_manager.config import Settings
from auroran_ha_ai_manager.ha_client import HomeAssistantClient
from auroran_ha_ai_manager.mqtt_client import MqttIngestor
from auroran_ha_ai_manager.optimizer import Optimizer


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


def _run_cycle(settings: Settings) -> int:
    notifier = Notifier()
    ha = HomeAssistantClient(settings.ha_base_url, settings.ha_token)

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

        # TODO: wire real price series from HA/MQTT connectors.
        current_price = None
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

        if alerts:
            for alert in alerts:
                notifier.send(f"[{alert.severity.upper()}] {alert.message}")

        if not recommendations and not alerts:
            notifier.send("Auroran HA AI Manager: cycle complete, no actions.")

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
