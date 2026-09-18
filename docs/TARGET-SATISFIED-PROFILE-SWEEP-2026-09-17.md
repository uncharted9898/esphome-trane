# Target satisfied-state profile sweep - 2026-09-17

## Capture context

Target system:

- 5TWV0X24A1000B outdoor unit
- 5TAMXC03AV31DB indoor unit
- UX360 + SC360
- Waveshare ESP32-S3 CAN tap

User-confirmed operating context: **the unit was satisfied** during this capture.
The configured thermostat mode remained cool, but there was no active cooling
call.

## What this capture proves

### Mode is not the same thing as active demand

The structured state reported:

- System mode: cool
- System demand stage: `--`
- `OdStatus.CompDemandPercent`: 0
- compressor-power candidate: 0 W
- drive/input-current candidates: 0 A
- outdoor fan speed: 0 rpm
- whole-unit input power: about 12-13 W

This is a useful idle/satisfied baseline. A decoder must keep configured mode,
active demand and equipment-running state separate.

### 0x387.f0 is not actual compressor speed

`0x387.f0` remained exactly 55.0 while the unit was satisfied and all
independent load indicators above were zero. The previous friendly name
`Actual Compressor Speed` and the derived `55 RPS * 60 = 3300 rpm` entity
were therefore false.

Action taken:

- `0x387.f0` is now exposed as `0x387 Float 1 Raw`.
- the synthetic `0x387 Compressor Speed RPM` entity was removed.

Do not promote this field again without a capture showing it move coherently
with a real compressor run.

### 0x381 requalification

Across the prior loaded-cooling capture, `0x381.f0` tracked the outdoor-coil
temperature family rather than the suction-line/evaporator temperature. In the
satisfied capture it naturally relaxed near outdoor ambient.

Action taken:

- `0x381.f0` -> `0x381 Outdoor Coil Temperature Candidate`.
- `0x381.f1` -> `0x381 Pressure Family Raw`.

The second float clearly behaves like a refrigerant-pressure-family value, but
its exact pressure role and 1:1 psi scaling are not sufficiently qualified to
publish as established suction pressure.

## CANopen SDO / profile sweep

The stock controller emitted `GetProfile` JSON on the 0x641/0x5C1 SDO pair
using object `0x300A:00`, and structured profile/status updates arrived on
0x649/0x5C9.

Observed request names include:

- `THERMOSETTINGS`
- `TECHAPPSETTINGS`
- `WEATHERDATA`
- `NOTIFICATIONDATA`
- `INDOORSTATE`
- `ZONESTATE`
- `SYSOP`
- `ODSTATE`
- `ODSETTINGS`

Strong request/response pairings observed in this sweep:

- `WEATHERDATA` -> `WeatherData.Update`
- `NOTIFICATIONDATA` -> `Notifications.Update`
- `SYSOP` -> `SystemOpStatus.Update`
- `ODSTATE` -> `OdStatus.Update`
- `ODSETTINGS` -> `OutdoorSettings.Update`

Each response transfer is followed by an application-level
`{"Ack":"200"}` returned on the 0x641 path after the CANopen SDO transaction.
This reinforces the current interpretation:

- 0x641/0x5C1: request / application-ack path
- 0x649/0x5C9: profile/status-update path

Do not force `HiSettings` onto `THERMOSETTINGS` solely from sweep ordering;
the capture does not prove that pairing.

## What this capture did not contain

There was no `SpOverride` or `SystemMode` JSON transaction in the full
capture. Therefore it is **not** the stock UX360 setpoint/mode-change capture
needed to qualify active application writes.

Keep Trane application TX fail-closed until a real user-initiated setpoint or
mode change is captured and the initiating SDO endpoint plus complete
request/ack sequence are observed.

## Source changes made from this capture

- demoted `0x387.f0` to raw and removed the false RPM derivative;
- requalified `0x381.f0` to outdoor-coil-temperature candidate;
- demoted `0x381.f1` to pressure-family raw;
- added target-observed profile names to the validator;
- increased bounded structured-JSON snapshot slots from 16 to 32;
- kept active JSON TX fail-closed;
- corrected the `trane_hvac` platform's explicit `trane_bus` source dependency
  and canonical component include.


## Follow-up steady-state capture

A later ~60-second capture was taken with the same unit still satisfied. It
contains 1,821 parsed CAN frames and 76 standard CAN IDs, but **no new
structured JSON transfer**. The retained Home Assistant structured values
therefore pre-date the wire window and must not be treated as events that
occurred during this capture.

This is especially important for retained strings such as the indoor fault
display and the accumulated "last unknown CAN" field. The binary wire itself
shows a quiet satisfied system:

- 0x281 actual airflow = 0 CFM;
- 0x318 current/airflow/speed family = all zero;
- 0x320 blower power = 0 W;
- 0x384 live speed/max-speed candidate = 0 RPS and outdoor fan = 0 RPM;
- 0x385 compressor-power and target-speed candidates = 0;
- 0x388/0x389 current families = 0 A;
- 0x38C input power = 15-16 W;
- 0x38F line-voltage candidate = 240-241 V.

### Minimum-speed family strengthened

While all live compressor-target/load channels above are zero, the persistent
limit family remains:

- 0x3D0.float[1] = 20.83-20.91 RPS;
- 0x3E0.float[0] = 20.82 RPS when observed.

The earlier running captures also placed this family near 20 RPS. This strongly
supports the existing "compressor target minimum speed" / lower-limit
interpretation. Keep Candidate wording until a synchronized Technician value
confirms the exact OEM field name.

### 0x387 falsification repeated

0x387.float[0] remains exactly 55.0 for the entire satisfied capture while:

- compressor target = 0;
- compressor power = 0;
- outdoor fan = 0;
- drive/input currents = 0.

This independently repeats the evidence that 0x387.float[0] is not live
compressor speed.

### Structured-data freshness

Because no JSON was received during this steady-state window, the runtime now
tracks and exposes:

- Last Structured JSON Age;
- SystemOpStatus Snapshot Age;
- IndoorStatus Snapshot Age;
- SpOverride Snapshot Age.

These ages distinguish retained profile state from current wire activity and
prevent stale values from being mistaken for a live alarm, mode transition or
setpoint transaction.
