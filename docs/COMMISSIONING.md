# Trane Link bridge commissioning

Reference board: Waveshare ESP32-S3-RS485-CAN

Target architecture: parallel CAN tap. UX360 remains installed and usable. SC360 remains authoritative. The bridge must be removable without changing normal HVAC operation.

See `docs/TELEMETRY.md` for the current confidence/provenance map and `docs/WIRING.md` for the Waveshare connection and bus-topology diagrams. Installation-day captures should preserve raw evidence even when an existing friendly entity name is wrong or ambiguous.

## 0. Before connecting anything

1. Confirm the Waveshare CAN 120 ohm jumper is open/disabled.
2. With the bridge disconnected and HVAC power off, measure DH to DL at the system. Record the resistance; do not add another termination resistor.
3. Power the Waveshare from USB-C for first commissioning.
4. Connect only CAN H -> DH and CAN L -> DL.
5. Do not connect Trane R/B to the Waveshare CAN terminal side.
6. Keep the Waveshare as a short parallel tap. Do not put it in series with an OEM device.
7. Record the installed model/serial/software information visible on UX360 equipment summary before interpreting any `UnitID` payload.
8. Record the installed BAYEA heater model/size and the UX360 heater configuration.

## 1. Preferred commissioning firmware

For Home Assistant ESPHome Device Builder, use `waveshare-trane-homeassistant.yaml`.

For a repo-local build, use `waveshare-trane-commissioning.yaml`.

While tracking the moving `dev` branch, keep remote ESPHome packages/components at `refresh: always`. ESPHome caches remote `packages:` separately from per-device build files, so a normal "Clean Build Files" does not necessarily refresh a stale Git checkout. If a build log says `Skipping update ... refresh: 1d`, that build is intentionally reusing cached package source rather than current `dev`.

Expected behavior:

- GPIO17 = CAN TX into the Waveshare onboard CAN interface.
- GPIO18 = CAN RX from the onboard CAN interface.
- GPIO15/GPIO16 are not the onboard CAN pair for this board.
- 50 kbit/s.
- ESP32 TWAI mode = NORMAL.
- The CAN controller participates normally in arbitration and ACKs valid received frames.
- `trane_bus.tx_enabled = false`.
- raw JSON TX disabled.
- no Trane application command is sent merely because the CAN controller is in NORMAL mode.
- bounded RAM capture enabled.
- continuous `TRANE_CAN_LIVE` logging can be retained by the host for effectively unlimited capture.

This is preferred over hardware LISTENONLY for first commissioning because a LISTENONLY controller does not ACK bus frames and can therefore make the observed bus behave differently from the eventual installed bridge.

`waveshare-trane-listenonly.yaml` remains available as a diagnostic fallback when a true no-ACK CAN observer is specifically needed.

Acceptance checks:

- UX360 continues to operate normally.
- No new HVAC fault appears after attaching CAN H/L.
- SC360 traffic is detected.
- 0x649 traffic is visible.
- 0x5C1/0x5C9 activity appears during UX360 interactions/reboot.
- outdoor 0x380-0x38F family appears.
- indoor/air-handler traffic appears.
- previously unknown standard CAN IDs are retained in the capture ring rather than discarded.
- `Trane TX Messages` remains 0 unless application TX is explicitly enabled in a later control profile.

## 2. Establish a bus census before decoding anything new

The target R-454B system contains hardware not present in the original upstream capture set, especially the refrigerant-detection/mitigation subsystem. Do not assume the old CAN-ID inventory is complete.

Capture at least 60 seconds of stable idle traffic and build an ID census containing:

- CAN ID;
- DLC;
- frame count;
- approximate period/rate;
- whether payload is static or changing;
- whether the ID existed in the upstream map;
- probable node only when evidence supports it.

Then repeat the census immediately after a full system cold boot. Pay special attention to IDs that appear only during startup because those may be discovery, identity, configuration, or mitigation-controller traffic.

The capture ring intentionally records all standard CAN frames, not only currently known Trane IDs.

## 3. Capture workflow

The Home Assistant profile continuously emits raw frames as `TRANE_CAN_LIVE`. Save the ESPHome logger output on the host whenever possible.

For a controlled event:

1. Start/save the host logger before the event.
2. Wait for a short stable baseline.
3. Perform **one** UX360/system operation.
4. Keep recording through the complete response and a short stable period afterward.
5. Note the exact event timestamp.
6. Preserve the resulting log and any corresponding UX360 diagnostic values.

If using a profile that exposes the RAM capture controls, a freeze/dump of the ring can be retained as a secondary artifact.

Do not change two service/test variables at once. Correlation quality matters more than capture quantity.

For every capture note:

- local timestamp and timezone;
- HVAC mode;
- room temperature and humidity;
- heat/cool setpoints;
- outdoor temperature;
- UX360 screen/test state;
- requested compressor demand, if a test mode is active;
- displayed/reported compressor speed if available;
- selected/requested blower CFM, if applicable;
- blower percent if displayed;
- indoor heat stage;
- aux/emergency-heat indication;
- active alarms;
- Diagnostics/UX360 monitor values relevant to the test;
- capture filename/hash or other durable identifier.

