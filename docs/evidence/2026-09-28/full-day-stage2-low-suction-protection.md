# 2026-09-28 full-day cooling, Stage 2 and low-suction protection

Source bundle: `trane-2026-09-28.tar.gz`

## Capture integrity

- 24 hourly JSONL members
- 2,634,619 CAN records
- 1,534 decoded Trane JSON records
- 82 unique CAN IDs
- zero malformed JSONL records
- first record: 2026-09-28 00:00:00 UTC
- last record: 2026-09-28 23:59:59 UTC

## Cooling operation

Twelve compressor-running intervals were captured:

1. carry-over run at midnight, ending ~00:02:39 UTC
2. 17:56:39-18:02:42 UTC (~6.1 min)
3. 18:16:17-19:48:59 UTC (~92.7 min)
4. 19:56:46-20:11:42 UTC (~14.9 min)
5. 20:21:13-20:36:16 UTC (~15.1 min)
6. 20:44:43-21:05:46 UTC (~21.0 min)
7. 21:13:23-21:34:14 UTC (~20.9 min)
8. 21:42:33-21:58:39 UTC (~16.1 min)
9. 22:06:41-22:42:54 UTC (~36.2 min)
10. 22:49:58-23:07:19 UTC (~17.3 min)
11. 23:17:44-23:27:51 UTC (~10.1 min)
12. 23:53:47-23:59:56 UTC (~6.1 min)

The structured lifecycle remains coherent with prior days:

- `SystemOpStatus.C = AC Stage 1` during ordinary cooling
- `OdStatus.C = A` while outdoor cooling is active
- `IndoorStatus.D = B` while the indoor unit is active
- `ZoneStatus.HcStatus = 2` while cooling
- shutdown returns through the known coast/idle states

## Sustained AC Stage 2 interval

The long 18:16-19:49 UTC run contains a sustained `AC Stage 2` period:

- Stage 1 begins: ~18:16:08 UTC
- Stage 2 begins: ~18:34:35 UTC
- Stage 1 resumes: ~19:41:01 UTC
- cooling ends: ~19:48:45 UTC

Stage 2 therefore lasts roughly 66.4 minutes.

The compressor remains continuously variable through the transition:

- near Stage 2 entry, request/actual speed are ~30 RPS
- compressor demand is ~35-40%
- speed and demand continue to ramp gradually afterward

This reinforces that the stage text is supervisory demand/staging state rather
than a discrete fixed-speed second compressor stage.

## Blower speed command/feedback confirmation

The 2026-09-27 blower requalification holds strongly.

Across 89 numeric `IndoorStatus.E` observations:

- correlation with `0x200.u16@2` is ~0.999
- median scale is ~7.98 request units per percent
- numeric E spans normal running values while `TA_INV_HI` remains a healthy
  startup token

The maintained interpretation remains:

- `IndoorStatus.E` numeric -> blower speed percent
- `0x200.u16@2` -> blower speed request candidate
- `0x318.u16@4` -> blower motor speed feedback
- `0x281.u16@0` -> airflow target/command candidate
- `0x318.u16@6` -> unresolved motor-adjacent candidate

## Low-suction-pressure protection event

The first afternoon cooling cycle produces two short-lived Level 1 alarms:

- `Err 185.10`
- `Err 185.11`

Public Trane alert documentation identifies the 185.10/185.11 family as
cooling low-suction-pressure protection states.

At the 185.10 event:

- `0x383.f0` suction-pressure field is ~69.1
- `0x383.f1` paired high-side field remains ~274
- compressor request has already been reduced from 45 RPS toward 20 RPS
- actual compressor speed is still decaying through ~27 RPS
- the alarm clears shortly afterward as suction pressure recovers

At the 185.11 event:

- suction-pressure field is ~72.2
- paired high-side field remains ~267
- request remains at 20 RPS
- suction pressure continues recovering over the following minute

This directly confirms the **suction-pressure semantic** of `0x383.f0`.

It does not independently prove whether the raw wire value is gauge or absolute
pressure. The maintained entity names therefore deliberately avoid the old
`Absolute` wording and preserve the raw wire PSI pending synchronized
Technician display comparison.

## Pressure-pair behavior

Outside the protection event, all cooling intervals continue to show the same
low/high behavior:

- near idle the two `0x383` fields move toward equalization
- on compressor startup the suction field falls
- the paired high-side field rises
- shutdown collapses the split back toward equalization

This is now supported both statistically and by an OEM low-suction protection
event.

## Outdoor thermal families

`0x460.f0` remains strongly associated with the power-electronics thermal
family but is still not independently identified:

- correlation with `0x410.f0`: ~0.985
- correlation with `0x410.f1`: ~0.978
- correlation with `0x430.f0`: ~0.981
- weak/no useful correlation with `0x430.f1` and both `0x450` fields

The Technician app exposes `ViTemp`, but this archive does not prove that
`0x460.f0` is that field. Keep the generic temperature-candidate label.

The following remain raw/unqualified:

- `0x430.f1`
- `0x450.f0`
- `0x450.f1`

## Stator heat

Six isolated stator-heat cycles occurred earlier in the day.

Combined with prior archives, the project now has **64 isolated stator-heat
cycles** supporting:

- `0x282.byte1` -> Stator Heat Enable
- `0x390.byte0` -> Stator Heat Power Level
- `0x388.f0/f1` + `0x389.f0` -> compressor phase-current family

## Safety boundary

All conclusions are receive-side only. Application/control TX remains
fail-closed.
