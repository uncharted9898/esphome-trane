# 2026-09-24 24-hour idle / stator-heat cadence archive

Source bundle: `trane-2026-09-24.tar.gz`

This archive contains all 24 hourly JSONL chunks from the long-term ESPHome
native-API collector.

## Capture integrity

- 24 hourly JSONL members
- 2,590,986 CAN records
- 24 decoded Trane JSON records
- 82 unique CAN IDs
- zero malformed JSONL records
- first record: 2026-09-24 00:00:00 UTC
- last record: 2026-09-24 23:59:59 UTC

## Mechanical state

The HVAC system remained mechanically idle for the full day:

- compressor speed request = 0
- actual compressor speed = 0
- compressor demand mirror = 0
- outdoor fan speed = 0
- actual airflow = 0
- blower-active flag = 0
- compressor power = 0

This makes the archive unusually clean for isolating outdoor standby/stator
heating behavior.

## Stator heat cadence

`0x282.byte1` asserted 19 times during the day.

Observed cycle duration:

- minimum: ~461.5 s
- median: ~470.4 s
- maximum: ~494.5 s
- mean: ~474.1 s (~7.9 min)

Observed start-to-start cadence:

- minimum: ~64.4 min
- median: ~76.4 min
- maximum: ~91.7 min
- mean: ~75.9 min

Each cycle shows the same sequence:

1. `0x282.byte1` asserts
2. about 9.0-9.8 s later:
   - input power rises from ~12-13 W standby to ~85-95 W
   - input current rises to ~0.7 A
   - `0x388.f0`, `0x388.f1`, and `0x389.f0` enter a three-current pattern
   - `0x390.byte0` becomes nonzero
3. compressor actual speed remains 0 RPS
4. outdoor fan remains 0 RPM
5. the electrical load returns to standby as the cycle ends

Together with the two cycles captured on 2026-09-23, this gives 21 repeatable
stator-heat observations.

## 0x390 requalification

`0x390` is nearly stator-heat-exclusive in this archive.

Observed frames:

- 219 total `0x390` frames
- 200 nonzero observations during stator heat
- nonzero byte0 values: 44-46
- one zero frame appears at the end of each cycle

The first nonzero `0x390` sample appears at the same 9.0-9.8 s delay after
`0x282.byte1` assertion as the outdoor input-power rise.

The Technician application exposes a monitor named `MocStatorHeatPower`.
That makes `0x390.byte0` a strong stator-heat power/level candidate, but the
wire value must remain unitless for now because the archive does not prove that
44-46 is literal watts.

## Compressor phase-current family

The full-day archive strongly reinforces:

- `0x388.f0` -> compressor phase-current candidate
- `0x388.f1` -> compressor phase-current candidate
- `0x389.f0` -> compressor phase-current candidate

All three are effectively zero during ordinary standby and become active
together during all 19 stator-heat cycles while compressor speed remains 0 RPS.
Exact U/V/W ordering remains unresolved.

## Pressure/equalization baseline

The long idle baseline continues to support the pressure-pair interpretation:

- `0x383.f0`: roughly 184-198
- `0x383.f1`: roughly 182-199

The pair remains close during full-day idle while the compressor/fan are stopped,
which is consistent with equalized low/high-side pressure behavior.

## Other useful observations

- `0x387.f0` stayed exactly 55.0 for the entire day.
- `0x386.f0` and `0x386.f1` remained fixed at their known idle values.
- `0x430.f1` and both `0x450` channels remained highly variable despite no
  mechanical operation, so they remain raw/unqualified.
- `0x460.f0` remained in a narrow ~82-84 F range but still lacks an OEM label.
- `SystemOpStatus.E` moved through 61-64 without any mechanical startup,
  reinforcing a ceiling/reference/configuration interpretation rather than
  actual speed.

## Safety boundary

This archive and all resulting mappings are receive-side only.
Application/control TX remains fail-closed.
