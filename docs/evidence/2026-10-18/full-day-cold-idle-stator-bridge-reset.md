# 2026-10-18 full-day cold idle, 23 stator cycles, and bridge-only reboot

Source: `trane-2026-10-18.tar.gz`, SHA-256 `4db157e28d45da45a0f85e46151d2ceedf65672ad3148cf5236abbedaf8ca8e4`. Read-only analysis; no CAN transmission. The companion sanitized machine-readable report is `trane-2026-10-18-analysis.json`.

## Capture integrity and full CANopen replay

- 24 hourly JSONL chunks; UTC 00:00:00.177 through 23:59:59.992.
- **2,594,692 records**: **2,594,593 raw CAN**, **98 `trane_json`**, and **one collector reconnection event**.
- **81 unique CAN IDs**; zero malformed JSON, bad CAN DLCs, or invalid binary lengths.
- In original captured wire order, independently reconstruct **49 block-SDO status JSON updates** (`0x649/0x5C9`) and **49 segmented application JSON ACKs** (`0x641/0x5C1`).
- **98/98 messages match the collector** by source channel, parsed JSON and order; all 49 application ACKs are `200`.
- No SDO aborts, sequence failures, incomplete transfers or raw/collector discrepancies. Every transfer includes the normal indicated trailing NUL. No new exact-length/no-NUL DebugUI sample.
- JSON roots: `SystemOpStatus=40`, `ZoneStatus=9`, `Ack=49`. No `SpOverride.Put`, `IndoorSettings.Put`, system-mode or other `Put` family appears. The setpoint-write corpus remains 13 and the exact-length/no-NUL corpus remains 11.

## Full-day mechanical idle

Compressor request (`0x280.f0`), achieved compressor speed (`0x384.f0`), compressor power (`0x385.f0`), blower request (`0x200.u16@2`), blower feedback (`0x318.u16@4`), blower power (`0x320.f0`), airflow target (`0x281.u16@0`), compressor demand (`0x281.byte6`) and the neutral `0x281.byte7` state candidate all stay at zero throughout the capture.

There are **no cooling/heating/defrost/reversing-valve runs, electric heat stages, 185.x pressure protection or A2L/mitigation events** supported by this archive.

Outdoor ambient from `0x380.f1` spans **42.44–65.65°F**. The idle pressure pair ranges:

- `0x383.f0`: **138.16–196.39** raw units;
- `0x383.f1`: **135.51–196.56** raw units;
- absolute pair separation: **median 1.609**, **mean 1.577**, **maximum 3.481** raw units (42,927 observations);
- synchronized correlation with outdoor ambient: **r≈0.988** for `f0`, **r≈0.994** for `f1`.

This is a strong low-ambient equilibrium baseline, reinforcing the paired suction/high-side interpretation without establishing absolute/gauge calibration or PSI conversion.

The `0x2D0.u16@4` airflow-limit/configuration candidate continues changing between roughly 707 and 755 with blower request and feedback fixed at zero. It is not actual delivered airflow.

## Twenty-three completed isolated stator cycles: 214 → 237

The cold idle day includes **23 complete cycles**, with no carry-in/carry-out or cycle interrupted by the bridge restart. All 23 have:

- `0x282.byte1 = 1` during the heat window;
- `0x390.byte0` nonzero approximately nine seconds after enable;
- nonzero levels confined to **44, 45, 46** (wire units still unresolved);
- nonzero `0x388.f0/f1` and `0x389.f0` phase-current candidates;
- actual compressor speed and fan speed remaining zero;
- outdoor input-power median **~88 W** during stator heat (maximum **97 W**) versus **~13 W** standby median.

Summary across the 23 complete cycles:

| Metric | Minimum | Median | Mean | Maximum |
|---|---:|---:|---:|---:|
| Cycle duration, min | 7.81 | **8.80** | 8.81 | 10.69 |
| `0x282→0x390` onset, sec | 8.83 | **9.21** | 9.25 | 9.77 |
| Start-to-start spacing, min | 38.46 | **65.62** | 63.89 | 127.94 |

The two longest cycles start near 12:51:36 UTC (10.68 min) and 14:12:59 UTC (10.69 min); they are complete, not transport/reset artifacts. Outdoor ambient at cycle start spans **42.53–64.51°F**. The per-day duration/ambient Pearson correlation is roughly **−0.455**, insufficient to infer a controller scheduling equation or fixed temperature boundary.

Stator-enable start times, UTC:
`00:22:02, 01:29:06, 02:35:35, 03:43:18, 04:52:10, 05:58:06, 07:03:24, 08:01:13, 09:09:32, 10:15:39, 11:18:47, 12:10:39, 12:51:36, 13:34:31, 14:12:59, 14:53:27, 15:35:20, 16:20:53, 17:03:09, 18:23:51, 20:12:59, 21:39:46, 23:47:43`.

**Cumulative target evidence: 237 completed isolated stator-heat cycles.** Do not interpret these power levels as commandable watts or infer temperature scheduling from a single cold day.

## Bridge reset without OEM network reset

An ESP device-tick discontinuity occurs at **~15:07:31 UTC**:

- last earlier observed device tick ~230,879,414 ms;
- first post-reconnect CAN tick ~4,664 ms;
- collector logs `connected` at 15:07:31.297 UTC, followed by CAN at ~15:07:31.338 UTC.
- no `0x000` NMT, `0x081/0x083` EMCY or node boot/pre-operational events;
- all five heartbeat IDs `0x701…0x705` remain `0x05` throughout the captured samples;
- all 40,878 `0x53D` frames remain `00 00 00 00 00`; all 40,876 `0x53E` frames remain `00 00 00 00 01 05`.

This is consistent with a **bridge-only restart/reconnect**, not the genuine node-3 NMT reset observed on October 15. The raw CAN does **not** establish whether the ESP restart was caused by watchdog, brownout, software or power. The Home Assistant profile therefore gains passive ESP uptime, reset-reason and heap diagnostics to improve the next field investigation. No bus TX change is necessary.

## Structured indoor humidity and room temperature

- `SystemOpStatus.Update.E`: **37/40** nearest binary `0x490.byte4` values exact.
- `ZoneStatus.Update.1.H`: **8/9** nearest `0x490.f0` values exact.
- Four apparent mismatches are explained by preceding/following matching binary samples within approximately **1.1 s**. This is the same sparse-update ordering effect observed on previous capture days, not evidence for different field semantics.

## Safety and remaining evidence

There are **no newly qualified stock writes**. Zone-1 `SpOverride.Put` setpoints (13 independent captured requests) and the October 6 Technician fan 0/1/50/100 family remain independently default-off and guarded. System mode, network/profiles, arbitrary JSON, electric heat, defrost/reversing valve, EEV and A2L controls remain unqualified and blocked.

The high-value next work remains system-mode request capture, synchronized Technician pressure/temperature calibration, live electric heat stage 1/2, defrost/reversing valve and CNT09525 mitigation state. The October 15 large-JSON logger correction is already independently qualified and should not remain on the unresolved task list.
