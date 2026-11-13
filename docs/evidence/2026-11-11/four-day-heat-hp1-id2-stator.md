# November 8–11, 2026 — stator continuity, HP1+ID2 operating state and CANopen replay

Source: `download-2026.11.13_5.1.58-root-(iotmain).tar.gz` containing four complete, non-duplicate archives `trane-2026-11-08.tar.gz` to `trane-2026-11-11.tar.gz`. Read-only CAN analysis; no device or host configuration was changed. The sanitized machine-readable report is available in the analysis session; it intentionally omits source IPs, hardware serials, Wi-Fi and full profile content.

## Archive and transport integrity

| UTC day | Raw CAN frames | Collector JSON | Independent matching SDO JSON | Complete stator cycles |
|---|---:|---:|---:|---:|
| Nov 8 | 2,591,315 | 68 | **68/68** | **24** (one Nov 7 carry-in + 23 new) |
| Nov 9 | 2,593,177 | 210 | **210/210** | **22** |
| Nov 10 | 2,605,921 | 697 | **697/697** | **12** |
| Nov 11 | 2,587,154 | 57 | **57/57** | **20** |

Each archive has 24 hourly JSONL files and 82 CAN IDs, without malformed JSONL records, invalid CAN lengths, ESP device-tick resets or collector lifecycle interruptions. Across all four days **10,377,567 CAN frames** and **1,032/1,032** structured JSON messages independently replay by COB-ID, original order and parsed content, with **zero** SDO aborts, malformed/incomplete sessions or pending transfers. All five CANopen heartbeat nodes `0x701–0x705` remain exclusively operational (`05`), `0x53D` all zero, `0x53E.byte5` five, with no observed NMT/EMCY.

## Stator chronology and exception

The November 7 carry-out starting ~23:54:39.944 UTC ends **November 8 at 00:02:43.071 UTC**, total **8.052 minutes**, counted exactly once. The 23 further November 8 starts, 22 November 9 starts, 12 November 10 starts and 20 November 11 starts all complete with no new carry-out. Thus **609 + 78 completions = 687 completed isolated stator cycles**, and none pending after November 11.

| Day | New-start completed cycle median | Median 0x282-enable to 0x390-power-onset |
|---|---:|---:|
| Nov 8 | 8.647 min | 9.444 s |
| Nov 9 | 8.720 min | 9.236 s |
| Nov 10 | 8.599 min | 9.185 s |
| Nov 11 | 8.739 min | 9.465 s |

Every newly started cycle exhibits the three `0x388.f0/f1` and `0x389.f0` phase-current candidates while compressor speed is zero, as in previous independent stator periods. **One brief `0x390.byte0=18` sample on November 9 at ~02:54:40.548 UTC** occurs during a normal stator onset, which then completes at ~03:03:07 UTC. Normal sustained levels are still 44/45/46, but the prior absolute claim that *all nonzero* values are 44/45/46 is now disproved by this transition sample. Do not interpret 18 as a separately controllable heating level or change timing thresholds.

November 11 also has a fully supported **12.302-minute** isolated cycle (~13:59:48–14:12:06 UTC), longer than earlier recent examples, with phase-current evidence and normal shutdown. Do not impose an invented maximum stator duration.

## November 10 — two heat-pump compressor runs and combined indoor stage

Unlike November 8/9/11, **November 10 is not mechanically idle**. Two verified heat-pump runs based on nonzero `0x384.f0` actual compressor speed and corresponding `0x280` requested speed, `0x385` compressor power, `0x200/0x318` blower request/feedback and `0x320` blower power:

| Run | Compressor actual-speed window (UTC) | Duration |
|---|---|---:|
| 1 | ~12:24:45.814–12:30:50.750 | **6.082 min** |
| 2 | ~12:42:49.894–14:51:08.628 | **128.313 min** |

