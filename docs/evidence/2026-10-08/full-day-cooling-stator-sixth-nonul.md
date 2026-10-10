# 2026-10-08 full-day mixed idle/cooling, stator and live optional-NUL qualification

Source archive: `trane-2026-10-08.tar.gz`

## Capture integrity

- 24 hourly JSONL chunks, complete UTC day `00:00:00.032` through `23:59:59.971`;
- 2,625,998 total records;
- 2,624,871 raw CAN records;
- 1,127 collector `trane_json` records;
- 82 distinct CAN IDs;
- zero malformed JSONL records and zero invalid DLC/payload-length records;
- no ESP device tick resets or collector lifecycle records.

All 1,127 structured messages were independently reconstructed from the raw CAN stream (563 `0x649` block-download updates and 564 `0x641` messages). They match the emitted collector messages by count and content, with no observed reassembly failures.

## Mechanical state: idle to cooling

The system remains mechanically idle until approximately 19:02 UTC. Eight separate cooling/compressor intervals follow, totaling **~191.75 minutes** of nonzero `0x384.f0` actual speed:

| # | Actual compressor start (UTC) | Stop (UTC) | Duration |
|---:|---|---|---:|
| 1 | 19:02:54 | 19:09:38 | ~6.74 min |
| 2 | 19:20:43 | 21:08:05 | ~107.37 min |
| 3 | 21:15:11 | 21:32:32 | ~17.36 min |
| 4 | 21:40:55 | 21:58:27 | ~17.54 min |
| 5 | 22:06:30 | 22:21:34 | ~15.06 min |
| 6 | 22:30:34 | 22:42:49 | ~12.25 min |
| 7 | 22:55:07 | 23:03:53 | ~8.77 min |
| 8 | 23:25:34 | 23:32:14 | ~6.66 min |

The structured `SystemOpStatus.C` transitions identify about **116.37 minutes AC Stage 1** and **73.54 minutes AC Stage 2**. Most Stage 2 time belongs to the long second run:

- 19:38:13 - 20:50:57 UTC (about 72.73 minutes);
- 20:52:06 - 20:52:55 UTC (about 0.81 minutes), with brief Stage 1 transitions around it.

The distinction between structured Stage 1/2 durations and actual-speed runtime is expected: the state transition and physical compressor ramp/coast are not synchronous.

Peak observed values during this capture:

- `0x280.f0` requested compressor speed ~52.85 RPS;
- `0x384.f0` actual speed ~52.8 RPS;
- `0x385.f0` compressor power 1,024 W;
- `0x38C.f1` outdoor input power 1,207 W;
- `0x281.byte6` compressor demand 60%;
- `0x318.u16@4` blower feedback ~403;
- `0x320.f0` blower power ~16.9 W;
- `0x383.f0` suction-side raw pressure as low as ~77.13 under cooling;
- `0x383.f1` high-side raw pressure as high as ~312.73.

In structured Stage 2 windows the median actual compressor speed is ~44 RPS versus ~29.9 RPS during Stage 1; median compressor power ~790 W versus ~461 W, and median outdoor input power ~940 W versus ~573 W. These are correlations under different loads/ambient conditions, not independent OEM field-unit calibration.

There are **four additional** `0x385.f1=65535` startup sentinels, confirming the existing >200-RPS filter must remain. There is no structured 185.x protection event, A2L/leak alarm, heating, electric heat or defrost in this archive. `TA_INV_HI` appears as the known transient `IndoorStatus.E` state during cooling startup and should not be reclassified as a new fault without independent evidence.

## Compressor request / 0x281.byte7 discrimination

Eight `0x281.byte7=1` intervals appear, exactly aligned with the eight `0x280.f0>0` compressor-request intervals:

- each assertion occurs within roughly 1.1 s of compressor request;
- deassertion is within roughly 2 s of compressor request going to zero;
- `0x281.byte7` asserts before `0x384.f0` actual compressor speed rises;
- on the first short run it clears at ~19:09:03 while compressor speed coasts toward zero until ~19:09:38.

This complements the 2026-10-06 Technician fan-only disproof (blower runs but byte7 stays 0). The strongest current hypothesis is **compressor-request/operation-enable adjacent**, not blower active and not actual compressor motor speed. Retain the neutral `0x281 Byte 7 State Candidate` entity name until heating and other modes isolate the exact semantics.

## Stator heating: 139 -> 152 completed cycles

There are **13 fully completed isolated stator-heat cycles**, all before 14:42 UTC and all with compressor actual speed zero. No stator cycle carries across a day boundary.

New-cycle duration:

