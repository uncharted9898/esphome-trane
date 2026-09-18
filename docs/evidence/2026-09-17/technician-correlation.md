> **Historical evidence — 2026-09-17.** This is a point-in-time capture/requalification note. Some interpretations recorded below were later disproved or refined. For current authoritative meanings, use [../../TELEMETRY.md](../../TELEMETRY.md) and [../../CANOPEN-LINK-TRANSPORT.md](../../CANOPEN-LINK-TRANSPORT.md). Preserve this file as evidence; do not use an older friendly label when it conflicts with the current map.

# Target Technician correlation — 2026-09-17

> **Historical correlation warning:** several outdoor labels below were based on one nonsimultaneous Technician point and have since been requalified with additional target captures. In particular, `0x383.float[1]` is not line voltage, `0x38F.float[0]` is the leading line-voltage candidate, and `0x385.float[0]` is not a 500-step outdoor EEV position. Use `TARGET-HIGH-LOAD-REQUALIFICATION-2026-09-17.md` and `TARGET-COOL-AMBIENT-REQUALIFICATION-2026-09-17.md` for current conclusions.


This note correlates the target 5TAMXC03 / 5TWV0X24 Link capture with an older Trane Technician 3.4.0 Monitor screenshot supplied from the same installation.

The screenshot and capture are **not simultaneous**. Numeric agreement is therefore used only where the relationship is physically and structurally discriminating. Ambiguous channels remain candidates.

## Reference Technician monitor point

Older Technician screenshot, cooling / automatic verification:

### Outdoor

- suction pressure: 127 psig
- vapor saturation temperature: 49 F
- suction temperature: 66 F
- suction superheat: 17 F
- liquid pressure: 265 psig
- liquid saturation temperature: 90.2 F
- liquid temperature: 71 F
- subcool: 20.7 F
- line voltage: 239 V
- compressor speed: 3480 RPM = 58 RPS
- outdoor fan speed: 774 RPM
- ambient temperature: 69 F
- outdoor coil temperature: 74 F
- outdoor EEV position: 500 / 500
- compressor power: 1043 W
- drive DC voltage: 346 Vdc
- drive current average: 4 A
- compressor dome temperature: 132 F
- OD superheat: 18 F
- compressor target max speed: 33 RPS
- compressor target min speed: 20 RPS
- compressor target speed: 58 RPS
- inverter temperature: 131 F
- APFC temperature: 122 F
- input AC current: 5 A
- fan phase current: 0 A
- input power: 1210 W

### Indoor

- actual airflow: 803 CFM
- target airflow: 100%
- return-air temperature: 79 F
- supply-air temperature: 53 F
- temperature split: 26 F
- indoor EEV position: 181 / 500
- indoor evaporator/liquid temperature: 47 F
- indoor gas temperature: 65 F
- indoor superheat: 17 F
- total static pressure: 0.124 inWC
- blower speed: 529 RPM
- blower power: 77 W
- external switch 1: closed
- external switch 2: closed
- A2L sensor 1: not alarmed

Top-level thermostat reading was approximately 81 F / 57% RH.

## High-confidence indoor correlations

The target capture's steady cooling point contains approximately:

- `0x281.u16[0] = 660–662`
- `0x281.u16[3] = 356`
- `0x310.float[0] = 0.056–0.060`
- `0x320.float[0] = 24–26`
- `0x308.float[0] = 77 F`
- `0x308.float[1] = 54 F`
- `0x300.float[0] = 61–62`
- `0x300.float[1] = 49–50`
- `0x490.float[0] = 80 F`
- `0x490.byte[4] = 56`

### `0x281.u16[0]` — Actual Airflow CFM

Strong correlation. The current 660-ish value is in the correct range for the Technician Actual Airflow channel; historical start/stop captures show this word falling with blower operation rather than remaining constant.

### `0x281.u16[3]` — Blower Speed RPM

Effectively confirmed by the cross-operating-point fan-law check below.

### `0x310.float[0]` — Total Static Pressure, inWC

The old label `Return Static` should be removed. The value behaves like the Technician-displayed **Total Static Pressure**.

Fan-law validation using the two operating points:

- current: about 356 RPM and 0.0566 inWC
- Technician reference: 529 RPM and 0.124 inWC

For the same blower/system family, static pressure scales approximately with RPM squared:

`0.0566 * (529 / 356)^2 = 0.12498 inWC`

That is essentially the Technician value of 0.124 inWC.

### `0x320.float[0]` — Blower Power, W

The old `Motor Power Candidate` can be promoted to blower power.

Fan power scales approximately with RPM cubed:

`24.56 * (529 / 356)^3 = 80.6 W`

Technician showed 77 W. Given two nonsimultaneous operating points, this agreement is highly discriminating.

### `0x308` — Return / Supply Air Temperature

Strong/near-confirmed:

- float 0: Return Air Temp
- float 1: Supply Air Temp

Current capture is about 77 / 54 F; Technician reference is 79 / 53 F.

### `0x300` — Indoor Gas / Evaporator-Liquid temperatures

Strong candidate and a better fit than the earlier `0x283` ET/GT hypothesis:

- float 0: ID Gas Temp candidate
- float 1: ID Evap/Liquid Temp candidate
- float0 - float1: ID Superheat candidate

Current values are about 61.5 / 49.9 F. Technician reference is 65 / 47 F with about 17 F indoor superheat.

`0x283` should therefore be demoted to generic indoor temperature candidates until independently identified.

### `0x200.u16[0]` — Indoor EEV position candidate

New high-value channel. Current raw frames are typically `7C/7D 00 xx 01 00 00 00 00`, making the first word about 124–125 while the second word sits around 495–503.

Technician displays ID EEV position on a 0–500 scale and showed 181 / 500 in the older operating point. The first word is therefore a strong ID EEV-position candidate. Do **not** call the second word the denominator/max: it varies around 500 and may instead be target/command/calibration state.

### `0x490` — Zone 1 room temperature + RH

Very strong:

- float 0: Zone 1 / thermostat room temperature
- byte 4: relative humidity candidate

Current is exactly 80 F / 56; older Technician top-level display was about 81 F / 57% RH. `0x491`–`0x495` remain at the unused-zone-looking 70 / 50 defaults on this single-zone installation.

## High-confidence outdoor correlations

### `0x381`

Strong pair:

- float 0: Suction Temperature — already exposed by the older decoder and remains plausible
- float 1: **Suction Pressure**, psi

Current is about 69.5 F / 121 psi. Technician reference is 66 F / 127 psi.

### `0x38F.float[0]` — Liquid Pressure, psi

Promote generic refrigerant pressure to liquid pressure. Current is 240–241 psi; Technician reference is 265 psi.

### `0x383.float[1]` — Line Voltage, VAC

Current is about 236–238 V; Technician reference is 239 V.

### `0x384.u16[2]` — Drive DC Voltage, Vdc

Current is about 349–356 Vdc; Technician reference is 346 Vdc. This also has the expected relationship to approximately 238 VAC input with an active-PFC drive.

### `0x384.u16[3]` — Outdoor Fan Speed, RPM

Current is about 648–660 RPM; Technician reference is 774 RPM.

### `0x387.float[0]` — Actual Compressor Speed, RPS

Current is 55 RPS, equivalent to 3300 RPM. Technician reference is 3480 RPM = 58 RPS.

The old temperature label on this field is wrong.

### `0x385.float[0]` — Outdoor EEV Position / Steps

Current is about 373–383 steps on a 500-step system. Technician reference showed 500 / 500. Keep the denominator as a known UI/mechanism scale, not as `0x385.float[1]`.

### `0x385.float[1]` — Compressor Target Speed candidate, RPS

The second float moves around 47–51 while actual compressor speed is around 55 RPS. This is much more consistent with the Technician `Comp Target Speed` field than with a second EEV-position value. Rename the old `EEV Position` candidate accordingly, but retain candidate status until a synchronized monitor point is captured.

### `0x389.float[1]` — Input AC Current candidate, A

Current is about 2.0–2.1 A.

### `0x38C.float[1]` — Input Power, W

Current is about 472–500 W. Combined with `0x383.float[1] ~= 238 V` and `0x389.float[1] ~= 2.0–2.1 A`, the electrical relationship is striking:

- `238.43 V * 2.10 A = 500.7 VA`, while `0x38C` reports about 500 W;
- `238.43 V * 2.00 A = 476.9 VA`, while nearby `0x38C` values are about 480 W.

This substantially upgrades both the line-voltage/current/power mapping confidence.

### `0x460.float[0]` — Liquid Saturation Temperature candidate

