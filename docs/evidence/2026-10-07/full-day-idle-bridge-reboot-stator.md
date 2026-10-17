# 2026-10-07 full-day idle, bridge reboot and stator/network evidence

Source bundle: `trane-2026-10-07.tar.gz`

## Capture integrity

- 24 hourly JSONL chunks
- 2,592,872 total JSONL records
- 2,592,845 raw CAN records
- 26 collector `trane_json` records
- 1 collector lifecycle record
- 82 unique CAN IDs
- zero malformed JSONL rows
- UTC coverage approximately 00:00:00.006 through 23:59:59.981

The ESP bridge itself reboots/reconnects around 10:42 UTC:

- last pre-reboot device tick: 680,049,457 ms at ~10:42:01.653 UTC
- collector `connected` event: ~10:42:14.580 UTC
- first post-reboot CAN tick: 5,898 ms at ~10:42:14.700 UTC

No OEM NMT reset traffic appears on `0x000`, no EMCY appears on `0x081` or
`0x083`, and CANopen heartbeat nodes 1 through 5 remain operational
(`0x05`) throughout the captured day. This is useful field evidence that a
bridge reboot does not reset the stock Link network, though it is not a
substitute for the planned explicit bridge-removal/failure qualification.

## Mechanical state

The HVAC equipment remains mechanically idle for the full day:

- `0x280.f0` compressor request = 0
- `0x384.f0` actual compressor speed = 0
- `0x385.f0` compressor power = 0
- `0x200.u16@2` blower request = 0
- `0x318.u16@4` blower feedback = 0
- `0x320.f0` blower power = 0
- `0x281.u16@0` airflow target = 0
- `0x281.byte6` compressor demand = 0
- `0x281.byte7` state candidate = 0

No cooling, heating, fan-only, defrost, reversing-valve, A2L/leak or 185.x
pressure-protection event appears.

## Stator heat: carry-in closes and 15 new cycles complete

The stator cycle that began near the end of the October 6 archive is still
active at midnight and clears at approximately 00:00:59 UTC. That closes the
previous carry-out cleanly.

October 7 then contains **15 new fully completed stator-heat cycles**. Excluding
the carry-in cycle from same-day cadence statistics:

- cycle duration:
  - min ~7.27 min
  - median ~8.27 min
  - max ~9.97 min
  - mean ~8.43 min
- start-to-start spacing:
  - min ~37.73 min
  - median ~72.61 min
  - max ~290.24 min
  - mean ~81.70 min
- `0x390.byte0` onset after `0x282.byte1` enable:
  - min ~8.77 s
  - median ~9.07 s
  - max ~9.77 s
  - mean ~9.13 s

Nonzero `0x390.byte0` remains confined to:

- 44
- 45
- 46

Every one of the 15 new cycles again shows nonzero values on all three
compressor-phase-current candidate channels:

- `0x388.f0`
- `0x388.f1`
- `0x389.f0`

while compressor speed remains zero. Outdoor input power rises into roughly
88-97 W during these cycles.

The continuous project corpus therefore advances from **123 completed + one
carry-out** to **139 completed isolated stator-heat cycles**.

### Ambient-inhibit clue

Outdoor ambient spans approximately 50.16-79.44 F, much wider than the previous
idle baselines.

Stator starts continue as ambient rises through the low 70s, with starts near
70.7 F and 73.4 F. After the ~15:57 UTC start there is then a ~290-minute gap
while ambient spends the warmest part of the day mostly around 75-79 F. Stator
heat resumes near 20:48 UTC as ambient has fallen to about 74.8 F.

This is the first strong full-day clue that stator scheduling has an
outdoor-temperature inhibit/eligibility boundary in roughly this region. It is
**not** enough evidence to hard-code a 75 F threshold; keep it as a scheduling
candidate only.

## Idle pressure equalization

With the compressor stopped all day:

- outdoor ambient `0x380.f1`: ~50.16-79.44 F
- `0x383.f0`: ~157.98-229.21
- `0x383.f1`: ~156.34-227.52
- absolute pressure-pair separation:
  - median ~1.70
  - mean ~1.74
  - maximum ~3.68

The two fields continue to track as an equalizing suction/high-side pressure
pair over a very broad ambient range.

## Structured room/humidity mirrors

The archive contains only 26 emitted structured JSON records:

- 8 `ZoneStatus.Update.1.H` room-temperature updates
- 5 `SystemOpStatus.Update.E` humidity updates
- 13 application `{"Ack":"200"}` responses

All eight room-temperature values exactly match the nearest `0x490.f0` sample.
All five humidity values exactly match the nearest `0x490.byte4` sample. Every
comparison is within roughly one second.

There is no `SpOverride.Put`, `IndoorSettings.Put`, system-mode write or new
application command family on this day.

There is also no `0x601/0x581` or `0x621/0x5A1` Debug transfer, so October 7
does not add a sixth exact-length/no-NUL `DebugUI.HiHeapRemaining` example.

No long structured profile body occurs after the logger-buffer increase, so
this archive does **not** yet validate the 4,608-byte ESPHome logger TX buffer
under a >512-byte `TRANE_JSON` line.

## 0x2D0 is not actual airflow

October 7 is particularly useful for the `0x2D0` family because every real
blower signal is zero for the full day.

Despite that:

- `0x2D0.word1` at byte offset 2 varies roughly 513-765
- `0x2D0.word2` at byte offset 4 varies roughly 773-827

The second word therefore cannot be delivered/actual airflow. This strongly
supports the existing **airflow limit/ceiling/configuration candidate**
interpretation.

The maintained source already reads the airflow-limit candidate from byte offset
4. The maintained telemetry document was stale and still said
`0x2D0.u16@2`; it is corrected to `0x2D0.u16@4`.

## 0x53D / 0x53E network-status refinement

October 7 weakens the old notion that `0x53D 01 00 00 00 00` represents a
universal steady-state value.

Across the entire day:

- all 40,986 `0x53D` frames are `00 00 00 00 00`
- all 40,986 `0x53E` frames are `00 00 00 00 01 05`
- heartbeat nodes `0x701` through `0x705` are all continuously
  `0x05` (operational)

The bridge-only reboot near 10:42 UTC does not change those OEM heartbeat
states.

Consequences:

- `0x53D` must remain raw; byte0=1 is not required for a healthy five-node
  operational network.
- `0x53E.byte5 = 5` gains another independent full-day correlation with five
  simultaneously operational heartbeat nodes, strengthening—but not yet
  promoting beyond—the active/available Link node-count candidate.

## Safety boundary

No new application write family is qualified by October 7.

The active control boundary remains:

- zone-1 `SpOverride.Put` setpoints: qualified + dedicated opt-in
- Technician `IndoorSettings.Put` fan enable/disable and 50/100%: qualified +
  separate dedicated opt-in
- system mode: blocked
- profile writes: blocked
- arbitrary JSON: blocked
- electric heat / defrost / EEV / A2L control: blocked
