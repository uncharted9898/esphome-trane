# 2026-10-30 complete idle, October 29 carry-in closure and CANopen verification

Source: `trane-2026-10-30.tar.gz`, independently decoded read-only. No CAN frames were transmitted.

## Capture integrity

- 24 hourly JSONL files; **2,593,272** records, including **2,593,248** raw CAN and **24** structured `trane_json` records.
- 82 distinct CAN IDs; zero malformed JSONL rows or invalid DLC/payload lengths.
- Device ticks remain continuous across the archive; no collector lifecycle events, observed NMT or EMCY frames.
- Independent original-tick-order block/segmented CANopen parser reconstructs **24/24** structured messages exactly, including **12 complete `0x649/0x5C9` block status transfers** and **12 complete `0x641/0x5C1` segmented application ACKs**, all `200`. No aborts, incomplete sessions, unmatched messages or invalid lengths.
- All transfers include their terminating NUL; no new `DebugUI.HiHeapRemaining` or unqualified `Put` appears.

## October 29 carry-out closure and 16 new stator cycles

The stator cycle asserted on October 29 at approximately 23:59:01 UTC clears at **2026-10-30 00:06:27 UTC**, completing a **~7.44-minute** isolated cycle. This closes the previously documented carry-out and counts as **one** newly completed historical event, not a new October 30 start.

October 30 independently contains **16 new fully completed isolated cycles** with no active cycle at day end. Their durations range **7.524–10.095 minutes**, median **8.172 minutes**, mean **8.336 minutes**. The median first-nonzero `0x390.byte0` delay after `0x282.byte1` enable is **9.154 seconds** (range 8.854–9.698). Only nonzero `0x390.byte0` values 44/45/46 occur. All 16 newly started cycles and the October 29 carry-in feature active phase-current candidate channels `0x388.f0/f1` and `0x389.f0` while actual compressor speed is zero.

Cumulative count: **442 fully completed through October 29 + 1 closed carry-in + 16 new October 30 completed = 459 fully completed isolated stator cycles**.

## Full-day mechanical idle and refrigeration equilibrium

All observations of compressor request (`0x280.f0`), actual speed (`0x384.f0`), compressor power (`0x385.f0`), blower request (`0x200.u16@2`), blower feedback (`0x318.u16@4`), blower power (`0x320.f0`), airflow target (`0x281.u16@0`), demand (`0x281.byte6`) and passive request-mode candidate (`0x281.byte7`) are zero.

Across **42,942** paired samples, `0x383.f0` spans **161.968–227.087** and `0x383.f1` spans **160.509–226.644** raw units. Median absolute separation is **1.327**, maximum **2.605**; outdoor ambient spans **51.695–79.800°F**. Each pressure field correlates strongly with ambient (r≈0.992 and r≈0.994). Do not assign an unverified gauge/absolute PSI conversion.

Structured roots comprise `SystemOpStatus=5`, `ZoneStatus=7`, `Ack=12`. **7/7 room-temperature** and **5/5 humidity** updates match nearest `0x490` fields.

## Stock network and transmit boundary

Five CANopen heartbeat nodes `0x701` through `0x705` remain exclusively operational (0x05). `0x53D` is all-zero in **40,957** observations and `0x53E` remains `000000000105` in **40,956** observations. There is no observed bridge tick reset, NMT/EMCY or OEM topology disturbance.

Historical corpus remains **18 independent stock zone-1 setpoint writes** and **17 exact-length/no-NUL transfers**; none are added on October 30. The global and separate qualified setpoint/Technician fan gates remain default-off, and all system-mode/profile/network/electric heat/defrost/EEV/A2L control transmit remains unqualified and blocked.

## CI fixture repair

The exact-head October 29 workflow compiled its five firmware variants, but the safety-contract job failed at import because `tests/test_capture_analyzer.py` omitted the closing parenthesis in the no-NUL tuple. The fixture is now formatted as a multiline tuple and its 16 existing enumerated examples are preserved. This syntax correction is independent of the October 30 telemetry evidence and changes no runtime firmware behavior. The historical no-NUL evidence corpus is 17, with 16 explicitly enumerated regression values in this fixture; the October 29 `22528000` example is already present. No unverified value was invented to fill the remaining historical fixture gap.
