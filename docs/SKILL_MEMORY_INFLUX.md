# Skill: Influx Memory Usage for Auroran HA AI Manager

## Purpose
Create high-volume, fast-access episodic memory in InfluxDB while keeping curated strategic memory in Markdown files.

## Buckets
- Main health bucket: `health`
- Assistant memory bucket: `ha_ai_memory`

## Env configuration
Required in `.env` (gitignored):
- `INFLUXDB_URL`
- `INFLUXDB_TOKEN`
- `INFLUXDB_ORG`
- `INFLUXDB_AI_MEMORY_BUCKET`

## What is written each cycle
Measurement | Description
---|---
`ha_event` | Snapshot of HA entity states (`entity_id`, `domain`, numeric/text state)
`assistant_recommendation` | Recommendation type/target/confidence/reason
`assistant_action` | Executed policy/service actions + reason/result
`profitability_snapshot` | Miner hashrate + cost/revenue/net when available

## Query examples (Flux)
```flux
from(bucket: "ha_ai_memory")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "assistant_recommendation")
```

```flux
from(bucket: "ha_ai_memory")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "ha_event" and r.entity_id == "sensor.temperature_tapio_s_office")
```

## Design notes
- Keep source-of-truth control in HA; this app adds intelligence and memory.
- Store high-frequency data in Influx; summarize important conclusions into `*.md` files.
- Use policy constraints before optimization (safety and user-defined hard rules first).

## Hard rules currently implemented
- Bedroom heat pump entity (`climate.ac_12488762` by default) must be OFF between 19:00 and 09:00 Helsinki time.
- Hallway heat pump is monitored and managed (`climate.ac_12494102` by default).
- If indoor temperatures are above 21°C, heat pumps are forced OFF.
- If electricity is expensive, target floor is 20°C and bedroom heat pump is avoided.

## Next evolution
- Add price/weather forecast feature vectors into `ha_ai_memory`.
- Add reward signals from user feedback (accepted/rejected recommendations).
- Train lightweight models from Postgres history + Influx feature windows.
