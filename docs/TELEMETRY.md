# Trane Link telemetry map

This is the **maintained semantic map** for the current target system.

Target:

- 5TWV0X24A1000B outdoor unit
- 5TAMXC03AV31DB air handler
- UX360 + SC360
- R-454B / A2L system
- Waveshare ESP32-S3-RS485-CAN parallel tap

Dated reverse-engineering notes live under [evidence/](evidence/). Those notes intentionally preserve old hypotheses and disproved labels. When they conflict with this file, **this file and current source/tests are authoritative**.

## Confidence vocabulary

- **Confirmed** — repeatedly observed and independently correlated against a known state/value.
- **Strong candidate** — repeated cross-capture correlation with coherent transition behavior; exact OEM label still unverified.
- **Candidate** — plausible but not sufficiently isolated for promotion.
- **Raw** — preserve value without assigning semantic meaning.
- **Superseded** — an older interpretation disproved by later captures.

## Environmental telemetry

| Signal | Source | Confidence | Notes |
|---|---|---|---|
| Room Temperature | `0x490.float[0]` | Confirmed | Directly matched six `ZoneStatus.Update.1.H` updates at 72, 73, 74, 75 and 76°F within ~1 second in the 2026-09-25 archive; invalid/sentinel values filtered. |
| Indoor Humidity | `0x490.byte4` | Strong candidate | Normal operation repeatedly 50s/60s; user-facing entity accepts only 0..100. Startup value 157 is rejected as invalid. |
| Outdoor Air Temperature | `0x380.float[1]` | Confirmed | Tracks outdoor ambient independently of SC360 JSON. |
| Return Air Temperature | `0x308.float[0]` | Confirmed | Matches air-handler return-air behavior. |
| Supply Air Temperature | `0x308.float[1]` | Confirmed | Tracks active cooling supply-air temperature. |

The friendly environmental entities intentionally use the live binary sources above instead of depending on sparse structured JSON snapshots.

## Indoor / 5TAMX telemetry

| CAN field | Current meaning | Confidence | Notes |
|---|---|---|---|
| `0x200.u16@0` | Indoor EEV Position Candidate | Candidate | Tracks a step-like control value; exact OEM label not independently confirmed. |
| `0x200.u16@2` | Blower Speed Request Candidate | Strong candidate | 2026-09-27 long-run data shows numeric `IndoorStatus.E` tracks this word at ~7.9 request units per percent (correlation ~0.99); it leads the `0x318.u16@4` motor-speed feedback through starts, modulation, and coast-down. |
| `0x280.float[0]` | Compressor Speed Request | Strong/confirmed | Commanded/requested compressor RPS. Tracks ~29 RPS low load, ~40-43 moderate load, ~57.5-58 high load, and changes ahead of achieved speed on shutdown. |
| `0x280.float[1]` | Raw/Candidate | Candidate | Do not call literal power factor. |
| `0x281.u16@0` | Airflow Target Candidate | Strong candidate | Airflow-shaped, but 2026-09-27 startup/shutdown timing disproves delivered/actual airflow: it jumps to ~720 before blower current/power and `0x318` feedback leave zero, and remains nonzero briefly after the blower stops. |
| `0x281.u16@2` | Raw fixed/configuration field | Raw | Often 500; remains 500 with blower stopped, so not actual airflow. |
| `0x281.byte6` | Compressor Demand Mirror | Confirmed/strong | Matches structured `OdStatus.CompDemandPercent` exactly at independent 72, 82, 84 and 82 percent updates. |
| `0x281.byte7` | Blower Active Flag Candidate | Strong candidate | Remains 1 during blower coast-down, reaches 0 when stopped. |
| `0x281.u16@6` | Composite raw only | Raw | Literally byte6 + (byte7 << 8); not independent telemetry. |
| `0x282.byte1` | Stator Heat Enable | Confirmed/strong | Across 75 isolated cycles from 2026-09-23 through 2026-10-02, this bit consistently asserts about 9-10 s before stator-heating current/power appears, remains asserted through the heat interval, and clears as the load returns to standby. Compressor and outdoor fan stay stopped throughout isolated cycles. |
| `0x283.float[0..1]` | Indoor Temperature 1/2 Candidate | Candidate | Likely refrigeration/coil family; do not relabel as simple inlet/coil air without Technician correlation. |
| `0x300.float[0]` | ID Gas Temperature Candidate | Strong candidate | Refrigerant-side temperature family. |
| `0x300.float[1]` | ID Evap Liquid Temperature Candidate | Strong candidate | Refrigerant-side temperature family. |
| `0x300.f0 - f1` | ID Superheat Candidate | Strong candidate | Dynamic difference behaves coherently during cooling. |
| `0x308.float[0]` | Return Air Temperature | Confirmed | See environmental map. |
| `0x308.float[1]` | Supply Air Temperature | Confirmed | See environmental map. |
| `0x310.float[0]` | Total Static Pressure | Strong candidate | ~0.09-0.12 inWC across active captures. |
| `0x318.float[0]` | Blower Input Current Candidate | Strong candidate | Follows blower load. |
| `0x318.u16@4` | Blower Motor Speed | Strong/confirmed family | Follows the `0x200.u16@2` speed request only after the blower actually starts, tracks modulation and power, and returns to zero with motor stop. Literal RPM scaling is retained as the best working unit pending synchronized Technician speed. |
| `0x318.u16@6` | Raw/Candidate | Candidate | Moves with blower operation but no longer carries the primary speed label; exact physical meaning remains unresolved. |
| `0x320.float[0]` | Blower Power | Confirmed/strong | ~45-73 W under observed active states and 0 W stopped. |
| `0x2D0.u16@2` | Airflow Limit Candidate | Candidate | ~775 CFM at high load and ~771 while delivered airflow was only ~658 CFM; behaves more like an airflow ceiling/configuration value than actual airflow. |

