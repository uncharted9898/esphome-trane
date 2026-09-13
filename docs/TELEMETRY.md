# Trane Link telemetry map and discovery plan

This document is the protocol/telemetry notebook for the parallel Trane Link bridge.

It deliberately separates **observed facts** from **working hypotheses**. The original upstream system used a different equipment mix, including gas auxiliary heat. The target system for this fork is an all-electric R-454B system:

- outdoor: `5TWV0X24A1000` / 5TWV0X24A family;
- indoor: `5TAMXC03AV31D` / 5TAMXC03AV31DA family;
- indoor auxiliary heat: expected BAYEA 5 kW class;
- UX360 thermostat;
- SC360 system controller.

Do not promote an inferred field to a named Home Assistant entity until it has been correlated against a known equipment state on the target system.

## Confidence vocabulary

- **Confirmed** — observed repeatedly and has an independent reference or a controlled-state correlation.
- **Observed** — repeatable on the upstream system, but exact semantic meaning is not independently proven.
- **Candidate** — plausible interpretation that should remain raw/disabled until the target system confirms it.
- **Target-only** — expected on the new R-454B system but absent from the upstream capture set.

Historical upstream comments and observations are protocol evidence. Preserve them even when a later implementation no longer uses the same entity name.

## Transport inventory

| CAN ID / range | Direction / owner | Status | Notes |
|---|---|---|---|
| `0x641` | command / response | Confirmed | Segmented JSON, local writes and ACKs. |
| `0x649` | SC360 broadcast | Confirmed | Segmented JSON state/delta stream. |
| `0x5C1` | UX360 private transport | Observed | A0/A1/A2 segmented profile/request channel. Do not transmit on this channel yet. |
| `0x5C9` | SC360 private transport | Observed | Boot/full-profile response channel. Richest likely source for cold-start inventory. |
| `0x380`-`0x38F` | outdoor unit | Observed | Mostly little-endian float telemetry on upstream equipment. Meanings must be re-qualified on 5TWV0X. |
| `0x283` | indoor / refrigerant sensors | Candidate | Two little-endian floats. Existing labels are probably too air-centric; 5TAMX has ET/GT thermistors. |
| `0x308` | indoor air temperatures | Observed | Two float values currently treated as return/supply air. Re-qualify against UX360/Diagnostics monitor values. |
| `0x410`,`0x430`,`0x450` | unknown temperature sources | Candidate | Three temperatures observed upstream; exact source is unknown. |
| `0x490` | air-handler multiplex | Observed | Raw 5-byte style channel/multiplex behavior; byte/channel encoding unresolved. |
| unknown IDs | target-system additions | Target-only | Especially important for R-454B mitigation/A2L hardware. Never discard unknown standard IDs during commissioning. |

The bounded capture ring in `components/trane_bus` records **all standard CAN frames**, not only IDs already recognized by the decoder. This is intentional so the new system can reveal new nodes and IDs.

## JSON telemetry already known

### `SystemOpStatus`

| Field | Current meaning | Confidence / caution |
|---|---|---|
| `A` | system state (`A`,`E`,`G`,`I` observed) | Observed. Preserve raw code. |
| `B` | mode: `A` heat, `B` cool, `C` off | Confirmed on upstream system. |
| `C` | demand/stage text | Observed. Gas/ID stage strings are historical upstream evidence, not an electric-heat mapping. |
| `D` | changing numeric/string operating value | **Ambiguous.** Upstream notes alternately describe elapsed runtime and demand-like values. Do not call this system demand percent without target correlation. |
| `E` | humidity or outdoor temperature depending message/value format | **Ambiguous heuristic.** Integer-vs-decimal formatting is not a protocol type guarantee. Keep raw until object/message context is proven. |

