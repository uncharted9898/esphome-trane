# 2026-10-24 — complete idle, 20 stator cycles and transport qualification

Source: `trane-2026-10-24.tar.gz`. Passive/read-only analysis; no CAN transmission.

## Integrity and CANopen

- 24 complete hourly JSONL chunks, 2,591,808 records.
- 2,591,720 raw CAN frames, 88 emitted structured JSON messages, 82 distinct CAN IDs.
- Zero malformed JSONL records or invalid CAN lengths; no collector reconnect or ESP device-clock reset.
- Independent receive-side SDO reconstruction matches **88/88** emitted messages, in original order and content: **44** `0x649/0x5C9` block-SDO status updates and **44** `0x641/0x5C1` segmented application ACKs, all `200`.
- No transport abort, incomplete transfer, out-of-sequence frame or unmatched structured message. No `Put` request or new profile family. All messages include trailing NUL in the indicated length; no new exact-length/no-NUL case and no Schedule/WifiList fragment this day.
- Emitted roots: SystemOpStatus 38, ZoneStatus 6, Ack 44; largest JSON body 45 bytes.

## Entire day mechanically idle

The compressor request, achieved speed and compressor power are all zero throughout. Blower request, motor feedback and power remain zero. The raw `0x281.byte7` compressor request-mode candidate remains 0 for all 40,882 observed frames. No cooling, heat-pump heating, fan-only, defrost, auxiliary electric heat, or A2L/pressure protection event appears.

Outdoor ambient `0x380.f1` ranges **49.26–69.11°F**. Both `0x383` pressure values track ambient closely (r≈0.9951 and 0.9972), with 42,946 samples of paired fields: `f0` ~155.95–209.93, `f1` ~154.52–210.08 and absolute separation median **1.237**, maximum **3.083** raw units. This reinforces the idle equalization mapping but does not establish gauge/absolute scaling or display PSI.

## Twenty complete stator-heat cycles: 328 → 348

All twenty `0x282.byte1` cycles start and finish inside the October 24 archive. All include nonzero `0x390.byte0` levels 44/45/46 and all three `0x388/0x389` phase-current candidate fields, with actual compressor speed fixed at zero.

| Metric | Min | Median | Mean | Max |
|---|---:|---:|---:|---:|
| Cycle duration (min) | 7.02 | **8.19** | 8.26 | 9.66 |
| `0x282` enable→`0x390` first nonzero (sec) | 8.83 | **9.21** | 9.21 | 9.77 |
| Start-to-start (min) | 41.84 | **69.16** | 70.34 | 171.17 |
| Outdoor ambient at start (°F) | 49.47 | 56.27 | 57.62 | 68.69 |

Outdoor electrical input-power median during the full enable windows is **88 W**, versus **13 W** standby; the observed input power maximum is **96 W**. Cycle enable edges include the initial ~9 s before input power rises, so the enable-window minimum still contains standby samples.

**Cumulative corpus through October 24: 348 completed isolated stator cycles.** No temperature cutoff or stator setpoint is inferred.

## Structured mirrors and network

- All six structured `ZoneStatus.Update.1.H` room-temperature messages match nearest binary `0x490.f0`.
- 36 of 38 sparse `SystemOpStatus.Update.E` humidity messages match nearest `0x490.byte4`; both others match the binary field within two seconds.
- `0x53D` remains `0000000000` for all 40,883 observed frames; `0x53E` remains `000000000105` for all 40,883.
- All five heartbeat IDs `0x701`–`0x705` report CANopen operational `05`; no NMT reset or EMCY appears.

## Receive-only Schedule regression from the October 22 source

The October 22 Schedule first block ends at byte 2048 immediately after the JSON key `"Start"`, and the continuation begins with the colon character. The two independently valid CANopen SDO block transfers indicate 2048 bytes and 1626 bytes (including a final NUL), concatenating to **3673 JSON bytes**. The existing bounded receive-only Schedule assembler correctly handles this boundary. A native C++ regression now reproduces the actual key-boundary seam in addition to the older synthetic string-value seam, preserving timeout, overflow, and interleaving guards. No application TX was added.

## Safety boundary

No new stock setpoint or Technician fan request is observed. The project totals remain 18 independently captured zone-1 setpoint writes and 14 no-NUL transfers. The global/default-off setpoint and Technician fan qualification gates remain unchanged. Mode, network/profile, arbitrary JSON, electric heat stages, EEV, defrost/reversing-valve and CNT09525/A2L controls remain blocked pending stock wire evidence.
