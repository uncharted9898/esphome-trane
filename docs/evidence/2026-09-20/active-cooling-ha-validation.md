> **Historical evidence — 2026-09-20.** This is a point-in-time target capture/requalification note. Current authoritative meanings live in [../../TELEMETRY.md](../../TELEMETRY.md) and [../../CANOPEN-LINK-TRANSPORT.md](../../CANOPEN-LINK-TRANSPORT.md).

# Active-cooling / Home Assistant validation — 2026-09-20

Capture set:

- logs 16
- logs 17
- logs 18
- logs 19
- Home Assistant entity snapshot captured after the curated/debug profile split

## Operating envelope

The system is actively cooling near the upper end of the observed modulation range.

Representative values across the capture set:

- room temperature: about 78 F
- indoor humidity: about 53 percent
- outdoor ambient: about 89-90 F
- return air: about 76.1 F
- supply air: about 47.4-47.7 F
- actual airflow: about 773-774 CFM
- actual compressor speed: about 57.3-58.1 RPS
- compressor speed request: about 57.7-58.0 RPS
- 0x385 speed-family value: about 66-70 RPS
- compressor power: about 1.35-1.39 kW
- total input power: about 1.53-1.60 kW
- line voltage: about 237-238 V
- drive DC bus: about 339-355 V
- outdoor fan: about 762-774 RPM

The promoted friendly HA entities remained coherent together through all four captures.

## 0x281 byte 6 is compressor demand, not blower demand

The decisive correlation is with structured
`OdStatus.CompDemandPercent`.

Independent observed points include:

- structured compressor demand 72 percent -> 0x281.byte6 = 72
- structured compressor demand 82 percent -> 0x281.byte6 = 82
- structured compressor demand 84 percent -> 0x281.byte6 = 84
- later structured compressor demand 82 percent -> 0x281.byte6 = 82

During the same captures, `IndoorStatus.E` carries a different value
(for example low-60s), so byte 6 cannot be the indoor blower percentage.

Current interpretation:

- `0x281.byte6` = compressor-demand percent mirror
- normal HA `Compressor Demand` reads the binary byte directly
- structured `OdStatus.CompDemandPercent` remains an independent validation
  source when a fresh JSON update arrives

This also improves startup behavior because compressor demand no longer waits
for a sparse structured profile/status update.

## Compressor speed-family separation

The 2026-09-20 captures strengthen the distinction between the speed fields.

### 0x280.float[0] — compressor speed request

Observed roughly:

- 29 RPS at low load in earlier captures
- 40-43 RPS at moderate modulation
- 57.5-58 RPS in this high-load set
- drops ahead of achieved speed during satisfaction

This is now the normal HA `Compressor Speed Request` entity.

### 0x384.float[0] — actual compressor speed

Observed about 57.3-58.1 RPS in the current set and zero when satisfied.

This remains the normal HA `Actual Compressor Speed` entity.

### 0x385.float[1] — speed ceiling/limit family

This field remains above the immediate request:

- about 40 RPS while request is about 29 RPS at low load
- about 63 RPS while request is about 56 RPS
- about 66-70 RPS while request is about 58 RPS in this set
- zero when the outdoor unit is idle

The old `Compressor Target Speed` friendly label is therefore demoted.
Current label:

`0x385 Compressor Speed Ceiling Candidate`

It remains diagnostic and disabled by default.

## 0x2D0 airflow-family duplication

The current set repeatedly carries:

`0x2D0 = 00 00 FF/00 01/02 07 03`

which decodes approximately as:

- word 1 = 511-512
- word 2 = 775

At the same operating point:

- `0x318.u16@4` airflow feedback is roughly 490-517
- `0x281.u16@0` actual airflow is roughly 773-774

This strongly suggests 0x2D0 is another airflow/status mirror or rounded
airflow-family block. It is not yet promoted because the first word is close
to, but not identical with, the 0x318 feedback channel and the full transition
relationship is not yet isolated.

Keep both 0x2D0 words as disabled raw diagnostics.

## 0x430 / 0x450 / 0x460

A four-capture nearest-sample correlation pass found:

- `0x430.float[0]` stays about 97.40-97.47 and correlates very strongly with
  `0x410.float[0]` drive temperature (correlation about 0.98, average
  separation about 0.6 F).
- `0x430.float[1]` varies widely and does not cleanly map to an already
  qualified live temperature.
- `0x450.float[0..1]` vary substantially but do not yet show a clean enough
  relationship for a friendly semantic.
- `0x460.float[0]` remains around 84.44-84.48 F in this set; it correlates
  with several outdoor temperature-family fields but is not close enough to a
  qualified source to name safely.

No new friendly entities are created for these fields.

## Structured-profile coverage

The new `Profile Coverage` diagnostic correctly exposes why many metadata and
setpoint/profile entities are blank after bridge boot.

Observed states in this run include:

- initially 0/8 high-value roots observed
- later 2/8 or 4 retained roots depending on capture timing
- SystemOpStatus and IndoorStatus eventually become fresh
- ZoneStatus, SpOverride, UnitID, VersionDetails, IndoorSettings and
  SystemSettings may remain absent if their OEM profile sweep occurred before
  the bridge booted

This is a passive-observation limitation, not evidence that the live binary
decoder is missing those measurements.

Application TX remains fail-closed, so the bridge does not force a profile
refresh.

## Home Assistant organization validation

The curated normal profile successfully surfaces the useful live equipment
telemetry while keeping the reverse-engineering surface opt-in.

Normal device pages now prioritize:

- room temperature / humidity
- return / supply temperature
- actual airflow
- static pressure
- blower motor current/speed/power
- indoor refrigerant temperatures / superheat
- outdoor ambient / coil / liquid-line / discharge temperatures
- compressor demand
- compressor speed request
- actual compressor speed
- compressor/input power
- input current / line voltage / DC bus
- outdoor fan speed

Candidate/raw fields and per-ID dumps remain in diagnostics or the dedicated
debug HA profile.