Total compressor actual-speed runtime **~134.395 minutes** (measured at ≥1 RPS). Highest observed actual and requested speed **58 RPS**, compressor power up to **964 W** in these fields, blower-feedback word up to 1,050 and blower power up to ~156 W. These are observed channel values, not whole-system electric power or verified heater watts.

The raw `0x281.byte7` compressor-request-mode candidate transitions:

- `0` idle → `2` at **12:24:40.036 UTC** during first `HP Stage 1` request;
- `2` → `0` after first run;
- `0` → `2` at **12:42:40.323 UTC** for second run;
- **`2` → `3` at 12:47:42.319 UTC**, lasting **~80.278 s**, then `3` → `2` at 12:49:02.597 UTC;
- `2` → `0` after the long run.

The exact synchronous structured status transitions are `SystemOpStatus.C="HP Stage 1"` at ~12:42:42 UTC, then **`SystemOpStatus.C="HP1+ID2"` at 12:47:55.487 UTC**, then `"HP Stage 1"` again at 12:49:03.284 UTC. `SystemOpStatus.A` shifts from `A` to `H` and back; `OdStatus.1.C` changes `B`→`C`→`B`; and `IndoorStatus.1.E` reaches `100` before returning to `49` and `35`. The compressor stays running through the `3` interval, reaching ~58 RPS; the blower command and feedback increase substantially. The evidence strongly supports **code 3 as a received HP-plus-indoor-stage-2 request/state candidate**, not a general system-mode writer.

**Caution:** the capture does not prove whether the 10 kW electric accessory energized, whether this is defrost, or which physical relays/valves changed. Do not promote code 3 to confirmed electric heat or reversing valve, and do not expose an associated transmit command. The existing raw numeric `0x281.byte7` entity remains intact. The separately disabled diagnostic text entity now labels code 3 `HP + Indoor Stage 2 Request (Observed)`, with regression test coverage; all global and per-family TX gates remain default-off.

## Refrigeration equilibrium and indoor mirrors

Median absolute idle pressure-pair separations (`0x383.f0/f1`) are **1.016** (Nov 8), **0.974** (Nov 9), **1.533** (Nov 10 *full-day including heating*), and **1.107** (Nov 11) raw units. The full-day November 10 median is *not a compressor-idle-only statistic*; running windows show a large pressure differential. Units and gauge/absolute conversion still need synchronized Technician PSI proof.

All structured room and humidity updates match the nearest or a within-two-second `0x490` value: room **34/34** and humidity **181/181** across four days. Independent mirrors support existing room-temperature and humidity semantics, not control writes.

## Four more exact-length/no-NUL `DebugUI` transfers

Four complete `0x641/0x5C1` block-SDO downloads advertise **42 bytes** with no trailing NUL and reconstruct exactly:

- Nov 9 ~00:31:03 UTC: `HiHeapRemaining=20463616`.
- Nov 9 ~21:00:53 UTC: `HiHeapRemaining=19947520`.
- Nov 10 ~05:13:22 UTC: `HiHeapRemaining=19431424`.
- Nov 11 ~07:39:22 UTC: `HiHeapRemaining=18915328`.

Cumulative historical exact-length/no-NUL corpus advances **20→24**, with all four captured values added to the regression fixture. The monotonic decrease of this reported diagnostic is **not** sufficient to conclude an ESP memory leak, especially without verifying the counter's device ownership.

## Engineering boundaries

No `Put` request from the observed structured JSON corpus changes the qualified control surface; independent stock zone-1 setpoint-write samples remain **18**. The November 9–11 Technician sessions include `OdStatus`, `IndoorStatus`, runtime/profile and access-status responses but no newly qualified transmit operation. Keep SC360 as master and retain the default-off global/setpoint/Technician-fan TX gates. System mode, arbitrary JSON, network, auxiliary heat, defrost/reversing valve, EEV and CNT09525/A2L transmit remain blocked.

Current next high-value evidence: specific physical electric-heater stage or relay state synchronized to `HP1+ID2`, deliberate stock system-mode `Put` capture, defrost/reversing-valve status, and Technician-aligned pressure calibration.