### Blower request/feedback chain

Current best interpretation:

```text
0x200.u16@2   -> blower speed request
0x318.u16@4   -> blower motor speed feedback
0x281.u16@0   -> airflow target/command candidate
0x281.byte7   -> blower active flag
0x318.u16@6   -> unresolved motor-adjacent raw field
0x320.float0  -> blower power
```

This interpretation is based on lead/lag behavior across modulation and cooling-to-satisfied shutdown captures.

## Outdoor / 5TWV0X telemetry

| CAN field | Current meaning | Confidence | Notes |
|---|---|---|---|
| `0x380.float[0]` | unavailable/raw | Raw | Frequently `-99`; treat as unavailable sentinel. |
| `0x380.float[1]` | Outdoor Air Temperature | Confirmed | Live ambient temperature. |
| `0x381.float[0]` | Outdoor Coil Temperature Candidate | Strong candidate | Tracks condenser/outdoor-coil family rather than suction temp in later captures. |
| `0x381.float[1]` | Compressor Discharge Temperature Candidate | Strong candidate | Long-idle capture on 2026-09-23 disproved the old suction-pressure interpretation: this field cooled through ~81→75°F while `0x383.f0/f1` equalized as a pressure pair, and earlier active captures put it in the ~155-194°F range. |
| `0x382.float[0]` | Suction Line Temperature | Strong/confirmed | Fits the outdoor-board suction-temperature position between coil and liquid-temperature channels and behaves coherently across the active-cooling captures. |
| `0x382.float[1]` | Liquid Temperature Candidate | Strong candidate | Tracks liquid-line temperature family. |
| `0x383.float[0]` | Suction Pressure Raw | Confirmed semantic / representation unresolved | Long-idle captures show equalization with `0x383.float[1]`; active cooling drives this field down while the paired high-side field rises. On 2026-09-28 OEM Err 185.10/185.11 low-suction protection occurred with this field around ~69-74 while the high-side field remained ~266-274, directly confirming the suction-pressure role. Gauge-vs-absolute display conversion remains unresolved. |
| `0x383.float[1]` | Liquid/High-Side Pressure Raw | Strong candidate / representation unresolved | Rises as the suction field falls under cooling and converges with it during idle equalization. The 2026-09-28 low-suction protection sequence leaves this field high while `0x383.float[0]` collapses, strongly supporting the paired high-side interpretation. Gauge-vs-absolute conversion remains unresolved. |
| `0x384.float[0]` | Actual Compressor Speed Candidate | Strong candidate | 0 when satisfied; ~58 RPS at high load; coherent ramp-down. |
| `0x384.u16@4` | Drive DC Voltage | Strong candidate | ~340-352 Vdc. |
| `0x384.u16@6` | Outdoor Fan Speed | Strong candidate | ~750-775 RPM under high load, 0 stopped. |
| `0x385.float[0]` | Compressor Power Candidate | Strong candidate | ~1.3-1.5 kW high load; 0 stopped. |
| `0x385.float[1]` | Compressor Speed Ceiling Candidate | Strong candidate | Sits above the immediate `0x280` request across low/moderate/high load (~40 vs 29, ~63 vs 56, ~66-68 vs ~58 RPS) and becomes 0 idle. The 65535 startup sentinel recurs across later clean starts (six more on 2026-10-02) and is filtered rather than published as a fake RPS spike. |
| `0x386.float[0]` | Raw | Raw | Often 2.0 in target captures. |
| `0x386.float[1]` | Raw | Raw | Often fixed 50.0; old saturation-temperature label disproved. |
| `0x387.float[0]` | Compressor Speed Reference/Limit Candidate | Strong candidate | Fixed ~55 RPS across idle and varying load; not actual speed. |
| `0x387.float[1]` | Fan Phase Current Candidate | Candidate | ~0.3-0.4 A active, 0 stopped. |
| `0x388.float[0..1]` | Compressor Phase Current 1/2 Candidate | Strong candidate | Both are zero at ordinary standby, participate in the three-phase current pattern during active compressor operation, and assert during 66 isolated stator-heat cycles with compressor speed still 0 RPS. |
| `0x389.float[0]` | Compressor Phase Current 3 Candidate | Strong candidate | Completes the three-current family with `0x388`; active during compressor operation and all 64 observed stator-heat cycles, zero during ordinary standby. Exact U/V/W ordering is unresolved. |
| `0x389.float[1]` | Input AC Current Candidate | Strong candidate | ~6-7 A under observed high load. |
| `0x390.byte0` | Stator Heat Power Level | Strong/confirmed semantic, unit unresolved | Across 75 isolated stator-heat cycles through 2026-10-02, this channel remains heat-specific, sits at 44-46, and appears about 9-10 s after the enable bit at the same time outdoor input power rises. Technician exposes `MocStatorHeatPower`, but exact wire units are not yet proven. |
| `0x38C.float[1]` | Input Power | Strong/confirmed | ~1.5-1.7 kW active; ~15 W satisfied standby. |
| `0x38F.float[0]` | Line Voltage Candidate | Strong candidate | ~237-241 V across active/idle captures. |
| `0x38F.float[1]` | Raw/Candidate | Candidate | ~3.7-4.0 in observed captures. |
| `0x3D0.float[1]` | Compressor Target Minimum Speed Candidate | Strong candidate | ~20-21 RPS even when live speed/target are zero. |
| `0x3E0` | Minimum-speed mirror/status family | Candidate | Sparse/NA in some captures. |
| `0x410.float[0]` | Drive Inverter/IPM Temperature Candidate | Strong candidate | ~98°F at high load; matches the Technician `MocDriveIpmTemperature` family. |
| `0x410.float[1]` | Drive Rectifier/PFC Temperature Candidate | Strong candidate | ~99-100°F at high load; adjacent to the IPM channel and matches the Technician `MocDrivePfcTemperature` family. |
| `0x430.float[0]` | Outdoor Fan IPM Temperature Candidate | Candidate | ~97°F and closely tracks the drive thermal family; Technician exposes a separate `OdFanIpmTemperature` monitor. |
| `0x430.float[1]` | Raw | Raw | Highly dynamic ~260-360 values in otherwise steady operation; not credible as a direct temperature. |
| `0x450.float[0..1]` | Raw pair | Raw | Both vary broadly in the new captures and have no trustworthy physical label yet. |
| `0x460.float[0]` | Temperature Candidate | Candidate | Old liquid-saturation label disproved. |

