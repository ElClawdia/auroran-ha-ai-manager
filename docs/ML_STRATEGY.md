# ML Strategy: Holistic Context + Location Intelligence

## Goal
Turn HA + activity + location signals into actionable coaching context:
- where the user is (home office, outside, pool, gym, ski tracks)
- what usually follows each location pattern
- what action is optimal now (comfort, energy, training readiness)

## Recommended Stack
- **Core service:** Python
- **Time-series:** InfluxDB (fast feature retrieval over time windows)
- **Relational/metadata:** PostgreSQL (HA historical snapshots, labels, model registry)
- **Inference cadence:** near-real-time rules + periodic ML scoring

## Why Python over Node.js for ML-heavy scope
- Better ML ecosystem (scikit-learn, lightgbm/xgboost, pytorch if needed)
- Strong feature engineering stack (pandas, numpy)
- Easier hybrid of deterministic safety rules + ML predictions

## Data Sources
1. Home Assistant entities
   - device trackers / person entities (location)
   - climate, room temps, occupancy, power, alarms
2. Electricity prices
3. Weather forecast + observed weather
4. Training events (e.g. Strava workouts)
5. Optional calendar context

## Feature Store Pattern
### InfluxDB
Use for rolling windows and aggregates:
- room temp mean/min/max over 15m, 1h, 24h
- electricity price current + next-hour deltas
- occupancy transitions and durations
- host CPU sustained usage windows

### PostgreSQL
Use for structured dimensions and labels:
- known places dictionary (home, office, pool, track, etc.)
- derived labels ("location X followed by swim within 2h")
- model versions, metrics, retraining metadata

## Location Intelligence Design
1. Resolve raw location to semantic place label
   - HA zones first
   - fallback geofencing/radius matching
2. Build transition graph
   - P(next_activity | location, weekday, hour)
3. Learn repeated sequences
   - e.g. `Location X -> swim workout` probability
4. Generate context memory facts
   - confidence-scored, expiring if pattern decays

## ML Tasks (phased)

### Phase A — No-regret baselines
- Rule-based detection + simple frequency stats
- Markov transition probabilities for location->activity

### Phase B — Lightweight supervised models
- Predict likely next activity in next 1–3 hours
- Predict heating demand and comfort drift
- Predict risk events (sustained high CPU, unusual safety sensor behavior)

### Phase C — Personalization layer
- Reinforcement by user feedback (accepted/rejected recommendations)
- Confidence calibration per domain (energy, training, alerts)

## Safety & Human Control
- ML never bypasses safety constraints
- Hard limits always deterministic:
  - min/max room setpoint
  - no unsafe actuator changes
- Explainable output required: top factors for each recommendation

## Privacy & Security
- Keep precise location retention short unless needed
- Redact tokens/secrets from logs
- Use dedicated HA token and least-privilege roles

## MVP Integration Plan
1. Add location + activity feature extraction pipeline
2. Add InfluxDB and PostgreSQL connectors
3. Store labeled transitions
4. Add first model: location -> likely next activity
5. Use predictions in recommendation messages (advice mode only)
