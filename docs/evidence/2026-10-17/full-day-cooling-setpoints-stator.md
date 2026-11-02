# 2026-10-17 full-day cooling, six stock setpoint writes, and nine stator cycles

Source: `trane-2026-10-17.tar.gz`, SHA-256 `47870db796d11b7970292fefbc0ebedf41a0d2f7fb0821c83893eacb02b9416d`. Analysis was passive and uses CAN device ticks for motor/stator intervals.

## Capture integrity and CANopen replay

- 24 hourly chunks, 2,633,202 JSONL records: 2,631,192 raw CAN frames and 2,010 structured JSON messages.
- 81 unique CAN IDs, zero malformed records, DLC faults, CAN clock resets, NMT reset commands, or EMCY frames.
- All 2,010 CANopen JSON messages independently reconstructed and matched to emitted collector messages **in order and by content**. No SDO aborts, incomplete transactions or mismatches.
- 1,002 `0x649/0x5C9` block status updates, 1,002 segmented `0x641/0x5C1` application ACKs (all `200`) and six additional `0x641/0x5C1` stock `SpOverride.Put` block downloads.
- All transfers include a terminating NUL; no twelfth exact-length/no-NUL transfer. No long structured profile payload or split `WifiList` observed on this day.

## Eight completed cooling runs

Eight complete actual compressor-speed intervals total **200.46 minutes**. The longest runs approximately 02:57:39–04:48:24 UTC (**110.74 minutes**), including one uninterrupted `AC Stage 2` interval 03:12:25–04:43:16 UTC (**90.85 minutes**). Two other Stage 2 intervals last ~23.59 and 12.86 min, respectively; Stage 2 total **127.30 min**. Overall observed maximum actual compressor speed 49.2 RPS, compressor power 853 W, outdoor input power 1,023 W. Three `0x385.f1=65535` speed-ceiling startup sentinels remain correctly outside valid RPS; **no 65535 W compressor-power reading** occurs.

The `0x281.byte7` compressor-request-adjacent field repeats all eight request windows. The 2026-10-06 blower-only disproof remains in force: do not rename it to blower active.

## Nine isolated stator cycles: 205 -> 214

All nine stator events start and end within October 17, with compressor speed zero:

| Enable UTC | Duration (s) | Ambient (F) | 0x390 onset delay (s) |
|---|---:|---:|---:|
| 12:40:38 | 508.83 | 57.65 | 9.240 |
| 14:01:06 | 524.58 | 58.01 | 9.217 |
| 15:30:54 | 509.81 | 57.03 | 9.213 |
| 16:37:38 | 488.58 | 58.23 | 9.474 |
| 18:01:45 | 518.51 | 56.10 | 8.836 |
| 19:03:03 | 516.00 | 57.01 | 9.515 |
| 20:06:44 | 513.61 | 57.31 | 9.537 |
| 21:11:48 | 512.62 | 56.85 | 9.517 |
| 22:45:50 | 474.06 | 53.62 | 9.669 |

Median cycle duration **512.62 s (8.54 min)**; median enable-to-power delay **9.474 s**. Nonzero `0x390.byte0` values remain 44/45/46. Project corpus now **214 fully observed isolated stator cycles**. Outdoor-temperature control logic remains unresolved.

## Six more stock UX360 setpoint writes: 7 -> 13

All six `0x641/0x5C1` block downloads are 81 advertised bytes (80-byte JSON plus NUL), targeting `0x300A:00`. Each contains only `SpOverride.Put` zone 1, `Hsp=62`, `HoldType=1`, `Source=1`, and preserves stock field order:

| UTC | Csp (F) |
|---|---:|
| 01:40:36 | 77 |
| 02:12:36 | 78 |
| 02:30:29 | **80** |
| 02:53:43 | 78 |
| 02:54:14 | 77 |
| 19:58:46 | 78 |

All have corresponding `SpOverride.Update` status and application `Ack:200`. The capture expands observed cooling-setpoint values but **does not broaden** the supported zone/hold/source policy or enable new command families. Total independent stock UX360 setpoint writes: **13**.

## Environmental and network mirrors

- `SystemOpStatus.E` indoor humidity: **28/28** sparse structured updates match nearest `0x490.byte4`.
- `ZoneStatus.1.H` room temperature: **5/5** match nearest `0x490.f0`.
- `0x383.f0/f1` pressure pair separates strongly in cooling; median absolute difference during Stage 2 about **129.36 raw units**. Gauge-versus-absolute calibration still unproven.
- `0x53D` remains all zero in 40,926 samples; `0x53E.byte5` remains 5 in 40,925 samples; heartbeat nodes 1–5 remain operational. No NMT/EMCY.

## CI repair

The previous exact-head validation failed only the safety-contract tests (all firmware profiles compiled successfully): an unterminated Python tuple in `tests/test_capture_analyzer.py` and a synthetic native `WifiList` fixture missing its fourth closing brace. Both tests have been corrected, preserving the bounded receive-only assembler and all default-off write gates. Runtime writer/decoder semantics remain unchanged by this day's capture.