### Compressor speed chain

Three distinct speed-family channels are now supported by transition/modulation evidence:

```text
0x281.byte6  -> compressor demand % mirror
0x280.float0 -> commanded/requested compressor speed
0x384.float0 -> achieved/actual compressor speed
0x385.float1 -> compressor speed ceiling candidate
0x387.float0 -> fixed speed reference/limit candidate
0x3D0/3E0    -> minimum-speed limit family
```

Do not collapse these into one “compressor frequency” entity.

## UX360 / zone sensor family

| Field | Current meaning | Confidence |
|---|---|---|
| `0x490.float[0]` | Zone 1 / room temperature | Confirmed |
| `0x490.byte4` | humidity byte | Strong candidate; user-facing sensor filters >100 |
| `0x491..0x495.float[0]` | zone 2-6 temperature candidates | Candidate |
| `0x491..0x495.byte4` | zone 2-6 byte-4 candidates | Candidate |
| `0x4B1.u32` | epoch seconds | Confirmed |
| `0x4B2` | raw float pair | Raw |

The raw `0x490.byte4` diagnostic is intentionally preserved even though the friendly Indoor Humidity entity filters invalid values.

## Structured JSON profiles

Trane structured JSON is transported through CANopen SDO writes to object `0x300A:00`. See [CANOPEN-LINK-TRANSPORT.md](CANOPEN-LINK-TRANSPORT.md).

