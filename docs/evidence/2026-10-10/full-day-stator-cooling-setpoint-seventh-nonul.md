# 2026-10-10 full-day cooling, stator and stock control evidence

Source: `trane-2026-10-10.tar.gz`. Original archive analyzed passively, without bus transmission.

## Archive/reassembly integrity

- 24 hourly chunks covering 00:00:00.056–23:59:59.917 UTC.
- 2,599,760 JSONL records: 2,599,232 raw CAN frames, 528 structured JSON logs.
- 82 distinct 11-bit CAN IDs; zero malformed rows, invalid CAN payload lengths, or bridge clock resets.
- 528/528 raw CANopen JSON bodies reconstructed and matched to collector output. No missed, extra, malformed, abort or incomplete transactions.
- SDO session breakdown: 263 `0x649/0x5C9` block status transfers; two `0x641/0x5C1` block downloads (DebugUI and SpOverride.Put); 263 `0x641/0x5C1` segmented application ACKs. All 263 application ACK values were 200.
- No >512-character JSON profiles. Long logger-buffer validation remains outstanding.

## Three cooling runs

| Start UTC (approx) | End UTC (approx) | Actual compressor runtime |
|---|---|---:|
| 03:00:10 | 03:09:14 | 9.07 min |
| 03:17:48 | 04:07:01 | 49.22 min |
| 04:14:35 | 04:29:30 | 14.91 min |

Total physical runtime **73.20 min**. The structured `SystemOpStatus.C` timeline contains `AC Stage 1` for ~70.92 min and four very brief `AC Stage 2` intervals totaling **52.60 seconds**. These are real transient status messages, not sustained Stage 2 operation. Requested compressor speed peaks at 45 RPS; achieved speed ~45.1 RPS, compressor power ~644 W, outdoor input power ~800 W. One additional `0x385.f1=65535` startup sentinel supports the existing speed sanity filter.

`0x281.byte7` matches all three compressor request intervals, with start-edge lag ~0.10–1.15 s and end-edge lag ~-0.91–0.77 s. Compressor motor onset follows request by ~4.46–9.74 s. In combination with October 6 fan-only evidence, this remains a **compressor-request-adjacent state candidate**, not confirmed motor speed or blower activity.

## Ten stator-heat cycles (156 -> 166)

All ten are complete, compressor speed remains exactly zero and each aligns with three nonzero phase-current candidate channels. Total duration ~80.69 min, per-cycle duration ~7.64–8.67 min, median ~8.04 min, mean ~8.07 min. Start-to-start intervals ~57.43–95.91 min, median ~70.10 min. `0x390.byte0` onset follows `0x282.byte1` by ~8.90–9.68 s, median ~9.46 s; nonzero values 44, 45, 46. Outdoor power rises to ~88–97 W during isolated stator intervals. Starts span ~11:38–22:29 UTC, ambient ~60.08–70.80 F. Cumulative project corpus **166 completed isolated stator cycles**.

## Seventh exact-length/no-NUL DebugUI transfer

At ~01:28:47 UTC the raw `0x641/0x5C1` CANopen block download advertises **42 bytes** and carries exactly:

```json
{"DebugUI":{"HiHeapRemaining":"29868032"}}
```

No trailing NUL is indicated. Sequence 1 through 6, final `0x86`, `A2 06 00`, `C1` and `A1` are observed. The deployed receiver emits the full valid JSON. This is the seventh independent field example and directly confirms the optional-NUL fix remains healthy.

## Sixth independent stock setpoint Put

At ~02:56:51 UTC, `0x641/0x5C1` contains the exact stock write:

```json
{"SpOverride":{"Put":{"1":{"Csp":"77","Hsp":"62","HoldType":"1","Source":"1"}}}}
```

The transaction advertises **81 bytes** (80 JSON + NUL), uses negotiated block size 12, final request sequence `8C`, matching `A2 0C 00`, block-end `CD` and success `A1`. It is followed by `SpOverride.Update`, `ZoneStatus`, and segmented `{"Ack":"200"}` (with further application ACKs for follow-up updates). Combined with October 3/5: **six stock setpoint writes**, all zone 1 / HoldType 1 / Source 1. No write-scope expansion is implied.

## Environment and raw numeric families

Outdoor ambient spans **~59.98–71.32 F**. Compressor-idle pressure samples at least 20 minutes after completed running intervals have `0x383.f0/f1` median absolute separation ~0.97 (mean ~0.82; max ~5.13). In cooling the high-minus-low pressure separation reaches ~130.56 raw units. Gauge-vs-absolute conversion remains unresolved.

`0x460.f0` electronics-thermal candidate remains highly correlated with `0x410.f0` (r≈0.995), `0x410.f1` (r≈0.989) and `0x430.f0` (r≈0.988). Raw `0x430.f1` and `0x450.f0/f1` remain unrelated to this thermal family (|r| less than ~0.02 in this day). Avoid assigning units or exact sensor ownership.

All five CANopen heartbeat node IDs remain operational; `0x53D.byte0` stays 0 and `0x53E.byte5` stays 5, each for 40,970 corresponding status frames. No NMT/EMCY network reset appears.

## Structured room/humidity mirrors

Three `ZoneStatus.Update.1.H` room-temperature values match nearest `0x490.f0` exactly. Eight of nine `SystemOpStatus.Update.E` humidity values match the nearest binary `0x490.byte4`; the ninth updates from 55 to 54 about 0.606 seconds after the structured message, another transport-ordering difference rather than a conflicting mapping.

## Safety boundary and remaining work

No stock system-mode `Put`, indoor-fan `Put`, electric-heat stage, defrost, reversing-valve, A2L event or 185.x pressure protection event appears. Qualified zone-1 setpoint and Technician fan writers remain independently opt-in/default-off. Mode, arbitrary JSON, profile and HVAC safety-related writes remain blocked. Long (>512-byte) structured logger validation still requires a new stock profile sweep.

The October 10 archive required a wire regression fixture and maintained documentation/evidence updates, not new application-write behavior.
