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

The maintained nonblocking CANopen SDO client now supports two captured write families only:

- stock UX360 zone-1 `SpOverride.Put` setpoints;
- Technician `IndoorSettings.Put` fan enable/disable and captured 50/100% requests.

Global TX plus the matching per-family qualification gate must both be explicitly armed. Mode, profile and arbitrary JSON writes remain fail-closed.

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
- one response-driven SDO client targets `0x300A:00` over `0x641/0x5C1`;
- stock-qualified zone-1 setpoints additionally require `qualified_setpoint_tx_enabled: true`;
- Technician-qualified indoor-fan writes independently require `qualified_indoor_fan_tx_enabled: true`;
- fan percentage is intentionally limited to the captured 50% and 100% values;
- mode, profile and arbitrary JSON writers remain blocked;
- passive receive/capture remains available regardless of write arming.

Qualified evidence now includes five independent stock UX360 `SpOverride.Put` writes across October 3 and 5, plus the October 6 Technician `IndoorSettings.Put` fan sequence. Both families use the captured block-SDO request/response path and require application `{"Ack":"200"}` after transport completion.

Still required before widening writes:

1. capture the originating stock request transaction for each new command family;
2. preserve exact payload shape/policy rather than extrapolating uncaptured values;
3. require the same response-driven SDO handshake, abort/timeout handling, SC360-presence guard, serialization and quiet-bus guard;
4. add an independent default-off qualification gate for any newly admitted family;
5. validate on-device coexistence with the stock UX360 before considering a path production-ready.


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
- airflow target/command candidate: `0x281.u16@0`;
- compressor demand: `0x281.byte6` (binary mirror of structured `OdStatus.CompDemandPercent`);
- unresolved operating-state candidate: `0x281.byte7`;
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
- suction-pressure raw/confirmed semantic: `0x383.float[0]`;
- liquid/high-side pressure raw candidate: `0x383.float[1]`;
- stator-heat enable: `0x282.byte1`;
- stator-heat power/level candidate: `0x390.byte0`;
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

## Latest capture checkpoint

The 2026-10-07 archive is mechanically idle and closes the 10/06 stator carry-out. The 2026-10-08 archive adds eight real cooling runs and 13 stator cycles, taking the corpus to **152 completed isolated stator-heat cycles**. Its sixth exact-length/no-NUL JSON example is received correctly by the installed bridge. It also strengthens `0x2D0.u16@4` as an airflow limit/configuration field rather than actual airflow, and strengthens `0x53E.byte5` as an active/available node-count candidate while proving `0x53D.byte0=1` is not required for a healthy five-node operational network.

## Immediate engineering work

Highest-value remaining work:

1. capture/qualify a stock UX360 system-mode write; setpoint TX is already stock-qualified and opt-in guarded;
2. validate the separately guarded Technician-qualified indoor-fan writer on-device through the control profile; it is implemented, exposed as typed services, and remains default-off behind both global TX and its dedicated qualification gate;
3. confirm the `0x383.float[0..1]` gauge-vs-absolute display conversion against synchronized Technician suction/liquid PSI and confirm `0x381.float[1]` against discharge temperature;
4. independently qualify `0x430.float[1]`, `0x450.float[0..1]`, and `0x460.float[0]`;
5. capture defrost/reversing-valve behavior;
6. qualify live A2L concentration/status/alarm telemetry; the mitigation board itself is now identified as CNT09525;
7. correlate live electric-heat stage states; `EquipSummary` now confirms a 10 kW single-phase 2-stage heater accessory;
8. validate long structured JSON logging on-device after the logger-buffer increase and continue hydrating any remaining profile fields not present in `EquipSummary`.

## Source hygiene

Project rules:

- no build-time source-rewrite scripts;
- no patch-wrapper chains or generated-source monkey-patching;
- behavior belongs in maintained source;
- preserve useful upstream comments/evidence;
- use Candidate/Raw names until evidence justifies promotion;
- keep passive capture usable even while active-control work is incomplete.