### `SystemOpStatus`

| Key | Current interpretation | Confidence |
|---|---|---|
| `A` | system state code | Observed; preserve raw |
| `B` | system mode code | Strong/observed |
| `C` | demand/stage text | Observed |
| `D` | System Demand Percent Candidate | Strong candidate; slower cadence than dedicated OdStatus demand |
| `E` | Indoor Humidity Mirror | Confirmed on target; 2026-10-03 matched `0x490.byte4` on 22/23 nearest updates (R² ~0.991, |r| ~0.996), including changes while compressor demand was zero |

Superseded: the old parser interpreted `SystemOpStatus.E` as outdoor temperature when decimal-formatted and humidity otherwise. Target captures disproved both meanings.

### `OdStatus`

| Key | Meaning |
|---|---|
| `A` | outdoor active flag |
| `B` | structured compressor-speed percentage |
| `C` | outdoor unit state code |
| `D` | outdoor fault code |
| `CompDemandPercent` | compressor demand percentage |

`OdStatus.B` correlates tightly with `0x280.float[0]`: 70-73% modulation implied a nearly constant ~58.05 RPS full-scale request.

### `IndoorStatus`

| Key | Meaning |
|---|---|
| `D` | indoor/blower operating-state family |
| `E` | blower-speed request/target percentage in normal operation; 2026-09-28/29 long-run data correlates it ~0.998-0.999 with the `0x200.u16@2` speed request at ~7.95-7.98 request units per percent. On clean starts E can already be 36-38% while blower feedback/power are still zero. Healthy starts also emit nonnumeric `TA_INV_HI`, so raw value is retained and nonnumeric E values must not be treated as faults. |
| `F` | raw/unknown |
| `HumControl` | humidity-control state |
| `HumidifierStatus` | humidifier status |
| `DehumidifierStatus` | dehumidifier status |
| `VentilatorStatus` | ventilator status |

A cooling-to-satisfied transition showed `D` changing running→stopped and `E` updating to 0 when the blower stopped.

### `ZoneStatus`

Observed keys include:

- `H` room temperature;
- `Hsp` / `Csp` active heat/cool setpoints;
- `HcStatus` heat/cool status code;
- `HoldText`;
- `E` airflow-like percentage;
- `F` zone state;
- `G` zone demand.

The friendly Room Temperature entity uses the live `0x490` frame so sparse structured updates do not leave it unavailable.

### Other observed objects

- `SpOverride`
- `PresetSettings`
- `ZoneSettings`
- `IndoorSettings`
- `SystemSettings`
- `ScheduleSettings`
- `ActiveAlarms`
- `Notifications`
- `VersionDetails`
- `ZoneCardState`
- `ZoningInfo`
- `WeatherData`
- `WeatherToday`
- `UnitID`
- `OutdoorSettings`
- `OdWidget`
- `Debug`

Structured snapshots have freshness ages because profile values may remain cached long after the last wire update.

## CANopen/network telemetry

Target-observed standard behavior:

- `0x000` — NMT;
- `0x701..0x705` — heartbeat/error-control nodes observed operational;
- `0x7E5/0x7E4` — LSS manager/server;
- `0x601/0x581`, `0x621/0x5A1`, `0x641/0x5C1`, `0x649/0x5C9` — SDO JSON pairs.

A complete LSS Fastscan capture reconstructed identity words:

- vendor ID `0x00000001`
- product code `0x00000004`
- revision `0x00000000`
- serial `0xC345985F`

followed by successful configuration/startup of node ID 3. Physical Trane product identity for CANopen node numbers remains intentionally unassigned until topology/disconnect evidence proves it.

## Superseded mappings

These names should not be reintroduced without new independent evidence:

