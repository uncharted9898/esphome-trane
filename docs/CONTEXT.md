# Development context

This file is the current engineering handoff for `dev`.

For navigation and document authority, start at [README.md](README.md). For semantic mappings use [TELEMETRY.md](TELEMETRY.md); for CANopen transport use [CANOPEN-LINK-TRANSPORT.md](CANOPEN-LINK-TRANSPORT.md).

## Architecture

The project does **not** replace the UX360 or SC360.

Production intent:

- keep UX360 stock and usable;
- keep SC360 authoritative;
- attach the ESP bridge as a parallel CAN node;
- bridge removal/failure must not interrupt OEM HVAC operation;
- expose local monitoring to Home Assistant;
- add local control only after the stock write protocol is captured and qualified.

## Reference installation

- outdoor: `5TWV0X24A1000B`
- indoor: `5TAMXC03AV31DB`
- controls: UX360 + SC360
- refrigerant: R-454B / A2L
- bridge: Waveshare ESP32-S3-RS485-CAN
- CAN: 50 kbit/s classic CAN
- Waveshare TWAI pins: GPIO15 TX / GPIO16 RX
- bridge termination: open/no added 120-ohm resistor

## Firmware profiles

### `waveshare-trane-listenonly.yaml`

Safest first-connect image.

- TWAI listen-only;
- no CAN ACK participation;
- application TX disabled;
- bounded raw capture/census;
- discovery of unknown standard IDs.

### `waveshare-trane-commissioning.yaml`

Commissioning/correlation profile for census and known-state tests.

### `waveshare-trane-homeassistant.yaml`

Primary monitoring integration.

- normal CAN participation/ACK;
- application TX disabled;
- structured JSON receive;
- target telemetry packages;
- environmental signals sourced continuously from live binary frames;
- freshness diagnostics for retained structured profiles.

### `waveshare-trane-control.yaml`

Guarded control-development profile.

The typed control API remains present, but the application writer is fail-closed until a valid CANopen SDO client is implemented and stock command direction is captured.

### `waveshare-trane-full.yaml`

Full decoder/integration compile target.

### `esphome-trane.yaml`

Legacy decoder retained for compatibility and regression coverage. It is not the documentation source of truth.

## Transport state

Passive captures prove that Trane structured JSON is transported through standard CANopen SDO download transactions to manufacturer object **`0x300A:00`**.

Observed pairs:

- `0x601 / 0x581`
- `0x621 / 0x5A1`
- `0x641 / 0x5C1`
- `0x649 / 0x5C9`

Observed standard CANopen behavior also includes:

- NMT on `0x000`;
- heartbeat/error-control nodes `0x701..0x705`;
- LSS manager/server on `0x7E5/0x7E4`.

A complete Fastscan capture reconstructs identity:

- vendor ID `0x00000001`
- product code `0x00000004`
- revision `0x00000000`
- serial `0xC345985F`

and is followed by successful assignment/startup of CANopen node ID 3.

Do not map CANopen node IDs 1-5 to physical Trane products without a topology/disconnect capture.

## Control safety contract

Application TX is **fail-closed**.

Current rules:

- `tx_enabled: false` by default;
- raw JSON TX disabled by default;
- climate state is non-optimistic;
- typed actions remain validated;
- `send_json_internal_` refuses application writes because the historical guessed writer is not a valid qualified SDO transaction;
- passive receive/capture remains available.

Required before writes are re-enabled:

1. start capture before a physical UX360 setpoint or mode change;
2. recover the originating JSON write, not merely `SpOverride.Update`;
3. identify the exact request/response SDO channel and Ack behavior;
4. implement a nonblocking SDO client for `0x300A:00`;
5. handle aborts, timeout, segmented toggle, block sequence/ACK, and end response;
6. preserve SC360-presence, validation, serialization, and restore-OFF arming guards.

No captured log currently contains a literal stock JSON `"Put"` transaction.

## Current telemetry highlights

Maintained details live in [TELEMETRY.md](TELEMETRY.md). High-value qualified/candidate relationships include:

### Environment

- room temperature: `0x490.float[0]`;
- indoor humidity: `0x490.byte4`, user-facing values restricted to 0..100;
- outdoor ambient: `0x380.float[1]`;
- return/supply air: `0x308.float[0..1]`.

### Blower

- airflow request candidate: `0x200.u16@2`;
- airflow feedback candidate: `0x318.u16@4`;
- actual airflow: `0x281.u16@0`;
- compressor demand: `0x281.byte6` (binary mirror of structured `OdStatus.CompDemandPercent`);
- active flag candidate: `0x281.byte7`;
- speed candidate: `0x318.u16@6`;
- power: `0x320.float[0]`.

### Compressor/outdoor

- compressor speed request: `0x280.float[0]`;
- actual compressor speed: `0x384.float[0]`;
- speed ceiling candidate: `0x385.float[1]`;
- speed reference/limit candidate: `0x387.float[0]`;
- minimum speed family: `0x3D0/0x3E0`;
- line voltage: `0x38F.float[0]`;
- input power: `0x38C.float[1]`;
- suction line temperature: `0x382.float[0]`;
- liquid line temperature: `0x382.float[1]`;
- compressor discharge-temperature candidate: `0x381.float[1]`;
- suction-pressure absolute candidate: `0x383.float[0]`;
- liquid-pressure absolute candidate: `0x383.float[1]`;
- stator-heat active candidate: `0x282.byte1`;
- compressor phase-current candidates: `0x388.float[0..1]` + `0x389.float[0]`;
- drive IPM/PFC temperature candidates: `0x410.float[0..1]`;
- outdoor-fan IPM temperature candidate: `0x430.float[0]`;
- fan speed: `0x384.u16@6`;
- drive DC bus: `0x384.u16@4`.

## Structured-profile freshness

Structured profile values are cached by design and may be much older than the current binary telemetry.

The integration exposes:

- Last Structured JSON Age;
- SystemOpStatus Snapshot Age;
- IndoorStatus Snapshot Age;
- SpOverride Snapshot Age.

Do not interpret a retained structured string/value as a live event without checking its age.

## Documentation organization

Maintained docs stay at `docs/`.

Dated reverse-engineering notes live at:

```text
docs/evidence/YYYY-MM-DD/
```

The evidence archive preserves old hypotheses, including mappings later disproved. Current truth belongs in `TELEMETRY.md`, source, and tests.

## Immediate engineering work

Highest-value remaining work:

1. capture a physical UX360 setpoint/mode change from before the user action;
2. implement/qualify application SDO TX only after that capture;
3. confirm the `0x383.float[0..1]` absolute-pressure interpretation against synchronized Technician suction/liquid PSI and confirm `0x381.float[1]` against discharge temperature;
4. independently qualify `0x430.float[1]`, `0x450.float[0..1]`, and `0x460.float[0]`;
5. capture defrost/reversing-valve behavior;
6. identify A2L mitigation telemetry and node/device identity;
7. correlate electric heat stages;
8. qualify per-device model/serial/software objects.

## Source hygiene

Project rules:

- no build-time source-rewrite scripts;
- no patch-wrapper chains or generated-source monkey-patching;
- behavior belongs in maintained source;
- preserve useful upstream comments/evidence;
- use Candidate/Raw names until evidence justifies promotion;
- keep passive capture usable even while active-control work is incomplete.