Historical `SystemOpStatus.C` strings observed upstream include `--`, `HP Stage 1`, `HP Stage 2`, `HP1+ID1`, `HP1+ID2`, `HP2+ID1`, `HP2+ID2`, `ID Stage 1`, and `ID Stage 2`. The `ID` labels came from a gas-aux system. On the all-electric target, capture the exact strings for electric AUX, emergency heat, and defrost before assigning semantics.

### `OdStatus`

| Field | Current meaning | Confidence / caution |
|---|---|---|
| `A` | outdoor active flag | Observed. |
| `B` | compressor speed **percent** | Confirmed by upstream protocol notes. Current legacy YAML incorrectly exposes this as `Compressor Frequency` in Hz; fix before treating the entity as trustworthy. |
| `C` | outdoor state (`B` running, `D` off observed) | Observed. |
| `D` | outdoor fault code (`0` observed for no fault) | Observed. |
| `CompDemandPercent` | compressor demand % | Confirmed/strongly observed. Keep separate from actual compressor speed. |

The distinction between **requested compressor demand** and **reported compressor speed** is valuable on the 5TWV0X. UX360 test mode can command a known demand percentage, providing an excellent controlled correlation.

### `IndoorStatus`

| Field | Current meaning | Confidence / caution |
|---|---|---|
| `D` | blower state (`A` transition/off, `B` running upstream) | Observed. |
| `E` | numeric blower speed % or fault string | Observed; dual use means type/contents must be retained. |
| `F` | unknown (`0` observed upstream) | Candidate; expose raw/disabled if useful. |
| `HumControl` | humidity-control state | Observed. |
| `HumidifierStatus` | humidifier status | Observed. |
| `DehumidifierStatus` | dehumidifier status | Observed. |
| `VentilatorStatus` | ventilator status | Observed. |

The target 5TAMX is a variable-speed ECM air handler. Percent blower output is useful, but **actual/requested CFM** is more useful and is currently missing from this project.

### `ZoneStatus`

Known/observed fields include room temperature, Hsp/Csp, `HcStatus`, `HoldText`, airflow %, zone state, and zone demand %. Existing legacy substring searches are not always scoped tightly enough to a specific zone/object. Source migration should parse the object structurally before exposing more zones.

Observed upstream `HcStatus` values include `3` active call, `4` satisfied, `5` elevated call, `7` aux/emergency, and `9` inactive. Re-qualify `7` on the all-electric installation.

### Other profile/state objects

Already observed on the bus:

- `SpOverride` — per-zone setpoints/hold/source;
- `PresetSettings` — Home/Away/Sleep setpoints;
- `ZoneSettings` — zone-related settings/flags;
- `ActiveAlarms` — alarm ID/origin/level;
- `VersionDetails` — configuration/alarm DB versions;
- `ZoneCardState` — zone names and wireless-sensor information;
- `SystemSettings` — system configuration values;
- `ScheduleSettings` — schedule configuration;
- `WeatherData` / `WeatherToday`;
- `UnitID` — identity/build information;
- `OutdoorSettings`;
- `OdWidget`.

The UX360 equipment-summary screen can display communication status, description, model, and serial for installed communicating devices. Therefore **per-device identity exists somewhere in the Link state/profile data** and should be captured for the SC360, air handler, outdoor unit, and any mitigation/A2L node instead of treating a single `UnitID` object as the complete equipment inventory.

## Raw float/frame telemetry: current state

### `0x380`

Upstream capture:

- float 1: usually `0.0` or `-99.0`; unknown;
- float 2: outdoor air temperature.

Keep float 1 as an unknown candidate on 5TWV0X. A different generation of outdoor unit may populate it.

### `0x386` / `0x387` documentation drift

This is a known upstream inconsistency that must not be hidden:

- an upstream protocol-documentation commit explicitly states **`0x386` float 2** was the refrigerant-circuit temperature, observed around 18-19 F in cooling;
- the legacy YAML still publishes **`0x387` float 1** into the entity named `Refrig Circuit Temp`;
- the same YAML sends `0x386` float 2 to `Refrig Sensor B` while its comment says float 1 is the constant/unknown channel.

