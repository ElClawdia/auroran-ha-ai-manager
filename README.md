# Auroran HA AI Manager

AI assistant sidecar for **Home Assistant (HA)** that monitors entities, energy prices, weather, and system health, then suggests/automates actions to reduce electricity cost while preserving comfort and safety.

---

## Vision

Build a trustworthy “energy + home operations co-pilot” for Home Assistant that:
- understands current home state (temperatures, sensors, alerts, host health)
- predicts near-future cost/comfort risk (price spikes, weather shifts, abnormal telemetry)
- recommends or executes low-risk actions (e.g., heating setpoint adjustments)
- keeps user informed in clear language through Slack/WhatsApp

## Goals

1. **Cost optimization**: reduce heating/electricity spend using price-aware scheduling.
2. **Comfort protection**: keep room temperatures inside user-defined bands.
3. **Operational awareness**: detect and notify abnormal trends (e.g., sustained high CPU, unusual fire-system values).
4. **HA-native integration**: use Home Assistant APIs/entities with minimal friction.
5. **Safe automation**: default to recommendation mode first, then controlled auto-actuation.

## Non-goals (MVP)

- Full autonomous control of all HA entities without guardrails.
- Training heavy ML models from scratch.
- Replacing existing HA automations immediately.
- Building a full dashboard frontend (initially logs + notifications).

---

## Functional Scope

- Read all available HA entities and state metadata.
- Prioritize entity domains:
  - `sensor` (temps, prices, power)
  - `climate` (setpoints, hvac modes)
  - `binary_sensor` / `alarm_control_panel` (safety)
  - host/system metrics (CPU, memory, disk where exposed)
- Fetch:
  - current electricity price
  - upcoming price forecast (hourly/day-ahead)
  - weather forecast
- Compute recommendations:
  - preheat when cheap if forecasted expensive period ahead
  - reduce setpoint during high-price windows while respecting comfort floor
- Alert on anomalies:
  - sustained high CPU
  - unusual sensor drift/spikes
  - suspicious safety-related values/events

---

## Architecture Options

| Option | Stack | Pros | Cons | Best for |
|---|---|---|---|---|
| A. Python service | FastAPI + APScheduler + pydantic + httpx | Strong data tooling, easy rules/forecast logic, clean typing/config | Slightly more backend plumbing | **Recommended** for MVP + growth |
| B. Node/TypeScript service | NestJS/Express + cron + zod | Unified JS ecosystem, strong async/event handling | Numeric/time-series ergonomics weaker than Python | Teams already all-in on TS |
| C. Automation hybrid | n8n/Node-RED + HA automations + small custom workers | Fast visual workflows, low-code onboarding | Complex logic/versioning can become messy; testing harder | Rapid prototyping, non-dev-heavy ops |

### Recommended Option: **A. Python Service**

Why:
- Best ergonomics for optimization logic and time-series analysis.
- Clear path from simple heuristics → advanced prediction.
- Strong ecosystem for robust config, retries, testing, observability.

---

## Security Model

### Auth
- Use Home Assistant **Long-Lived Access Token** (Bearer token).
- Keep token in environment variables / secret manager only.
- Never commit tokens to git.

### Storage & Handling
- `.env` for local dev only; production via secret store.
- Least privilege where possible (HA user with scoped permissions).
- Redact sensitive fields in logs.

### API Safety
- Read-only mode by default.
- Write actions behind explicit `AUTO_APPLY=false/true` feature flag.
- Action guardrails:
  - min/max allowed setpoint
  - max delta per adjustment
  - quiet hours / safety lockouts

---

## Data Model (Conceptual)

- **EntitySnapshot**
  - `entity_id`, `domain`, `state`, `attributes`, `ts`
- **PricePoint**
  - `ts`, `price`, `currency`, `source`
- **WeatherPoint**
  - `ts`, `outdoor_temp`, `condition`, `wind`, `source`
- **Recommendation**
  - `id`, `type`, `target_entity`, `proposed_value`, `reason`, `confidence`, `expires_at`
- **AlertEvent**
  - `id`, `severity`, `category`, `message`, `evidence`, `created_at`, `acked`

---

