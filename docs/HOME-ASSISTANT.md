# Home Assistant entity layout

The Home Assistant integration intentionally separates **normal HVAC telemetry**
from **reverse-engineering diagnostics**.

## Normal profile

Use:

`waveshare-trane-homeassistant.yaml`

The normal profile exposes the useful live equipment view:

### Trane UX360 Thermostat

Enabled by default:

- Room Temperature
- Indoor Humidity
- Heat Setpoint
- Cool Setpoint
- zone-1 call/state surfaces that have current structured data

Other zones and profile/configuration details remain disabled until populated or
needed.

### Trane SC360 Controller

Enabled by default:

- System Mode
- System Demand Stage
- current alarm summary surfaces when available

Raw profile values, firmware/config metadata, timezone/weather internals and
candidate fields remain Diagnostic, generally disabled by default.

### Trane 5TAMX Air Handler

Enabled by default:

- Return Air Temperature
- Supply Air Temperature
- Actual Airflow
- Total Static Pressure
- Blower Power
- Indoor Blower Speed/status when fresh structured data exists

Unqualified refrigerant, EEV, raw-word and candidate channels remain available
as disabled diagnostics.

### Trane 5TWV0X Heat Pump

Enabled by default:

- Outdoor Air Temperature
- Compressor Speed
- Compressor Demand
- Outdoor Unit State
- Outdoor Fault Code
- Drive DC Voltage
- Outdoor Fan Speed
- Input Power

Candidate/raw refrigerant, current, speed-limit and pressure-family fields are
disabled diagnostics until independently qualified.

### Trane Link Diagnostics

Bridge/protocol health is grouped on a dedicated diagnostics device instead of
appearing as loose root-level entities.

Useful visible health surfaces include:

- SC360 Seen
- SC360 Recently Active
- RX Transport Errors
- Structured Data Status
- Last Structured JSON Age
- Unclassified CAN Frames

High-volume counters/capture internals are disabled by default.

`Structured Data Status` summarizes freshness as:

`fresh|aging|stale / <retained roots> roots / <age>s`

This matters because structured profile values can be hours old while binary
telemetry remains live.

## Debug profile

Use:

`waveshare-trane-homeassistant-debug.yaml`

This profile layers the normal HA profile with:

`waveshare-trane-target-raw.yaml`

and restores the per-CAN-ID raw text surfaces used for protocol development.

Use the debug profile when investigating a new ID or collecting qualification
evidence. It is intentionally noisy and is not the preferred permanent HA
surface.

## Visibility policy

Entity naming/visibility follows this rule:

- clean human-facing name + independently useful live signal -> enabled normally;
- `Candidate` -> Diagnostic + disabled by default;
- `Raw` -> Diagnostic + disabled by default;
- per-ID raw frame dumps -> debug profile only;
- sparse structured configuration/profile metadata -> Diagnostic and generally
  disabled until needed.

No data is discarded by this organization. The observation cache, raw capture,
ID census, structured snapshot store and debug profile retain the underlying
evidence.

## Why some profile fields are blank

A blank model/serial/version/settings/weather entity does not necessarily mean
the parser is missing that field.

Those values come from sparse structured profile exchanges. If the bridge boots
after the OEM profile sweep, or the relevant profile has not been repeated,
only the roots observed since bridge boot can be retained.

The bridge intentionally does not force a profile refresh while application TX
is fail-closed. Check:

- Structured Data Status
- Structured Profile Snapshots Retained
- Last Structured JSON Age
- per-root snapshot ages

before interpreting an empty profile field as a decoder failure.
