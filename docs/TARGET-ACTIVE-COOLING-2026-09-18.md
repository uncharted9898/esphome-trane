# Target active-cooling capture — 2026-09-18

Target system:

- 5TWV0X24A1000B outdoor unit
- 5TAMXC03AV31DB air handler
- UX360 / SC360 controls
- passive Waveshare Trane Link bridge, application TX disabled

This note covers the active-cooling captures taken around 14:32–14:34 local time.

## Operating state

The Home Assistant snapshot shows a strong cooling call:

- room temperature: 79 F
- cool setpoint: 78 F
- compressor demand: 100%
- compressor speed: 99% (structured status)
- system demand stage: AC Stage 2
- zone 1 airflow: 100%
- indoor blower status: 82%
- return air: about 78.5–78.7 F
- supply air: about 52.2–52.4 F
- measured 0x281 airflow: 774 CFM
- blower power: about 45 W
- outdoor ambient: about 95 F
- input power: about 1.68–1.75 kW
- line-voltage candidate: 237–238 V

## Compressor speed family

The active captures materially strengthen the compressor-speed map.

### 0x384.float[0] — compressor speed candidate

0x384.float[0]:

- is 0 RPS when the system is satisfied;
- sits at about 57.8–58.0 RPS in these active captures;
- changes independently from the commanded target carried by 0x385.float[1].

This behavior is much more consistent with actual compressor speed than with the previous
"target max speed" label. The Home Assistant entity is therefore renamed to:

`0x384 Compressor Speed Candidate`

Keep Candidate wording until synchronized OEM service telemetry confirms the exact name.

### 0x385.float[1] — compressor target speed candidate

0x385.float[1] carries about 63–66 RPS during the same interval. It remains distinct from
0x384.float[0], which is exactly what is expected from target versus achieved speed.

### 0x3D0 / 0x3E0 — minimum-speed family

0x3D0.float[1] stays around 20.2–20.3 RPS and 0x3E0.float[0] around 21.05 RPS even while
the target is 63–66 RPS. Combined with the satisfied-state capture, where live speed/target
collapse to zero while this family stays near 20–21 RPS, the minimum-speed/lower-limit
interpretation is now strong.

## Electrical / drive family

The capture repeatedly shows:

- 0x38F.float[0]: 237–238 V
- 0x38C.float[1]: about 1.68–1.75 kW
- 0x388: about 5.5–5.7 A
- 0x389.float[0]: about 5.5–5.6 A
- 0x389.float[1]: about 6.7–7.0 A
- 0x384.u16@4: about 338–352 Vdc
- 0x384.u16@6: about 756–768 RPM outdoor-fan speed
- 0x387.float[1]: about 0.3–0.4 A and zero while inactive

This independently reinforces the line-voltage, input-power and outdoor-fan mappings.

## Refrigerant / temperature family

During the active interval:

- 0x380.float[1] outdoor ambient: about 95.0 F
- 0x381.float[0] outdoor-coil-temperature candidate: about 100.8–101.7 F
- 0x381.float[1] pressure-family raw: about 198.3–198.8
- 0x382.float[0] temperature-1 candidate: about 69.7–70.4 F
- 0x382.float[1] liquid-temperature candidate: about 98.4–98.7 F
- 0x383.float[0] compressor dome/discharge candidate: about 147.2 F
- 0x383.float[1] liquid/high-side pressure candidate: about 410.7–413.9

0x381.float[1] remains deliberately raw. These captures add repeatability but do not prove
its scaling or exact pressure semantic.

## Indoor airflow / coil family

The active captures repeatedly show:

- 0x281 u16@0 = 774
- 0x281 u16@2 = 500
- 0x281 u16@6 = 356
- 0x318 u16@4 = roughly 649–657
- 0x318 u16@6 = roughly 437–441
- 0x318.float[0] = 0.6753
- 0x320.float[0] = roughly 45 W

0x281 u16@0 remains the strongest actual-airflow mapping. The two 0x318 trailing words
continue to track blower operation but should remain Candidate fields until a synchronized
Technician airflow/RPM screen identifies them.

## Setpoint transaction result

These files do **not** contain the 79 -> 78 F setpoint write.

The structured freshness counters prove the relevant snapshots pre-date the capture:

- SpOverride snapshot age grows from roughly 2,774 s to roughly 2,899 s;
- SystemOpStatus snapshot age grows from roughly 582 s to roughly 707 s;
- IndoorStatus snapshot age grows from roughly 138 s to roughly 263 s;
- Segmented JSON message count remains fixed at 428 across the captured interval.

Therefore the 78 F setpoint had already been established before this recording began.
A future capture must start before the physical UX360 setpoint change to recover the native
SpOverride SDO write/echo.

## Transport / network observations

- CANopen nodes 1–5 remain operational.
- 0x53E active-node candidate remains 5.
- LSS Fastscan initialization `0x7E5 51 00 00 00 00 80 00 00` repeats about every 5.25 s.
- No application TX was emitted by the bridge.
- Unclassified CAN frame count is zero in the Home Assistant snapshot.

