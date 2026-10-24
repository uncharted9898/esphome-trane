# 2026-10-13 full-day Stage 2, stator, and ninth exact-length/no-NUL SDO

Source archive: `trane-2026-10-13.tar.gz` (SHA-256 `547724db73e1b7b5f4080204a851538c3805b0baef43294de1e1a6a3c4ecc2ff`). Read-only CAN/log analysis: no application TX was sent.

## Capture integrity

- 24 hourly JSONL files covering the full UTC day;
- **2,639,486** valid records: **2,637,881** raw CAN and **1,605** emitted structured JSON;
- **82** unique 11-bit CAN IDs;
- zero malformed JSONL rows or invalid DLC/payload lengths;
- no ESP32 device-tick reset;
- CANopen exchanges reconstructed in original wire/capture order, preserving frames sharing a tick.

The independent raw replay yields **1,605/1,605** valid JSON messages matching the collector by source CAN ID, JSON body and chronological order:

| Family | Complete messages |
|---|---:|
| `0x649/0x5C9` stock block-SDO status updates | 802 |
| `0x641/0x5C1` segmented application ACKs | 802 |
| `0x641/0x5C1` block-SDO `DebugUI` transfer | 1 |

All **802** application acknowledgements are `{"Ack":"200"}`. No truncated, aborted, orphaned, incomplete, extra or missing transactions were observed.

Structured roots: `OdStatus=513`, `IndoorStatus=156`, `SystemOpStatus=96`, `ZoneStatus=37`, `Ack=802`, `DebugUI=1`. The structured stream contains **no** `SpOverride.Put`, `IndoorSettings.Put`, system-mode `Put`, profile write or other new application command. No heating, defrost, A2L/mitigation or 185.x pressure-protection event is identified. Normal startup `TA_INV_HI` indoor-status strings remain non-alarm evidence unless independently qualified.

## Twelve compressor starts, eleven complete runs and one carry-out

Actual compressor-speed intervals (`0x384.float[0] > 0`) are below. Times are approximate UTC, calibrated from ESP device ticks rather than delayed host-log arrival.

| Run | Compressor start | Stop | Observed time |
|---:|---|---|---:|
| 1 | 00:09:24 | 00:16:03 | 6.65 min |
| 2 | 17:48:18 | 17:55:02 | 6.72 min |
| 3 | 18:06:09 | 20:34:13 | **148.06 min** |
| 4 | 20:42:56 | 20:55:17 | 12.36 min |
| 5 | 21:05:22 | 21:23:22 | 18.01 min |
| 6 | 21:31:44 | 21:49:41 | 17.95 min |
| 7 | 21:57:51 | 22:12:49 | 14.96 min |
| 8 | 22:22:07 | 22:35:47 | 13.67 min |
| 9 | 22:45:39 | 22:57:18 | 11.66 min |
| 10 | 23:09:17 | 23:19:48 | 10.52 min |
| 11 | 23:32:34 | 23:42:20 | 9.76 min |
| 12 | 23:57:39 | active at 23:59:59 UTC | **>=2.33 min, carry-out** |

Total **observed** compressor-speed runtime: **>=272.66 minutes**. Do not call the twelfth event complete: its request, `0x281.byte7`, and actual motor speed all remain active at the archive boundary.

The third run has one uninterrupted structured `AC Stage 2` interval from **18:20:42.525 to 20:25:18.880 UTC** (**124.61 minutes**). Across the full archive, Stage 1 accounts for **>=145.86 minutes** including the still-active final stage. Comparing stages, source-specific medians should be calculated with device-tick-aligned CAN samples, not host-reception timestamps.

Day maxima:

- compressor request `0x280.f0`: **58.0 RPS**;
- actual compressor speed `0x384.f0`: **~58.1 RPS**;
- compressor power `0x385.f0`: **1,173 W**;
- outdoor input power `0x38C.f1`: **1,377 W**;
- blower speed-feedback word `0x318.u16@4`: **522**;
- blower power `0x320.f0`: **~29.27 W**;
- outdoor ambient `0x380.f1`: **~59.08–86.19 F**.

Seven additional `0x385.f1=65535` speed-ceiling startup sentinels reinforce the retained >200 RPS filter.

### 0x281.byte7 remains compressor-request adjacent

There are 12 `0x281.byte7=1` intervals and exactly 12 `0x280.f0>0` request intervals. Completed-event start and stop edges differ by roughly -0.87 to +1.72 seconds; actual motor speed typically begins about 3.7–9.8 seconds after the request. One short run coasts **~32 seconds** after request termination.

Together with the prior October 6 Technician fan-only disproof, this continues to support **compressor-request/enable-adjacent state**, *not* a general blower-running or actual compressor-speed flag. Keep the publicly exposed diagnostic name neutral until independent heating/mode qualification.

