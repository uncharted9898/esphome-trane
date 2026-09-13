# Development context

## Current direction

The project is no longer targeting replacement of the UX360 or SC360.

Production architecture:

- keep UX360 stock and fully usable;
- keep SC360 stock and authoritative;
- bridge is a parallel CAN node/tap;
- bridge failure/removal must not affect HVAC operation;
- Home Assistant/local control is a second control surface;
- SC360 bus state wins over requested local state;
- external/cloud access can be restricted at the network boundary later.

## Reference hardware

Primary hardware: Waveshare ESP32-S3-RS485-CAN.

Reference CAN interface:

- ESP32-S3 native TWAI;
- GPIO15 TX;
- GPIO16 RX;
- 50 kbit/s;
- onboard isolated CAN physical layer;
- 120 ohm termination jumper left open;
- USB-C power for initial commissioning;
- CAN H -> Trane DH;
- CAN L -> Trane DL;
- no Trane R/B connection needed on isolated CAN field side.

## Firmware profiles

### `waveshare-trane-listenonly.yaml`

First-connect commissioning image.

- TWAI LISTENONLY;
- no CAN ACK participation;
- TX queue disabled;
- application TX disabled;
- raw JSON disabled;
- 8192-frame bounded RAM capture ring;
- freeze/dump/resume controls;
- total-vs-known-vs-unclassified CAN frame counters;
- segmented JSON message and transport-error counters.

The unclassified counter is intentional. The target R-454B system contains hardware not present in the original upstream capture set, especially the refrigerant-detection/mitigation subsystem. New standard CAN IDs must be preserved and investigated rather than filtered out.

### `waveshare-trane-control.yaml`

Minimal guarded control/transport image.

- TWAI NORMAL;
- TX disabled by repository default;
- typed mode/setpoint/profile actions;
- SC360-presence gate;
- ACK serialization and timeout counters;
- no raw JSON by default.

### `waveshare-trane-full.yaml`

Preferred full integration target.

- includes the mature existing decoder from `esphome-trane.yaml`;
- overrides hardware to Waveshare GPIO15/16;
- removes the legacy raw API service surface;
- removes legacy boot-time raw GetProfile transmission;
- binds the climate entity directly to the guarded `trane_bus`;
- exposes local-control arming as a restore-OFF switch;
- refuses arming unless SC360 traffic is recent.

## Guarded transport contract

`components/trane_bus` now owns safety-critical TX behavior.

Default policy:

- `tx_enabled = false`;
- `raw_json_enabled = false`;
- require recent SC360 activity before transmitting;
- reject unsupported system modes;
- validate setpoint range/deadband/zone/hold/source;
- allow one write command outstanding at a time;
- wait for SC360 ACK;
- track ACK success/error/timeouts;
- bound payload size;
- check CAN send errors frame by frame.

Typed actions:

- `trane_bus.set_mode`;
- `trane_bus.set_setpoints`;
- `trane_bus.get_profile`;
- `trane_bus.set_tx_enabled`.

Raw action remains available only when explicitly enabled:

- `trane_bus.send_json`.

## Climate contract

`components/trane_hvac` is non-optimistic.

- only OFF/HEAT/COOL advertised;
- no fake BOOST/Home/Away/Sleep climate presets;
- requested mode/setpoint is not immediately published as state;
- observed SC360/UX360-derived sensors update climate state;
- when `trane_bus_id` is configured, climate writes use guarded typed transport;
- legacy automation triggers remain only for backward compatibility.

Historical upstream reverse-engineering comments are treated as protocol evidence. Do not remove them merely because a refactor changes the implementation. If an observation is no longer appropriate inline, preserve it in protocol/telemetry documentation with provenance and qualification notes.

## Known target equipment

Planned all-electric target:

