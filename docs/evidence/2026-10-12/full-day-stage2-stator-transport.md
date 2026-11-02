# 2026-10-12 full-day Stage 2, isolated stator heat, and CANopen transport qualification

Source: `trane-2026-10-12.tar.gz`. Archive SHA-256:
`ed906855983e17a65562a5f585248ec9d75c5caddc8c57ec7ab863502ba90ca0`.

This pass is passive/read-only. The full event-level calculation output is retained in the accompanying downloadable `trane-2026-10-12-analysis.json` from the analysis session; the archive itself is not committed.

## Integrity and time model

- 24 hourly JSONL chunks, covering 2026-10-12 00:00:00.000 to 23:59:59.859 UTC.
- 2,637,881 records total: 2,636,299 raw CAN and 1,582 structured `trane_json`.
- 82 unique 11-bit CAN identifiers; zero malformed JSONL or invalid CAN DLC/payload records.
- No device-tick resets or collector lifecycle events.
- Operating intervals use the ESP32 device tick, with UTC fitted to the low-latency portion of the host timestamp stream. The collector can briefly batch frames; host arrival time alone is not reliable for subsecond event sequencing.

The complete raw SDO stream was replayed **in captured frame order**. This matters when requests and responses share the same millisecond device tick: sorting ties by numeric CAN ID falsely reorders three valid ACK exchanges on this day. Order-preserving replay correctly reconstructs all transactions.

## CANopen transport: 1,582 / 1,582 correct

- 791 block-SDO status transfers `0x649/0x5C9`, all complete.
- 791 segmented application acknowledgements `0x641/0x5C1`, all `{"Ack":"200"}`.
- All 1,582 reconstructed JSON bodies match the collector **in original order**.
- Zero SDO aborts, incomplete transfers, malformed JSON, sequence/ACK failures, or missing collector messages.
- Status roots: `OdStatus` 534, `IndoorStatus` 151, `SystemOpStatus` 77, `ZoneStatus` 29; application `Ack` 791.
- Every transaction on this day advertises a payload length **including the terminating NUL**. There is **no ninth** exact-length/no-NUL `DebugUI.HiHeapRemaining` event; the October 11 eighth example remains the latest.
- Maximum CANopen JSON wire length was 75 bytes (74 JSON bytes plus NUL). The installed `logger.tx_buffer_size: 4608` change still has not been exercised by a new >512-byte `EquipSummary` or `WifiList` profile capture.

There is **no** `SpOverride.Put`, `IndoorSettings.Put`, system-mode `Put`, profile-write or newly observed command family. The seven stock setpoint writes and October 6 Technician fan sequence remain the only qualified application TX families.

## Nine actual compressor-running intervals

Runs are measured using nonzero `0x384.f0` actual compressor speed, not inferred from the status broadcast alone. All times approximate UTC.

| Run | Start | End | Actual runtime |
|---:|---|---|---:|
| 1 | 17:03:31 | 17:10:29 | 6.98 min |
| 2 | 17:23:06 | 20:54:25 | **211.32 min** |
| 3 | 21:02:48 | 21:14:44 | 11.93 min |
| 4 | 21:27:31 | 21:36:44 | 9.22 min |
| 5 | 21:51:30 | 22:00:23 | 8.88 min |
| 6 | 22:13:41 | 22:22:39 | 8.96 min |
| 7 | 22:41:31 | 22:48:54 | 7.38 min |
| 8 | 23:08:22 | 23:16:00 | 7.63 min |
| 9 | 23:36:00 | 23:43:29 | 7.48 min |

Total nonzero-speed runtime: **279.77 minutes**.

Structured `SystemOpStatus.Update.C` records show ~101.54 minutes in `AC Stage 1` and **176.26 minutes uninterrupted in `AC Stage 2`**, from 17:52:28.491 to 20:48:44.033 UTC. That Stage 2 period belongs to the 211.32-minute physical run. The discrepancy between total structured run-state time and physical motor runtime is explained by normal request/ramp/coast transitions.

| Physical observation | Stage 1 median | Stage 2 median |
|---|---:|---:|
| `0x384.f0` actual speed | ~29.8 RPS | ~44.2 RPS |
| `0x385.f0` compressor power | ~452 W | ~756 W |
| `0x38C.f1` outdoor input power | ~566 W | ~924 W |
| `0x320.f0` blower power | ~8.05 W | ~14.09 W |

Observed day maxima: actual compressor speed 58.0 RPS; compressor power 1,162 W; outdoor input power 1,358 W; blower feedback word 520; blower power ~29.41 W; outdoor ambient ~83.58 F. These are operating observations, not nameplate ratings. Six further `0x385.f1=65535` invalid speed-ceiling startup sentinels support retaining the existing numeric sanity filter.

### 0x281.byte7 remains compressor-request adjacent

