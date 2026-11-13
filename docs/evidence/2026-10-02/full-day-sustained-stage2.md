# 2026-10-02 full-day sustained Stage 2 and control confirmation

Source bundle: `trane-2026-10-02.tar.gz`

## Capture integrity

- 24 hourly JSONL members
- 749,874,215 uncompressed bytes
- 2,663,778 JSONL records
- 2,661,324 CAN records
- 2,454 structured Trane JSON records
- 82 unique CAN IDs
- zero malformed JSONL rows
- zero malformed structured JSON payloads

## Cooling operation

Nine compressor-running intervals were captured:

1. 00:54:17-01:01:00 UTC (~6.7 min)
2. 01:26:12-01:32:59 UTC (~6.8 min)
3. 03:35:50-03:42:01 UTC (~6.2 min)
4. 04:10:33-06:22:15 UTC (~131.7 min)
5. 16:49:11-16:55:53 UTC (~6.7 min)
6. 17:06:20-22:51:38 UTC (~345.3 min)
7. 22:59:32-23:16:13 UTC (~16.7 min)
8. 23:25:26-23:39:06 UTC (~13.7 min)
9. 23:48:53 through end of capture (~11.1 min observed)

The 17:06 run is the longest sustained cooling interval in the archive set so
far.

## Sustained Stage 2 behavior

The 04:10 run transitions:

- Stage 1 at ~04:10:24 UTC
- Stage 2 at ~04:18:20 UTC
- Stage 1 at ~06:17:46 UTC
- off at ~06:22:00 UTC

for ~119.4 minutes of sustained Stage 2.

The 17:06 run transitions:

- Stage 1 at ~17:06:11 UTC
- Stage 2 at ~17:21:14 UTC
- Stage 1 at ~22:39:30 UTC
- brief Stage 2 re-entry at ~22:41:22 UTC
- Stage 1 again at ~22:41:50 UTC
- off at ~22:51:21 UTC

The main Stage 2 interval lasts ~318.3 minutes / 5.30 hours.

Actual compressor speed remains continuously variable and peaks around 58 RPS,
further confirming that AC Stage 1/2 is supervisory demand/staging state rather
than fixed inverter speeds.

## Blower request/feedback confirmation

Across 232 numeric `IndoorStatus.E` observations paired to `0x200.u16@2`:

- correlation: ~0.998
- median scale: ~7.97 request units per percent
- positive request ratio range: ~7.14-8.09

The maintained chain remains:

- `IndoorStatus.E` -> blower speed request/target percent
- `0x200.u16@2` -> blower speed request candidate
- `0x318.u16@4` -> blower motor speed feedback
- `0x281.u16@0` -> airflow target/command candidate
- `0x318.u16@6` -> unresolved motor-adjacent candidate

## Compressor speed-ceiling sentinel

Six additional clean compressor starts emit:

`0x385.f1 = 65535`

before the speed-ceiling field returns to its normal operating range.

Observed sentinel times include approximately:

- 00:54:17 UTC
- 01:26:11 UTC
- 03:35:48 UTC
- 16:49:09 UTC
- 23:25:25 UTC
- 23:48:52 UTC

This strongly validates the existing 0-200 RPS sanity filter.

## Structured setpoint override path

Two zone-1 cooling setpoint transactions were captured:

- 04:10:22 UTC -> Csp 77 F
- 11:38:19 UTC -> Csp 78 F

Each follows the expected:

`SpOverride.Put -> SpOverride.Update -> ZoneStatus.Update.1.Csp`

path.

## Pressure behavior

The `0x383` pressure pair behaves consistently across all active cooling:

- active suction field median: ~134.8
- active high-side field median: ~306.5
- active median pressure split: ~173.9
- maximum observed active split: ~237.0

During idle/equalization the pair moves back together; the median idle
difference is only ~0.09 in the directly paired samples.

No 185.x low-suction-pressure protection event was observed.

## Outdoor thermal/raw families

`0x460.f0` remains tightly correlated with the outdoor power-electronics
thermal family over the full day:

- corr with `0x410.f0`: ~0.944
- corr with `0x410.f1`: ~0.945
- corr with `0x430.f0`: ~0.940

It remains effectively unrelated to:

- `0x430.f1`
- `0x450.f0`
- `0x450.f1`

so it remains a generic temperature candidate rather than receiving an OEM
friendly name.

## Stator heat

Two isolated stator-heat cycles occurred:

- ~12:18:06-12:26:09 UTC
- ~13:14:51-13:22:56 UTC

The cumulative project total is now **75 isolated cycles**.

## Structured JSON transport

This day contains many 42-byte `0x300A` block transfers. The inspected
examples are normal NUL-terminated messages, for example an `OdStatus` update
whose final block segment carries the trailing NUL.

No exact-length/no-NUL `DebugUI.HiHeapRemaining` transfer appears in this
archive. The optional-NUL transport fix remains grounded by the independently
captured 2026-09-30 and 2026-10-01 examples.

## Negative evidence

No structured event was observed for:

- A2L leak/concentration alarm
- heating operation
- defrost
- reversing-valve state
- 185.x low-suction protection

## Safety boundary

All conclusions remain receive-side only. Application/control TX remains
fail-closed.