## 4. Highest-value install-day captures

### 4.1 Full cold boot / profile exchange

This is the most important capture.

Start recording before HVAC power is applied and continue until the UX360 is fully operational and traffic has settled.

The 0x5C1/0x5C9 private UX360-SC360 transport has been observed carrying the boot-time profile exchange. Look for:

- all communicating node IDs;
- model/serial/software identity for UX360, SC360, 5TAMX, 5TWV0X and mitigation/A2L hardware;
- heater type/model/size;
- system configuration;
- setpoints/mode;
- complete alarms/history sent during startup;
- configuration/profile objects that disappear after delta-update mode begins.

Do not transmit a private-channel request yet; first recover the target-system framing from captures.

### 4.2 Blower CFM sweep

The UX360/Diagnostics service interface can command known blower CFM in `Test Blower` mode. This is the cleanest way to identify real airflow telemetry.

Capture separate runs at several valid CFM points for this air handler, for example:

1. a low permitted airflow;
2. a midrange airflow;
3. the normal design cooling airflow;
4. a higher permitted airflow.

Use the exact values shown/selected by UX360 rather than assuming a generic range.

Correlate:

- requested CFM;
- actual CFM, if separately reported;
- `IndoorStatus.E` blower percent;
- 0x490 multiplex channels;
- 0x283/0x308 indoor values;
- any changing motor/load/static-pressure candidate.

### 4.3 Compressor cooling demand sweep

Use UX360 `Test Compressor Cool` at known demand percentages within the available range.

Capture several points such as minimum, a mid point, and a high point while remaining within normal service-test constraints.

Correlate:

- `OdStatus.CompDemandPercent`;
- `OdStatus.B` — expected compressor **speed percent**, not Hz;
- outdoor unit state;
- 0x380-0x38F raw floats;
- suction/liquid pressures;
- suction/liquid/coil/discharge/dome temperatures;
- indoor blower CFM;
- outdoor fan/EEV candidates.

This test should let us decisively separate commanded compressor demand from actual compressor response.

### 4.4 Compressor heating demand sweep

When ambient/system conditions allow, repeat the same process with UX360 `Test Compressor Heat`.

Heating-mode comparison is useful for identifying:

- reversing-valve/state fields;
- pressure-channel identity;
- suction/liquid temperature identity;
- outdoor EEV behavior;
- heating airflow mapping.

### 4.5 Electric indoor heat stages

Use UX360 `Test Indoor Heat` and capture stage 1 first. Only capture stage 2/3 if those stages are actually available for the installed BAYEA heater configuration.

For each stage record:

- exact `SystemOpStatus.C` text;
- `SystemOpStatus.A/B`;
- `ZoneStatus.HcStatus`;
- `IndoorStatus` fields;
- requested/actual CFM;
- return/supply temperature rise;
- any heater configuration/state object;
- every CAN ID/payload that changes.

Do **not** assume the upstream gas-system `ID Stage 1/2` strings will be reused for electric heat.

### 4.6 Fan-only / circulate

Capture UX360 fan `On` and `Circ` operation separately if available.

This is needed because the upstream implementation never established a safe/real fan-only control mapping. It also cleanly separates blower telemetry from compressor/heat telemetry.

### 4.7 Dehumidification / humidity-control transition

If the system invokes dehumidification naturally or a safe installer test exposes it, capture the transition.

Correlate:

- `HumControl`;
- `DehumidifierStatus`;
- compressor demand/speed;
- airflow reduction;
- indoor humidity;
- any setpoint or configuration delta.

### 4.8 Natural defrost

Prefer a natural defrost event rather than forcing one solely for protocol research.

Record several minutes before defrost, the full defrost, supplemental-heat interval, and several minutes after recovery.

The 5TAMX sequence of operation states that the outdoor unit sends a defrost message to the air-handler control. The air handler then changes EEV/superheat behavior and may energize electric/hydronic heat to temper the air. Therefore we expect a distinct bus signature.

Correlate:

- outdoor defrost state/message;
- compressor demand/speed;
- reversing-valve state candidate;
- indoor supplemental electric-heat stage;
- blower CFM;
- indoor EEV behavior;
- suction/liquid pressure;
- outdoor coil, suction, liquid and discharge/dome temperatures;
- `SystemOpStatus` and `HcStatus` transitions.

### 4.9 Required A2L/refrigerant-mitigation verification

The R-454B 5TAMX has a refrigerant-detection/mitigation controller. Trane documentation describes communicating mode, CAN-loss indication, node count, sensor faults and leak/mitigation alarm state.

If the installer performs the required mitigation verification, record it **passively** from start through full recovery.

Look especially for:

- previously unknown CAN IDs;
- a new node at startup;
- refrigerant sensor state;
- sensor communication fault/state;
- leak-detected/mitigation-active state;
- forced dilution-airflow command;
- compressor-disable message;
- past-alarm/history delta after the test.

