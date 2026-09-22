# Target evidence archive

These files are **chronological reverse-engineering evidence**, not the current semantic source of truth.

Current mappings live in [../TELEMETRY.md](../TELEMETRY.md). CANopen transport behavior lives in [../CANOPEN-LINK-TRANSPORT.md](../CANOPEN-LINK-TRANSPORT.md).

## 2026-09-17

| File | What it captured |
|---|---|
| [can-census-initial.md](2026-09-17/can-census-initial.md) | Initial target CAN census and first 5TAMX/5TWV0X correlations |
| [can-census-followup.md](2026-09-17/can-census-followup.md) | Follow-up census, additional IDs, airflow/min-speed/transport observations |
| [technician-correlation.md](2026-09-17/technician-correlation.md) | Correlation against Technician monitor values |
| [blower-electrical.md](2026-09-17/blower-electrical.md) | Blower electrical/airflow correlations and later superseded assumptions |
| [high-load-requalification.md](2026-09-17/high-load-requalification.md) | High-load capture that disproved several old outdoor labels |
| [cool-ambient-requalification.md](2026-09-17/cool-ambient-requalification.md) | Cooler-ambient cross-check and CANopen SDO identification |
| [satisfied-profile-sweep.md](2026-09-17/satisfied-profile-sweep.md) | Satisfied/idle baseline, profile sweep, freshness findings |
| [canopen-lss-fastscan.md](2026-09-17/canopen-lss-fastscan.md) | Initial LSS Fastscan decode and analyzer support |

## 2026-09-18

| File | What it captured |
|---|---|
| [active-cooling.md](2026-09-18/active-cooling.md) | Active cooling, modulation, shutdown, LSS identity, environmental source corrections, logs 9-14 |

## How to use these notes

A useful pattern is:

1. Read the current mapping in [../TELEMETRY.md](../TELEMETRY.md).
2. Follow the evidence links/dated notes when you need to understand *why* a field has its current confidence level.
3. When new captures disprove a mapping, update the maintained map and append a new evidence note rather than rewriting old observations.


## 2026-09-20

| File | What it captured |
|---|---|
| [active-cooling-ha-validation.md](2026-09-20/active-cooling-ha-validation.md) | Curated HA validation, 0x281 compressor-demand proof, compressor speed request/ceiling requalification, and 0x2D0/0x430 follow-up |

## 2026-09-22

| File | What it captured |
|---|---|
| [outdoor-sensor-chain-long-pass.md](2026-09-22/outdoor-sensor-chain-long-pass.md) | Logs 16-21 outdoor sensor-chain decode, suction-pressure scaling boundary, drive/fan thermal candidates, 0x450 stale-value fix, and 0x2D0 airflow-limit clue |
