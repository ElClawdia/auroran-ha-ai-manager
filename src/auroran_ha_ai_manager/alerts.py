from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Alert:
    severity: str
    message: str


class AlertEngine:
    """Anomaly and threshold alerting (MVP skeleton)."""

    def detect(self) -> list[Alert]:
        # TODO: Implement sustained threshold and trend detection.
        return []


class Notifier:
    """Notification abstraction for Slack/WhatsApp/webhooks."""

    def send(self, text: str) -> None:
        # TODO: Implement real delivery clients.
        print(text)
