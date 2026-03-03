from __future__ import annotations

from auroran_ha_ai_manager.alerts import AlertEngine, Notifier
from auroran_ha_ai_manager.config import Settings
from auroran_ha_ai_manager.ha_client import HomeAssistantClient
from auroran_ha_ai_manager.optimizer import Optimizer


def run() -> None:
    settings = Settings()
    ha = HomeAssistantClient(settings.ha_base_url, settings.ha_token)
    notifier = Notifier()

    try:
        states = ha.get_states()
        optimizer = Optimizer()
        recommendations = optimizer.evaluate(states, current_price=None, upcoming_prices=None)

        alerts = AlertEngine().detect()

        if recommendations:
            for rec in recommendations:
                notifier.send(
                    f"RECOMMENDATION: {rec.target_entity} -> {rec.proposed_value} ({rec.reason})"
                )

        if alerts:
            for alert in alerts:
                notifier.send(f"[{alert.severity.upper()}] {alert.message}")

        if not recommendations and not alerts:
            notifier.send("Auroran HA AI Manager: cycle complete, no actions.")

    finally:
        ha.close()


if __name__ == "__main__":
    run()
