from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import urllib.parse
import urllib.request


def _esc_tag(v: str) -> str:
    return v.replace("\\", "\\\\").replace(",", "\\,").replace(" ", "\\ ").replace("=", "\\=")


def _esc_field_str(v: str) -> str:
    return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'


class InfluxMemoryWriter:
    """Writes assistant episodic memory and observations to InfluxDB bucket."""

    def __init__(self, url: str, token: str, org: str, bucket: str) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.org = org
        self.bucket = bucket

    def _write_lines(self, lines: list[str]) -> None:
        if not lines:
            return
        params = urllib.parse.urlencode({"org": self.org, "bucket": self.bucket, "precision": "s"})
        endpoint = f"{self.url}/api/v2/write?{params}"
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Token {self.token}",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )
        with urllib.request.urlopen(req, timeout=20):
            pass

    def write_entity_snapshot(self, states: list[dict[str, Any]], source: str = "ha_api") -> None:
        now = int(datetime.now(timezone.utc).timestamp())
        lines: list[str] = []
        for e in states:
            entity_id = str(e.get("entity_id", ""))
            if not entity_id:
                continue
            domain = entity_id.split(".", 1)[0] if "." in entity_id else "unknown"
            raw_state = e.get("state")

            tags = f"entity_id={_esc_tag(entity_id)},domain={_esc_tag(domain)},source={_esc_tag(source)}"

            # Numeric fast-path
            try:
                val = float(raw_state)
                fields = f"state_num={val}"
            except (TypeError, ValueError):
                fields = f"state_text={_esc_field_str(str(raw_state))}"

            lines.append(f"ha_event,{tags} {fields} {now}")

        self._write_lines(lines)

    def write_recommendation(self, rec: dict[str, Any]) -> None:
        now = int(datetime.now(timezone.utc).timestamp())
        tags = (
            f"type={_esc_tag(str(rec.get('action', 'unknown')))},"
            f"target={_esc_tag(str(rec.get('target_entity', 'unknown')))}"
        )
        reason = _esc_field_str(str(rec.get("reason", "")))
        confidence = float(rec.get("confidence", 0.0))
        line = f"assistant_recommendation,{tags} confidence={confidence},reason={reason} {now}"
        self._write_lines([line])

    def write_action(self, service: str, entity_id: str, result: str, reason: str = "") -> None:
        now = int(datetime.now(timezone.utc).timestamp())
        tags = f"service={_esc_tag(service)},entity_id={_esc_tag(entity_id)}"
        fields = f"result={_esc_field_str(result)},reason={_esc_field_str(reason)}"
        self._write_lines([f"assistant_action,{tags} {fields} {now}"])

    def write_profitability(self, hashrate_gh: float | None, revenue_h: float | None, cost_h: float | None) -> None:
        if hashrate_gh is None and revenue_h is None and cost_h is None:
            return
        now = int(datetime.now(timezone.utc).timestamp())
        parts = []
        if hashrate_gh is not None:
            parts.append(f"hashrate_gh={float(hashrate_gh)}")
        if revenue_h is not None:
            parts.append(f"revenue_hourly_eur={float(revenue_h)}")
        if cost_h is not None:
            parts.append(f"cost_hourly_eur={float(cost_h)}")
        if revenue_h is not None and cost_h is not None:
            parts.append(f"net_hourly_eur={float(revenue_h)-float(cost_h)}")
        self._write_lines([f"profitability_snapshot,source=ha_powerpool {','.join(parts)} {now}"])
