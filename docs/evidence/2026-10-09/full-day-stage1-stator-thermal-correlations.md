# 2026-10-09 full-day Stage 1 cooling, stator and electronics-thermal qualification

Source: `trane-2026-10-09.tar.gz`. This is a read-only evidence pass; the underlying capture remains outside the repository.

## Archive integrity and replay

- 24 hourly JSONL chunks, covering 00:00:00.195–23:59:59.990 UTC;
- **2,624,988** JSONL records: **2,623,684** raw standard-CAN records and **1,304** emitted `trane_json` records;
- **82** distinct CAN IDs;
- zero malformed JSONL rows, invalid DLC/hex payloads, or device-tick resets;
- no collector lifecycle events.

The CANopen exchange was independently reconstructed from the raw frames, including block-init, segment sequence, final block acknowledgement, block-end and the accompanying segmented application ACK. The reconstruction contains **652** valid `0x649/0x5C9` block-SDO JSON updates plus **652** valid `0x641/0x5C1` segmented messages. All 1,304 reconstructed JSON bodies match the collector output, with **zero missing, extra, aborted or incomplete** transactions. All 652 application responses contain `{"Ack":"200"}`.

Every observed October 9 SDO transfer includes its terminating NUL in the advertised size. There is **no seventh** exact-length/no-NUL transfer, no DebugUI message, and no profile body longer than 74 JSON characters, so this archive does not qualify the separate 4,608-byte logger-buffer fix against long `EquipSummary`/`WifiList` traffic. The sixth exact-length example from October 8 remains the most recent verified one.

## Twelve real cooling intervals — Stage 1 only

The compressor reaches nonzero `0x384.float[0]` speed twelve times. Durations are calculated from ESP device ticks (not host log-buffer arrival times); approximate UTC times use collector timestamps.

| Run | Compressor start (UTC) | End (UTC) | Actual-speed time |
|---:|---|---|---:|
| 1 | 00:14:57 | 00:20:51 | 5.90 min |
| 2 | 01:51:19 | 01:57:59 | 6.65 min |
| 3 | 02:20:43 | 02:28:04 | 7.36 min |
| 4 | 02:43:22 | 02:52:55 | 9.55 min |
| 5 | 03:06:37 | 03:15:18 | 8.69 min |
| 6 | 03:27:29 | 03:38:33 | 11.07 min |
| 7 | 03:52:38 | 04:00:41 | 8.05 min |
| 8 | 20:48:35 | 20:54:49 | 6.24 min |
| 9 | 21:15:53 | 21:24:55 | 9.05 min |
| 10 | 21:36:14 | 21:48:21 | 12.11 min |
| 11 | 21:59:13 | 22:11:27 | 12.23 min |
| 12 | 22:27:51 | 22:34:59 | 7.14 min |

Total physical compressor runtime: **~104.04 minutes**. The structured `SystemOpStatus.C` updates contain 12 `AC Stage 1` starts and 12 `--` shutdowns, yielding **~99.24 minutes** in the structured Stage 1 state and **zero Stage 2**. Structured-stage time differs slightly from physical runtime because ramp and coast are asynchronous.

Observed maxima, not rated equipment capacities:

- `0x280.f0` requested speed: ~45.0 RPS;
- `0x384.f0` achieved speed: ~45.1 RPS;
- `0x385.f0` compressor power: **735 W**;
- `0x38C.f1` outdoor input power: **897 W**;
- `0x281.byte6` demand: **80%**;
- `0x318.u16@4` blower motor-feedback word: **339**;
- `0x320.f0` blower power: **~12.71 W**.

Seven additional `0x385.f1 = 65535` startup-sentinel samples appear. Maintain the existing >200-RPS validity filter rather than publishing this sentinel as a real speed ceiling.

### 0x281.byte7 is compressor-request adjacent, not a blower flag

There are twelve `0x281.byte7=1` intervals, one for each compressor **request** interval. Its start edge differs from `0x280.f0>0` by roughly -0.14 to +1.23 s; its stop edge differs by roughly -0.55 to +1.36 s. Achieved speed typically begins **~8.5–10.2 s after** the compressor request, and several shutdowns have tens of seconds of compressor coast after request and `byte7` clear.

Combined with the October 8 eight-request correlation and the October 6 Technician fan-only disproof (blower operating while byte7=0), this strongly constrains byte7 to a **compressor-request/enable-adjacent state**. Keep the public diagnostic name **0x281 Byte 7 State Candidate** until heating and other operating modes distinguish exact semantics; it is not confirmed to mean physical compressor running.

## Four additional isolated stator-heating cycles

October 9 contributes **four complete cycles**, raising the project corpus from **152 to 156** completed isolated stator-heat cycles, with no carry-in/carry-out interval.