For commissioning, preserve all three channels separately:

1. `0x386` float 1 — unknown/candidate;
2. `0x386` float 2 — upstream refrigerant-circuit-temperature candidate;
3. `0x387` float 1 — separate temperature candidate until correlated.

Do not merge these values under one friendly name.

### `0x381`, `0x383`, `0x38F`

Legacy meanings are suction temperature, discharge temperature, and one refrigerant pressure respectively. The 5TWV0X service data shows the new outdoor unit has more physical sensors than the current decoder exposes, so these IDs must be re-qualified rather than assumed to retain exactly the older mapping.

### `0x283`

Two little-endian floats are currently named `AHU Inlet Air Temp` and `Indoor Coil Temp`. The first upstream value was reported in the 28-40 F range during cooling, which is inconsistent with ordinary return/inlet **air** temperature.

The 5TAMX service manual explicitly documents separate **ET (evaporator temperature)** and **GT (gas temperature)** thermistors plus supply-air and return-air sensing. Therefore the strongest pre-install hypothesis is that the two `0x283` values are refrigerant/coil thermistor data (possibly ET/GT), not two air temperatures. Do not rename them ET/GT until the target Diagnostics/UX360 monitor values are correlated one at a time.

### `0x308`

Two float values are currently interpreted as return-air and supply-air temperatures. This is plausible and can be directly checked against the 5TAMX return-air/supply-air sensors during blower-only and heating/cooling tests.

### `0x410`, `0x430`, `0x450`

Three temperatures observed upstream, exact source unknown. They were specifically determined not to be the wireless room sensors. Keep as candidate component temperatures until a controlled test identifies them.

### `0x490`

Known to carry air-handler data, but current firmware only logs it. Upstream notes describe a multiplexed payload with a still-unknown channel selector. This should be a major target during:

- blower CFM sweep;
- indoor heat stage sweep;
- EEV open/close test if a qualified technician chooses to run it;
- ET/GT/SAT/RAT temperature changes.

## Telemetry the 5TWV0X/5TAMX definitely gives us a reason to hunt

The following are not guesses that the equipment *has a concept of* these values; they are named in Trane installation/service material or exposed as UX360/Diagnostics tests/configuration. What remains unknown is **where they appear on the Link CAN protocol**.

### Indoor / 5TAMX

High priority:

- commanded/requested blower CFM;
- actual blower CFM if separately reported;
- blower percent / motor state;
- ET (evaporator temperature);
- GT (gas/refrigerant temperature);
- supply-air temperature;
- return-air temperature;
- EEV command/position/step count if exposed;
- superheat actual;
- superheat target;
- electric heat stage 1 / 2 / 3 state;
- installed heater type;
- heater size / kW;
- heater model/serial if present;
- electric-heat airflow setting;
- blower on/off delays;
- freeze-protection state;
- defrost message received from outdoor unit;
- supplemental heat requested during defrost;
- active/historical indoor faults;
- air-handler model/serial/software version.

The 5TAMX manual says Link-mode test modes are available from UX360 or Diagnostics. It specifically provides blower tests, indoor-heat tests, and fully-open/fully-closed indoor EEV tests, and says the monitor screen exposes information that proves test success. This gives us controlled stimulus for finding each signal without writing our own control frames.

### Outdoor / 5TWV0X

The 5TWV0X service data documents at least these physical measurements/functions:

- outdoor ambient temperature;
- outdoor coil temperature;
- suction/gas temperature;
- liquid temperature;
- compressor/discharge/dome temperature diagnostics;
- suction pressure;
- liquid/high-side pressure;
- outdoor EEV control;
- defrost state/initiation/termination;
- compressor operating demand/speed;
- low-pressure/charge/airflow protection diagnostics.

The current decoder exposes only a subset and has only one generic refrigerant-pressure entity. On the target unit, specifically search for **both suction and liquid pressure** and keep them separate.

