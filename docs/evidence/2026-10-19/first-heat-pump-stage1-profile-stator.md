# 2026-10-19: first heat-pump heating, Technician profiles and request-mode discriminator

Source `trane-2026-10-19.tar.gz`; SHA-256 `9ce95aebe0656e8a49eedf51f8118d027d90b436ec5b24aa6a291829aa4e9f88`. All observations are passive.

## Integrity and CANopen
24 complete hourly files; 2,601,728 JSONL records (2,601,366 CAN and 362 emitted JSON), 82 CAN IDs, zero malformed records, invalid CAN lengths, device-tick resets, NMT commands, or EMCY. Independent, order-preserving reassembly matches **362/362** structured JSON messages. Completed transactions: 168 `0x649/0x5C9` block status transfers, 168 `0x641/0x5C1` segmented application ACKs (all 200), and 26 complete `0x641/0x5C1` stock block downloads. Zero parser mismatches, aborts or incomplete transactions.

The Technician session ~13:33–13:36 UTC includes two rounds of `GetProfile`/`RemoveProfile` requests and reports `DailyRuntime` (1,088 JSON bytes) and `MonthlyRuntime` (1,594 JSON bytes), both logged fully on each sweep, plus `IndoorConfigSettings`, `TechAppAccess`, `WeatherData`, `ZoneSettings` and `OutdoorSettings`. These are read-only observations; `GetProfile`, `RemoveProfile`, mode and arbitrary JSON TX remain unqualified and disabled. No Wi-Fi credentials or unrelated identifiers are retained here.

The twelfth field-observed exact-length/no-NUL `DebugUI.HiHeapRemaining` is **25108480** at 23:53:59 UTC, advertised exactly 42 bytes, successfully reassembled/logged. No memory-leak conclusion is drawn from the diagnostic trend.

## First explicit HP Stage 1 heating operation

The stock system broadcasts `SystemOpStatus.C = HP Stage 1` across three runs:

| Actual compressor start UTC | Stop UTC | Nonzero-speed runtime |
|---|---|---:|
| 13:34:10 | 13:39:56 | 5.77 min |
| 14:17:33 | 14:24:01 | 6.46 min |
| 14:48:09 | 14:54:19 | 6.16 min |

Total actual-speed runtime ~**18.38 minutes**. Maximum actual compressor speed **45.1 RPS**, compressor power **689 W**, outdoor input power **825 W**, blower power **13.59 W**; two `0x385.f1=65535` invalid speed-ceiling startup sentinels support retaining that filter, with no compressor-power sentinel. Indoor gas/liquid candidate channels rise under heating; do not infer exact physical gas/liquid sensor locations without Technician correlation.

During the active heating windows, `0x383.f0` has median ~108.16, `0x383.f1` median ~225.29, with signed median high-minus-low separation ~125.90 raw units. This is consistent with the existing paired-pressure interpretation even during heat-pump operation, but exact physical port roles, gauge/absolute calibration and PSI conversion are not yet established.

**New mode discriminator:** `0x281.byte7=2` across all three heat-pump compressor request windows, with each rise/fall within roughly 1.4 s of `0x280.f0>0`. Compare October 17's eight cooling request windows, where `byte7=1` throughout, and October 6's Technician blower-only test, where `byte7=0`. Idle and isolated stator heat on October 19 also show `0`. Strong interpretation is **compressor-request mode: 0 none, 1 cooling, 2 heating**. A *new diagnostic-only candidate* text sensor exposes these three observed values. The original numeric raw sensor remains intact, unknown codes remain unqualified, and this is not proof of reversing-valve, defrost or electric-heat control semantics.

## First stock heat setpoint increase

At 13:33:59 UTC, the stock UX360 emits exact 81-byte block-SDO:

```json
{"SpOverride":{"Put":{"1":{"Csp":"78","Hsp":"68","HoldType":"1","Source":"1"}}}}
```

The request has all 12 expected segments and final `A2 0C 00`, `CD`, `A1`; `SpOverride.Update`, `ZoneStatus.Hsp=68` and `Ack:200` follow. This increases independently observed stock setpoint writes **13 → 14**, now directly including heating Hsp=68 in addition to prior Hsp=62. The existing writer already accepts heat/cool setpoints within its configured validation bounds, and no broader zone/hold/source or new TX family is authorized.

## Isolated stator heat 237 → 255

**18 complete cycles** with no boundary carry-out; median duration **8.56 min** (range ~6.97–10.71), median `0x282.byte1` to `0x390.byte0` delay **9.17 s** (range ~8.81–9.79). Nonzero `0x390` values remain **44, 45, 46**. All operate with actual compressor speed zero and stator phase-current candidates active. Outdoor ambient at stator starts spans ~42.65–68.31 F. Cumulative project evidence is **255 complete isolated cycles**.

## Mirrors and network
42 humidity structured updates: 41 match the nearest `0x490.byte4`; the remaining one matches within 1.5 seconds. Nine room-temperature updates: 7 nearest matches, the other 2 match within 1.5 seconds. `0x53D` all zero (40,867 samples), `0x53E` stays `000000000105` (40,864 samples), and all five CANopen heartbeat nodes report operational `05`. No OEM restart, leak/mitigation, 185.x protection, confirmed defrost or electric-heat stage event appears.

## Safety
The SC360 remains master. Zone-1 setpoint writer and independently gated Technician fan writer remain default-off. System-mode, profile, network, raw JSON, electric heat, EEV, defrost/reversing-valve and A2L writes remain blocked. Capturing HP Stage 1 is evidence for passive decoding, not qualification to command heat mode.
