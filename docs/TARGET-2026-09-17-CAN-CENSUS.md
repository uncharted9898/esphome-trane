# 2026-09-17 target CAN census — 5TAMX + 5TWV0X + UX360/SC360

This note records observations from the first live captures on the target system:

- outdoor: `5TWV0X24A1000B`
- indoor: `5TAMXC03AV31DB`
- controller/thermostat: SC360 + UX360 (`TLINK360A2VVUG` kit)
- refrigerant generation: R-454B / A2L mitigation system
- UX360 firmware reported on the wire: `09.04.00.260420`

This is evidence, not a declaration that every candidate name below is correct. The promotion criteria in `TECHNICIAN-3.4.0-MONITOR-SCHEMA.md` still apply.

## Capture-wide result

A normal live capture contained about **99 distinct 11-bit CAN IDs**. The first Home Assistant profile promoted only a small subset of them, so the old `Last Unknown CAN Frame` surface discarded most of the useful history.

The target traffic has obvious periodic families, including:

- `0x200`–`0x210`
- `0x240`, `0x250`–`0x252`, `0x260`–`0x262`
- `0x280`–`0x285`
- `0x2D0`–`0x2D2`
- `0x300`, `0x308`, `0x310`, `0x318`, `0x320`, `0x328`, `0x330`
- `0x380`–`0x38F`
- `0x3D0`, `0x3E0`
- `0x410`, `0x420`, `0x430`, `0x450`, `0x460`
- `0x490`–`0x496`
- `0x4B0`–`0x4B4`
- `0x4C0`–`0x4C5`
- `0x53D`, `0x53E`
- `0x5C1`, `0x5C9`
- `0x641`, `0x649`
- `0x701`–`0x705`
- `0x7E4`, `0x7E5`

Many repeat on roughly 1 s, 2.1 s, 3 s, 5 s, or 15 s cadences. They are not random bus noise.

## Strong indoor correlations

### `0x308` — air-side temperature pair

During active cooling, representative values were approximately:

- float 0: 79.7–80.0 °F
- float 1: 54.8–56.3 °F

That follows return/supply air behavior closely and remains the strongest target evidence for the existing return/supply candidate labels.

### `0x283` — indoor refrigeration-side pair

During cooling, both values moved in the roughly mid-30s to low-40s °F region in later snapshots, clearly separated from the `0x308` air temperatures. This continues to support an ET/GT / coil/gas-temperature working hypothesis, but ordering still requires direct Technician correlation.

### `0x281` — airflow/motor status candidate

The frame is not sensibly represented as IEEE floats. Interpreting the 8 bytes as four little-endian uint16 values produced a particularly useful shutdown transition:

- running: `[535, 500, 0, 356]`
- running later: `[535, 500, 0, 256]`
- shutdown: `[200, 500, 0, 0]`
- later/off captures trend toward zero in the first/last fields while the second remains 500

Technician 3.4.0 explicitly expects `ActualAirflow`, `RequestedAirflow`/`TargetAirflow`, `ActualSpeed`, and `MotorPower` in the 5TAMX monitor schema. Therefore:

- uint16[0] = **ActualAirflow candidate**
- uint16[1] = **TargetAirflow candidate**
- uint16[2] = raw/unresolved
- uint16[3] = **ActualSpeed candidate**

These are correlations, not yet promoted semantics.

### `0x310`, `0x318`, `0x320` — static/motor group candidate

All three followed the indoor blower shutdown:

- `0x310` float 0: about 0.058 -> 0
- `0x318` float 0: about 0.483 -> 0
- `0x320` float 0: about 29.2 -> 24.4 -> 19.7 -> 0

Technician expects `RetStaticPressure`, `ExtStaticPressure`, and `MotorPower`. The first-pass candidate surfaces are therefore:

- `0x310` float 0: Return Static candidate
- `0x318` float 0: External Static candidate
- `0x320` float 0: Motor Power candidate

Units are intentionally not asserted yet.

### `0x300`

