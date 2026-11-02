# 2026-10-31 and 2026-11-01 — full-day cold idle, stator and Eastern time transition

Sources: `trane-2026-10-31.tar.gz` (SHA-256 `f0a5c1ec475829fea2452ebe0b5b56b3739082d62a147117d712eb1ef5bf2ac0`); `trane-2026-11-01.tar.gz` (SHA-256 `e7c40b623345f7a96180485131b54a3a93e4690f4a5e65a421789f2d8c5826c6`). Read-only analysis, no CAN TX. Full sanitized per-event machine-readable report supplied separately.

## Integrity and CANopen transport

| Metric | October 31 | November 1 |
|---|---:|---:|
| Hourly JSONL files | 24 | 24 |
| Raw CAN | 2,594,698 | 2,591,289 |
| Emitted structured JSON | 53 | 30 |
| Unique CAN IDs | 82 | 82 |
| Invalid JSONL/CAN lengths | 0 | 0 |
| ESP tick resets / collector lifecycle events | 0 / 0 | 0 / 0 |
| Fully reconstructed JSON | **53/53** | **30/30** |

October 31: **26** completed 0x649/0x5C9 status block-SDOs, **26** completed 0x641/0x5C1 segmented application ACKs (all 200), and **one** completed 0x641/0x5C1 DebugUI block-SDO. November 1: **15** completed status block transfers and **15** completed application ACKs (all 200). Independent raw-CAN reconstruction matches all 83 emitted JSON messages in exact order, source, and parsed content. No abort, incomplete transfer, missing output or sequence mismatch.

## Fully idle HVAC and 38 isolated stator cycles

All compressor request, actual compressor speed, compressor power, blower request/feedback/power, airflow target, demand and 0x281.byte7 request-mode samples are zero across both days. There is no observed cooling, heating, defrost, auxiliary heat, A2L mitigation or 185.x protection event.

| Stator statistic | October 31 | November 1 |
|---|---:|---:|
| Complete cycles | **18** | **20** |
| Median duration | **8.133 min** | **8.182 min** |
| Min–max duration | 7.465–9.324 min | 7.706–9.062 min |
| Median enable-to-0x390 onset | **9.252 s** | **9.338 s** |
| Start-to-start median | 66.57 min | 65.23 min |
| Ambient range | 53.573–67.948°F | 51.847–70.807°F |

All 38 cycles have all three phase-current candidate signals active with the compressor stationary, and observed nonzero 0x390.byte0 remains confined to 44/45/46. No carry-in/carry-out at either boundary. Stator-enabled outdoor input-power median ~88 W versus ~13 W standby on both days.

**Completed cumulative stator corpus: 459 + 18 + 20 = 497 cycles.** There is no justified stator eligibility threshold or commandable-power inference.

## Paired refrigeration pressure and structured mirrors

October 31: 42,932 paired 0x383 pressure frames, median absolute separation **0.964 raw units**, maximum 2.454; ambient correlation 0.9855/0.9919 for the two raw fields. November 1: 42,933 pairs, median separation **1.437**, maximum 2.780; ambient correlation 0.9935/0.9966. This reinforces pressure equalization and paired field roles but does **not** qualify gauge/absolute units or PSI conversion.

All 23 humidity + 3 room structured updates on October 31, and all 9 humidity + 5 room updates on November 1, match their nearest 0x490 binary fields exactly.

## Exact-length no-NUL and historical fixture completion

October 31 at ~19:36:10 UTC contains **42 exact wire bytes** for `{"DebugUI":{"HiHeapRemaining":"22011904"}}`, with no terminating NUL; it reassembles and logs correctly. This is the **18th** directly verified such transfer. November 1 contains none.

The earlier October 21 capture is independently reopened: a prior documentation entry lacked the actual value. Its valid 42-byte no-NUL transfer at 10:45:59 UTC contains `HiHeapRemaining=24592384`. The regression fixture now enumerates all 18 supported samples, including October 21 and October 31. The downward heap series is diagnostic only, not proof of a leak or source ownership.

## November 1 time change — observed SystemSettings.Update, not Put

At **2026-11-01 06:02:39 UTC** (~01:02:39 EST), stock 0x649 status traffic emits:

```json
{"SystemSettings":{"Update":{"J":"-0500"}}}
```

The complete 44-byte indicated block SDO and `Ack:200` independently reconstruct from the original wire frames. Eastern daylight-saving time ended at **06:00:00 UTC** (02:00 EDT → 01:00 EST). A previous October 15 structured snapshot had `J="-0400"`, `K="-0500"`. The November 1 update therefore strengthens `J` as a *currently effective UTC-offset candidate* and `K` as a *standard-offset candidate*, but exact OEM ownership/semantics are unqualified. No stock `SystemSettings.Put` is captured, and this evidence does **not** enable setting time or system mode.

## Stable network and safety boundary

October 31: 40,967 all-zero 0x53D frames and 40,966 unchanged `000000000105` 0x53E frames. November 1: 40,893 of each, likewise stable. All five 0x701–0x705 heartbeat nodes remain operational (0x05), no NMT or EMCY on either day. No ESP tick reset or collector restart.

Historical stock zone-1 setpoint writes remain **18**; Technician fan control remains separately qualified/default-off. Global and per-family write gates remain unchanged. SystemSettings, mode, profiles, network, electric heat, defrost/valve, EEV, A2L and arbitrary JSON TX remain blocked.
