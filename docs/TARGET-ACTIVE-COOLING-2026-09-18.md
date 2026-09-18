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



## Cooling-to-satisfied transition capture

A later capture beginning around 14:42:41 local time contains the full transition
from active cooling into a satisfied/idle state.

### Compressor ramp-down

The binary telemetry shows a coherent compressor ramp:

- 0x384.float[0] (compressor speed candidate) falls from about 57.9 RPS through
  55, 52.5, 47.4, 40.6, 35.4, 29.2 and 5.9 RPS before reaching 0.
- 0x385.float[1] (target speed candidate) begins around 64-65 RPS, then steps
  down through the 50s/40s/30s, reaches about 26 RPS during final rundown and
  then falls to zero.
- 0x385.float[0] (compressor-power candidate) falls from about 1544 W to
  roughly 696 W and then zero.
- 0x38C input power falls from roughly 1.73 kW through about 802 W, then
  180 W / 32 W and finally the ~15 W standby baseline.

This dynamic correlation materially strengthens 0x384.float[0] as actual
compressor speed and 0x385.float[1] as target/commanded speed.

### Indoor airflow ramp-down

The indoor side also transitions coherently:

- 0x281 actual-airflow word starts at 774 CFM;
- steps to 550 CFM while the blower is reducing;
- reaches 200 CFM during the final rundown;
- then reaches 0 CFM.
- 0x318 u16@4 / u16@6 fall in parallel from roughly 647/434 through
  612/405, 565/376, 514/347, 462/318 and finally 0/0.
- 0x320 blower power falls from about 44 W through the 30/25/20 W range and
  then zero.

0x281 u16@2 remains 500 throughout this transition, so it is not actual
airflow. Preserve it as a target/configuration candidate until OEM service
telemetry identifies it.

### Structured state transition

The same transition produces fresh application-level state updates:

- `IndoorStatus.D` changes from `B` during active operation to `A` as
  the indoor unit stops.
- `IndoorStatus.E` reports a numeric blower/status value during operation
  and explicitly updates to `0` when the blower has stopped.
- `ZoneStatus.HcStatus` updates to `4` during the shutdown transition and
  later to `1` once the zone is satisfied.
- two transient SOP alarms are deleted as the transition completes.

Because IndoorStatus.E has also been observed carrying a non-numeric string in
older retained data, keep the raw entity alongside the numeric blower-speed
interpretation rather than assuming the field is always numeric.

### Fresh SpOverride update is startup/profile hydration, not a Put

The capture contains a fresh:

`{"SpOverride":{"Update":{"1":{"Csp":"78","Hsp":"62","Source":"1","HoldType":"1"}, ...}}}`

at approximately 14:42:56.791. This is important, but it is **not** evidence
of the client-side setpoint write syntax.

Immediately before this profile burst, CANopen LSS assigns node 3 and NMT
starts it. The controller then emits UnitID and a sequence of normal 0x649
profile `Update` objects, each acknowledged by `{"Ack":"200"}` on 0x641.
No JSON object containing `Put` appears anywhere in the three capture files.

Therefore application TX remains fail-closed until a capture starts before a
physical UX360 setpoint change and records the originating write.

## Complete CANopen LSS Fastscan identity

This capture contains a complete positive CiA-305 Fastscan for the node that is
subsequently assigned node ID 3.

The four reconstructed 32-bit identity words are:

- vendor ID: `0x00000001`
- product code: `0x00000004`
- revision number: `0x00000000`
- serial number: `0xC345985F`

After the final positive Fastscan probe the manager sends the node-ID
configuration request for node 3 and receives success. It then switches the
LSS state, after which node 3 emits boot-up, enters pre-operational, receives
NMT Start Remote Node, and reports operational.

The offline capture analyzer now reconstructs this identity/configuration/NMT
startup sequence as one LSS session instead of exposing only individual probes.


## 15:01-15:04 active modulation capture

The follow-up capture set `trane-5tv0x-2ton-upstairs-logs (9-12)`
contains a long steady cooling modulation interval rather than another startup
profile burst.

### Structured compressor modulation

Fresh 0x649 application updates observed in order include:

- `OdStatus.CompDemandPercent = 66`
- `OdStatus.B = 70`
- `OdStatus.CompDemandPercent = 70`
- `SystemOpStatus.D = 70`
- `OdStatus.B = 71`
- `OdStatus.B = 72`
- `OdStatus.CompDemandPercent = 72`
- `OdStatus.B = 73`

The existing Home Assistant parser publishes `OdStatus.B` as the structured
compressor-speed percentage. Across the 70 -> 73% steps, 0x384.float[0] rises
from roughly 39.1 -> 39.6 -> 40.5 -> 41.2 RPS. This materially strengthens
0x384.float[0] as **actual compressor speed**, so the diagnostic label is now
`0x384 Actual Compressor Speed Candidate`.

0x385.float[1] remains a distinct target-speed family value in roughly the
50-54 RPS range during this interval. The target and actual channels therefore
remain independently justified.

0x387.float[0] remains pinned at exactly 55.0 throughout this modulation and
was also 55.0 in the earlier satisfied/idle capture. It is not actual
compressor speed. The stable non-zero value is now classified as
`0x387 Compressor Speed Reference Limit Candidate` without claiming whether
the OEM semantic is a maximum, minimum, rated, or another reference.

### Indoor blower modulation

Fresh `IndoorStatus.E` updates step through:

`62 -> 63 -> 68 -> 69 -> 70 -> 71 -> 72`

while measured 0x281 airflow stays in the high-600 / low-700 CFM range and the
0x318 speed/current/power family rises in parallel.

0x281 byte 6 also rises through the 60s/70s during this active interval.
However, the earlier cooling-to-satisfied transition is decisive against
equating it directly with `IndoorStatus.E`: when the structured status still
reported `E=40` and measured airflow was about 550 CFM, byte 6 had already
fallen to zero while byte 7 remained one. Byte 7 later falls to zero only when
the blower stops.

The binary fields are therefore exposed conservatively as:

- `0x281 Blower Demand Candidate` (byte 6)
- `0x281 Blower Active Flag Candidate` (byte 7)

The former `0x281 Tail Word Raw` is renamed
`0x281 Bytes 6-7 Composite Raw` and disabled by default because it is not an
independent field; it is simply the little-endian composite
`byte6 + (byte7 << 8)`.

### 0x490 byte 4 is not proven relative humidity

The same capture family exposes a qualification failure in the old
`0x490.byte4 = relative humidity` label. Normal operation produces
humidity-looking values such as 54 and 57, but during the node-3 transition
the field repeatedly becomes `0x9D` (157). One frame contains a valid 79 F
0x490 temperature while byte 4 is still 157, so this cannot be dismissed as a
single malformed frame.

The field is now exposed only as:

`0x490 Zone 1 RH Status Byte Candidate`

with no humidity device class or percent unit. The 0x490 temperature entity
also filters the observed -99 unavailable sentinel to NaN while the raw frame
remains available through the diagnostic surface.

### No setpoint write captured

There is no JSON object containing `Put` in any of logs 9-12. The capture
contains routine 0x649 status updates and matching 0x641 `{"Ack":"200"}`
responses, but no client-originated setpoint transaction. `SpOverride`
snapshot age remains unavailable in this run.

This capture must not be used to infer a setpoint write format. Application TX
remains fail-closed until a capture starts before a physical UX360 setpoint
change and records the originating transaction.