- minimum ~7.72 min;
- median ~8.19 min;
- mean ~8.25 min;
- maximum ~9.22 min.

Start-to-start separation:

- minimum ~35.89 min;
- median ~69.02 min;
- mean ~63.53 min;
- maximum ~96.48 min.

The `0x390.byte0` onset follows `0x282.byte1` enable by ~8.90-9.59 s, median ~9.19 s. Its only nonzero observed values remain 44, 45 and 46.

All three compressor-phase-current candidates (`0x388.f0/f1`, `0x389.f0`) assert during each of the 13 cycles. Outdoor input power reaches approximately 88-97 W while actual compressor and outdoor-fan speed stay zero.

Cumulative evidence through **2026-10-08: 152 complete isolated stator-heat cycles**.

The last stator start is ~14:33:40 UTC with outdoor ambient ~73.08 F. No subsequent stator starts occur as ambient rises toward the day's ~88.4 F peak, before cooling starts at 19:02. This independently supports the emerging warm-ambient stator inhibit/eligibility *candidate* from October 7, but still does not establish an exact threshold or rule.

## Refrigeration/pressure baseline

Outdoor ambient spans ~54.72-88.39 F. During the long compressor-idle period before ~19:02 UTC:

- `0x383.f0` suction-side raw spans ~170.31-237.76;
- `0x383.f1` high-side raw spans ~168.06-237.02;
- median absolute separation ~2.05;
- mean absolute separation ~1.69;
- maximum absolute separation ~3.28.

The pair separates strongly in cooling (instantaneous separation reaches ~216 raw units). This further supports the paired suction/high-side roles; gauge-vs-absolute representation remains unqualified.

## Structured data and environmental mirrors

The 1,127 valid messages comprise:

- `Ack`: 563, all `200`;
- `OdStatus`: 355;
- `IndoorStatus`: 100;
- `SystemOpStatus`: 78;
- `ZoneStatus`: 30;
- `DebugUI`: 1.

`SystemOpStatus.E` humidity updates: **13/13** exactly match nearest live `0x490.byte4`.

`ZoneStatus.Update.1.H` room-temperature updates: **5/6** exactly match nearest live `0x490.f0`. The sixth announces 78 F at ~17:49:55.635 UTC, when the last binary sample is 77 F; the binary source changes to 78 F at ~17:49:56.350 UTC, **0.715 s later**, so this is an ordinary ordering/timing difference, not a semantic contradiction.

The numeric `IndoorStatus.E` fan-request updates again scale approximately eight `0x200.u16@2` request units per percentage point, with bounded quantization and asynchronous transition differences. Do not claim that every integer percentage maps to an exactly equal wire multiple.

## Sixth exact-length/no-NUL transfer: receiver works in production

At ~04:20:58 UTC, object `0x300A:00` on request CAN-ID `0x641` carries:

```json
{"DebugUI":{"HiHeapRemaining":"30384128"}}
```

- CANopen block-download initiate advertises **42** bytes;
- JSON UTF-8 length is exactly **42** bytes;
- there is no trailing NUL in the indicated length;
- raw transaction reconstructs correctly;
- **unlike the pre-fix captures, the installed ESPHome bridge emits complete, valid `TRANE_JSON`**.

This is the **sixth independent** exact-length/no-NUL `HiHeapRemaining` sample and direct field verification of the optional-NUL receiver behavior.

All other October 8 structured messages use the normal size-includes-NUL form (563 block-SDO `0x649` status updates and 563 segmented-SDO `0x641` application ACKs). Every raw transaction reconstructs successfully. No large profile body exceeding 512 JSON characters is present, so this day does **not** independently qualify the new `logger.tx_buffer_size: 4608` path for long `EquipSummary`/`WifiList` logs.

## 0x53D / 0x53E node-status persistence

- `0x53D`: all **40,973** samples have first byte zero;
- `0x53E`: byte 5 equals five in all **40,972** samples;
- all five `0x701`-`0x705` heartbeat records are exclusively operational (`0x05`);
- no observed `0x000` NMT or `0x081/0x083` EMCY frames.

The node-count interpretation for `0x53E.byte5` gains another full-day correlation. The `0x53D` field remains unqualified raw network/status.

The `0x2D0.u16@4` airflow-limit/configuration candidate ranges ~755-845, including times when the blower is stopped; it is still not actual airflow.

## Write qualification boundary remains unchanged

There is no observed `SpOverride.Put`, `IndoorSettings.Put`, system-mode write, profile write or other new command family. The existing stock zone-1 setpoint and Technician fan writers remain separately default-off and guarded. Mode/profile/raw JSON, electric heat, defrost and A2L control remain blocked pending independent stock request captures.
