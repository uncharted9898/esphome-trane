# 2026-10-06 Technician profile, fan-only control and long-JSON evidence

Source bundle: `trane-2026-10-06.tar.gz`

## Capture integrity

- 24 hourly JSONL chunks
- 2,599,468 total JSONL records
- 2,599,173 raw CAN records
- 292 collector `trane_json` records
- 3 collector lifecycle records
- 82 unique CAN IDs
- zero malformed JSONL rows
- UTC coverage approximately 00:00:00.021 through 23:59:59.972

Nine emitted `trane_json` records are malformed. Raw CAN analysis separates
them into two already-understood logging/receiver cases:

- one fifth exact-length/no-NUL `DebugUI.HiHeapRemaining` transfer captured by
  the pre-fix receiver;
- eight large, valid profile messages clipped by ESPHome's old 512-byte logger
  TX buffer.

The archive itself is not corrupt.

## Mechanical state

The compressor remains off for the full day:

- `0x280.f0` compressor request = 0
- `0x384.f0` actual compressor speed = 0
- `0x385.f0` compressor power = 0

There is one deliberate Technician fan-only interval around 13:53-13:56 UTC.
During that interval blower feedback reaches about 807 and blower power about
79 W while compressor request/actual/power remain zero.

No cooling-compressor, heating, defrost, reversing-valve, A2L/leak, or 185.x
pressure-protection event appears.

## Technician-qualified indoor fan control

The Technician session sends four application writes on the same qualified
`0x641/0x5C1`, `0x300A:00` block-SDO transport used by stock setpoints:

```json
{"IndoorSettings":{"Put":{"1":{"A":"1"}}}}
{"IndoorSettings":{"Put":{"1":{"C":"100"}}}}
{"IndoorSettings":{"Put":{"1":{"C":"50"}}}}
{"IndoorSettings":{"Put":{"1":{"A":"0"}}}}
```

Each transfer completes the CANopen response-driven handshake, produces a
matching `IndoorSettings.Update`, and receives application `{"Ack":"200"}`.

Observed control/feedback relationship:

- `A=1` enables the indoor fan path with compressor still off;
- `C=100` -> `IndoorStatus.E=100` -> `0x200.u16@2=800`;
- `C=50` -> `IndoorStatus.E=50` -> `0x200.u16@2=400`;
- `0x318.u16@4` is physical motor feedback and peaks around 807;
- `0x320.f0` blower power peaks around 79 W;
- `A=0` stops the fan path and feedback returns to zero.

This is direct qualification of the 8 request-units-per-percent scaling.

The component now has a separate default-false
`qualified_indoor_fan_tx_enabled` gate. The local fan-percent writer accepts
only the two captured values, 50 and 100. Global `tx_enabled` is still also
required. Mode, profile and arbitrary JSON writes remain fail-closed.

## 0x281.byte7 hypothesis disproved

The entire fan-only interval occurs while `0x281.byte7 = 0`, despite roughly
807 motor-feedback units and ~79 W blower power.

The earlier cooling-only **Blower Active Flag Candidate** interpretation is
therefore disproved. The maintained entity is now the neutral:

`0x281 Byte 7 State Candidate`

until its real operating-state semantic is independently identified.

## HcStatus=4

`ZoneStatus.HcStatus=4` persists during the deliberate fan-only interval.
Earlier captures also show code 4 during cooling shutdown while the blower is
coasting.

The best-supported meaning is therefore a **fan/blower-only or blower-coast
state**, rather than merely a generic shutdown transient.

## EquipSummary inventory

The raw CAN stream reconstructs a valid 1,377-byte `EquipSummary` JSON profile
that was clipped only at the logger layer.

Directly observed enrolled equipment:

| Role | Model | Software |
|---|---|---|
| System controller | `TSYS2C60A2VVUGA` | `09.04.00.260518` |
| Indoor unit | `5TAMXC03AV31DBA` | `09.04.00.260304` |
| Outdoor unit | `5TWV0X24A1000BA` | `09.04.00.260320` |
| Thermostat | `THUI2360A200UGA` | `09.04.00.260420` |
| Mitigation board | `CNT09525` | `09.04.00.260304` |

The air-handler record additionally reports:

```text
HeaterAccessory = Electric, 10KW, Single-Phase, 2-Stage
```

This identifies the installed heater accessory but does not yet identify the
live stage-state telemetry.

Per-device model/serial/software diagnostics and the heater-accessory diagnostic
are now hydrated from `EquipSummary`.

## Large JSON logger truncation

The CANopen receiver accepts JSON payloads up to 4,096 bytes and correctly
reassembles the Technician profile traffic.

Large target-observed bodies include:

- `ZoneStatus`: 596 JSON bytes / 597 indicated bytes including NUL
- `EquipSummary`: 1,377 JSON bytes / 1,378 indicated bytes including NUL
- `WifiList`: 1,680 JSON bytes / 1,681 indicated bytes including NUL

The old HA logger used ESPHome's 512-byte default TX buffer. All large emitted
`TRANE_JSON` messages clip at about 468 JSON characters after logger metadata,
even though the raw CAN body is complete.

The HA profile now uses:

```yaml
logger:
  tx_buffer_size: 4608
```

which covers the component's 4,096-byte RX JSON ceiling plus log metadata.

## Fifth exact-length/no-NUL JSON observation

At approximately 13:51:53 UTC, the raw bus carries:

```json
{"DebugUI":{"HiHeapRemaining":"30900224"}}
```

The initiate request again advertises exactly 42 bytes, with no trailing NUL
inside the indicated length.

This is the fifth independent observation of that wire form, after September 30
and October 1, 3 and 4. Regression coverage now includes all five captured heap
values.

## Stator heat

Fifteen stator-heat starts occur on October 6.

Fourteen cycles complete within the archive:

- duration: ~7.25-9.51 min
- median duration: ~8.95 min
- mean duration: ~8.71 min

The final event begins at ~23:53:39 UTC and is still asserted at the final
23:59:58 `0x282` frame, so it is intentionally treated as a carry-out rather
than a completed cycle.

Across all 15 starts, `0x390.byte0` becomes nonzero after:

- minimum: ~8.84 s
- median: ~9.49 s
- maximum: ~9.80 s
- mean: ~9.38 s

Cumulative evidence is now **123 fully observed stator-heat cycles plus one
carry-out cycle**.

## Idle pressure/ambient baseline

Outdoor ambient `0x380.f1` spans roughly 57.4-76.5 F.

With the compressor stopped all day:

- `0x383.f0`: ~176.5-224.5
- `0x383.f1`: ~175.7-224.2
- median absolute separation: ~1.55
- mean absolute separation: ~1.54
- maximum absolute separation: ~4.55

The pair continues to behave as an equalized suction/high-side pressure family
during mechanical idle.

## Safety boundary

Qualified setpoint and Technician indoor-fan writers are separate opt-in
families and both remain disabled by default. System mode, profile and arbitrary
JSON TX remain unqualified/fail-closed.
