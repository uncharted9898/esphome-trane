# 2026-10-04 full-day idle stator cadence and fourth exact-length JSON evidence

Source bundle: `trane-2026-10-04.tar.gz`

## Capture integrity

- 24 hourly JSONL chunks
- 2,585,185 total records
- 2,585,170 raw CAN records
- 15 collector `trane_json` records
- 82 unique CAN IDs
- zero malformed JSONL rows
- one malformed decoded `TRANE_JSON` payload from the known pre-fix
  optional-NUL receiver behavior; raw CAN reassembles cleanly

## Mechanical state

The system remains mechanically idle for the entire 24-hour capture:

- `0x280.f0` compressor speed request = 0
- `0x384.f0` actual compressor speed = 0
- `0x385.f0` compressor power = 0
- blower current/speed/power remain zero

No structured cooling, heating, defrost, reversing-valve, A2L/leak, or 185.x
pressure-protection event appears.

## Stator heat: 18 isolated cycles

`0x282.byte1` asserts 18 times.

Cycle duration:

- minimum: ~7.54 min
- median: ~7.96 min
- maximum: ~8.32 min
- mean: ~7.95 min

Start-to-start spacing:

- minimum: ~65.4 min
- median: ~76.0 min
- maximum: ~116.2 min
- mean: ~80.0 min

`0x390.byte0` becomes nonzero:

- minimum lag: ~8.84 s
- median lag: ~9.48 s
- maximum lag: ~9.76 s
- mean lag: ~9.41 s

Nonzero `0x390.byte0` values remain limited to 44-46.

The cumulative project total is now **94 isolated stator-heat cycles**.

## Outdoor ambient and pressure equalization

Outdoor ambient `0x380.f1` spans roughly:

- minimum: ~60.31 F
- maximum: ~67.97 F

With no compressor operation, the pressure pair remains tightly equalized:

- `0x383.f0`: ~182.42-200.90
- `0x383.f1`: ~182.48-201.17
- median absolute separation: ~0.74
- mean absolute separation: ~0.64
- maximum absolute separation: ~2.85

This is the cleanest full-day pressure-equalization baseline in the capture set.

## Structured mirror confirmation

Sparse structured updates independently match the binary sources:

### SystemOpStatus.E

Observed structured values:

- 59
- 58
- 59
- 61
- 62

Every value matches the nearest `0x490.byte4` humidity sample exactly.

### ZoneStatus.Update.1.H

Observed room-temperature updates:

- 77 F
- 76 F

Both match nearest `0x490.f0` room-temperature samples exactly.

## Fourth exact-length/no-NUL 0x300A JSON transfer

At approximately 11:18:54 UTC the raw CAN stream carries:

```json
{"DebugUI":{"HiHeapRemaining":"31506432"}}
```

The initiate request declares 42 bytes, exactly the UTF-8 JSON length. No
trailing NUL is present inside the indicated length.

The archived bridge still uses the pre-fix receiver and emits the payload one
byte early as malformed `TRANE_JSON`. The underlying CAN transaction is valid
and reassembles correctly with the maintained optional-NUL rule.

This is the fourth independent exact-length/no-NUL observation:

- 2026-09-30: 33054720
- 2026-10-01: 32538624
- 2026-10-03: 32022528
- 2026-10-04: 31506432

Regression coverage now includes all four observed payload values.

## Safety boundary

All observations are receive-side. Setpoint TX remains explicit opt-in on the
qualified stock `SpOverride.Put` path only; mode and arbitrary JSON TX remain
unqualified/fail-closed.