| Old mapping | Why superseded |
|---|---|
| `0x383.float[1] = line voltage` | active capture showed ~400 while actual line source stayed ~237 V |
| `0x38F.float[0] = liquid pressure` | stable ~237-241 across operating states; behaves as line voltage |
| `0x385.float[0] = outdoor EEV position` | values ~1400-1500 track compressor/input power, not EEV steps |
| `0x387.float[0] = actual compressor speed` | remains 55 while compressor is stopped |
| `0x386.float[1] = vapor saturation temperature` | fixed ~50 across changing load |
| `0x460.float[0] = liquid saturation temperature` | does not track high-side pressure changes |
| `SystemOpStatus.E = outdoor temperature` | 2026-10-03 directly matches the indoor-humidity byte instead |
| `SystemOpStatus.E = compressor speed ceiling/reference` | 2026-10-03 changes 51-59 while compressor is often stopped and matches `0x490.byte4` on 22/23 nearest updates |
| `0x281.u16@6 = blower RPM` | it is only byte6/byte7 combined; bytes are separate demand/active fields |

## Still unresolved / high-value targets

Do not invent friendly names for these until captured against a known OEM value:

- confirm `0x381.float[1]` against synchronized Technician discharge-temperature telemetry;
- exact meaning of `0x386` fields;
- exact identity/scaling of `0x430.float[1]` and both `0x450` fields;
- exact meaning of `0x460.float[0]`;
- outdoor EEV command/position;
- both suction and liquid/high-side pressure with independently verified units;
- defrost state and reversing-valve state;
- A2L mitigation controller/sensor status and alarms;
- electric heat stage states;
- per-device model/serial/software mapping;
- native UX360 setpoint/mode write transaction.

## Control-write status

Receive-side SDO/JSON transport is well understood, but **application writes remain fail-closed**.

No capture to date has contained the originating stock UX360 JSON `Put` transaction for a setpoint change. Fresh `SpOverride.Update` messages have been captured, but those were profile/state hydration rather than the client write.

Required before enabling writes:

1. start capture before a physical UX360 mode/setpoint change;
2. capture the complete request-side SDO transaction;
3. identify exact request/response COB-ID pair and application Ack behavior;
4. implement a nonblocking CANopen SDO client for `0x300A:00`;
5. preserve timeout/abort/toggle/block-ACK handling and current safety gates.

## Evidence trail

Key dated evidence is indexed at [evidence/README.md](evidence/README.md).

The most current multi-capture active-cooling/requalification note is:

- [evidence/2026-09-22/outdoor-sensor-chain-long-pass.md](evidence/2026-09-22/outdoor-sensor-chain-long-pass.md)

Earlier 2026-09-17 notes are intentionally preserved because they document how current mappings were falsified and requalified.


### 2026-09-26 cooling-cycle qualification

Five independent AC Stage 1 cycles were captured with coherent startup,
modulation, shutdown, and blower coast-down. Across all five:

- `SystemOpStatus.C` changed to `AC Stage 1` at call start and back to `--`
  at shutdown;
- `OdStatus.C` was `A` during active cooling and `D` after shutdown;
- `IndoorStatus.D` was `B` while active and `A` after shutdown;
- `ZoneStatus.HcStatus` was `2` during cooling, briefly `4` during
  shutdown/coast, and `1` once idle;
- `IndoorStatus.E` emitted `TA_INV_HI` at healthy startup, then numeric
  values around 35-40 during operation, and 0 once stopped.

The pressure pair also behaves exactly as expected for low/high sides: before
startup `0x383.f0/f1` are nearly equal, then within 30 seconds the pair splits
by roughly 56-71 psi and by ~2 minutes the split is ~113-148 psi. After
shutdown the split collapses back toward equalization.

These transitions strongly reinforce the existing `0x383` suction/high-side
pressure mapping and show that `TA_INV_HI` is an operating-status
token, not a fault string.


### 2026-09-27 long-run blower requalification

The day contains nine compressor-running intervals, including one continuous
~83-minute cooling run and one `AC Stage 2` transition. The low-load startup
timing separates command from physical motor feedback:

- `0x281.u16@0` jumps to about 720 before blower current/power and `0x318`
  feedback leave zero, so it is not actual/delivered airflow;
- `0x200.u16@2` tracks numeric `IndoorStatus.E` at roughly 7.9 request
  units per percentage point (correlation about 0.99);
- `0x318.u16@4` remains zero until the blower actually starts, then follows
  request/modulation/coast-down and returns to zero with the motor;
