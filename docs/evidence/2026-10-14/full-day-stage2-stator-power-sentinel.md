# 2026-10-14 complete-day CAN qualification and compressor-power sentinel

Source: `trane-2026-10-14.tar.gz` SHA-256 `1cf7ece12e6e747c9a6dafb18777b49f6109118dfb968c5205ed598307823f41`. Read-only analysis, with full machine-readable report `trane-2026-10-14-analysis.json`.

## Integrity and transport
- 24 hourly JSONL files, 00:00:00.001–23:59:59.909 UTC.
- 2,642,347 records: **2,640,867 CAN**, **1,480 emitted structured JSON**; **82 IDs**, zero malformed rows, invalid DLCs or bridge clock resets.
- Reconstructed all **1,480/1,480** JSON messages from CAN in capture order: 740 `0x649` block-status transfers and 740 `0x641` segmented application acknowledgements. Every application ACK is `200`. No abort, orphan, incomplete transfer, collector mismatch, block-SDO `Put`, or new command family.
- All messages are NUL-terminated in indicated wire size, maximum 74 bytes. No tenth exact-length/no-NUL example and no post-logger-fix long EquipSummary/WifiList >512-byte validation.

## Compressor carry-in, running intervals and carry-out
The October 13 final compressor run remains active across midnight, confirmed using both archives' original ESP device ticks. It closes ~00:05:55 UTC, a total of ~8.27 minutes from its October 13 start (~23:57:39). Do not double-count it as a new compressor start.

October 14 has **9 observed compressor-speed intervals**, including **one carry-in**, **7 new completed runs**, and **one carry-out active at midnight**. The long 17:31:03–22:07:07 UTC run lasts **276.06 minutes**; structured Stage 2 runs **17:44:00–21:51:12 UTC, 247.20 uninterrupted minutes**, followed by Stage 1. Total compressor-speed time observed *within* this archive is ~363.44 minutes (includes partial boundary runs; do not report as nine fully completed new starts).

Observed maximum actual speed **58.1 RPS**, outdoor input power **1,521 W**, blower feedback word **547**, blower power **32.73 W**, outdoor ambient **62.33–90.70 F**. Repeated compressor-speed ceiling `0x385.f1=65535` startup sentinels (three more) remain filtered.

### New confirmed data-quality bug: compressor power 65535 W
At ~17:14:15 UTC, `0x385.f0` (normally compressor power) emits a single **65535.0 W** startup sentinel (`00FF7F47`), with second float zero. Excluding this provably invalid single value, maximum physical compressor power on this day is **1311 W**. The maintained `Compressor Power` Home Assistant sensor previously published the raw unfiltered value. We now explicitly reject nonfinite/negative values and exactly **65535.0** while preserving genuine zero and other finite power samples; no arbitrary wattage cap was invented. A regression assertion locks this behavior down.

## Six complete isolated stator-heat cycles
Six new completed isolated cycles, no stator boundary carry-over, take cumulative evidence **194 -> 200 complete cycles**. All occur with compressor speed zero and all three phase-current candidate channels nonzero. Start times: 07:17:51, 09:23:23, 11:05:35, 12:22:54, 13:12:27, 13:59:12 UTC. Durations **7.57–9.11 min**, median **8.18 min**. `0x390.byte0` starts **8.80–9.63 s** after `0x282.byte1`, median **8.94 s**, with nonzero levels 44/45/46. Ambient at starts ~62.4–70.5 F. No inferred ambient cutoff.

## Pressure, thermal, mirrors and Link network
- Stage 2 `0x383` pressure-pair median absolute separation **~177.19 raw units**; recovered idle (>=20 min after last completed run) **~1.21 raw units**. Gauge/absolute units and Technician calibration remain unresolved.
- `0x460.f0` electronics thermal-family correlations: r~0.878 with `0x410.f0`, r~0.880 with `0x410.f1`, r~0.923 with `0x430.f0`; raw `0x430.f1`/`0x450` channels have negligible correlation. Exact sensor remains unknown.
- All **14/14** structured humidity `SystemOpStatus.E` samples equal the nearest `0x490.byte4`; **2/2** room `ZoneStatus.H` samples match `0x490.f0`.
- `0x53D`: 40,995 frames all zero; `0x53E`: 40,995 frames all `000000000105`; heartbeat nodes 1–5 all operational (`05`). No NMT/EMCY.
- No electric heat-stage, defrost/reversing-valve, A2L mitigation, 185.x protection, or new stock system-mode commands found.

The only runtime change is the scoped compressor-power sentinel filter. Stock-qualified zone-1 setpoint TX and Technician fan TX remain individually default-off and gated; mode/profile/arbitrary JSON/aux heat/defrost/EEV/A2L writes remain blocked.
