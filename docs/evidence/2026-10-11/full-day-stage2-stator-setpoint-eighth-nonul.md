# 2026-10-11 full-day Stage 2, stator, stock setpoint and eighth no-NUL evidence

Source archive: `trane-2026-10-11.tar.gz`. Analysis was read-only; no CAN frames were transmitted by the analyzer.

## Capture and transport integrity

- 24 hourly JSONL chunks, UTC 00:00:00.034 through 23:59:59.982.
- **2,615,222** valid JSONL records, including **2,614,246** raw CAN frames and **976** collector `trane_json` records.
- **82** unique CAN IDs, zero malformed JSONL records, zero invalid CAN payload lengths, zero ESP32 device-tick resets.
- Independent raw-CAN reconstruction produces **976** structured messages: **487** `0x649/0x5C9` block-SDO status updates, **487** `0x641/0x5C1` segmented application responses, and **two** `0x641/0x5C1` block-SDO transfers.
- Every reconstructed JSON value and source CAN ID matches the collector's 976 messages; **all 487 application ACK values are 200**.
- No observed CANopen SDO aborts. Both new block transfers include a successful initiate, final sequence ACK, end request and end response. No new profile/control transport family appeared.
- No long `EquipSummary` or `WifiList` body occurs, so the separate `logger.tx_buffer_size: 4608` improvement is still awaiting an on-device >512-character profile test.

Structured roots: `Ack=487`, `OdStatus=336`, `IndoorStatus=84`, `SystemOpStatus=53`, `ZoneStatus=13`, `SpOverride=2` (one Put, one Update), `DebugUI=1`.

## Four cooling intervals, including 118.29 minutes sustained AC Stage 2

Actual compressor-speed intervals (`0x384.float[0]>0`):

| Start UTC | Stop UTC | Runtime |
|---|---|---:|
| 19:24:40.836 | 19:31:14.799 | 6.57 min |
| 19:43:49.792 | 22:06:27.106 | **142.62 min** |
| 22:14:58.539 | 22:25:57.256 | 10.98 min |
| 22:43:13.144 | 22:50:24.967 | 7.20 min |

Total physical compressor runtime **167.36 min**.

`SystemOpStatus.C` structured staging during the second interval:

- 19:43:40.968 – 20:03:01.215: `AC Stage 1` (~19.34 min);
- 20:03:01.215 – 22:01:18.694: **uninterrupted `AC Stage 2` (~118.29 min)**;
- 22:01:18.694 – 22:06:11.731: `AC Stage 1` (~4.88 min).

The other three physical runs are Stage 1. Across the complete day, structured Stage 1 totals ~47.80 minutes, and Stage 2 ~118.29 minutes; the small gap versus physical runtime is due to start/ramp/coast transition timing.

| Operating observation | Stage 1 median | Stage 2 median |
|---|---:|---:|
| `0x384.f0` actual compressor speed | ~29.9 RPS | ~39.0 RPS |
| `0x385.f0` compressor power | ~421 W | ~614 W |
| `0x38C.f1` outdoor input power | ~534 W | ~744 W |

Day maxima: actual compressor speed ~49.1 RPS, compressor power **864 W**, outdoor input power **1,032 W**, compressor demand `0x281.byte6` **61%**. Two additional `0x385.f1=65535` startup sentinels reconfirm the maintained speed sanity filter. `0x281.byte7` produces four intervals following compressor request, not blower feedback; the previous blower-active label remains disproved.

No heating, defrost, electric-heat stage, refrigerant mitigation/A2L event, 185.x protection, or novel CAN identifier is evidenced by this capture.

## Thirteen complete isolated stator-heat cycles: 166 -> 179

All thirteen cycles complete within October 11. None crosses either archive boundary; all occur with actual compressor speed zero.

- Duration min **~7.34 min**, median **~7.72 min**, mean **~7.66 min**, max **~7.94 min**.
- Start-to-start cadence varies through the day; the last two starts are ~16:08:38 and ~18:10:30 UTC.
- `0x390.byte0` appears **8.83–9.74 s** after `0x282.byte1` assertion, median **~9.35 s**, with observed nonzero levels still limited to **44/45/46**.
- During all 13 cycles the three `0x388.f0/f1`, `0x389.f0` phase-current candidate fields become nonzero, while compressor motion remains zero and outdoor input power peaks ~89–96 W.

The cumulative corpus is **179 fully completed isolated stator-heat cycles**.