Additional candidates worth looking for because the Diagnostics/UX360 control stack needs them operationally:

- outdoor EEV position/command;
- outdoor fan command/speed;
- inverter/compressor current or power;
- compressor speed actual vs requested;
- protection/derate reason;
- sump/preheat state;
- reversing-valve state;
- charge-mode state.

Do not create named entities for the additional candidates until captures prove them.

### R-454B / A2L mitigation telemetry

The target 5TAMX includes a refrigerant leak-detection/mitigation system that was not part of the original upstream R-410A capture set.

Trane documentation describes a mitigation control board with:

- communication mode;
- a CAN communication-loss indication;
- a node-count indication;
- refrigerant-leak alarm state;
- sensor communication error;
- sensor failure;
- past refrigerant-detected alarm;
- mitigation actions that include shutting down compressor/ignition sources and providing dilution airflow.

This makes the A2L/mitigation subsystem a **first-class telemetry target**. It may introduce entirely new CAN IDs. The capture ring must therefore retain unknown standard IDs.

During the installer-required mitigation verification, passively capture the complete CAN bus. Do not add an extra artificial leak/mitigation test merely for reverse engineering; correlate against the normal required verification if it is performed during commissioning.

Desired eventual entities:

- mitigation controller present/communicating;
- A2L sensor present/communicating;
- leak detected active;
- sensor communication fault;
- sensor fault;
- mitigation active;
- mitigation history/past alarm if broadcast;
- mitigation-requested blower/airflow state.

## Configuration telemetry worth recovering

UX360 installer documentation exposes values that should be discoverable in profile/configuration traffic even if they are not in the current parser:

- heater type;
- heater size and model;
- electric-heat airflow setting;
- minimum system speed;
- cooling min/max CFM per ton;
- cooling maximum airflow;
- heating CFM per ton;
- heating maximum RPM selection;
- auxiliary heat lockout enable and temperature;
- compressor heat lockout if configured;
- compressor/indoor heat cycles per hour;
- fan delays;
- dehumidification behavior;
- configured accessories and external switches;
- load-shed/generator-backup restrictions.

These are especially useful because they explain **why** the SC360 is staging/modulating the system the way it is. Read-only capture is the first objective; do not write configuration fields until their protocol and constraints are understood.

## Best controlled-correlation tests after installation

Use `waveshare-trane-listenonly.yaml`. Freeze/dump the bounded capture after each single-variable test.

### 1. Cold boot / equipment inventory

Capture from power application through a stable idle state. This is the highest-value single capture because `0x5C1/0x5C9` carries the UX360/SC360 full profile exchange before the system drops into delta-only updates.

Look for:

- every node/CAN ID present;
- per-device model/serial/software;
- heater inventory/configuration;
- A2L/mitigation node;
- current setpoints/mode/profile;
- all previously unseen IDs.

### 2. Blower CFM sweep

From UX360/Diagnostics `Test Blower`, command several known values spanning the allowed range for the installed air handler.

Suggested points: low, approximately 50%, normal design airflow, and a higher point that remains inside the test-mode range.

Correlate every changing field against the selected CFM. This is the best way to identify:

- requested CFM;
- actual CFM;
- blower percent;
- possible static-pressure or motor-load telemetry;
- `0x490` channel meanings.

### 3. Compressor demand sweep

Use UX360 `Test Compressor Cool` and, when appropriate, `Test Compressor Heat` at known percentages. Compare:

- `OdStatus.CompDemandPercent`;
- `OdStatus.B` compressor speed %;
- any outdoor float values;
- suction/liquid pressures;
- suction/liquid/coil/discharge temperatures;
- indoor CFM;
- outdoor fan/EEV candidates.

This will separate **commanded demand** from **actual compressor response**.

### 4. Indoor electric heat stage sweep

Use UX360 `Test Indoor Heat` stage 1, then stage 2/3 only if those stages actually exist for the installed heater configuration.

