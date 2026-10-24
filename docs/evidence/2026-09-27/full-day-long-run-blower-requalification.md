# 2026-09-27 full-day long-run cooling and blower requalification

Source bundle: `trane-2026-09-27.tar.gz`

## Capture integrity

- 24 hourly JSONL members
- 2,621,127 CAN records
- 1,409 decoded Trane JSON records
- 82 unique CAN IDs
- zero malformed JSONL records
- first record: 2026-09-27 00:00:00 UTC
- last record: 2026-09-27 23:59:59 UTC

## Cooling operation

Nine compressor-running intervals were captured, including one unusually long
continuous cooling run:

1. 19:35:36-19:42:35 UTC (~7.0 min)
2. 19:54:47-21:17:26 UTC (~82.6 min)
3. 21:25:43-21:38:04 UTC (~12.4 min)
4. 21:49:43-21:59:14 UTC (~9.5 min)
5. 22:13:14-22:22:15 UTC (~9.0 min)
6. 22:35:44-22:47:54 UTC (~12.2 min)
7. 22:58:00-23:09:54 UTC (~11.9 min)
8. 23:21:53-23:42:36 UTC (~20.7 min)
9. 23:51:37 through end of capture

The structured lifecycle remains consistent with the 2026-09-26 archive:

- `SystemOpStatus.C = AC Stage 1` during normal cooling;
- one `AC Stage 2` transition appears at 20:15:10 UTC inside the long run;
- `OdStatus.C = A` while outdoor cooling is active, `D` after shutdown;
- `IndoorStatus.D = B` while the indoor unit is active, `A` when stopped;
- `ZoneStatus.HcStatus = 2` while cooling, `4` during some shutdown/coast
  transitions, and `1` once idle.

## AC Stage 2 observation

At 20:15:10 UTC `SystemOpStatus.C` changes from `AC Stage 1` to
`AC Stage 2`. The compressor does not make a discontinuous jump at that exact
instant; instead the existing variable-speed ramp continues:

- request/actual speed were roughly 30 RPS at transition;
- compressor demand was about 39-40%;
- over the following minutes demand and speed continued to rise gradually.

This supports the idea that the stage text is supervisory demand/staging state,
not a discrete fixed-speed compressor stage.

## Blower command/feedback requalification

The low-load startups in this day provide the clearest separation yet between
indoor blower commands and actual motor response.

At the first cooling start:

- `0x281.u16@0` jumps from 0 to about 720 before blower current, blower power,
  and `0x318` feedback leave zero;
- `0x200.u16@2` begins around 286 request units;
- `0x318.u16@4` remains 0 until the blower physically starts, then rises to
  about 300 and follows subsequent modulation;
- `0x318.u16@6` also moves with motor operation but lacks an independently
  proven physical scale.

During shutdown, `0x281.u16@0` can remain nonzero after motor current/power
and `0x318` feedback collapse to zero. It therefore cannot be maintained as
"Actual Airflow."

Numeric `IndoorStatus.E` provides the strongest command-side correlation:

- E spans roughly 35-48 during the long modulation run;
- `0x200.u16@2 / E` has median scale about 7.9 request units per percentage
  point;
- correlation between E and `0x200.u16@2` is about 0.99.

Maintained map after this capture:

- `0x200.u16@2` -> blower speed request candidate;
- `0x318.u16@4` -> blower motor speed feedback;
- `0x281.u16@0` -> airflow target/command candidate;
- `0x318.u16@6` -> unresolved motor-adjacent candidate.

A synchronized Technician `ActualAirflow` / `ActualSpeed` screen is still
needed to establish the literal physical scaling of the two motor-related
binary words.

## Refrigerant pressure behavior

The `0x383` pair continues to behave coherently as low/high absolute pressure
through all nine cooling intervals:

- near idle/equalization the pair is close;
- on compressor start the low side falls while the high side rises;
- sustained cooling maintains a large pressure split;
- shutdown collapses the split back toward equalization.

The long 82-minute run provides sustained modulation evidence rather than only
short-cycle startup/shutdown evidence.

## Remaining raw outdoor families

The long modulation run was used to re-check:

- `0x430.f1`
- `0x450.f0`
- `0x450.f1`
- `0x460.f0`

The first three still show no stable correlation with compressor speed, power,
pressure, current, fan speed, or the qualified thermal channels and remain raw.

`0x460.f0` continues to correlate extremely tightly with the power-electronics
thermal family (`0x410` and `0x430.f0`) over the full day, but it remains
offset rather than directly matching a known Technician field. Keep the generic
temperature-candidate label until the OEM monitor identity is proven.

## Stator heat

Eight isolated stator-heat cycles occurred earlier in the day before compressor
operation began.

Across those eight cycles:

- `0x282.byte1` asserts first;
- `0x390.byte0` becomes nonzero after a median ~9.42 s;
- compressor and outdoor fan remain stopped during the isolated heating cycle.

Combined with the prior archives, the project now has 58 isolated stator-heat
cycles supporting the existing enable/power-level mapping.

## Safety boundary

All conclusions are receive-side only. Application/control TX remains
fail-closed.
