# Target CAN census — 2026-09-17

> **Superseded mapping warning:** This document predates the later cool-ambient requalification and standards-backed SDO/LSS decode. Its raw payload/cadence observations remain useful, but older labels such as `0x281.word3 = blower RPM`, `0x383.float1 = line voltage`, `0x385 = outdoor EEV`, saturation-temperature guesses, and the unresolved `0x7E4/0x7E5` interpretation are superseded. Current conclusions live in `TARGET-COOL-AMBIENT-REQUALIFICATION-2026-09-17.md`, `CANOPEN-LINK-TRANSPORT.md`, and `TARGET-CANOPEN-LSS-FASTSCAN-2026-09-17.md`.

This pass analyzes the 62.338-second target capture collected from the installed 5TAMXC03 / 5TWV0X24 / UX360 / SC360 system. It contains 1,938 standard CAN frames across 78 unique 11-bit IDs.

The purpose of this note is to separate three very different things that were previously all shown as `Unclassified CAN Frames`:

1. telemetry already correlated to Technician Monitor fields;
2. target-observed fixed/status/transport families whose exact byte semantics are not yet promoted;
3. genuinely novel CAN IDs.

`known` therefore means **classified as target Trane Link traffic**, not `every byte is semantically decoded`.

## Stronger correlations from this capture

### Indoor airflow command / target family

`0x281` is a four-word little-endian frame. During this capture it is approximately:

- word 0: 630–633 — Actual Airflow, CFM
- word 1: 500 — stable command/target candidate
- word 2: 0
- word 3: 356 — Blower Speed, RPM

An earlier live capture is important here: structured `IndoorStatus.E` was 63–64 while `0x281.word1` remained 500. The older Technician point also showed a distinct `Target Airflow %` concept, while the Technician schema evidence contains separate actual/requested/target airflow concepts.

That makes two interpretations possible:

1. raw 500 could be a five-count-per-percent encoding; or
2. raw 500 could be target/requested airflow in CFM, with the structured ~63% value being a separately normalized command. On an approximately 800-CFM nominal point, 500 CFM is 62.5%, strikingly close to the observed 63–64 structured value.

The second interpretation currently has the better cross-capture fit. Preserve word1 as a target/requested-airflow candidate rather than hard-code a `/5` conversion. A deliberate blower command sweep is required to distinguish target CFM, requested CFM, and normalized percent cleanly.

The `0x318` trailing words make this family more interesting: bytes 4..5 move around 474–505 across captures, while bytes 6..7 move around 336–356. Those values correlate strongly with blower power and may be additional requested/target airflow and motor-speed fields. They remain raw until the sweep separates them.

### Outdoor superheat and subcool remain independently derivable

At this capture point:

- suction temperature (`0x381.float0`) ~= 68.61–68.66 F
- vapor saturation temperature candidate (`0x386.float1`) = 50.00 F
- derived OD superheat ~= 18.61–18.66 F
- liquid saturation temperature candidate (`0x460.float0`) ~= 85.72–85.75 F
- liquid temperature candidate (`0x382.float0`) ~= 64.91–65.01 F
- derived OD subcool ~= 20.71–20.82 F

These calculations are useful cross-checks but should remain derived values until a synchronized Technician point confirms the underlying temperature mappings.

### 0x3D0 / 0x3E0 — compressor target-min-speed candidate

`0x3D0.float1` and `0x3E0.float0` carry the same sparse value, 20.065–20.100. `0x3E0` appends status byte `01`.

The first-pass temptation was to call this subcool because the derived OD subcool happens to be about 20.7–20.8 F in this operating point. The older Technician Monitor reference provides a substantially better discriminator: **Comp Target Min Speed = 20 RPS**. A slow-moving control value of about 20.08 is therefore a much stronger fit for target minimum compressor speed than for refrigerant subcool.

Current confidence:

- `0x3D0.float1`: Compressor Target Min Speed candidate, RPS
- `0x3E0.float0`: duplicate Compressor Target Min Speed candidate, RPS
- `0x3E0.byte4`: associated status candidate (`01` in this capture)

