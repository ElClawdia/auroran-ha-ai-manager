# Learnings & Memory Plan

## What we learned today
- HA integration is working (`/api/` healthcheck OK).
- Core entities are available for weather, location, climate, and energy.
- Miner economics can be computed from HA + PowerPool in near real-time.
- Rule execution from assistant to HA service calls works.

## Memory strategy (hybrid)

### Markdown memory (`*.md`)
Use for curated, human-readable long-term memory:
- decisions
- policy preferences
- architecture rationale
- lessons learned

### InfluxDB memory (`ha_ai_memory` bucket)
Use for high-frequency episodic memory:
- event observations (location, sensor transitions, alerts)
- recommendation outputs and confidence
- action outcomes + user feedback
- rolling feature windows for ML

## Initial Influx bucket
- Bucket: `ha_ai_memory`
- Org: `auroran`
- Retention: 365 days

## Suggested measurements
- `ha_event` (entity_id, state, source, zone)
- `assistant_recommendation` (type, confidence, reason, accepted)
- `assistant_action` (service, entity_id, result)
- `profitability_snapshot` (hashrate, revenue, cost, net)
- `location_pattern` (from_zone, to_activity, probability)

## Security
- Keep tokens only in `.env`/secret stores (never in repo).
- Rotate credentials if exposed.