Current is about 86.19 F while liquid pressure is about 240 psi. Technician reference showed 90.2 F at 265 psi. This is the strongest current candidate for the liquid saturation-temperature field and should be retained explicitly.

## Medium-confidence outdoor channels

### `0x382`

Current values are about 65.1 and 69.0 F. The old Technician monitor separately shows suction temp, liquid temp, and OD coil temp. Since `0x381.float[0]` already remains a strong suction-temperature mapping, the current leading hypotheses are:

- `0x382.float[0]`: Liquid Temp candidate
- `0x382.float[1]`: OD Coil Temp candidate

Do not promote these two until a synchronized Technician snapshot is available.

### `0x383.float[0]`

About 150 F currently; older Technician showed Compressor Dome Temp 132 F. Compressor dome/discharge temperature is the leading interpretation. Keep `Compressor Dome/Discharge Temperature` wording until the exact OEM field is synchronized.

### `0x384.float[0]`

About 30–31. The older Technician reference showed Comp Target Max Speed = 33 RPS. This is a strong numeric candidate, but the OEM monitor's target-min/max semantics are odd because the displayed target/actual speed may exceed that value. Keep candidate status.

### `0x387.float[1]`

About 0.3. Fan Phase Current is a plausible candidate, but do not promote yet.

### `0x388.float[0..1]`, `0x389.float[0]`

About 2.5 A at the current operating point. These likely include MOC/drive current metrics. More synchronized Technician current values are needed to distinguish drive-current average from phase/current channels.

### `0x410`

Both floats are near 100 F at the current lower electrical load. Drive IPM / APFC temperature is plausible because Technician exposes both and the older higher-load point showed 131 / 122 F. Exact ordering is unresolved.

### `0x3D0` / `0x3E0`

Both carry the same approximately 20.28 value, with `0x3E0` appending a status-like byte of `01`. This could match several older Technician values near 20 (target min speed, OD superheat, or subcool), so it must remain raw until a synchronized monitor point separates them.

## Corrections to make in the HA surface

1. Rename `0x310 ... Return Static` to **Total Static Pressure** and give it `inWC`.
2. Rename `0x320 ... Motor Power` to **Blower Power** and give it `W`.
3. Rename `0x281 word3 ... Actual Speed` to **Blower Speed** and give it `rpm`.
4. Retain `0x281 word0` as **Actual Airflow** in CFM.
5. Demote `0x281 word1 Target Airflow`: historical shutdown traces left this at 500 while the blower stopped, so its exact meaning remains unresolved.
6. Promote `0x308` to Return / Supply Air Temp.
7. Add `0x300` Gas Temp / Evap-Liquid Temp / derived ID Superheat candidates.
8. Demote `0x283 ET GT` to generic raw indoor temperature candidates.
9. Add `0x200 word0` ID EEV Position candidate and retain word1 separately/raw.
10. Promote `0x381 float1` to Suction Pressure.
11. Promote `0x38F float0` to Liquid Pressure.
12. Promote `0x383 float1` to Line Voltage.
13. Promote `0x384 words 2/3` to Drive DC Voltage / OD Fan Speed.
14. Rename `0x387 float0` from temperature to Actual Compressor Speed RPS; optionally expose RPM = RPS * 60.
15. Keep `0x385 float0` as OD EEV steps and reinterpret float1 as Compressor Target Speed candidate.
16. Promote `0x38C float1` to Input Power and `0x389 float1` to Input AC Current candidate.
17. Add `0x460 float0` Liquid Saturation Temperature candidate.
18. Promote `0x490` temperature/RH as a reliable raw fallback for room temperature and humidity.
19. Remove temperature semantics from `0x430` / `0x450`; current values near 300 make those labels demonstrably unsafe.
20. Keep A2L status raw. The old screenshot proves a first-class `A2L Sensor 1: NOT ALARMED` monitor value exists, but this capture does not yet prove which raw ID carries it.

## Why the structured-profile entities are blank in this capture

The current HA table shows only four retained JSON roots and many boot/profile-backed fields are blank. That is expected when the new snapshot firmware attaches after the one-shot startup profile exchange: it can retain only structured objects observed after it starts. With application TX disabled, it also cannot actively request the missing profiles.

A cold UX360/SC360 profile exchange while the listener is already running should populate the one-shot profile cache without requiring semantic guesses.