| Stator enable (UTC) | Duration | Outdoor ambient at start | First 0x390 nonzero after enable |
|---|---:|---:|---:|
| 10:57:28 | ~8.07 min | ~63.59 °F | 9.264 s |
| 12:23:28 | ~8.22 min | ~64.43 °F | 9.195 s |
| 13:14:31 | ~8.32 min | ~68.87 °F | 8.866 s |
| 14:09:24 | ~8.56 min | ~72.29 °F | 8.826 s |

Median duration **~8.27 min**, lag median **~9.03 s**. Nonzero `0x390.byte0` is **44/45 only** on this day; that remains inside the previously observed 44/45/46 family, with wire units still unproven. All three phase-current candidates (`0x388.f0/f1`, `0x389.f0`) assert while achieved compressor speed stays zero and input power reaches ~86–93 W.

Outdoor ambient covers **63.39–80.87 °F**. Stator cycles stop after the last ~72.29 °F start while ambient warms, independently supporting the prior warm-ambient eligibility/inhibit **hypothesis**. The data still does not establish a safe/accurate thermostat threshold or rule.

## Pressure and refrigeration chain

Under cooling:

- `0x383.f0` suction/raw pressure reaches **~82.91**;
- `0x383.f1` high-side/raw pressure reaches **~264.57**;
- instantaneous high-minus-suction separation reaches **~167.37 raw units**.

For idle pressure samples at least **20 minutes after any completed compressor interval**, median absolute pressure-pair separation is **~0.70**, mean **~0.98** (34,054 samples). The strong idle equalization and active-running separation continue to support the paired suction/high-side interpretation. Gauge-vs-absolute pressure units and display conversion remain **unqualified**; no psi calibration is inferred.

`0x2D0.u16@4` varies ~739–815 on this day and remains nonzero while the blower is fully stopped, again excluding actual delivered airflow and supporting the airflow-limit/configuration candidate.

## Raw electrical/thermal family discrimination

October 9 is useful for `0x430.float[1]`, `0x450.float[0..1]` and `0x460.float[0]` because it includes both intermittent cooling and extended idle.

- `0x430.f1`: ~221.6–426.0, adjacent-sample autocorrelation ~0.018, negligible overall correlation with compressor speed/power or outdoor ambient;
- `0x450.f0`: ~259.9–408.0, adjacent-sample autocorrelation ~0.009, negligible correlation with compressor speed/power/ambient;
- `0x450.f1`: ~283.7–336.6, adjacent-sample autocorrelation ~-0.008, negligible correlation with compressor speed/power/ambient.

These three fields remain **Raw**, not identified as direct temperature, current or compressor demand measurements.

By contrast, `0x460.f0` varies slowly ~85.09–86.69 with adjacent-sample autocorrelation ~0.99999 and closely tracks known electronics-temperature candidate channels when aligned by device ticks:

- versus `0x410.f0` inverter/IPM candidate: **r ~0.991** (R² ~0.983);
- versus `0x410.f1` rectifier/PFC candidate: **r ~0.987**;
- versus `0x430.f0` outdoor-fan IPM candidate: **r ~0.984**;
- versus outdoor ambient directly: only **r ~0.248**.

This independently strengthens `0x460.f0` as an **outdoor-electronics thermal-family candidate** (also consistent with earlier correlated captures), but does not establish the exact physical sensor, unit or OEM label. Keep the entity diagnostic and candidate, not a promoted friendly temperature.

## Structured environmental mirrors

- `SystemOpStatus.Update.E` indoor-humidity mirror: **4/5** nearest `0x490.byte4` readings match exactly. The fifth reports 57 while the last `0x490` frame still says 58; the live byte changes to 57 **0.578 seconds later**, resolving the apparent disagreement as update ordering.
- `ZoneStatus.Update.1.H` room temperature: **2/2** directly match `0x490.f0`.
- No new `SpOverride.Put`, `IndoorSettings.Put`, system-mode or profile write, electric heat-stage activation, defrost, reversing-valve, A2L/leak-alarm or 185.x protection evidence is present.

## Network state and write boundary

All 40,986 `0x53D` frames are `00 00 00 00 00`. All 40,986 `0x53E` frames are `00 00 00 00 01 05`. Heartbeat nodes `0x701`–`0x705` remain exclusively operational (`05`). There is no NMT or EMCY event in the day.

Both stock-qualified local write families remain default-off and independently gated: zone-1 setpoints and Technician fan 0/1 / 50/100. Mode, profile, raw JSON, heating stages, defrost/valve and A2L control remain unqualified/blocked.

This archive did not require a decoder, receiver or TX-code change. The evidence and cumulative counts should advance without guessing new active writes.
