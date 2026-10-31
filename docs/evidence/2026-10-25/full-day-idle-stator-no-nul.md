# 2026-10-25 full-day idle and CANopen qualification

Source archive: `trane-2026-10-25.tar.gz`. SHA-256 `57b8b2ce6d3bcb58434a9a29a5cfbb67818d207281beb39241001050ac8bffbd`. Analysis was passive: no CAN transmissions or firmware deployment.

## Capture integrity

24 hourly JSONL chunks span approximately 00:00:00.018–23:59:59.995 UTC. There are **2,592,904 records**: **2,592,765** raw CAN frames and **139** valid collector `trane_json` records, from **82** unique CAN IDs. No malformed rows, invalid DLC/payload lengths, ESP device-tick resets or collector lifecycle events were observed.

Original-order CANopen reassembly reconstructs **139/139 messages**, matching the collector exactly by source and JSON body:
- 69 `0x649/0x5C9` completed block status downloads;
- 69 `0x641/0x5C1` completed segmented application ACKs, all `{"Ack":"200"}`;
- one `0x641/0x5C1` completed block download carrying `DebugUI`.
There are **zero SDO aborts, incomplete transactions, out-of-sequence frames, collector mismatches, or pending sessions at archive close**. Status roots include 63 `SystemOpStatus` and six `ZoneStatus` updates. No `SpOverride.Put`, `IndoorSettings.Put`, system-mode, profile-write or new application TX family appears.

## Mechanically idle day

For all observed frames, compressor request (`0x280.f0`), achieved speed (`0x384.f0`), compressor power (`0x385.f0`), blower request (`0x200.u16@2`), feedback (`0x318.u16@4`) and blower power (`0x320.f0`) equal zero. The `0x281.byte7` request-mode candidate remains zero. There is no observed heat-pump heating/cooling, auxiliary electric heat, reversing-valve/defrost, leak-mitigation or pressure-protection event.

## Nineteen isolated stator heat cycles: 348 -> 367

Nineteen `0x282.byte1` cycles start and finish entirely within October 25; all have associated `0x390.byte0` 44/45/46 values, with actual compressor speed at zero.

| Measurement | Min | Median | Mean | Max |
|---|---:|---:|---:|---:|
| Cycle duration, minutes | 7.355 | **8.261** | 8.331 | 9.591 |
| `0x282 -> 0x390` first-nonzero lag, seconds | 8.795 | **9.377** | 9.277 | 9.712 |
| Start-to-start spacing, minutes | 35.606 | **67.992** | 66.326 | 133.255 |
| Outdoor ambient at start, °F | 50.28 | 56.21 | 58.03 | 72.82 |

Observed outdoor input power has a median ~88 W across stator-enabled samples, against ~13 W during standby, reaching a maximum 97 W. The cumulative project corpus is now **367 fully completed isolated stator cycles**.

## Idle pressure, indoor mirrors, network

Outdoor ambient ranges ~50.225–72.903 °F. The `0x383.f0` pressure candidate ranges ~158.169–217.230, `0x383.f1` ~156.761–215.456. Across **42,932 paired observations** median absolute separation is **1.251 raw units**, maximum ~2.563. Correlation to ambient is ~0.9951 and ~0.9971 respectively. This remains equalization evidence, **not** a validated gauge/absolute or PSI conversion.

All six `ZoneStatus.1.H` room-temperature mirrors match nearest live `0x490.f0` readings. Of 63 `SystemOpStatus.E` indoor-humidity updates, 56 match the nearest `0x490.byte4` reading, and the other seven match within two seconds (asynchronous update ordering).

All **40,910** observed `0x53D` frames are zero and `0x53E.byte5` remains five across **40,910** frames. Heartbeat nodes `0x701–0x705` report only operational `0x05`; no `0x000` NMT reset or `0x081/0x083` EMCY frames occur.

## Fifteenth exact-length/no-NUL JSON

At ~16:27:22 UTC, `0x641/0x5C1` carries `{"DebugUI":{"HiHeapRemaining":"23560192"}}`. The block-SDO initiate advertises **42 bytes**, exactly the JSON body length, with **no trailing NUL**. The transaction completes with final block ACK/end response and appears intact in the collector. This is the fifteenth independently captured exact-length/no-NUL transfer. The recorded heap value is a diagnostic only: no memory-leak conclusion is established.

## CI / regression and TX boundary

The October 24 GitHub workflow compiled all five ESPHome firmware configurations successfully, but its separate safety-test job failed because C++ string escaping in the synthetic October 22 Schedule split-seam fixture was malformed. That test fixture has been corrected using standard C++ raw string literals; its standalone native regression compiles and passes locally. The current October 25 replay also passes with no transport errors. No runtime assembler or TX behavior needed a new change.

Total qualified historical evidence: **367** isolated stator cycles, **18** stock zone-1 setpoint writes, **15** no-NUL transfers. Existing global and per-family setpoint/fan opt-in gates remain off. System mode, profiles, network settings, arbitrary JSON, auxiliary heat stages, EEV, defrost, reversing valve and A2L mitigation writes remain blocked.
