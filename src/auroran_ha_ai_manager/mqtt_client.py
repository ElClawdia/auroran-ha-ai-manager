from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

import paho.mqtt.client as mqtt


@dataclass
class MqttMessage:
    topic: str
    payload: str


class MqttIngestor:
    """Lightweight MQTT subscriber for quick signal ingestion.

    This keeps a short in-memory buffer for recommendation cycles.
    """

    def __init__(
        self,
        host: str,
        port: int = 1883,
        username: str | None = None,
        password: str | None = None,
        max_messages: int = 500,
    ) -> None:
        self.host = host
        self.port = port
        self._buffer: deque[MqttMessage] = deque(maxlen=max_messages)

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if username and password:
            self._client.username_pw_set(username, password)

        self._client.on_message = self._on_message

    def _on_message(self, _client: mqtt.Client, _userdata: object, msg: mqtt.MQTTMessage) -> None:
        payload = msg.payload.decode("utf-8", errors="replace")
        self._buffer.append(MqttMessage(topic=msg.topic, payload=payload))

    def connect_and_subscribe(self, topics: Iterable[str]) -> None:
        self._client.connect(self.host, self.port, 30)
        for topic in topics:
            self._client.subscribe(topic)
        self._client.loop_start()

    def recent_messages(self, limit: int = 50) -> list[MqttMessage]:
        return list(self._buffer)[-limit:]

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