There are nine `0x281.byte7=1` intervals, one for every `0x280.f0>0` compressor-request interval. On/off differences are about -0.90 to +1.68 seconds, while actual compressor speed typically starts 4.50–10.10 seconds after request.

On the first run, actual compressor speed continues for **~46.55 seconds after the request clears**, so byte7 is neither blower-active (disproved by October 6 fan-only testing) nor an actual-motor-speed flag. Keep the public entity named `0x281 Byte 7 State Candidate`; exact compressor enable/operation semantics remain unqualified.

## Eight new complete isolated stator-heat cycles: 179 -> 187

All eight complete on October 12 with no archive-boundary carry-in/out and actual compressor speed zero throughout each event.

| Enable UTC | Duration | Ambient at start | First nonzero 0x390 lag |
|---|---:|---:|---:|
| 04:52:17 | 7.72 min | 68.18 F | 8.942 s |
| 06:38:43 | 7.62 min | 67.67 F | 9.712 s |
| 08:27:48 | 7.50 min | 65.77 F | 9.000 s |
| 10:10:39 | 8.45 min | 64.83 F | 8.788 s |
| 11:40:25 | 7.79 min | 64.58 F | 9.167 s |
| 12:40:48 | 8.20 min | 66.36 F | 9.337 s |
| 13:40:03 | 8.75 min | 69.40 F | 9.730 s |
| 14:38:33 | 7.42 min | **77.35 F** | 9.598 s |

- Duration: 7.42–8.75 minutes, median **7.76**, mean 7.93.
- Start-to-start separation: 58.49–109.09 minutes, median 89.76.
- Enable-to-`0x390.byte0>0` lag: 8.788–9.730 seconds, median **9.25**.
- Nonzero `0x390.byte0` remains 44/45/46; exact units still unconfirmed.
- `0x388.f0/f1` and `0x389.f0` all carry nonzero phase-current candidates within each isolated event. Outdoor input power rises to ~89–97 W while actual compressor speed remains zero.

Cumulative evidence through October 12: **187 fully completed isolated stator-heat cycles**. The new 77.35 F start reinforces the October 11 disproof of a fixed 75 F inhibit threshold. Scheduling/eligibility remains unknown and must not be hard-coded.

## Suction/high-side pressure interpretation

The `0x383.f0/f1` pair continues separating during cooling and equalizing at idle:

- suction-side raw field overall ~85.89–233.85;
- high-side raw field overall ~195.59–315.89;
- median absolute separation across all compressor-running samples ~142.85 raw units;
- during Stage 2 alone ~153.81 raw units, with a maximum ~180.19;
- for compressor-idle samples at least 20 minutes after the latest completed compressor run, median absolute separation **~0.97** raw units (30,503 samples).

This supports the existing pressure pair roles, **not** a verified PSI conversion. The actual gauge/absolute representation, exact field scaling and Technician display calibration remain unresolved.

## Structured room/humidity and thermal families

- All three `ZoneStatus.Update.1.H` room-temperature updates exactly match nearest `0x490.f0`.
- Six of seven `SystemOpStatus.Update.E` humidity values exactly match nearest `0x490.byte4`. The one apparent mismatch announces 61 while the nearest binary sample still says 62; the binary source changes to 61 **0.626 seconds later**. This is update ordering, not semantic disagreement.
- `0x460.f0` correlates with nearby electronics-thermal candidates (`0x410.f0` r ~0.970, `0x410.f1` r ~0.978, `0x430.f0` r ~0.984). It also correlates with ambient on this day (r ~0.904), so do not promote it to a specific electronics sensor. Even a simple ambient-adjusted correlation with `0x410.f0` remains ~0.882, but sensor ownership and units are still unproven.
- The raw unresolved `0x430.f1` channel contains one isolated ~-459.67 sample at ~03:50 UTC. It remains disabled/raw rather than being labeled as a temperature or fault.
- `0x2D0.u16@4` remains nonzero (~748–825) during both blower operation and idle. It is not actual delivered airflow.

## Stable network and safety boundaries

All **41,001** `0x53D` frames are `00 00 00 00 00`, and all **41,001** `0x53E` frames are `00 00 00 00 01 05`. All five heartbeat nodes `0x701..0x705` remain exclusively operational (`0x05`). No NMT reset or `0x081/0x083` EMCY event is present.

There is no supported evidence for electric-heat stage activation, defrost/reversing-valve transition, 185.x low-pressure protection or CNT09525/A2L mitigation action on this day.

Qualified zone-1 setpoint and Technician fan 0/1, 50/100 TX remain **independently default-off**, both requiring global TX and their own qualification gate. Mode, profile, arbitrary JSON, electric heat stages, EEV, defrost, reversing valve and A2L writes remain unqualified/blocked.

October 12 warrants a dated evidence update and refreshed cumulative comments, **not a runtime code change or expanded write permissions**.