### Earlier 75°F inhibit hypothesis is too narrow

Outdoor ambient for October 11 ranges **~68.94–80.83°F**. Critically:

- a stator cycle begins ~16:08:38 UTC with outdoor ambient **~75.24°F**;
- another begins ~18:10:30 UTC at **~77.03°F**.

This **disproves a hard 75°F stator-heat cutoff**. The October 7–10 warm-period gaps still suggest scheduling depends on temperature and/or additional conditions, but the exact OEM eligibility/interval rule remains unresolved and must not be hard-coded.

## Pressure equalization and electronics thermal family

The `0x383` pressure pair retains coherent refrigeration behavior:

- suction/low field `0x383.f0` overall raw range ~94.43–224.48;
- high-side field `0x383.f1` overall raw range ~202.73–293.01;
- Stage 2 median absolute separation **~134.47 raw units**;
- idle samples at least 20 minutes after the latest compressor stop: median absolute separation **~0.86**, maximum ~3.66.

This supports the suction/high-side roles; *gauge versus absolute representation and Technician display calibration remain unverified*.

`0x460.f0` continues to vary slowly (~84.58–85.95) and correlate with the outdoor power-electronics thermal family:

- versus inverter/IPM candidate `0x410.f0`: **r ~0.968**;
- versus PFC candidate `0x410.f1`: **r ~0.974**;
- versus outdoor-fan IPM candidate `0x430.f0`: **r ~0.986**.

Exact sensor ownership and units are still unknown. `0x430.f1` and `0x450.f0/f1` remain raw; near-zero correlation with this thermal family does not justify giving them guessed labels.

## Room/humidity and network status

Four sparse `SystemOpStatus.Update.E` humidity values (**62, 63, 62, 61**) match the nearest live `0x490.byte4` samples exactly. No structured `ZoneStatus.Update.1.H` room-temperature mirrors occur on October 11, so this day provides no new direct room-mirror qualification.

All `0x53D` status frames (**40,953**) remain `00 00 00 00 00` and all `0x53E` frames (**40,953**) remain `00 00 00 00 01 05`. Heartbeat nodes `0x701` through `0x705` are exclusively `0x05` (operational), with no NMT reset or EMCY.

## Eighth exact-length / no-NUL JSON transfer

At **19:02:07 UTC**, the `0x641/0x5C1` block-SDO on object `0x300A:00` advertises exactly **42 bytes**:

```json
{"DebugUI":{"HiHeapRemaining":"29351936"}}
```

The 42-byte JSON has **no trailing NUL**. The request contains six segments, final `0x86`, followed by `A2 06 00`, end request `C1`, and response `A1`. The installed receiver emits the complete valid `TRANE_JSON`.

This is the **eighth independent** target-observed exact-length/no-NUL `DebugUI.HiHeapRemaining` transfer.

## Seventh stock UX360 zone-1 setpoint write

At **23:35:12.743 UTC**, the stock thermostat sends:

```json
{"SpOverride":{"Put":{"1":{"Csp":"78","Hsp":"62","HoldType":"1","Source":"1"}}}}
```

Wire evidence:

- request `0x641`, response `0x5C1`, object `0x300A:00`;
- `C2 0A 30 00 51 00 00 00`: 81 indicated bytes, 80 JSON bytes plus NUL;
- response `A0 0A 30 00 0C`: negotiated 12-segment block;
- final sequence `8C`, ACK `A2 0C 00`, block-end `CD`, end response `A1`;
- `SpOverride.Update` at ~23:35:13.181;
- application `{"Ack":"200"}` at ~23:35:13.267;
- `ZoneStatus.Update.1.Csp=78` at ~23:35:13.382 and another `Ack:200` at ~23:35:13.433.

The seven independent stock writes across October 3, 5, 10 and 11 all preserve zone 1 / `HoldType=1` / `Source=1` and fixed application field order. As on prior idle setpoint captures, the write does **not** directly start the compressor. It strengthens existing local setpoint qualification without widening it.

## Control safety boundary

- Qualified zone-1 setpoint writer remains separately default-off and requires global TX plus its own gate.
- Qualified Technician indoor-fan enable 0/1 and percent 50/100 writer remains independently default-off and requires global TX plus its own gate.
- System mode, profile writes, arbitrary JSON, electric heat, defrost, EEV and A2L control remain unqualified and blocked.

No application decoder or TX behavior change is justified by October 11. Add only captured-wire regression coverage, corpus-count/source comments and corrected scheduling evidence.