- `0x318.u16@6` moves with blower operation but no longer has enough evidence
  to carry the primary speed/RPM label.

The maintained map therefore treats `0x200.u16@2` as the blower-speed request,
`0x318.u16@4` as the motor-speed feedback, and `0x281.u16@0` as an airflow
target/command candidate.


### 2026-09-28 low-suction protection cross-check

The first afternoon cooling cycle produced two short-lived OEM alarms:

- `Err 185.10`
- `Err 185.11`

Public Trane alert documentation identifies this 185.10/185.11 pair as
cooling low-suction-pressure protection states. In the capture, the sequence is
coherent with the bus telemetry:

- suction-pressure field `0x383.f0` falls to roughly 69-74;
- paired high-side `0x383.f1` remains roughly 266-274;
- compressor request is reduced from 45 RPS toward 20 RPS;
- the alarms clear within seconds while suction pressure recovers.

This independently confirms the **suction-pressure semantic** of
`0x383.f0`. It does **not** by itself prove whether the raw wire value is
gauge or absolute pressure, so the maintained names now deliberately avoid the
old `Absolute` wording.

The same day also contains a sustained `AC Stage 2` interval lasting about
66 minutes inside a ~93-minute cooling run. Compressor speed remains
continuously variable through the stage transition, reinforcing that the stage
text is supervisory demand/staging state rather than a discrete fixed-speed
compressor step.


### 2026-09-29 control-day confirmation

The full-day archive contains 16 compressor-running intervals, including long
runs of roughly 100 and 88 minutes, with no A2L/leak/defrost/heating JSON and
no repeat of the 2026-09-28 Err 185.10/185.11 low-suction protection event.
That makes 09/29 a useful clean control day for the prior mappings.

The structured blower field is better described as a request/target percent,
not actual speed:

- `IndoorStatus.E` correlates ~0.998 with `0x200.u16@2`;
- median scale is ~7.95 request units per percent;
- on clean starts E is already 36-38% while `0x318.u16@4` motor feedback and
  `0x320.f0` blower power are still zero.

The `0x385.f1` compressor speed-ceiling field also shows a repeatable literal
`65535` startup sentinel on multiple clean compressor starts. The entity now
filters values outside a sane 0-200 RPS range.

Two structured setpoint overrides were captured:

- 03:32:31 UTC: zone 1 cooling setpoint -> 77 F
- 13:17:41 UTC: zone 1 cooling setpoint -> 78 F

At 03:32:31, the override is followed about 3 seconds later by
`AC Stage 1`, and actual compressor speed leaves zero about 13 seconds after
the override. This is a useful end-to-end confirmation of the structured
setpoint/override decode path.

Two additional isolated stator-heat cycles bring the cumulative total to 66.


### 2026-09-30 exact-length JSON and control confirmation

The full-day archive contains 14 compressor-running intervals, including:

- a ~121-minute run beginning 03:00 UTC;
- a ~151-minute run beginning 17:39 UTC;
- a ~50-minute run beginning 22:44 UTC.

The first long run spends ~103.3 minutes in `AC Stage 2`; the second spends
~104.1 minutes in Stage 2 before returning to Stage 1, followed by two brief
Stage-2 re-entries. Compressor speed remains continuously variable throughout.

Blower command evidence remains stable:

- 148 numeric `IndoorStatus.E` / `0x200.u16@2` pairs;
- correlation ~0.996;
- median scale exactly ~8.0 request units per percent.

Four more clean starts emit the `0x385.f1 = 65535` startup sentinel, further
justifying the existing 0-200 RPS validity filter.

Two cooling-setpoint override transactions were again captured:

- 03:00:26 UTC -> 77 F;
- 12:39:36 UTC -> 78 F.

No A2L/leak, heating, defrost, reversing-valve, or 185.x pressure-protection
event appears in the structured stream.

Three isolated stator-heat cycles raise the cumulative project total to **69**.

#### Exact-length CANopen JSON transfer

One `DebugUI.HiHeapRemaining` transfer exposed a transport bug in the bridge.
The CANopen initiate request declares 42 bytes, exactly the UTF-8 JSON length:

```json
{"DebugUI":{"HiHeapRemaining":"33054720"}}
```

There is no trailing NUL. The previous receiver unconditionally subtracted one
from every indicated `0x300A:00` size and therefore emitted the JSON after
41 bytes, before the final closing brace arrived 12 ms later.