Do not use 0x3D0/0x3E0 as the subcool measurement. Keep subcool independently derived from liquid saturation minus liquid temperature until direct Technician correlation is available.

### 0x601 / 0x581 segmented transport

The capture proves a third segmented JSON application channel in addition to 0x641/0x649.

Observed 0x601 message 1:

- header: `C2 0A 30 00 25 00 00 00`
- wire length: 37 bytes including trailing NUL
- JSON length: 36 bytes
- payload: `{"Debug":{"IDBLE":"NOTADVERTISING"}}`

Observed 0x601 message 2:

- payload: `{"Debug":{"IDBLE":"ADVERTISING"}}`

0x581 carries companion A0/A1/A2-style control frames around those 0x601 transfers. Exact 0x581 control semantics are not promoted yet.

The receive transport now treats 0x601 as a read-only segmented JSON source using the same target framing decoder as 0x641/0x649. `Debug.IDBLE` should be surfaced as a diagnostic state without assuming which physical node owns it until a topology capture proves the sender.

## Full target-observed census

### Moving / telemetry-rich

| ID | Frames | Unique payloads | Current interpretation |
| --- | ---: | ---: | --- |
| 0x200 | 31 | 7 | ID EEV position candidate + second changing word |
| 0x281 | 30 | 3 | actual airflow / target-or-requested airflow candidate / raw / blower RPM |
| 0x283 | 31 | 3 | two indoor Celsius temperature channels, exact semantics unresolved |
| 0x2D0 | 31 | 2 | status family; one small field incremented 0x0D -> 0x0E |
| 0x300 | 36 | 34 | ID gas / evap-liquid temperature candidates |
| 0x308 | 32 | 4 | return / supply air temperatures |
| 0x310 | 20 | 10 | total static pressure; second float fixed -99 sentinel |
| 0x318 | 20 | 10 | compound indoor frame; float0 fixed 0.396972656, trailing words 474–482 / 336–339 |
| 0x320 | 20 | 6 | blower power |
| 0x380 | 31 | 3 | -99 sentinel / outdoor air temperature |
| 0x381 | 31 | 3 | suction temperature / suction pressure |
| 0x382 | 32 | 5 | liquid-temperature candidate / OD-coil-temperature candidate |
| 0x384 | 53 | 19 | target-max-speed candidate / DC bus / OD fan RPM |
| 0x385 | 41 | 4 | OD EEV steps / compressor-target-speed candidate |
| 0x38C | 58 | 19 | zero / input power |
| 0x38F | 32 | 2 | liquid pressure / ~1.8–1.9 secondary value |
| 0x3D0 | 3 | 3 | zero / compressor target-min-speed candidate |
| 0x3E0 | 3 | 3 | compressor target-min-speed candidate + byte status 1 |
| 0x410 | 4 | 4 | two ~99–100 F drive-temperature candidates |
| 0x430 | 12 | 12 | float0 ~98.28; float1 ~298–340, exact semantics unresolved |
| 0x450 | 12 | 12 | two dynamic ~272–316 / ~294–304 scalar channels; not safe to label temperatures |
| 0x460 | 13 | 2 | liquid saturation temperature candidate / zero |
| 0x4B1 | 30 | 2 | epoch seconds |
| 0x601 | 15 | 13 | segmented JSON Debug transport |
| 0x581 | 6 | 5 | companion control/transport around 0x601 |

### Stable during this run

These IDs are not `unknown noise`; they are recurring target Link status/config/heartbeat frames. The capture does not provide enough state variation to assign exact byte semantics:

- `0x201 = 00 01 01 00 00 00 00`
- `0x203 = 00 00`
- `0x208 = 00 00 00 00 00`
- `0x20D = 00 00 00 00`
- `0x240 = 00 3C 00`
- `0x250`, `0x251`, `0x252 = 64 64 64 00`
- `0x260 = 00 00 00 00 00 00 00 00`
- `0x261 = 00 00 00 00 00`
- `0x262 = 00`
- `0x280 = 29.41 / 0.25` as two floats; static in this run but 30.71 / 0.25 in an earlier operating point, so it remains a candidate telemetry frame
- `0x282 = 00 00 03 02 01 00 00 00`
- `0x284 = 00 00`
- `0x285 = 00`
- `0x2D1 = 00 00 00 00 00 00`
- `0x2D2 = 00 00 00 00`
- `0x328 = 00 00 C6 C2 00 01 01 00`
- `0x330 = 00 00 00 00`
- `0x383 = 149.739 / 233.232` as floats: dome/discharge-temperature candidate + line voltage
- `0x386 = 2.0 / 50.0`
- `0x387 = 55.0 / 0.3`
- `0x388 = 2.4 / 2.4`
- `0x389 = 2.4 / 1.9`
- `0x38A = 00 00 00 00`
- `0x38B = 00 00 00 00 00 00 00 00`
- `0x38D = 00 00 00 00 00 00 01 00`
- `0x38E = 00`
- `0x420 = 00 00 00 00 2D 00`
- `0x490 = 79 F / 56% RH`
- `0x491`–`0x495 = 70 F / 50` unused-zone-looking defaults on this single-zone install
- `0x4B0 = 00 00 00 00 00`
- `0x4B2 = 70.0 / 70.0`
- `0x4B3 = 00`
- `0x4B4 = 23`
- `0x4C0`–`0x4C5 = 00 00 00 00 00`
- `0x53D = 01 00 00 00 00`
- `0x53E = 00 00 00 00 01 05`
- `0x701`–`0x705 = 05`, approximately five-second heartbeat/status traffic
- `0x7E5 = 51 00 00 00 00 80 00 00`

Do not assign A2L/mitigation semantics to 0x53D/0x53E or any other stable family solely because an A2L node is installed. The capture proves presence and cadence, not ownership or meaning.

## 0x318 warning and new torque hypothesis

The earlier `External Static` guess was incorrect and has already been removed. In this capture:

- float at bytes 0..3 is exactly `0.39697265625` for the entire run;
- bytes 4..5 interpreted as LE U16 move 474–482;
- bytes 6..7 interpreted as LE U16 move 336–339.

Across the earlier and current captures, `0x318.float0` tracks blower electrical power unusually well: roughly 0.397–0.430 while `0x320` moves about 22.6–26.0 W at a reported 356 RPM. If the float were motor torque in N·m, `torque * angular_speed` gives roughly 14.8–16.0 W mechanical, corresponding to a plausible ~62–65% operating efficiency for this small ECM point.

That is an interesting **torque hypothesis**, not a promoted mapping. The trailing words also correlate strongly with blower power and need a deliberate blower-speed sweep to distinguish command, speed, torque/current, and airflow-related fields.

## Why the old Unclassified counter was misleading

The Home Assistant all-frame callback had a historical hard-coded `switch` containing only a small early subset of known IDs. Newer target mappings such as 0x200/0x281/0x300/0x310/0x318/0x320/0x382/0x384/0x385/0x388/0x389/0x38C/0x3D0/0x3E0/0x460 still incremented `Unclassified CAN Frames` even while their decoded entities were displayed elsewhere.

The target transport now owns the authoritative `is_known_trane_id()` classification and the HA callback consults that same classifier. All 78 standard CAN IDs in this capture are covered by the target-observed classifier. Target-observed but not fully decoded families are classified as known Link traffic while their byte semantics remain raw/candidate. A future genuinely unseen ID therefore remains useful discovery signal instead of being buried under thousands of ordinary heartbeat/telemetry frames.

## Remaining qualification work

The highest-value remaining captures are deliberately state-changing rather than simply longer steady-state logs:

1. cold boot with listener already active, to retain full 0x5C1/0x5C9 and structured profile exchanges;
2. synchronized Technician Monitor + CAN while compressor speed changes materially;
3. indoor blower airflow/static sweep to resolve 0x318 and distinguish requested/target airflow from normalized percent in 0x281;
4. a natural A2L/mitigation self-test or documented state change to identify the mitigation-board frames without inducing a refrigerant leak;
5. natural defrost / heat-mode capture to distinguish refrigerant-temperature and valve/status channels that are degenerate in steady cooling.
