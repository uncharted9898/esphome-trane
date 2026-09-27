# 2026-09-26 full-day cooling-cycle qualification

Source bundle: `trane-2026-09-26.tar.gz`

## Capture integrity

- 24 hourly JSONL members
- 2,607,190 CAN records
- 531 decoded Trane JSON records
- 82 unique CAN IDs
- zero malformed JSONL records
- first record: 2026-09-26 00:00:00 UTC
- last record: 2026-09-26 23:59:59 UTC

## Real AC Stage 1 operation

Unlike the preceding idle-only days, this archive contains five independent
cooling cycles with coherent startup, modulation, shutdown and blower coast.

Approximate compressor-running intervals from `0x384.f0 > 1 RPS`:

1. 21:31:35-21:36:51 UTC (~5.3 min)
2. 21:56:44-22:06:47 UTC (~10.0 min)
3. 22:17:13-22:29:30 UTC (~12.3 min)
4. 22:40:31-22:50:29 UTC (~10.0 min)
5. 23:08:09-23:15:20 UTC (~7.2 min)

All five cycles share the same structured lifecycle:

- `SystemOpStatus.C = "AC Stage 1"` at call start, then `"--"` at shutdown.
- `OdStatus.C = A` active, then `D` stopped.
- `IndoorStatus.D = B` active, then `A` stopped.
- `ZoneStatus.HcStatus = 2` during cooling.
- `ZoneStatus.HcStatus = 4` appears briefly during shutdown/coast.
- `ZoneStatus.HcStatus = 1` once idle.
- `IndoorStatus.E` emits `TA_INV_HI` at healthy startup, then numeric
  35-40 values, then 0 after shutdown.

The repeated `TA_INV_HI` startup token proves that an arbitrary nonnumeric
`IndoorStatus.E` value must not be published as an indoor fault. The HA parser
was corrected accordingly; E remains available on its raw entity.

## Pressure-pair qualification

The five cycles strongly reinforce the `0x383` low/high absolute-pressure
interpretation.

Representative transitions:

- immediately before startup, `0x383.f0/f1` are nearly equal;
- ~30 s after startup, the high/low split is roughly 56-71 psi;
- ~2 min after startup, the split is roughly 113-148 psi;
- during sustained cooling the low side remains near ~120-147 while the high
  side remains around ~235-255 for these ambient conditions;
- after shutdown the split collapses back toward equalization.

Example first cycle:

- pre-start: ~227.9 / 226.5
- +30 s: ~189.3 / 260.2
- +120 s: ~105.0 / 253.1
- end-30 s: ~144.3 / 255.2
- +60 s after shutdown: ~173.4 / 241.7

The temperature chain moves coherently at the same time:

- compressor-discharge candidate rises;
- suction-line temperature falls;
- liquid-line temperature remains on the warm/high side.

This is substantially stronger than idle equalization alone.

## Compressor/request relationships

The binary speed chain remains coherent:

- `0x280.f0` is the live compressor speed request;
- `0x384.f0` tracks achieved compressor speed;
- `0x385.f1` behaves as a dynamic speed ceiling;
- `0x387.f0` remains fixed at 55 and is not actual speed.

`OdStatus.CompDemandPercent` continues to track the binary demand mirror.
`OdStatus.B` is strongly correlated with the binary compressor request during
modulation but should remain documented as structured speed percentage rather
than converted to RPS directly without the enclosing OEM scale/reference.

## Indoor/blower behavior

During active cooling:

- actual airflow `0x281.u16@0` reaches ~720 CFM on startup and modulates into
  the ~535-660 CFM range;
- `0x318` blower feedback/speed channels follow the delivered airflow;
- `0x320.f0` blower power becomes nonzero;
- supply temperature falls into roughly the 50-60 F range during sustained
  cooling;
- return temperature remains around the upper-70s to mid-80s depending on the
  cycle.

The structured `IndoorStatus.E` numeric 35-40 family does not equal literal
RPM/CFM; preserve it as structured status/percentage and use the qualified
binary channels for live blower measurements.

## Stator heat

Thirteen isolated stator-heat cycles occur earlier in the day while the
compressor/fan remain stopped.

- `0x282.byte1` remains the stator-heat enable.
- `0x390.byte0` remains 44-46 while stator heating is electrically active.
- Combined with 2026-09-23/24/25, there are now 50 isolated stator-heat cycles.

That repetition is strong enough to treat the `0x390` semantic as
**Stator Heat Power Level**. Exact units remain unresolved because no
synchronized Technician display has proven 44-46 to be literal watts.

## Remaining raw families

The active cooling cycles still do not justify friendly names for:

- `0x430.f1`
- `0x450.f0`
- `0x450.f1`
- `0x460.f0`

Their behavior should continue to be evaluated against known Technician monitor
fields rather than inferred from magnitude alone.

## Safety boundary

All conclusions are receive-side only. Application/control TX remains
fail-closed.
