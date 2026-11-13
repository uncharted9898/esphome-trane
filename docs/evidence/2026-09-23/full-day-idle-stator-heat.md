# 2026-09-23 full-day idle / stator-heat archive

Source bundle: `trane-2026-09-23.tar.gz`

This archive contains hourly JSONL output from the long-term ESPHome native-API
collector. The useful continuous target capture spans approximately 21:00-23:59
UTC and contains 323,510 CAN frames, 36 already-decoded Trane JSON messages,
93 unique CAN IDs, and no malformed JSONL records.

## Mechanical state

The refrigeration system remained mechanically idle for the captured period:

- `0x280.f0` compressor speed request = 0
- `0x384.f0` actual compressor speed = 0
- `0x384.u16@6` outdoor fan speed = 0
- `0x385.f0` compressor power = 0
- `0x281.u16@0` actual airflow = 0
- `0x281.byte6` compressor demand mirror = 0
- `0x281.byte7` blower-active candidate = 0

This provides a long equalized baseline rather than an active cooling cycle.

## Refrigerant sensor-chain requalification

During the long idle baseline:

- `0x381.f1` cooled through roughly 81 -> 74 F
- `0x382.f0` remained roughly 64 -> 63 F
- `0x382.f1` remained roughly 67 -> 64 F
- `0x383.f0` stayed roughly 197 -> 192
- `0x383.f1` stayed roughly 196 -> 192

The two halves of `0x383` converge closely while the compressor and fan are
stopped. Combined with earlier active captures where `0x383.f0` falls while
`0x383.f1` rises, this strongly supports a low-side/high-side pressure pair
rather than the old `0x383.f0` discharge-temperature interpretation.

Maintained working map after this archive:

- `0x381.f1` -> compressor discharge-temperature candidate
- `0x383.f0` -> suction-pressure absolute candidate
- `0x383.f1` -> liquid/high-side pressure absolute candidate

The word **absolute** remains intentional. The archive supports pressure-pair
behavior but does not independently prove the Technician gauge-pressure
conversion.

## Stator-heating cycles

Two repeatable outdoor-drive heating cycles occurred while compressor speed
remained exactly 0 RPS:

1. `0x282.byte1 = 1` from about 21:56:13 to 22:03:37 UTC
2. `0x282.byte1 = 1` from about 23:18:53 to 23:26:34 UTC

In both cycles:

- `0x282.byte1` asserts first
- roughly 9-10 seconds later `0x389.f1` rises to about 0.7 A
- `0x38C.f1` rises from ~12-13 W standby to roughly 86-96 W
- `0x388.f0`, `0x388.f1`, and `0x389.f0` switch from zero into a
  three-current pattern
- compressor actual speed remains 0
- outdoor fan speed remains 0
- load returns to standby when `0x282.byte1` clears

This strongly supports:

- `0x282.byte1` -> stator-heat active candidate
- `0x388.f0` -> compressor motor phase-current candidate
- `0x388.f1` -> compressor motor phase-current candidate
- `0x389.f0` -> compressor motor phase-current candidate

Exact U/V/W ordering is not established.

## Other idle evidence

- `0x2D0.u16@2` remained about 759-764 while actual airflow was 0, further
  supporting an airflow ceiling/configuration interpretation rather than
  delivered airflow.
- `0x386.f0` remained exactly 2.0.
- `0x386.f1` remained exactly 50.0.
- `0x387.f0` remained exactly 55.0.
- `0x430.f1` and both `0x450` fields remained highly variable despite the
  mechanical system being idle, so they remain raw/unqualified.
- `0x4B1` continued to track epoch time correctly.

## Structured JSON observations

The archive includes:

- Technician/BLE access sequence around 21:17 UTC
- `SystemOpStatus.Update.E` updates from 60 -> 59 around 22:13 UTC
- later `SystemOpStatus.Update.E` updates to 61 and 62

No mechanical startup accompanied those `SystemOpStatus.E` changes, adding
support for a speed-ceiling/reference interpretation rather than live speed.

## Safety boundary

These observations are receive-side only. Application/control TX remains
fail-closed.