Two floats vary continuously during the cooling/shutdown sequence (roughly high-50s/low-60s and low/mid-50s). They are retained as candidate scalars pending correlation.

## Strong outdoor correlations

The target `0x380`–`0x38F` generation differs materially from the inherited labels. Every 8-byte frame must be considered as two potentially meaningful halves.

### Existing useful anchors

- `0x380` float 1 tracks outdoor ambient near 69 °F. Float 0 is commonly `-99`.
- `0x383` float 0 reaches roughly 150–170 °F during cooling and remains a plausible discharge-temperature candidate.
- `0x38F` float 0 is about 240–242 and remains a refrigerant-pressure candidate.

### Previously discarded second halves

Examples from active cooling:

- `0x381`: approximately 76 / 98
- `0x382`: approximately 64 / 74
- `0x383`: approximately 157–170 / 225–238
- `0x387`: 55 / 0.0–0.3
- `0x38F`: 240–242 / 0.0–1.9
- `0x410`: approximately 102 / 103
- `0x430`: approximately 101 / 298–322
- `0x450`: approximately 278–342 / 301–304

The prior HA profile exposed only one half of many of these frames. The target discovery package now exposes both where useful.

### `0x385` — strong EEV-family candidate

During compressor shutdown:

- float 0 fell from roughly 403 through 376, 367, 357, 347, 325, 314, ... to 0
- float 1 moved from roughly 50 to the 40s/30s/20s and down toward small values

Technician expects both EEV steps/position-like data. Candidate surfaces are therefore `EEV Steps` and `EEV Position`, but they remain explicitly marked Candidate.

### `0x388` / `0x389` — current-family candidates

Values near 2.4 fell toward zero as the outdoor unit shut down. Technician expects multiple current channels (`MocAcCurrent`, `MocFanPhaseCurrent`), so these are exposed as current candidates without assigning the final channel names.

### `0x38C` — power/RPM-like candidate

Float 0 is zero while float 1 varied roughly 500+ during high cooling and fell rapidly through the hundreds/tens during shutdown. Technician expects `MocInputPower` as well as speed-related quantities. The first discovery label is `Candidate Input Power`; direct monitor correlation is still required.

### Labels disproven or weakened by the target

- `0x381` should not be treated as proven `Suction Temperature`; its target behavior does not support retaining that semantic without qualification.
- `0x386` float 0 is consistently about `2.0` on the target, so a temperature unit is not justified.
- `0x450` float 0 is commonly around 300; treating it as a temperature merely because it fits an old range check is unsafe.
- inherited OdStatus enum meanings do not carry cleanly to this 5TWV0X firmware; raw A/C values should remain visible while state transitions are qualified.

## UX360 / zone sensor family

### `0x490`–`0x495`

These six adjacent 5-byte frames look strongly like six zone sensor records.

`0x490`:

- first four bytes are a little-endian float
- while zone 1 `ZoneStatus.H` reported 82.00 °F, the `0x490` float was exactly 82.0
- byte 4 moved through values including the 70s toward approximately 58 while the temperature remained 82 °F

Working hypothesis:

- `0x490` float = Zone 1 temperature
- `0x490` byte 4 = RH/status/quality field; **RH is the leading hypothesis, not yet proof**

`0x491`–`0x495` repeatedly held float 70 and byte 50 on this single-zone install, consistent with unused-zone placeholders or defaults. They are exposed disabled-by-default as Zone 2–6 candidates.

### `0x4B1` — epoch time

This mapping is unusually strong:

- bytes `9C 5C AB 6A` interpreted as little-endian uint32 = `1789615260` = 2026-09-17 03:21:00 UTC
- the next minute changed to `D8 5C AB 6A` = `1789615320` = 2026-09-17 03:22:00 UTC

That exactly matches the capture clock. `0x4B1` is therefore exposed as raw Unix epoch seconds.

`0x4B2` carries two stable floats (70/70 in this capture) and remains raw pending correlation.

## Structured profile data currently under-exposed

The corrected `0x641/0x649` decoder recovered more structured data than the first HA surface publishes.

Observed target-only or underused profile content includes:

### `IndoorSettings`

Unit 1 full profile observed:

```text
A=0 B=30 C=50 D=5 E=35 F=B G=50 H=45 I=10 J=65
K=35 L=5 M=5 N=0 O=1 P=0 Q=0 R=A S=A T=0 U=B
```

Units 2–8 also carried `Q=0` entries.

Do not assign meanings to compact keys merely from their letters. This object must be mapped independently from the Technician monitor schema.

### `ZoneSettings`

Zone 1 reported `ZoneMode=3`; zones 2–6 reported `ZoneMode=0`. The older upstream enum interpretation is not assumed valid for this target.

### `SystemSettings`

Observed:

```text
B=A C=A D=B E=C F=3 G=Upstairs H=B I=A J=-0400 K=-0500 L=A M=B N=A
```

Only the already-qualified display name/timezone fields are promoted today.

### `VersionDetails`

In addition to the known versions:

```text
ConfigPropertiesVersion=80
AlarmDetailsVersion=75
A=""
B=64
D=19
```

### OEM profile discovery

The target UX360 emitted a passive request:

```json
{"GetProfile":"THERMOSETTINGS"}
```

`THERMOSETTINGS` was not in the original request allowlist. It is now retained as an observed profile name. Application TX remains disabled in the HA profile; adding the name to the allowlist does not send anything by itself.

## `0x5C1` / `0x5C9` clarification

The target capture shows that these IDs behave as sideband/control framing synchronized with the actual `0x641`/`0x649` segmented payload stream rather than carrying a hidden second copy of JSON bytes.

For example, a large `0x649` certificate transfer is bracketed by `0x5C9` `A0`/`A2`/`A1` records whose lengths/sequences align with the `0x649` transfer boundaries. `0x5C1` similarly tracks `0x641` traffic and flow-control records (`60`, `20`, `30`).

They remain valuable for transport/session analysis, but the missing telemetry is primarily in raw CAN families and under-exposed structured profile fields.

## `0x7E4` / `0x7E5` — unresolved high-priority subsystem

This pair is unusually chatty during startup:

- `0x7E4` repeatedly sends `4F 00 00 00 00 00 00 00`
- `0x7E5` responds with structured `51 ...` records containing descending counters and changing state bytes
- a startup `0x11` exchange is also observed

Because this is the first capture from an A2L-generation 5TAMX, the pair is a high-priority candidate for mitigation/sensor-controller/service traffic, but there is **not enough evidence to label it A2L**. Keep it raw until a natural A2L event, board disconnect/reconnect qualification, or Technician monitor correlation identifies it.

## Instrumentation added after this capture

The `trane_bus` component now keeps a bounded fixed-size census for all 2048 possible standard 11-bit IDs:

- frame count per ID
- last DLC
- last 8-byte payload
- unique-ID count
- safe typed readers for LE float, uint16, byte, and uint32
- compact `TRANE_ID,...` census dump

This does not expand the capture ring and cannot grow without bound. It is observation-only.

The Home Assistant discovery package additionally exposes the strongest candidate channels above and adds diagnostic buttons to dump/clear the ID census or dump the current capture-ring snapshot.

## Next qualification targets

1. Capture one full cooling start -> steady state -> shutdown with the new candidate entities visible.
2. Capture blower-only operation if the UX360 permits it; this separates indoor motor/static data from outdoor-unit data.
3. Compare `0x281`, `0x310`, `0x318`, and `0x320` directly with Technician `ActualAirflow`, `ActualSpeed`, `MotorPower`, `RetStaticPressure`, and `ExtStaticPressure`.
4. Compare `0x385`, `0x388`, `0x389`, and `0x38C` directly with Technician EEV/current/input-power fields.
5. Record `0x490` float/byte4 while room temperature and indoor RH change independently.
6. Observe `0x7E4/0x7E5` during a safe, natural mitigation-board state change or controlled board communication qualification; do not create a refrigerant leak for testing.
7. Obtain and decode `THERMOSETTINGS` on a natural OEM request/response sequence.
