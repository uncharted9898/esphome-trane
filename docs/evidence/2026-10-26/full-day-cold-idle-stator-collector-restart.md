# 2026-10-26 — cold mechanical idle, 19 stator cycles and collector-only restart

Source: `trane-2026-10-26.tar.gz`, SHA-256 `57390309e95ef2923e7e3ee868686c5d5513124ec46ede2d0f381ffb2c46f40e`. All decoding was read-only; no Trane CAN frames were transmitted. The sanitized machine-readable report `trane-2026-10-26-analysis.json` accompanies this analysis session, not the repository.

## Archive integrity and CANopen replay

The archive has all **24 hourly JSONL chunks**, covering host timestamps `00:00:00.013–23:59:59.872 UTC`:

- **2,590,526 records**: **2,590,463 CAN**, **60 emitted `trane_json`**, **3 collector lifecycle** records;
- **82 distinct 11-bit CAN IDs**;
- **zero malformed JSONL rows, invalid DLC/payload lengths, or device-tick regressions**.

A completely independent, frame-order-preserving raw CANopen replay processes **540 SDO frames** and reconstructs:

- **30 completed `0x649/0x5C9` block-SDO status downloads**: 23 `SystemOpStatus` and 7 `ZoneStatus` updates;
- **30 completed `0x641/0x5C1` segmented-SDO application ACKs**, all `{"Ack":"200"}`.

**60/60 reconstructed JSON bodies match the collector in order, source and content.** There are no SDO aborts, malformed documents, incomplete/unmatched transfers, unexpected protocol frames or outstanding sessions at the end of the archive.

All 60 messages use the normal indicated-size-includes-NUL form. There is **no** `DebugUI.HiHeapRemaining` event (so the exact-length/no-NUL evidence corpus stays at **15**) and **no** stock `SpOverride.Put`, `IndoorSettings.Put`, `SystemSettings.Put` or other newly qualified application command.

## Mechanically idle for the full 24 hours

Every observed compressor request (`0x280.f0`), achieved speed (`0x384.f0`), compressor power (`0x385.f0`), blower speed request (`0x200.u16@2`), motor feedback (`0x318.u16@4`), blower power (`0x320.f0`), airflow target (`0x281.u16@0`) and compressor demand (`0x281.byte6`) stays **zero**. The request-mode field `0x281.byte7` stays **0** in all **40,909** frames. No heat-pump heating, cooling, fan-only, defrost, electric heat, leak/mitigation or 185.x pressure-protection state is supported by this day.

`0x2D0.u16@4` is ~766–815 while the blower remains entirely stopped, independently reinforcing that the field is an airflow-limit/configuration candidate and **not** delivered airflow.

## Nineteen complete isolated stator-heat cycles: 367 → 386

All 19 `0x282.byte1` asserted intervals start and end within October 26, with **no carry-in or carry-out**. All 19 independently show `0x390.byte0` becoming nonzero ~9 seconds later, nonzero values still limited to **44/45/46**, and **all three** `0x388.f0/f1`, `0x389.f0` phase-current candidate channels asserting with compressor motion zero.

| Metric | Minimum | Median | Mean | Maximum |
|---|---:|---:|---:|---:|
| Completed-cycle duration (minutes) | 7.621 | **8.341** | 8.604 | **11.191** |
| `0x282` enable → `0x390` first nonzero (seconds) | 8.873 | **9.240** | 9.274 | 9.763 |
| Start-to-start spacing (minutes) | 33.345 | **64.424** | 65.992 | 153.014 |
| Outdoor ambient at cycle start (°F) | 43.292 | 54.359 | 55.653 | 70.035 |

Outdoor input power has median **~88 W** during stator-enable intervals, versus **~13 W** with the bit cleared (maximum ~97 W with stator enabled).

The longest completed event starts around **14:15:42 UTC**, clears around **14:26:54 UTC**, and lasts **11.19 minutes** with first power onset **9.17 seconds** after enable. This exceeds earlier isolated-cycle durations in the recent capture sequence, but the corroborating phase-current/power signals and clean shutdown argue against dismissing it as a missing clear or rollover artifact. It is **not** enough evidence to impose any fixed maximum run time or change transmitter behavior.

**Cumulative completed isolated stator cycles through 2026-10-26: 386.**

## Paired idle pressure and structured indoor mirrors

Outdoor ambient ranges **42.927–71.589°F**. The compressor-idle `0x383` pair stays very closely equalized across **42,954 observations**:

- `0x383.f0`: ~141.071–214.494 raw units;
- `0x383.f1`: ~139.146–213.525 raw units;
- absolute pair separation: median **1.672**, mean **1.441**, maximum **2.963** raw units;
- correlation to aligned ambient: **r≈0.996** (`f0`) and **r≈0.998** (`f1`).

This supports the already-established paired suction/high-side semantics under equilibrium conditions, but **does not** establish gauge/absolute representation or a Technician PSI conversion.

All **23/23 `SystemOpStatus.Update.E` humidity messages** match the nearest `0x490.byte4` sample. **6/7 `ZoneStatus.Update.1.H` room-temperature messages** match nearest `0x490.f0`; the remaining 73°F structured value precedes the matching 73°F binary update by **~0.60 s**. These are compatible with the established sparse structured-mirror mappings.

## Collector restart is not an OEM network reset

Three collector lifecycle records appear in the final hour:

- **23:10:40.940 UTC:** collector `stop`;
- **23:10:55.430 UTC:** collector `start`;
- **23:10:55.452 UTC:** collector `connected`.

There is **no ESP device-tick regression** anywhere in the archived CAN stream, no NMT (`0x000`) or EMCY (`0x081/0x083`), and no observed heartbeat-state transition. All five nodes `0x701–0x705` remain exclusively `0x05` operational in captured samples. `0x53D` is zero in all **40,908** records, and `0x53E.byte5` remains 5 in all **40,909** records.

This event supports a **collector-process interruption/reconnect** without evidence of an ESP restart or OEM node reset; the capture alone does not establish why the collector restarted. It must not be conflated with the October 15 genuine node-3 NMT reset.

## Safety and engineering boundary

The October 25 exact-head CI previously passed. October 26 requires **no runtime decoder or TX behavior change**: the observed messages conform to already-qualified reception and the existing cooling/heating/stator mappings. The default-off global/setpoint/Technician-fan gates remain untouched. Mode, profiles/network, arbitrary JSON, heat stages, EEV, defrost/reversing valve and A2L/mitigation writers remain blocked.

The next high-value field evidence remains OEM mode `Put`, live electric-heat stage 1/2, defrost/reversing-valve, synchronized Technician pressure calibration, and CNT09525 mitigation status.