Record:

- `SystemOpStatus.C` exact text;
- `HcStatus`;
- indoor status fields;
- airflow/CFM;
- heater-related profile fields;
- supply-air rise;
- newly changing IDs.

This replaces the upstream gas `ID Stage` assumptions with real electric-stage semantics.

### 5. Defrost

Passive natural-event capture is preferred. Record at least 2-3 minutes before initiation, the entire defrost, supplemental-heat interval, and several minutes afterward.

The 5TAMX documentation states the outdoor unit sends a defrost message to the air-handler control; the air handler then changes EEV/superheat control and energizes electric or hydronic heat to temper the air. That means defrost should have a distinct and discoverable bus signature.

Correlate:

- outdoor defrost state;
- reversing-valve/state change;
- EEV behavior;
- indoor auxiliary heat stage;
- blower CFM;
- coil/suction/liquid/discharge temperatures;
- pressure changes;
- `SystemOpStatus` and `HcStatus`.

### 6. Required A2L mitigation verification

If/when the installer performs the required refrigerant-detection mitigation verification, capture the whole event in listen-only mode.

The goal is to discover the mitigation-controller CAN identity and state transitions without creating any additional test beyond normal commissioning.

### 7. Optional EEV service tests

The 5TAMX service test can fully open and fully close the indoor EEV. The close test can intentionally drive the system toward low pressure and may fault. Treat this as a technician/service test, not a routine reverse-engineering step.

If a qualified technician runs one of these tests anyway, it is extremely valuable for identifying:

- indoor EEV position/command;
- ET/GT pair;
- superheat actual/target;
- suction-pressure signal;
- low-pressure protection state.

## Known implementation issues to fix before trusting friendly telemetry names

1. `OdStatus.B` is a percent field but legacy YAML labels it `Compressor Frequency` in Hz.
2. `0x386` / `0x387` refrigerant-temperature entity assignments drifted from the upstream documentation.
3. `SystemOpStatus.D` is overinterpreted as `System Demand Percent`; keep raw until target correlation.
4. `SystemOpStatus.E` uses an integer-vs-decimal formatting heuristic; preserve raw value/context.
5. Several ZoneStatus searches are not tightly scoped to a particular zone/object.
6. `0x5C1/0x5C9` are still raw-only even though they carry the full boot profile.
7. `0x490` is captured but not decoded.
8. Existing generic `Refrigerant Pressure` cannot represent the 5TWV0X's separate suction and liquid pressure transducers.
9. Existing indoor temperature names likely mix actual air temperature with ET/GT refrigerant/coil thermistors.
10. The target A2L mitigation controller is absent from the upstream protocol map and must be discovered from unknown IDs.

## Source/provenance notes

Upstream protocol baseline:

- https://github.com/dewbot6/esphome-trane
- especially upstream commit `2e925815fedef0cacf64a1a12f84774300fdf060`, which documents the boot-profile transport and the `0x386` observations.

Target-equipment references used to build the discovery matrix:

- Trane 5TAMX Installation, Operation and Maintenance, document `18-GJ96D1-1B-EN` (5TAMXC03AV31DA included): sensor tables, Link operation, unit tests, EEV/superheat sequence, defrost behavior, heater attributes.
- Trane Link UX360 installation guide `CNTR-SVN001-EN` / `18-HD98D1` family: installer configuration, equipment summary, blower/compressor/indoor-heat test modes.
- Trane 5TWV0X / 5TTV0X Service Facts `5T-V0X-SF-1B-EN`: ambient/coil/suction/liquid temperature sensors, suction/liquid pressure transducers, defrost and protection functions.
- Trane R-454B 5TAMX refrigerant-detection/mitigation documentation `AHR-SVX007` family: mitigation-board communication state, CAN-loss indication, node count and alarm states.

Where a service document describes a signal/function but no CAN field is known, this document intentionally says **target to discover**, not **decoded**.
