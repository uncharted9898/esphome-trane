# 2026-10-03 full-day stock setpoint transport qualification

## Capture integrity

Source archive: `trane-2026-10-03.tar.gz`

- 24 hourly JSONL chunks
- 2,649,806 total records
- 2,647,343 raw CAN records
- 82 distinct CAN IDs
- 2,463 `TRANE_JSON` records
- zero malformed JSONL rows
- one malformed decoded `TRANE_JSON` payload, traced to the known pre-fix
  optional-NUL receiver bug rather than archive corruption
- UTC coverage approximately 00:00:00.081 through 23:59:59.932

## Stock SpOverride.Put transactions

Two stock writes were captured on request COB-ID `0x641`:

```json
{"SpOverride":{"Put":{"1":{"Csp":"77","Hsp":"62","HoldType":"1","Source":"1"}}}}
{"SpOverride":{"Put":{"1":{"Csp":"78","Hsp":"62","HoldType":"1","Source":"1"}}}}
```

Both use `HoldType:"1"` and `Source:"1"`. No stock
`SystemMode.Put` transaction appears anywhere in this day, so setpoint-write
qualification must not be generalized to mode control.

## CANopen transport

The first 80-byte JSON string is sent with a terminating NUL, so the CANopen
block-download initiate request declares 81 bytes:

```text
641 C2 0A 30 00 51 00 00 00
5C1 A0 0A 30 00 0C 00 00 00

641 01 ...
641 02 ...
...
641 0B ...
641 8C ...

5C1 A2 0C 00 00 00 00 00 00
641 CD 00 00 00 00 00 00 00
5C1 A1 00 00 00 00 00 00 00
```

This is standard CANopen block SDO download to object `0x300A:00`.
The server selects a 12-segment block, acknowledges sequence 12, and the
client's `CD` end request encodes three unused bytes in the final seven-byte
segment.

After transport completion, `0x649` broadcasts the accepted
`SpOverride.Update` / zone state. The application acknowledgement then uses a
standard segmented SDO transaction:

```text
641 21 0A 30 00 0E 00 00 00
5C1 60 0A 30 00 00 00 00 00
641 00 7B 22 41 63 6B 22 3A
5C1 20 00 00 00 00 00 00 00
641 11 22 32 30 30 22 7D 00
5C1 30 00 00 00 00 00 00 00
```

Decoded application payload:

```json
{"Ack":"200"}
```

The second setpoint change repeats the same transaction structure, independently
qualifying request direction, object index, COB-ID pair, block negotiation,
block acknowledgement, end handshake and application Ack path for setpoint
writes.

## SystemOpStatus.E

The day contains 23 `SystemOpStatus.Update.E` changes, values 51-59.

Nearest-sample comparison against `0x490.byte4`:

- 22/23 exact
- correlation approximately 0.996
- R² approximately 0.991

Many changes occur while the compressor is off. This directly disproves the
speed-ceiling interpretation and confirms E as a structured indoor-humidity
mirror. The continuously available `0x490.byte4` source remains the preferred
friendly Home Assistant humidity source.

## Operating-day summary

From `SystemOpStatus.C`:

- 18 new cooling starts
- about 261.2 minutes total structured cooling-state time
- about 100.4 minutes total `AC Stage 2`
- longest structured cooling interval about 105.5 minutes
- that interval contains about 100.4 minutes of Stage 2

From raw `0x384.f0` compressor motion there are 19 operating intervals,
because the archive begins with a carry-over run already active at midnight.

The maintained compressor speed, compressor-demand, blower request/feedback,
pressure-pair, line-voltage and power families remain coherent across the day.

## Third exact-length/no-NUL sample

At approximately 03:17:09 UTC, object `0x300A:00` declares exactly 42 bytes
and carries:

```json
{"DebugUI":{"HiHeapRemaining":"32022528"}}
```

There is no trailing NUL inside the declared length. This is the third
independent target observation, after September 30 and October 1, proving that
Trane JSON transport supports both NUL-sized and exact-JSON-sized payloads.


## Stator heat

One isolated stator-heat interval occurs at approximately
12:04:56-12:13:09 UTC (~8.2 minutes).

`0x390.byte0` first becomes nonzero about 8.8 seconds after the
`0x282.byte1` enable. The cumulative project total is now **76 isolated
stator-heat cycles**.

## Other maintained telemetry checks

The full-day archive independently confirms the existing mappings:

- numeric `IndoorStatus.E` remains tightly tied to the `0x200.u16@2`
  blower-speed request (correlation ~0.999; median scale ~8.0 units/%);
- seven additional `0x385.f1 = 65535` startup sentinels appear and remain
  correctly excluded by the 0-200 RPS validity filter;
- active `0x383.f0/f1` continue to split as suction/high-side pressure and
  re-equalize at idle;
- `0x460.f0` remains tightly correlated with the outdoor power-electronics
  thermal family while `0x430.f1` and both `0x450` fields remain
  unqualified.

No A2L/leak, heating, defrost, reversing-valve, or 185.x
low-suction-protection event is present in the structured stream.