## Scheduling Strategy

- **Polling loops** (MVP):
  - entity snapshot: every 1–5 min
  - price forecast: every 15–60 min
  - weather forecast: every 30–60 min
- **Event-driven hook** (later): HA WebSocket stream for near-real-time triggers.
- **Decision cadence**:
  - optimization pass hourly + on major price/temperature change.

---

## Rules Engine vs ML

### MVP: Deterministic Rules (recommended)
- Transparent, debuggable, safe.
- Example rules:
  - if next 3h avg price > threshold and indoor temp > comfort_min + margin → decrease setpoint.
  - if cheap window starts within 1h and forecast cold + high future price → preheat modestly.

### Later: ML-assisted predictions
- Forecast demand/thermal response per room.
- Keep human-readable policy layer above ML outputs.

---

## Notifications

- **Slack DM**: recommendations + anomaly alerts + daily summary.
- **WhatsApp**: high-priority alerts and concise action suggestions.
- Message classes:
  - info, recommendation, warning, critical

---

## MVP Roadmap

### Phase 0 — Foundation
- Project scaffold, config loading, structured logging.
- HA connectivity test + entity inventory.

### Phase 1 — Observability
- Poll core entities + energy/weather feeds.
- Persist snapshots (SQLite/Postgres optional).

### Phase 2 — Optimization Recommendations
- Implement rule engine and comfort/cost constraints.
- Send recommendation messages (no auto-write).

### Phase 3 — Controlled Actuation
- Optional `AUTO_APPLY` with hard safety limits.
- Action audit log + rollback strategy.

### Phase 4 — Predictive Anomaly Detection
- Sustained-threshold + trend-based alerts (CPU, safety systems, sensor drift).

---

## Risks & Mitigations

1. **Bad data / missing entities**  
   Mitigation: schema validation, fallback defaults, health checks.

2. **Over-aggressive control harms comfort**  
   Mitigation: strict comfort bounds, max-change limits, recommendation-first rollout.

3. **Token exposure**  
   Mitigation: secrets in env/manager, redaction, repo scanning.

4. **False positives in alerts**  
   Mitigation: debounce windows, persistence thresholds, severity tuning.

5. **External price API outage**  
   Mitigation: cached last-known values + degraded-mode logic.

---

## Setup Prerequisites

- Python 3.11+
- Home Assistant URL + long-lived token
- Optional:
  - electricity price API source
  - weather API source
  - Slack/WhatsApp webhook or bot credentials

### Environment variables (see `.env.example`)
- `HA_BASE_URL`
- `HA_TOKEN`
- `PRICE_API_URL` / `PRICE_API_KEY`
- `WEATHER_API_URL` / `WEATHER_API_KEY`
- `SLACK_WEBHOOK_URL`
- `WHATSAPP_WEBHOOK_URL`
- `AUTO_APPLY`

### Home Assistant Bearer Token setup (recommended)

1. Open Home Assistant in browser.
2. Go to: **Profile** (click your user at bottom-left).
3. Scroll to **Long-Lived Access Tokens**.
4. Click **Create Token**.
5. Name it for this app, e.g. `auroran-ha-ai-manager`.
6. Copy token immediately (HA shows it only once).

Set in `.env`:

```bash
HA_BASE_URL=http://<your-ha-host>:8123
HA_TOKEN=<paste-long-lived-token-here>
```

Quick connectivity check (optional):

```bash
curl -s \
  -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_BASE_URL/api/"
```

Expected response includes `"message": "API running."`

#### Security notes
- Do **not** commit `.env`.
- Rotate token if exposed.
- Prefer dedicated HA user/token for this app.
- Start in recommendation mode (`AUTO_APPLY=false`).

---

## Current Status

Scaffold created with modular components:
- configuration
- HA client
- price provider interface
- optimizer
- alerts pipeline
- main orchestration entrypoint

Next step: implement concrete connectors (HA + price/weather source) and first rule set.

For ML-centric roadmap (location intelligence, InfluxDB + PostgreSQL hybrid), see:
- [`docs/ML_STRATEGY.md`](docs/ML_STRATEGY.md)

## License

MIT License. See [LICENSE](LICENSE).
