from __future__ import annotations

from typing import Any

import httpx


class HomeAssistantClient:
    """Minimal REST client for Home Assistant."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=20.0,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )

    def healthcheck(self) -> dict[str, Any]:
        resp = self._client.get("/api/")
        resp.raise_for_status()
        return resp.json()

    def get_states(self) -> list[dict[str, Any]]:
        resp = self._client.get("/api/states")
        resp.raise_for_status()
        return resp.json()

    def inventory_by_domain(self) -> dict[str, int]:
        states = self.get_states()
        counts: dict[str, int] = {}
        for entity in states:
            entity_id = entity.get("entity_id", "")
            domain = entity_id.split(".", 1)[0] if "." in entity_id else "unknown"
            counts[domain] = counts.get(domain, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[0]))

    def call_service(self, domain: str, service: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Call HA service endpoint. Use only with safety guardrails."""
        resp = self._client.post(f"/api/services/{domain}/{service}", json=payload)
        resp.raise_for_status()
        return {"ok": True, "status_code": resp.status_code}

    def close(self) -> None:
        self._client.close()
