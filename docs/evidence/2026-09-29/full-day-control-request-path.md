# 2026-09-29 full-day control-day cooling and request-path evidence

Source bundle: `trane-2026-09-29.tar.gz`

## Capture integrity

- 24 hourly JSONL members
- 2,655,911 CAN records
- 2,349 decoded Trane JSON records
- 82 unique CAN IDs
- zero malformed JSONL records
- first record: 2026-09-29 00:00:00 UTC
- last record: 2026-09-29 23:59:59 UTC

## Cooling operation

Sixteen compressor-running intervals were captured, including:

- ~100.1 minute run beginning 03:32 UTC
- ~88.2 minute run beginning 16:30 UTC
- many shorter 7-47 minute cycles later in the day

No A2L/leak, defrost, or heating structured JSON was observed.

No repeat of the previous day's Err 185.10/185.11 low-suction-pressure
protection occurred, making this archive a useful clean control day against the
09/28 protection-event capture.

## Stage behavior

Structured `SystemOpStatus.C` continued to show:

- `AC Stage 1`
- `AC Stage 2`
- `--` at shutdown

The longest early run enters Stage 2 about ten minutes after startup and returns
to Stage 1 before shutdown. Later runs also contain very brief Stage 2
transitions while compressor speed remains continuously variable.

This continues to support supervisory demand/staging semantics rather than
fixed compressor-speed stages.

## Blower request/feedback chain

This day independently confirms the 09/27-09/28 blower requalification.

Across 152 numeric `IndoorStatus.E` observations:

- correlation with `0x200.u16@2`: ~0.998
- median command scale: ~7.95 request units per percent

Example clean startup:

- `IndoorStatus.E = 38%`
- `0x200.u16@2 = 303`
- `0x281.u16@0 = 720`
- `0x318.u16@4 = 0`
- blower power `0x320.f0 = 0 W`

The physical motor feedback rises later. During sustained modulation,
`0x318.u16@4` tracks the request closely.

This proves numeric `IndoorStatus.E` is better described as a **blower speed
request/target percentage**, not measured blower speed.

Maintained chain:

- `IndoorStatus.E` -> blower speed request percent
- `0x200.u16@2` -> blower speed request candidate
- `0x318.u16@4` -> blower motor speed feedback
- `0x281.u16@0` -> airflow target/command candidate
- `0x318.u16@6` -> unresolved motor-adjacent candidate

## 0x385 startup sentinel

Multiple clean compressor starts contain:

`0x385.f1 = 65535`

before the field settles into its normal ~40-60 RPS ceiling range.

Examples occur around:

- 03:32:42 UTC
- 16:12:01 UTC
- 16:30:45 UTC
- 18:30:19 UTC
- 19:21:04 UTC
- 21:24:26 UTC
- 22:19:39 UTC
- 23:07:53 UTC

The maintained diagnostic now rejects values outside 0-200 RPS so this startup
sentinel cannot create a false 65,535 RPS HA spike.

## Structured setpoint override path

Two zone-1 cooling-setpoint overrides were captured:

1. 03:32:31 UTC -> Csp 77 F
2. 13:17:41 UTC -> Csp 78 F

For the 03:32 event:

- `SpOverride.Put` requests Csp 77
- matching `SpOverride.Update` follows
- `ZoneStatus.Update.1.Csp = 77`
- `SystemOpStatus.C = AC Stage 1` appears about 3 seconds later
- actual compressor speed leaves zero roughly 13 seconds after the override

This is useful end-to-end evidence that the structured setpoint/override
decoder is following the live control path correctly.

## Pressure behavior

The `0x383` low/high pressure pair behaves normally throughout all 16 cooling
intervals:

- near idle the pair moves toward equalization
- under cooling the suction field falls and high-side field rises
- no OEM low-suction protection alarm appears

That provides a clean control day against the 2026-09-28 alarm event.

## Outdoor thermal/raw families

The unresolved families remain unresolved:

- `0x430.f1`
- `0x450.f0`
- `0x450.f1`

`0x460.f0` continues to track the power-electronics thermal family closely
(correlation roughly 0.96-0.97 with `0x410` / `0x430.f0`) while showing
essentially no useful relationship to `0x430.f1` or either `0x450` field.
That narrows its family but still does not prove the Technician `ViTemp`
identity.

## Stator heat

Two isolated stator-heat cycles were captured.

The cumulative project total is now **66 isolated cycles**, continuing to
support:

- `0x282.byte1` -> Stator Heat Enable
- `0x390.byte0` -> Stator Heat Power Level
- `0x388.f0/f1` + `0x389.f0` -> compressor phase-current family

## Safety boundary

All conclusions are receive-side only. Application/control TX remains
fail-closed.