- outdoor `5TWV0X24A1000`;
- indoor `5TAMXC03AV31D` / AHRI indoor model `5TAMXC03AV31`;
- electric auxiliary heat package expected around `BAYEA1305BK1A` 5 kW;
- UX360;
- SC360 `TSYS2C60A2VVU`.

The public reverse-engineering baseline was captured on a gas-aux system. Therefore electric auxiliary heat, emergency heat, defrost supplemental heat, and related operating states must be captured on this exact installation before unrestricted control is considered complete.

The R-454B 5TAMX also contains refrigerant-detection/mitigation hardware absent from the upstream capture set. Expect new nodes/IDs and preserve all unknown standard CAN traffic during commissioning.

## Important known CAN details

- bus rate: 50 kbit/s;
- 0x641 / 0x649: SC360 command/response/broadcast transport;
- 0x5C1 / 0x5C9: UX360-SC360 private segmented transport;
- 0x380-0x38F: outdoor equipment float/status frames;
- 0x490 and related indoor IDs: air-handler data;
- commands observed include `SystemMode Put`, `SpOverride Put`, `GetProfile`;
- successful writes observed with `Ack: 200`.

## Telemetry discovery status

See `docs/TELEMETRY.md` for the detailed confidence/provenance map and `docs/COMMISSIONING.md` for the controlled-correlation capture plan.

Important pre-install findings:

1. `OdStatus.B` is documented upstream as compressor **speed percent**, but legacy YAML currently exposes it as `Compressor Frequency` in Hz. Do not trust that friendly label.
2. Upstream documentation and legacy YAML disagree about the refrigerant-temperature use of `0x386` vs `0x387`; preserve each raw channel separately until target correlation.
3. `SystemOpStatus.D` has conflicting historical interpretations (run time vs demand-like value). Keep raw.
4. `SystemOpStatus.E` currently relies on an integer-vs-decimal heuristic to choose humidity vs outdoor temperature; preserve context/raw value.
5. The current project exposes one generic refrigerant pressure, while the 5TWV0X hardware/service information gives us a reason to hunt separate suction and liquid/high-side pressure signals.
6. Existing `0x283` names are probably too air-centric; target 5TAMX has ET/GT refrigerant/coil thermistors plus separate supply/return air sensors. Controlled target-system correlation is required.
7. `0x490` remains multiplexed/undecoded and is a high-priority target during blower-CFM and electric-heat tests.
8. `0x5C1/0x5C9` boot/private transport contains richer profile data than the current parser exposes and is a major target for passive cold-boot capture.
9. Controlled UX360/Diagnostics tests provide known stimuli for blower CFM, compressor demand, and indoor electric heat stages, making deterministic field correlation possible without custom CAN control frames.
10. A natural defrost capture and the installer-required A2L mitigation verification are especially valuable because both should create distinctive state transitions absent from the upstream R-410A/gas-aux baseline.

## Outstanding implementation work

1. Let CI prove every current ESPHome config after each transport change.
2. Move remaining monolithic receive/parser logic out of YAML into maintained C++ source.
3. Add a reusable segmented RX transport implementation for 0x641/0x649 and, after target framing is passively confirmed, 0x5C1/0x5C9.
4. Add structured message parsing rather than repeated substring searches.
5. Add capture/replay fixtures from the exact all-electric system.
6. Decode electric AUX/emergency/defrost states explicitly.
7. Decode fan-only and auto/heat-cool before exposing those modes.
8. Add full-state/profile synchronization after control is armed.
9. Add command correlation beyond generic ACK where protocol evidence allows it.
10. Add long-run bus-health counters and diagnostic ring-buffer export.
11. Decode requested/actual blower CFM and qualify return/supply vs ET/GT temperature channels.
12. Identify suction and liquid pressure, all outdoor temperature channels, EEV/superheat telemetry and defrost state on 5TWV0X/5TAMX.
13. Discover and document the R-454B mitigation/A2L node, IDs and alarm/mitigation states.
14. Preserve fail-passive behavior throughout all future changes.
