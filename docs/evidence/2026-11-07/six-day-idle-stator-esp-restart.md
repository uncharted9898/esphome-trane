# 2026-11-02–07: six days of isolated stator heating, ESP restart and no-NUL SDOs

This pass analyzes the nested daily archives `trane-2026-11-02.tar.gz` through `trane-2026-11-07.tar.gz` from the 2026-11-07 `iotmain` export. The included 2026-11-01 archive has the same SHA-256 as the one already qualified; it was re-run as a **regression baseline**, not counted again. Analysis was entirely read-only; no CAN transmissions or device configuration changes occurred.

## Complete archive and independent transport verification

| UTC day | CAN frames | Collector JSON | Exact raw SDO replay | Completed isolated stator cycles | Median cycle duration | Median power onset |
|---|---:|---:|---:|---:|---:|---:|
| Nov 2 | 2,590,225 | 10 | 10/10 | 20, plus one carry-out | 8.127 min | 9.002 s |
| Nov 3 | 2,594,231 | 215 | 215/215 | 20 (one Nov 2 carry-in + 19 new starts) | 8.237 min on new starts | 9.380 s |
| Nov 4 | 2,591,832 | 42 | 42/42 | 19 | 8.114 min | 9.354 s |
| Nov 5 | 2,591,795 | 183 | 183/183 | 14 | 7.644 min | 9.282 s |
| Nov 6 | 2,593,446 | 10 | 10/10 | 17 | 7.544 min | 9.211 s |
| Nov 7 | 2,592,808 | 142 | 142/142 | 22, plus one carry-out | 8.229 min | 9.272 s |

Each archive contains **24 hourly JSONL files**, the full UTC day, 82 unique CAN IDs, zero malformed JSONL lines or invalid CAN payload lengths. Across the six new days: **15,554,337 raw CAN frames**, **15,554,943 total JSONL records**, and **602/602 independently reassembled structured JSON messages**, matched in original capture order, source COB-ID and parsed JSON body. There are zero SDO aborts, incomplete transactions, malformed reconstructed JSON bodies, collector mismatches, or newly observed `Put` command families.

The previous November 1 archive was reprocessed with the same streaming analyzer. It reproduces the previously verified **20 complete cycles**, **30/30 structured messages**, and the `SystemSettings.Update.J="-0500"` received-status transaction. This provides a baseline check of the new analysis workflow.

## Stator cycle accounting across midnight: 497 → 609

November 2 has **20 fully completed** cycles and one stator enable beginning at approximately **23:55:54 UTC**, which carries into November 3. It deasserts at **00:03:38 UTC** on November 3. The complete interval is approximately **7.73 minutes**, and is counted exactly once, as a November 3 completion. November 3 separately adds 19 newly started and completed cycles.

November 4/5/6 contribute **19/14/17** new completions. November 7 contributes **22 completed cycles**, but another stator enable begins at approximately **23:54:39 UTC** and remains asserted at the November 7 archive boundary. This last cycle is **pending November 8 proof of completion**, not part of the 609 completed-cycle total.

Thus, **497 previously complete + 20 Nov 2 + 20 Nov 3 + 19 Nov 4 + 14 Nov 5 + 17 Nov 6 + 22 Nov 7 = 609 fully observed isolated stator cycles**, plus one November 7 carry-out.

All completed cycles and both carry-out edges have the same verified `0x282.byte1` enable, ~9-second later nonzero `0x390.byte0` values **44/45/46**, and all three `0x388.f0/f1`, `0x389.f0` phase-current candidate channels nonzero while actual compressor speed remains **zero**. No hardcoded maximum duration, power-level unit or ambient inhibit rule is justified.

## Mechanical idle, refrigeration pressure and indoor mirrors

Across all six days, compressor request, actual compressor speed/power, blower request, motor feedback/power, airflow target, demand and `0x281.byte7` request-mode remain **zero**. No cooling, heat-pump heating, defrost, electric auxiliary heat, mitigation/A2L, 185.x pressure alarm or system-mode command is evidenced.

Ambient ranges from **50.30°F** on November 3 up to **80.95°F** on November 5. Median absolute idle `0x383.f0/f1` pressure-pair separations by date are **0.826, 1.239, 1.426, 1.161, 0.899, 0.630 raw units**. These are equilibrium/suction-high-side mapping evidence, *not validated PSI scaling or absolute/gauge conversion*.

Sparse structured mirror updates remain consistent with live binary `0x490`: all **273/273 humidity** updates and **27/27 room-temperature** updates have matching binary values within two seconds (nearest exact: 260/273 humidity and 26/27 room). Differences reflect sparse update ordering, not a new semantic mapping.

## Two very different restarts

- **November 2, ~06:16:23 UTC:** ESP32 device-tick counter drops from approximately 1,264,132,625 ms to 5,721 ms, and the collector records a reconnect. This is a real **bridge device-clock reset**, not just a collector restart. On the OEM Link bus, all five nodes stay CANopen operational (`0x701–0x705 = 0x05`), `0x53E.byte5` remains 5, `0x53D` remains zero, and there is **no observed NMT reset or EMCY**. The reset's cause cannot be inferred from CAN traffic alone. The offline analyzer uses a monotonic virtual device-tick timeline across the epoch change so cycle durations, phase correlation and UTC dates are not corrupted. Event times immediately around the reset are approximate.
- **November 5, 11:11:44–11:11:56 UTC:** collector stop/start/connect records, **without** an ESP device-tick reset or OEM Link network reset. This is a separate collector-process interruption.

The separately added ESPHome uptime, last reset reason and heap diagnostic entities are the appropriate next source for diagnosing bridge resets; do not assign blame to an OEM controller without corroboration.

## Nineteenth and twentieth no-NUL `DebugUI` samples

Two additional complete stock `0x641/0x5C1` block-SDO transactions advertise exactly **42 bytes**, with no trailing NUL:

- **November 3 ~04:07:29 UTC:** `{"DebugUI":{"HiHeapRemaining":"21495808"}}`;
- **November 5 ~11:18:14 UTC:** `{"DebugUI":{"HiHeapRemaining":"20979712"}}`.

Both have successful transport handshakes and valid collector JSON. These increase the independent exact-length/no-NUL field corpus from **18 to 20**. The values continue to decline in 516,096-byte steps relative to the earlier captures, but **neither a memory leak nor the device owning this counter is established**.

## Write and safety boundary

The independent stock zone-1 `SpOverride.Put` corpus stays at **18**; the October 6 Technician indoor-fan 0/1, 50/100 command sequence remains the only second qualified application TX family. Both remain **default-off and separately gated** behind global TX. No system mode, SystemSettings, network/profile, arbitrary JSON, electric heat, EEV, defrost/reversing valve or CNT09525/A2L TX is newly qualified.

This pass calls for dated evidence, the two additional captured no-NUL regression values and maintained stator/source comments — **not new runtime decoder or transmitter behavior**.

Daily nested-archive SHA-256 checksums are retained in the separate sanitized analysis output, which excludes original Wi-Fi IDs, equipment serial numbers, source IP addresses and full profile data.
