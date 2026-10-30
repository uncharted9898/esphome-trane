# 2026-10-29 full-day idle, stator carry-out, and seventeenth no-NUL transfer

Source: `trane-2026-10-29.tar.gz` (SHA-256 `8fa43e5450d5feeb00d3a570527cde331880d4340a68d40a565e148e8700137f`). Read-only analysis; **no CAN frames transmitted**. An independently generated sanitized analysis report is available alongside the source conversation.

## Archive and CANopen integrity

- All 24 hourly JSONL chunks; approximately 00:00:00.196–23:59:59.998 UTC.
- **2,593,442** records: **2,593,335** raw CAN frames and **107** structured `trane_json` records.
- **82** unique CAN IDs, zero malformed JSONL rows, invalid CAN payload lengths, device-tick regressions, or collector lifecycle events.
- Strict original-wire-order replay reconstructs **107/107** collector JSON messages, equal by channel, order and parsed body:
  - 53 completed `0x649/0x5C9` block-SDO status transfers;
  - 53 completed `0x641/0x5C1` segmented application responses, **all `{"Ack":"200"}`**;
  - one completed `0x641/0x5C1` block-SDO `DebugUI` transfer.
- **Zero** SDO aborts, incomplete/unmatched transactions, sequence/ACK errors or missing emitted JSON messages. All transfers have completed end responses.
- Structured roots: **47 SystemOpStatus**, **6 ZoneStatus**, **53 Ack**, **1 DebugUI**. The largest JSON body is 45 bytes. No profile sweep, `SpOverride.Put`, `IndoorSettings.Put`, system-mode `Put` or new application-write family is captured.

## Mechanical idle for all 24 hours

The compressor request (`0x280.f0`), actual speed (`0x384.f0`), compressor power (`0x385.f0`), blower request (`0x200.u16@2`), blower feedback (`0x318.u16@4`), blower power (`0x320.f0`), airflow target (`0x281.u16@0`), demand (`0x281.byte6`) and request-mode candidate (`0x281.byte7`) remain **zero throughout**. No compressor motor movement, cooling, heat-pump heating, fan-only, defrost, electric auxiliary heat, 185.x pressure protection or mitigation/A2L event appears. The `0x2D0.u16@4` airflow-limit/configuration candidate remains nonzero (~788–838) despite a stopped blower, reinforcing that it is not delivered airflow.

## Stator heat: 17 complete cycles and one carry-out

There are **18 `0x282.byte1` stator-enable starts** on October 29. **17 cycles are fully observed from assertion to deassertion**, and the **18th begins at 23:59:01.515 UTC and remains active at the archive boundary** (last observed enabled frame ~23:59:58 UTC). The final event has a valid ~9.021-second `0x390.byte0` onset and three nonzero phase-current candidate channels, but **must not be counted as complete until the October 30 archive closes it**.

Across the **17 completed** cycles:

| Metric | Min | Median | Mean | Max |
|---|---:|---:|---:|---:|
| Duration, min | 7.331 | **8.167** | 8.147 | 9.541 |
| `0x282` → `0x390` delay, sec (all 18 starts) | 8.781 | **9.196** | 9.282 | 9.775 |
| Start-to-start spacing, min (18 starts) | 47.333 | **74.240** | 82.999 | 222.141 |
| Ambient at start, °F (18 starts) | 55.733 | **59.931** | 62.023 | 76.089 |

Every complete cycle and the carry-out have **nonzero `0x388.f0/f1` and `0x389.f0` phase-current candidates**, while actual compressor speed stays zero. `0x390.byte0` nonzero values remain **44/45/46**, wire units unresolved. Outdoor input-power median is approximately **88 W** with stator enabled, versus **13 W** when disabled.

The October 29 cycle at **17:51:32 UTC** starts around **76.09°F** ambient. This independently reinforces prior evidence that a strict 75°F stator inhibit threshold is incorrect; no replacement cutoff or scheduling model is justified. The 222-minute late-day start spacing also does not prove a particular thermostat control rule.

**Cumulative isolated stator evidence through October 29: 442 completed cycles (425 + 17), plus one October 29 carry-out.** Do not report 443 completed until the final October 29 cycle has a confirmed falling edge on a subsequent capture.

## Idle refrigeration pressure and structured mirrors

Outdoor ambient (`0x380.f1`) spans **55.594–77.869°F**. Across **42,929** paired `0x383` frames:

- `0x383.f0` ~171.926–225.048 raw units;
- `0x383.f1` ~170.880–223.346 raw units;
- absolute separation **median 1.680**, mean 1.271, maximum 2.072 raw units;
- correlations to timestamp-aligned outdoor ambient **r≈0.991** for `f0`, **r≈0.993** for `f1`.

This strongly supports equalized low/high refrigerant pressure fields while idle. Their gauge-vs-absolute meaning, units, and Technician display calibration remain unqualified.

All **6/6** structured `ZoneStatus.Update.1.H` room temperatures agree with the nearest live `0x490.f0`. **46/47** structured `SystemOpStatus.Update.E` humidity updates match the nearest `0x490.byte4`; the remaining one matches the binary sample **~0.617 s later**, a source/update-order effect. The unusually frequent 59↔60 humidity structured updates around 19:00 UTC align with the live binary field; they are **not evidence of CANopen transport failures or an HVAC compressor/fan event**.

## Seventeenth exact-length/no-NUL DebugUI transaction

At approximately **18:38:21 UTC**, stock `0x641/0x5C1` object `0x300A:00` carries:

```json
{"DebugUI":{"HiHeapRemaining":"22528000"}}
```

- Exactly **42 bytes** indicated by the CANopen block-SDO initiation; **no trailing NUL**.
- Six segments, valid final subblock ACK, block-end and success response.
- Complete and correct `TRANE_JSON` emitted by the installed ESPHome bridge.
- This is **the seventeenth independent** exact-length/no-NUL example. It is **516,096 bytes** lower than the October 27 value `23044096`, consistent with earlier decreases but not proof of a memory leak or diagnostic ownership.

A targeted analyzer fixture adds this seventeenth captured value. No receiver code change is needed.

## Link network integrity and safety boundary

- `0x53D`: **40,938** frames, all `00 00 00 00 00`.
- `0x53E`: **40,937** frames, all `00 00 00 00 01 05`.
- Heartbeat IDs `0x701`–`0x705` remain exclusively `0x05` operational.
- No NMT (`0x000`), node-1/node-3 EMCY (`0x081/0x083`), ESP tick reset, or collector reconnect is observed.

No new application write family is qualified. Historical stock zone-1 setpoint captures remain **18**; the separately gated Technician fan writer remains unchanged. The SC360 remains master; global and per-family TX gates stay default-off. System-mode, network/profile/raw JSON, auxiliary electric heat, EEV, defrost/reversing valve, and CNT09525/A2L transmit remain blocked.

The previous October 28 exact-head CI passed; run exact-head validation again after these evidence/fixture changes before treating the new commit as qualified.
