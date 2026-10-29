# 2026-10-27–28 — two full cold-idle days, 39 stator cycles and sixteenth no-NUL transfer

Sources: `trane-2026-10-27.tar.gz` (SHA-256 `b97612e2f92f376646690c1376d8c6ca4834afe7ce7c3a8293b9895dafbdd82a`) and `trane-2026-10-28.tar.gz` (SHA-256 `2070f7fcae22cfae1592b00b97d7e15fee8e2062e1ba92f7e410d06565b05dd3`). Both archives analyzed read-only; no CAN frames transmitted.

## Integrity and exact CANopen replay

| UTC day | Hourly chunks | Raw CAN | Collector JSON | Other records | CAN IDs | Bad JSONL/DLC |
|---|---:|---:|---:|---:|---:|---:|
| October 27 | 24 | **2,594,620** | **113** | 0 | 82 | 0 |
| October 28 | 24 | **2,591,582** | **20** | 3 collector lifecycle | 82 | 0 |

Both cover the entire UTC day and neither shows an ESP device-tick regression. The raw CANopen SDO stream was independently reassembled in **original frame order**, with strict comparison of every decoded JSON object and source CAN identifier to the collector output:

- October 27: **57** complete block-SDO downloads (`0x649/0x5C9` status plus one `0x641/0x5C1` DebugUI), **56** segmented application ACKs, **113/113** collector messages matched.
- October 28: **10** complete status block downloads, **10** segmented application ACKs, **20/20** collector messages matched.
- All **66** application ACKs are `{"Ack":"200"}`.
- No incomplete, aborted, out-of-sequence, orphaned, malformed or unmatched SDO transaction across either day.
- No stock setpoint, fan, system-mode, profile, network or other `Put` commands. No >512-byte structured profile appears.

## Mechanical idle and isolated stator heating

Every compressor request, actual speed, compressor power, blower request, motor-feedback word, blower power, airflow target, and compressor-demand field stays **zero** throughout both days. The raw `0x281.byte7` request-mode field is zero in every observation. No mechanical cooling, heat-pump heating, electric auxiliary heating, defrost or pressure/A2L alarm event is evidenced.

October 27 contains **20 fully completed isolated stator-heat cycles**, October 28 contains **19**. Neither day has a stator carry-in or carry-out. Every cycle has `0x282.byte1` enable, nonzero `0x390.byte0` about nine seconds later, and nonzero signals on all three `0x388.f0/f1`, `0x389.f0` phase-current candidates while actual compressor speed stays zero.

| Stator measurement | October 27 | October 28 |
|---|---:|---:|
| Completed cycles | **20** | **19** |
| Cycle duration min/median/max | 7.415 / **8.521** / 10.585 min | 7.365 / **8.283** / 8.789 min |
| Power-level onset min/median/max | 8.924 / **9.068** / 9.764 s | 8.785 / **9.222** / 9.748 s |
| Start-to-start median | **62.94 min** | **65.40 min** |
| Outdoor ambient range | **43.77–75.74°F** | **54.04–74.30°F** |

The only observed nonzero stator power-level byte values remain **44, 45 and 46**. Outdoor input power peaks at **97 W** on each day during isolated stator cycles. The 10.585-minute October 27 cycle is fully observed and should not be treated as an overlong timeout or corrupt edge.

**Cumulative corpus through October 28: 425 complete isolated stator-heat cycles** (386 prior + 39 new). Do not infer a controller scheduling rule, temperature inhibit or commandable wattage from these passive observations.

## Refrigeration pressure equilibrium and indoor mirrors

Under complete compressor idle, the paired `0x383.f0/f1` raw pressure fields remain closely equalized:

| Pressure evidence | October 27 | October 28 |
|---|---:|---:|
| Pair observations | 42,940 | 42,915 |
| Absolute separation median | **1.395** | **1.174** raw units |
| Absolute separation maximum | **2.375** | **3.177** raw units |
| Ambient correlation f0 / f1 | **0.9944 / 0.9958** | **0.9926 / 0.9955** |

These reinforce the paired suction/high-side interpretation but **do not establish PSI units or gauge-vs-absolute calibration**. The `0x2D0.u16@4` airflow-limit/configuration candidate remains nonzero despite all actual blower signals being zero; it is not delivered airflow.

Structured mirror results:

- October 27: **8/8** room-temperature `ZoneStatus.1.H` match nearest `0x490.f0`; **45/48** humidity `SystemOpStatus.E` match nearest `0x490.byte4`, all **48/48** match a nearby binary value within 2 seconds.
- October 28: **5/5** room and **5/5** humidity structured updates match the nearest corresponding `0x490` field.

## Sixteenth exact-length/no-NUL transfer

At approximately **2026-10-27 17:13:02 UTC**, stock `0x641/0x5C1` block-SDO object `0x300A:00` advertises **exactly 42 bytes** carrying:

```json
{"DebugUI":{"HiHeapRemaining":"23044096"}}
```

There is **no trailing NUL**. The entire transaction and application JSON log reconstruct successfully on the deployed bridge. This increases the captured exact-length/no-NUL corpus to **16**, with the analyzer regression fixture extended accordingly. October 28 contains no additional DebugUI/no-NUL example. The descending heap diagnostic series alone does **not** demonstrate a memory leak, or identify which device owns the diagnostic value.

## Collector lifecycle and stock Link network

On October 28, the collector records `stop` at **05:09:43.521 UTC**, `start` at **05:09:56.504 UTC** and `connected` at **05:09:56.520 UTC**. The ESP device tick never regresses; the capture does not establish the reason for the collector interruption.

All five node-heartbeat IDs `0x701` through `0x705` remain exclusively `0x05` operational throughout the observed frames on both days. There are no `0x000` NMT commands or `0x081/0x083` emergency messages. `0x53D` remains all-zero (40,895 / 40,929 frames) and `0x53E` remains `000000000105` (40,892 / 40,928 frames).

This supports a **collector-process restart**, not an observed ESP reboot or OEM network-reset event. The October 26 exact-head CI run was **cancelled**, not a passing qualification; check the new exact-head workflow before recommending firmware deployment.

## Write safety boundary

The total stock zone-1 setpoint-write corpus remains **18** and the independently captured Technician indoor-fan write family remains unchanged. Global and per-family TX gates stay default-off. System mode, profiles/network, arbitrary JSON, auxiliary heat stages, EEV, defrost/reversing valve and CNT09525/A2L writers remain blocked. October 27–28 require evidence and a narrow regression fixture, **not new runtime decoder or TX behavior**.
