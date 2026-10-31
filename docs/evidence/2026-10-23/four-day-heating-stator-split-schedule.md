# October 20–23: four-day continuity, 73 stator cycles and split Schedule

The target's four daily archives were analyzed as one continuity window, with October 20–21 observations carried forward from the prior pass. **Cumulative completed isolated stator-heat cycles: 328** (255 before October 20, +14 Oct 20, +19 Oct 21, +19 Oct 22, +21 Oct 23). Stock zone-1 setpoint writes: **18** (14 through October 19, +3 on October 21, +1 on October 22). Exact-length/no-NUL DebugUI transfers: **14** (12 before October 20, +1 Oct 21, +1 Oct 23).

## October 22–23 verified archive integrity

| UTC day | Hourly chunks | Raw CAN | Collector JSON | Unique IDs | Malformed/DLC errors | ESP clock resets |
|---|---:|---:|---:|---:|---:|---:|
| 2026-10-22 | 24 | 2,595,651 | 165 | 82 | 0 | 0 |
| 2026-10-23 | 24 | 2,592,971 | 159 | 82 | 0 | 0 |

All five CANopen heartbeat nodes are continuously operational (0x05) on both days. No NMT reset or EMCY is captured. The 0x53D frames stay all-zero, while 0x53E.byte5 remains 5. Both days have zero compressor request/actual speed/power and zero blower request/feedback/power. October 22 has **19 complete isolated stator cycles** (median 8.48 minutes, onset lag median 9.35 s); October 23 has **21 complete isolated cycles** (median 8.59 minutes, lag median 9.11 s). Nonzero 0x390.byte0 stays 44/45/46; all cycles occur with compressor speed zero. No cycle spans midnight.

The 0x383 pressure pair remains equalized while stopped: median absolute separation ~1.84 raw units on October 22 and ~1.47 on October 23. Units, gauge/absolute calibration and mapping to Technician PSI are still unresolved.

## CANopen JSON replay and new split Schedule

October 22 reconstructs **165/165 collector JSON messages** and October 23 **159/159**, matched by source CAN ID, content and original order; no collector mismatch or aborted/incomplete SDO session. Two *additional* October 22 status-channel block-SDO downloads are independently complete but contain invalid stand-alone JSON. Their indicated wire payloads are **2048 bytes** (without NUL) and **1626 bytes** (1625 JSON bytes plus NUL). Concatenation yields a **3673-byte valid Schedule JSON document**. The pre-change component does not emit this logical document because it only joined captured WifiList fragments.

The bounded passive profile assembler is now extended to recognize either a 2048-byte WifiList or Schedule first fragment. Continuations are accepted on status channel 0x649 within five seconds, with a 4096-byte maximum, and new JSON roots abort the old fragment. The prior WifiList helper name remains compatible. No new application TX or CANopen writer path was introduced. The native regression tests now include both captured profile lengths, wrong-channel traffic, new-root interruption, timeout and overflow.

October 22's Technician/profile sweep also emits valid 1072-byte DailyRuntime, 1597-byte MonthlyRuntime and 596-byte ZoneStatus messages; all are logged intact. The 165 collector messages exclude the unlogged split Schedule because neither half is separately valid. October 23 contains a 42-byte exact-length/no-NUL `DebugUI.HiHeapRemaining=24076288` that reassembles and logs correctly. The observed descending heap value is **not** proof of a memory leak.

## Setpoint and remaining boundaries

October 22 contains a stock `SpOverride.Put` (zone 1, Csp 78 F, Hsp 68 F, HoldType 1, Source 1) followed by accepted state and application ACK 200, raising the independent stock setpoint corpus to 18. No system-mode, heat-stage, defrost, reversing-valve or A2L control family was captured or enabled. All existing global and per-family write gates remain default-off. The SC360 remains the master controller.

October 20–21 also contributed three HP Stage 1 heating runs totaling ~21.29 minutes on October 20, followed by a mechanically idle October 21. October 21's three zone-1 stock setpoint writes show heating setpoint 69→70→69 F and the same established transport/policy.

Source archives: `trane-2026-10-20.tar.gz`, `trane-2026-10-21.tar.gz` (previous pass); `trane-2026-10-22.tar.gz` (SHA-256 `1d51adc867a1f00278ba12fce82f0add7d020311532d598c3a0e353f37c5063f`); `trane-2026-10-23.tar.gz`. The October 22–23 machine-readable report is exported separately with no device serial, IP, Wi-Fi identifier or Schedule content.