## Seven fully completed isolated stator-heat cycles: 187 -> 194

The archive adds seven complete cycles with no stator carry-in or carry-out. In each, compressor speed is zero and all three phase-current candidate channels (`0x388.f0/f1`, `0x389.f0`) become nonzero.

| Enable UTC | Duration | Ambient at start | 0x390 onset lag |
|---|---:|---:|---:|
| 06:55:21 | 8.57 min | 63.61 F | 9.071 s |
| 08:57:06 | 8.01 min | 61.15 F | 9.754 s |
| 10:43:39 | 8.02 min | 59.60 F | 9.254 s |
| 12:09:28 | 8.37 min | 59.59 F | 9.467 s |
| 13:03:38 | 8.67 min | 62.34 F | 8.925 s |
| 13:50:16 | 8.66 min | 65.59 F | 9.037 s |
| 14:22:33 | 9.63 min | 70.55 F | 9.184 s |

Duration **8.01–9.63 min**, median **~8.57 min**. The `0x390.byte0` first-nonzero delay is **8.925–9.754 s**, median **~9.184 s**. Nonzero `0x390` values remain **44/45/46** with OEM units unresolved. The full project corpus is now **194 fully observed isolated stator cycles**.

No new stator controller eligibility rule is justified. Outdoor ambient during the seven starts is ~59.6–70.6 F; prior starts above 77 F already disprove a hard 75 F inhibit threshold.

## Refrigeration/thermal/structured mirrors

The `0x383` pressure pair remains coherent:

- `0x383.f0` raw range **~79.82–235.86**;
- `0x383.f1` raw range **~179.14–321.72**;
- median absolute separation in structured Stage 2 **~172.26 raw units**;
- median absolute separation in confirmed recovered idle (>=20 minutes after an observed completed compressor run) **~0.72**.

This strengthens suction/high-side roles but does **not** establish gauge vs absolute pressure, exact PSI scaling, or Technician display conversion.

Structured mirror checks: **8/8** `SystemOpStatus.Update.E` humidity updates agree with the nearest `0x490.byte4`; **4/4** `ZoneStatus.Update.1.H` room-temperature updates agree with nearest `0x490.f0`. The timing allowance covers asynchronous broadcasts without altering semantics.

`0x460.f0` remains correlated with outdoor drive electronics temperatures (r ~0.974 against `0x410.f0`, r ~0.977 against `0x430.f0`) but has only an unqualified thermal-family label. `0x430.f1`, `0x450.f0/f1` remain raw; `0x2D0.u16@4` remains an airflow limit/configuration candidate, **not** actual delivered airflow.

## Ninth exact-length/no-NUL receiver verification

At approximately **15:36:41 UTC**, stock request `0x641` and response `0x5C1` carry object `0x300A:00` as a CANopen block download:

```json
{"DebugUI":{"HiHeapRemaining":"28835840"}}
```

The initiate request is `C2 0A 30 00 2A 00 00 00`, advertising exactly **42** bytes; no trailing NUL is present within that length. The negotiated block size is six, the final segment is `0x86`, followed by `A2 06 00`, `C1`, and success response `A1`. The deployed receiver emits complete valid JSON.

This is the **ninth independently observed** optional-NUL example. Across the nine captured `HiHeapRemaining` numbers from September 30 through October 13, the value has fallen from **33,054,720 to 28,835,840**, a decrease of **4,218,880 bytes (~4.02 MiB)**. Seven of eight adjacent readings decrease by exactly **516,096 bytes (504 KiB)**, with one **606,208-byte (592 KiB)** step. This pattern is worth preserving for longer-term diagnostics but must **not** yet be interpreted as an identified memory leak or an ESP/SC360 ownership attribution.

All other October 13 transfers use the normal length-includes-NUL wire form. No long `EquipSummary` or `WifiList` body appears, so the separate 4,608-byte ESPHome logger-buffer change still lacks a post-fix >512-character target capture.

## Stable Link network and unchanged write boundary

Every `0x53D` frame (41,022 samples) is `00 00 00 00 00`; every `0x53E` frame (41,022) is `00 00 00 00 01 05`. Nodes `0x701`–`0x705` stay exclusively CANopen `0x05` operational; no NMT or EMCY event appears.

- Zone-1 `SpOverride.Put` setpoints: stock-qualified from **seven** captured requests, still independently gated/default-off.
- Technician `IndoorSettings.Put` fan enable 0/1 and 50/100 requests: stock-qualified, separately gated/default-off.
- System mode, profile writes, raw JSON, auxiliary electric-heat stages, EEV, defrost/reversing valve and A2L/mitigation controls: **unqualified and blocked**.

No runtime decoder, thermal label promotion, or application TX behavior change is justified by this capture.
