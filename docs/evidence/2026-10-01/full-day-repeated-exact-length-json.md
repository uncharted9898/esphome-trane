# 2026-10-01 full-day long-run and repeated exact-length JSON evidence

Source bundle: `trane-2026-10-01.tar.gz`

## Capture integrity

- 24 hourly JSONL members
- 2,653,183 JSONL records
- 2,651,251 CAN records
- 1,929 collector `trane_json` records
- 82 unique CAN IDs
- zero malformed JSONL rows
- first record: 2026-10-01 00:00:00 UTC
- last record: 2026-10-01 23:59:59 UTC

One collector `trane_json` payload is malformed for the same reason identified
on 2026-09-30: this archive was captured with the pre-fix receiver, while the
underlying CAN transport is valid.

## Cooling operation

Six compressor-running intervals were captured:

1. 01:59:43-03:52:41 UTC (~113.0 min)
2. 15:12:18-15:18:51 UTC (~6.6 min)
3. 17:34:01-17:41:21 UTC (~7.3 min)
4. 17:50:50-20:37:54 UTC (~167.1 min)
5. 20:44:56-23:31:10 UTC (~166.2 min)
6. 23:40:53-23:50:35 UTC (~9.7 min)

The long runs contain sustained `AC Stage 2` intervals while compressor speed
continues to modulate continuously.

## Structured control/state path

The familiar lifecycle holds:

- `SystemOpStatus.C = AC Stage 1/2` during active cooling;
- `IndoorStatus.D = B` active and `A` stopped;
- `ZoneStatus.HcStatus = 2` during cooling, `4` during shutdown/coast, and
  `1` idle;
- `SystemOpStatus.A = B` on active call, then `E` / `D` during shutdown.

Two setpoint override transactions were captured:

- 01:59:30 UTC -> Csp 77 F
- 15:18:55 UTC -> Csp 78 F

The first override precedes `AC Stage 1` by about 3 seconds and actual
compressor motion by roughly 12 seconds.

## Blower request/feedback confirmation

Across 184 numeric `IndoorStatus.E` updates paired with `0x200.u16@2`:

- correlation: ~0.999
- median scale: ~8.0 request units per percent
- numeric E spans 35-71%

At clean startup, `IndoorStatus.E` and the `0x200` request can already be
nonzero while `0x318.u16@4` motor feedback and blower power are still zero.

The maintained chain remains:

- `IndoorStatus.E` -> blower speed request/target percent
- `0x200.u16@2` -> blower speed request candidate
- `0x318.u16@4` -> blower motor speed feedback
- `0x281.u16@0` -> airflow target/command candidate
- `0x318.u16@6` -> unresolved motor-adjacent candidate

## Pressure behavior

All six cooling intervals continue to show the established pressure behavior:

- idle/equalized pair before start;
- `0x383.f0` suction field falls after compressor startup;
- `0x383.f1` high-side field rises;
- shutdown collapses the split back toward equalization.

No 185.x low-suction protection event occurred.

## 0x385 startup sentinel

Two additional clean starts emit:

`0x385.f1 = 65535`

before the field returns to its normal compressor-speed-ceiling range.

The existing 0-200 RPS validity filter remains justified.

## Outdoor thermal/raw families

The unresolved families remain unresolved:

- `0x430.f1`
- `0x450.f0`
- `0x450.f1`

`0x460.f0` again tracks the outdoor power-electronics thermal family:

- corr with `0x410.f0`: ~0.93
- corr with `0x410.f1`: ~0.92
- corr with `0x430.f0`: ~0.94

while showing essentially no useful correlation with `0x430.f1` or either
`0x450` field. It remains a generic temperature candidate.

## Repeated exact-length/no-NUL 0x300A JSON

At 23:21:59 UTC the raw CAN stream carries:

```json
{"DebugUI":{"HiHeapRemaining":"32538624"}}
```

The initiate request again declares **42 bytes**, exactly the JSON byte length,
with no trailing NUL.

The old receiver emits the message after 41 bytes:

```text
{"DebugUI":{"HiHeapRemaining":"32538624"}
```

and the sixth/final block segment arrives immediately afterward with the
missing final brace.

This independently reproduces the exact same wire form first observed on
2026-09-30 with a different heap value. The optional-NUL firmware/analyzer fix
therefore addresses a repeatable protocol form rather than one anomalous
message. Regression coverage now includes both captured values.

## Stator heat

Four isolated stator-heat cycles occurred:

- 10:44:53-10:53:09 UTC
- 12:21:55-12:30:28 UTC
- 13:13:07-13:21:32 UTC
- 13:55:05-14:03:46 UTC

`0x390` becomes nonzero ~9.1-9.7 seconds after `0x282` enable in all four.

The cumulative project total is now **73 isolated cycles**.

## Safety boundary

All conclusions and fixes are receive-side only. Application/control TX remains
fail-closed.
