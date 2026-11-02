# 2026-10-05 full-day idle, setpoint-write and stator-cadence evidence

Source bundle: `trane-2026-10-05.tar.gz`

## Capture integrity

- 24 hourly JSONL chunks
- 2,583,067 total records
- 2,583,017 raw CAN records
- 49 collector `trane_json` records
- 82 unique CAN IDs
- zero malformed JSONL rows
- zero malformed structured JSON payloads
- UTC coverage approximately 00:00:00.015 through 23:59:59.983

## Mechanical state

The HVAC system remains mechanically idle for the complete 24-hour capture:

- `0x280.f0` compressor speed request = 0
- `0x384.f0` actual compressor speed = 0
- `0x384.u16@6` outdoor fan speed = 0
- `0x385.f0` compressor power = 0
- `0x281.u16@0` airflow target = 0
- `0x281.byte6` compressor demand mirror = 0
- `0x281.byte7` blower-active field = 0
- blower current/speed/power remain 0

No structured cooling, heating, defrost, reversing-valve, A2L/leak, or 185.x
pressure-protection event appears.

## Three additional stock SpOverride.Put writes

Three complete stock UX360 setpoint writes were captured:

1. 03:08:20 UTC -> Csp 77 F
2. 10:52:52 UTC -> Csp 79 F
3. 13:11:34 UTC -> Csp 78 F

The three request payloads are:

```json
{"SpOverride":{"Put":{"1":{"Csp":"77","Hsp":"62","HoldType":"1","Source":"1"}}}}
{"SpOverride":{"Put":{"1":{"Csp":"79","Hsp":"62","HoldType":"1","Source":"1"}}}}
{"SpOverride":{"Put":{"1":{"Csp":"78","Hsp":"62","HoldType":"1","Source":"1"}}}}
```

All three preserve:

- zone 1
- `Hsp:"62"`
- `HoldType:"1"`
- `Source:"1"`
- identical JSON field order

Each JSON body is 80 bytes and is sent with a trailing NUL, so the CANopen
block-download initiate request advertises 81 bytes.

Each request is followed by:

1. matching `SpOverride.Update`;
2. accepted zone-state update;
3. application `{"Ack":"200"}`.

Combined with the two stock writes captured on October 3, the project now has
**five independent stock setpoint-write observations**. The observed cooling
setpoints are 77, 78 and 79 F.

This strengthens the qualified setpoint writer but does not broaden its
semantics. Zone 1 / hold type 1 / source 1 remain the only qualified local
write policy, and mode/arbitrary JSON TX remain unqualified and fail-closed.

## Stator heat: 15 additional cycles

`0x282.byte1` asserts 15 times.

Cycle duration:

- minimum: ~7.29 min
- median: ~8.92 min
- maximum: ~9.37 min
- mean: ~8.69 min

Start-to-start spacing:

- minimum: ~69.82 min
- median: ~91.15 min
- maximum: ~134.72 min
- mean: ~90.29 min

`0x390.byte0` becomes nonzero after:

- minimum lag: ~8.73 s
- median lag: ~9.35 s
- maximum lag: ~9.78 s
- mean lag: ~9.29 s

Nonzero `0x390.byte0` values remain limited to 44, 45 and 46.

The cumulative project total is now **109 isolated stator-heat cycles**.

## Outdoor ambient and pressure equalization

Outdoor ambient `0x380.f1` spans roughly:

- minimum: ~64.72 F
- maximum: ~75.85 F
- median: ~66.16 F

With no refrigeration operation, the pressure pair remains tightly equalized:

- `0x383.f0`: ~195.77-222.36
- `0x383.f1`: ~193.96-222.99
- median absolute separation: ~0.74
- mean absolute separation: ~0.95
- maximum absolute separation: ~2.83

This independently reinforces the suction/high-side paired-pressure mapping.

## Structured environmental mirrors

### SystemOpStatus.E / humidity

Observed structured values:

- 63
- 62
- 61
- 62
- 61
- 59
- 61

Six of seven exactly match the nearest `0x490.byte4` sample.

At 20:29:43 UTC, structured E reports 61 while the immediately preceding binary
sample is still 62; `0x490.byte4` changes to 61 about 0.83 seconds later.
That timing remains consistent with E being a sparse structured humidity mirror,
not a different physical signal.

### ZoneStatus.Update.1.H / room temperature

Observed structured room-temperature values:

- 77 F
- 76 F
- 75 F
- 76 F
- 77 F

All five exactly match the nearest `0x490.f0` sample.

## JSON transport

Twenty-nine valid block-SDO JSON transfers were reconstructed from the raw CAN.

All block transfers observed on this day are normal NUL-sized forms. In
particular, the three stock setpoint request bodies are 80 JSON bytes plus one
trailing NUL and advertise 81 bytes.

No fifth exact-length/no-NUL `DebugUI.HiHeapRemaining` transfer appears on
October 5. The independently observed exact-length cases remain those from
September 30, October 1, October 3 and October 4.

## Safety boundary

All analysis is receive-side. Local setpoint TX remains explicit opt-in on the
qualified stock `SpOverride.Put` path only. Mode and arbitrary JSON TX remain
unqualified/fail-closed.
