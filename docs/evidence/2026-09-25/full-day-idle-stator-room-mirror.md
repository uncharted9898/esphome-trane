# 2026-09-25 24-hour idle / stator-heat and room-mirror archive

Source bundle: `trane-2026-09-25.tar.gz`

## Capture integrity

- 24 hourly JSONL members
- 2,595,611 CAN records
- 28 decoded Trane JSON records
- 82 unique CAN IDs
- zero malformed JSONL records
- first record: 2026-09-25 00:00:00 UTC
- last record: 2026-09-25 23:59:59 UTC

## Mechanical state

The HVAC equipment remained mechanically idle for the complete day:

- `0x280.f0` compressor speed request = 0
- `0x384.f0` actual compressor speed = 0
- `0x384.u16@6` outdoor fan speed = 0
- `0x385.f0` compressor power = 0
- `0x281.u16@0` actual airflow = 0
- `0x281.byte6` compressor demand mirror = 0
- `0x281.byte7` blower-active candidate = 0
- `0x318.f0` blower current = 0
- `0x320.f0` blower power = 0

This provides another full-day isolated outdoor standby/stator-heat baseline.

## Stator heat: 16 additional cycles

`0x282.byte1` asserted 16 times.

Observed heat-enable interval duration:

- minimum: ~7.21 min
- median: ~8.01 min
- maximum: ~9.13 min
- mean: ~8.13 min

Observed start-to-start spacing:

- minimum: ~38.25 min
- median: ~77.15 min
- maximum: ~247.51 min
- mean: ~83.04 min

The unusually long afternoon gap coincides with the warmest ambient block. The
capture supports ambient-dependent stator-heat scheduling/inhibition, but does
not establish a single temperature threshold.

Across every cycle the same sequence occurs:

1. `0x282.byte1` asserts.
2. About 8.86-9.68 s later (median ~9.23 s):
   - `0x390.byte0` becomes nonzero,
   - `0x38C.f1` input power rises into roughly the 82-97 W range,
   - `0x389.f1` input current rises to about 0.7 A,
   - `0x388.f0`, `0x388.f1`, and `0x389.f0` enter their three-current
     stator-heat pattern.
3. Compressor speed remains 0 RPS.
4. Outdoor fan remains 0 RPM.
5. The electrical load returns to standby as the enable clears.

Combined with 2026-09-23/24, there are now 37 isolated stator-heating cycles.

Because the bit consistently leads actual electrical load by about 9.25 s,
`0x282.byte1` is better described as **Stator Heat Enable** than simply
"active."

## 0x390 power-level evidence

This archive contains 176 `0x390` frames:

- 160 nonzero observations
- nonzero byte0 values are only 44, 45, or 46
- almost all nonzero observations occur while the stator-heat enable is set
- the first nonzero sample follows the enable by a median ~9.23 s
- that timing is effectively coincident with the outdoor input-power/current rise

Across the 2026-09-24 and 2026-09-25 full-day captures, `0x390` is therefore
a strong stator-heat power/level channel. Technician exposes
`MocStatorHeatPower`, but no synchronized Technician display has yet proven
that 44-46 is literal watts, so the maintained entity remains unitless.

## Direct room-temperature mirror

Sparse structured ZoneStatus room-temperature updates match the binary source
directly:

| UTC | ZoneStatus.Update.1.H | nearest 0x490.f0 |
|---|---:|---:|
| 08:02:57 | 73 F | 73 F |
| 12:02:35 | 72 F | 72 F |
| 12:55:13 | 73 F | 73 F |
| 16:07:52 | 74 F | 74 F |
| 18:00:44 | 75 F | 75 F |
| 19:39:07 | 76 F | 76 F |

Each binary sample occurred within about one second of the structured update.
This independently confirms `0x490.f0` as the live Zone 1 / room temperature
source.

## Pressure equalization evidence

With no compressor operation for the entire day:

- `0x383.f0`: ~168.70 to 223.80
- `0x383.f1`: ~166.13 to 222.42
- absolute separation between the two fields:
  - minimum: 0
  - median: ~1.33
  - mean: ~1.42
  - maximum: ~2.72

The two channels therefore move together extremely closely through a large
ambient-driven pressure range while the refrigeration circuit is idle. This
strongly reinforces the low/high absolute-pressure pair interpretation.

## Other observations

- Outdoor ambient ranged from roughly 54 to 76 F.
- `SystemOpStatus.E` updated through 60-64 while compressor request/actual
  remained zero, reinforcing a ceiling/reference/configuration role rather than
  live speed.
- `0x460.f0` did not respond materially to stator-heat electrical loading.
  It remained strongly correlated with the outdoor power-electronics thermal
  family but still lacks an independently proven OEM label.
- `0x430.f1` and both `0x450` fields remained highly variable during
  mechanical idle and remain raw/unqualified.

## Safety boundary

All evidence is receive-side only. Application/control TX remains fail-closed.