Firmware and the offline analyzer now preserve the indicated wire length and
accept both:

- exact-length JSON with no NUL; and
- JSON whose indicated size includes a trailing NUL.

This archive contains zero malformed JSONL records. The one malformed
`TRANE_JSON` payload was generated by the old receiver logic above and is the
regression fixture for the fix.


### 2026-10-01 repeated exact-length JSON and long-run confirmation

The full-day archive contains six compressor-running intervals:

- ~113 minutes beginning 01:59 UTC;
- ~6.6 minutes beginning 15:12 UTC;
- ~7.3 minutes beginning 17:34 UTC;
- ~167 minutes beginning 17:50 UTC;
- ~166 minutes beginning 20:44 UTC;
- ~9.7 minutes beginning 23:40 UTC.

The long runs contain sustained Stage 2 operation while compressor speed remains
continuously variable, again supporting supervisory demand/staging semantics.

Blower request evidence remains extremely stable:

- 184 numeric `IndoorStatus.E` / `0x200.u16@2` pairs;
- correlation ~0.999;
- median scale ~8.0 request units per percent.

Two more `0x385.f1 = 65535` startup sentinels were captured and are correctly
covered by the existing sanity filter.

Four isolated stator-heat cycles raise the cumulative total to **73**.

No A2L/leak, heating, defrost, reversing-valve, or 185.x pressure-protection
event appears in the structured stream.

#### Second exact-length/no-NUL JSON observation

At 23:21:59 UTC, a second independent `DebugUI.HiHeapRemaining` transfer uses
the same 42-byte exact-length/no-NUL form observed on 2026-09-30, this time with:

```json
{"DebugUI":{"HiHeapRemaining":"32538624"}}
```

The old receiver again emitted the payload one byte early because this archive
was captured before the optional-NUL transport fix was deployed. The raw CAN
contains the sixth/final segment immediately afterward with the missing brace.

The regression fixture now covers both independently captured heap values,
demonstrating that exact-length/no-NUL is a repeatable Trane wire form rather
than a one-off malformed sender.


### 2026-10-02 five-hour Stage 2 confirmation

The full-day archive contains nine compressor-running intervals. The standout
run is:

- compressor motion: ~17:06:20-22:51:38 UTC (~345.3 min / 5.75 h);
- structured Stage 2: ~17:21:14-22:39:30 UTC (~318.3 min / 5.30 h).

Actual compressor speed remains continuously variable throughout the sustained
Stage 2 interval and peaks around 58 RPS. This is the longest sustained
Stage-2-heavy run in the evidence set so far and strongly reinforces the
supervisory-demand/staging interpretation.

A second long run spans ~04:10:33-06:22:15 UTC (~131.7 min), with Stage 2
lasting ~119.4 minutes.

Blower request scaling remains stable across 232 numeric
`IndoorStatus.E` observations:

- correlation with `0x200.u16@2`: ~0.998;
- median scale: ~7.97 request units per percent.

Six additional clean compressor starts emit `0x385.f1 = 65535`, further
validating the existing 0-200 RPS sanity filter.

Two isolated stator-heat cycles raise the cumulative project total to **75**.

No A2L/leak, heating, defrost, reversing-valve, or 185.x low-suction-protection
event appears in the structured stream.

The pressure and unresolved outdoor families remain consistent:

- `0x383.f0/f1` continue to behave as suction/high-side pressure;
- `0x460.f0` remains strongly correlated with the outdoor power-electronics
  thermal family (~0.94 with `0x410` / `0x430.f0`);
- `0x430.f1` and both `0x450` fields remain unqualified.

The day contains many 42-byte `0x300A` transfers, but the observed examples
are NUL-terminated and parse cleanly. No exact-length/no-NUL DebugUI transfer
occurred on this day, so the 2026-09-30/10-01 regression evidence remains the
basis for that transport fix.


### 2026-10-03 stock setpoint transport

The full-day archive contains two stock `SpOverride.Put` writes on
`0x641/0x5C1`, both using CANopen block SDO download to `0x300A:00`,
followed by accepted-state broadcasts and application `{"Ack":"200"}`.
Both stock requests use `HoldType:"1"` and `Source:"1"`.

No stock mode-write transaction was observed. A qualified local writer may use
this evidence for setpoints only; mode and arbitrary JSON TX remain unqualified.