Do not create an additional mitigation event just for reverse engineering if the required commissioning verification has already provided the needed capture.

### 4.10 Optional indoor EEV service tests

5TAMX service modes include fully-open and fully-closed indoor EEV tests. The close test can intentionally drive pressure low and may produce a fault. These are technician/service tests, not routine protocol-discovery steps.

If a qualified technician runs them for legitimate commissioning/service reasons, capture them because they can identify:

- EEV command/position;
- ET/GT sensor pair;
- target vs actual superheat;
- suction pressure;
- low-pressure protection/fault fields.

## 5. Raw telemetry questions to answer on this exact system

Do not trust the friendly names until these are closed:

1. Is `OdStatus.B` actual compressor speed percent on 5TWV0X as it was documented upstream?
2. Which outdoor frame is suction temperature?
3. Which outdoor frame is outdoor-coil temperature?
4. Which frame is liquid temperature?
5. Which frame is discharge/dome temperature?
6. Which frame/field is suction pressure?
7. Which frame/field is liquid/high-side pressure?
8. What are 0x386 float 1, 0x386 float 2 and 0x387 float 1 independently?
9. Are the two 0x283 values the 5TAMX ET/GT thermistors?
10. Are 0x308 values truly return-air and supply-air temperature?
11. What are 0x410/0x430/0x450?
12. What does 0x490 byte/channel selection mean?
13. Where is requested and/or actual blower CFM?
14. Is external/static pressure exposed anywhere?
15. Where are indoor and outdoor EEV position/command?
16. Where are target and actual superheat?
17. What exact field(s) represent electric heat stages 1-3?
18. What exact field represents emergency heat?
19. What exact field represents defrost?
20. What CAN node/IDs belong to the A2L mitigation controller?
21. Where are per-device model/serial/software identities carried?
22. Where is heater size/model/configuration carried?
23. Are aux-heat lockout, compressor lockout and airflow settings present in profile data?

## 6. General all-electric operating capture matrix

In addition to controlled service-test captures, record normal operation:

1. idle/standby;
2. cooling startup;
3. cooling modulation;
4. cooling shutdown/coastdown;
5. heat-pump heating startup;
6. heating modulation;
7. heating shutdown;
8. auxiliary electric heat stage 1;
9. auxiliary electric heat stage 2/3 if configured;
10. emergency heat;
11. fan-only/circulate;
12. dehumidification;
13. schedule transition;
14. manual/timed hold;
15. UX360 reboot;
16. SC360 reboot;
17. full system power restoration;
18. natural defrost;
19. defrost plus supplemental electric heat;
20. installer-required A2L mitigation verification;
21. safe service/fault conditions encountered naturally or during legitimate commissioning.

## 7. Guarded local control

After monitoring is clean, `waveshare-trane-full.yaml` provides the guarded local-control surface.

At startup:

- TWAI remains NORMAL;
- Trane application TX starts disabled;
- raw JSON remains disabled;
- decoded telemetry continues working;
- the SC360 remains authoritative.

The `Local Trane Control` switch restores OFF after every reboot.

It may only enable if recent SC360 traffic has been observed. Even after enabled, command transport:

- validates supported modes;
- validates setpoint ranges/deadband;
- blocks a second write while waiting for ACK;
- times out a missing ACK;
- keeps SC360-reported state authoritative;
- does not continuously reassert Home Assistant state.

Do not expose emergency heat, auto, fan-only, electric-stage control, defrost control, EEV control, or other service functions as normal local commands until their target-system semantics are captured and reviewed.

## 8. First command sequence

Use a low-risk sequence while physically present at the equipment.

1. Request `SYSOP` profile only after its command path is confirmed compatible with the target system.
2. Confirm SC360 traffic is fresh.
3. Enable `Local Trane Control`.
4. Change one setpoint by 1 F.
5. Confirm CAN ACK 200.
6. Confirm the UX360 updates to the same setpoint.
7. Confirm the SC360 broadcast updates and Home Assistant reflects it.
8. Change the value back from the UX360 and confirm Home Assistant follows without the bridge fighting the thermostat.
9. Test heat/cool/off commands one at a time only after setpoint coexistence is proven.

## 9. Failure tests

All must pass before treating the bridge as production-ready.

- unplug bridge USB power while HVAC is running;
- reboot bridge;
- disable Wi-Fi;
- disable Home Assistant;
- reboot Home Assistant;
- disconnect LAN;
- use UX360 while bridge is online;
- issue a command then immediately change it at UX360;
- simulate an ACK timeout without repeated writes;
- leave bridge powered with local control switch OFF.

Expected result: HVAC and UX360/SC360 continue normally in every case.

## 10. Permanent power

Do not apply Trane 24 VAC directly to the Waveshare DC input.

Use an appropriately rated 24 VAC -> DC converter and feed the board within its documented DC input range. Keep the bridge electrically parallel to, never inline with, the Trane Link bus.
