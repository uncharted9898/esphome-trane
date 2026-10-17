# 2026-10-15 and 2026-10-16 — Technician sweep, split JSON, node restart, and long Stage 2

Sources: `trane-2026-10-15.tar.gz`, `trane-2026-10-16.tar.gz`. Read-only analysis, no CAN transmission. The machine-readable companion is sanitized before sharing: captured Wi-Fi SSIDs, device serials, and other identifiers are not reproduced here.

## Integrity, including resets

| UTC day | JSONL chunks | Records | Raw CAN | Emitted JSON | CAN IDs | Malformed/DLC faults |
|---|---:|---:|---:|---:|---:|---:|
| October 15 | 24 | 2,666,155 | 2,663,799 | 2,355 | 101 | 0 |
| October 16 | 24 | 2,677,378 | 2,674,754 | 2,624 | 81 | 0 |

The combined raw replay reconstructs **4,979/4,979 emitted JSON bodies**, matching original capture order. The October 15 Technician session additionally contains two application-level fragments that each fail independent JSON parsing but concatenate to valid JSON, described below. Four partial SDO attempts coincide with the 22:59 device restart and should not be conflated with ordinary steady-state transport failures.

## October 15 Technician sweep: newly exercised long logger lines

Two full `EquipSummary` messages carry 1,377 JSON bytes each and are emitted in full by the installed bridge. A `WifiList` update also contains 639 JSON bytes (640 including NUL) and is logged in full. These observations provide overdue **on-device confirmation** that the post-October 6 logger `tx_buffer_size: 4608` supports >512-byte messages; they do not prove every possible 4096-byte message remains within all downstream limits.

The stock profile confirms the existing equipment identities and the installed 10 kW single-phase two-stage electric heater accessory. It does not establish *live* stage-1/stage-2 heat feedback. Stock `SystemSettings.Put: {}` and `NetworkProperties.Put` requests were observed in the Technician session. Their semantics and safe scope are **unqualified**; do not enable either writer.

### Previously unseen application-level WifiList continuation

A stock `0x649/0x5C9` transfer advertises **2048 bytes** of a `WifiList` document, ending inside a JSON string. A second independent `0x649/0x5C9` transfer advertises **306 bytes** (305 content + NUL) containing the continuation. Independently, both fragments are invalid JSON. Joined at the advertised boundary, they form one valid **2353-byte JSON document**. Transport framing/ACKs are valid; the application document spans two completed SDO downloads.

The maintained bridge now has a *receive-only*, bounded WifiList assembler: it recognizes only the captured 2048-byte WifiList prefix, accepts a continuation from the same 0x649 channel within 5 seconds, caps the assembled message at 4096 bytes, and discards expired/unrelated fragments. It does not change CANopen writes or expose any new TX family. Regression tests cover successful concatenation, timeout, source restrictions and preventing interleaving with a new JSON root.

## October 15 bridge restart and actual OEM node event

At approximately **22:59:27 UTC** the ESP device clock resets. The captured Link bus subsequently carries:

- `0x000: 81 03` — node 3 reset command at ~22:59:44;
- `0x53E.byte5`: 5 → 4 temporarily;
- node-3 heartbeat `0x703`: boot-up `00`, then pre-operational `7F`;
- `0x000: 01 03` — node 3 start command at ~22:59:50;
- `0x083` EMCY all zeros and later `0x081` EMCY with nonzero payload (retain raw code);
- subsequently all five heartbeat nodes return to `05` operational.

**This is not merely a harmless bridge reconnect.** It is a genuine OEM network-management interval accompanying an ESP restart. Raw evidence alone does not establish whether the ESP reset, a control-unit restart, or some external condition caused the sequence. Do not attribute causality without targeted qualification.

The October 15 census includes LSS `0x7E4/0x7E5` discovery traffic in addition to the normal identifiers. October 16 returns to the stable 81-ID census and five operational nodes. The `0x53E.byte5` live-node count interpretation gains independent startup corroboration.

## Operating and stator evidence

October 15 has ~486.8 minutes of observed actual compressor runtime, including a **306.90-minute** run from ~16:19–21:26 UTC. The longest uninterrupted AC Stage 2 interval is **212.47 minutes**; several other short Stage 2 status intervals occur. October 16 contains ~590.44 minutes of actual compressor operation, including a **378.53-minute** run from ~15:45–22:04 UTC and **346.32 minutes uninterrupted AC Stage 2**. Actual-run timing comes from ESP device ticks with separate epochs across the reset. The compressor run spanning October 15/16 midnight is counted as one cross-day event.

Three new complete isolated stator cycles October 15, with durations 8.22–8.57 minutes and median `0x282 -> 0x390` lag ~8.85 seconds. Two new complete cycles October 16 have durations ~7.93 and ~8.35 minutes and median lag ~9.35 seconds. All are compressor-stopped, exhibit the three phase-current candidate channels, and keep `0x390.byte0` confined to 44–46. **Cumulative completed stator cycles: 205 (200 + 3 + 2).**

Recovered-idle `0x383.f0/f1` pressure-pair median absolute separation is ~0.99 on October 15 and ~0.95 on October 16; Stage 2 medians are ~179.16 and ~174.50 raw units, respectively. Neither field's gauge/absolute calibration has been demonstrated.

Three additional `0x385.f0 = 65535 W` startup sentinels occur October 15. The separately introduced compressor-power filter from October 14 is therefore corroborated; October 16 has no further power sentinel. Speed-ceiling `0x385.f1 = 65535` sentinels recur six and nine times respectively. Structured room/humidity mirrors all match their nearest binary samples (October 15: 8 room, 14 humidity; October 16: 1 room, 11 humidity).

## New exact-length/no-NUL captures and heap trend

October 15 records **two** further exact-length/no-NUL `DebugUI.HiHeapRemaining` values:

- `28319744` at ~04:30 UTC;
- `25624576` at ~14:55 UTC.

These extend the field examples from nine to **eleven**. The second occurs during the Technician sweep; its notable drop versus the previous values is a diagnostic to correlate with device restarts and memory ownership, not proof of a leak. October 16 contains no new such sample.

## Remaining safeguards

The full-day CAN log does not demonstrate native UX360 mode-write semantics, electric heat-stage command/feedback, defrost, EEV, actual pressure display units, or CNT09525 mitigation actuation. Setpoint and Technician fan writers remain independently gated/default-off. `SystemSettings.Put`, `NetworkProperties.Put`, system-mode, profile and arbitrary JSON TX remain blocked.
