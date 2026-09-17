# Target high-load requalification — 2026-09-17

Status: passive target-capture evidence. No CAN transmissions were generated for this analysis.

This note analyzes the later steady/high-load cooling capture from the installed system:

- outdoor: `5TWV0X24A1000B`
- indoor: `5TAMXC03AV31DB`
- controller: UX360 + SC360 (`TLINK360A2VVUG`)
- refrigerant generation: R-454B / A2L
- capture length: about 61 seconds
- raw `TRANE_CAN_LIVE` records parsed: 1,986

The purpose of this capture is important: several values that happened to be numerically similar in the earlier lower-load capture separate by a large amount here. That lets us reject some false labels and strengthen several other mappings.

## Promotion rule used in this note

A value is not promoted simply because one number looks plausible. The strongest evidence comes from combinations of:

1. the same field retaining the same representation over the whole capture;
2. behavior across more than one operating point;
3. agreement with the older Technician-monitor vocabulary/value set;
4. thermodynamic/electrical consistency;
5. an independent transition such as shutdown or load change.

Where one of those checks fails, the field stays a candidate or raw value.

## Capture-level anchors

The later capture is active cooling at a substantially higher outdoor load than the earlier correlation point. Representative stable values include:

```text
0x281 = [774, 500, 0, 356] as four LE uint16 words
0x308 = 76.53 F / 50.77..50.82 F
0x310 = 0.0866..0.0913 / -99 sentinel
0x320 = 45.40..46.76 W

0x380 = -99 sentinel / 93.09..93.39 F
0x381 = 98.18..99.23 / 195.14..195.42
0x382 = 69.52..69.87 / 95.85..96.58
0x383 = 143.533 / 391.18..400.29
0x384 = 57.8..58.0 / u16 340..353 / u16 768..774
0x385 = 1445..1486 / 66..68
0x387 = 55.0 / 0.4
0x388 = 5.3..5.4 / 5.3..5.4
0x389 = 5.2..5.4 / 6.4..6.7
0x38C = 0 / 1617..1701
0x38F = 237.0 / 3.9..4.0
```

The important result is not merely the values themselves. It is that fields which were both near 230–240 in the lower-load capture now separate into about `237` and about `391..400`.

## Outdoor refrigeration/electrical block requalification

### `0x383.float[1]` is not line voltage

The earlier lower-load correlation called this field line voltage because it happened to sit around 225–238 V while the Technician reference showed about 239 V.

That interpretation fails decisively in this capture: the same field is now about 391–400 while the equipment remains a 208/230-V-class residential outdoor unit. The value also moves with outdoor load instead of behaving like utility line voltage.

The line-voltage label must therefore be removed.

### `0x383.float[1]` — liquid/high-side pressure candidate

A high-side pressure interpretation now fits both operating points much better.

For R-454B, the Chemours Opteon XL41 pressure-temperature guide gives approximately:

- 118 F -> 385.3 psig
- 120 F -> 395.7 psig
- 122 F -> 406.2 psig

The observed `0x383.float[1] = 391..400` therefore corresponds to roughly 119–121 F saturated condensing temperature if the raw unit is psig. With outdoor ambient near 93 F, that is physically credible for active cooling.

The companion liquid-temperature candidate is near 96 F, which gives a plausible roughly 20-plus-degree subcooling relationship rather than an impossible below-ambient condensing state.

This is now the leading interpretation:

```text
0x383.float[0] -> compressor dome/discharge temperature candidate
0x383.float[1] -> liquid/high-side pressure candidate
```

`float[0]` remains candidate wording because the exact Technician field name has not yet been synchronized live.

### `0x38F.float[0]` — line-voltage candidate

`0x38F.float[0]` remains exactly 237.0 through this higher-load capture. Earlier target captures put the same field around 240–242, while the older Technician monitor reference showed 239 V.

Unlike `0x383.float[1]`, it does not rise with compressor load. This makes `0x38F.float[0]` the strongest current line-voltage candidate.

Keep candidate wording until a simultaneous voltmeter/Technician point is recorded, but the old `Liquid Pressure` label is no longer supportable.

### `0x385.float[0]` is not outdoor EEV position

The old EEV interpretation is disproven by scale alone in this run:

```text
0x385.float[0] = 1445..1486
```

The Technician reference expresses outdoor EEV position on a 500-step mechanism. A value near 1,500 therefore cannot be that same physical position.

The field instead tracks outdoor power extremely well:

```text
0x385.float[0] = 1445..1486
0x38C.float[1] = 1617..1701 W
```

Nearest-sample correlation in this capture is approximately `r = 0.86`. The ratio of `0x385.float[0]` to input power is roughly 0.87–0.90. In the earlier lower-load capture both fields were much lower, and both fell toward zero on shutdown.

The older Technician monitor also exposes separate compressor power and input power values. Therefore the new leading interpretation is:

```text
0x385.float[0] -> compressor power candidate, W
0x385.float[1] -> compressor target-speed candidate, RPS
```

This is a substantial correction from the earlier `Outdoor EEV Position` label.

### `0x381` / `0x382` ordering

Cross-operating-point temperatures now favor this layout:

```text
0x381.float[0] -> outdoor-coil temperature candidate
0x381.float[1] -> pressure-family / suction-pressure candidate RAW
0x382.float[0] -> outdoor suction-temperature candidate
0x382.float[1] -> liquid-temperature candidate
```

Why:

- Earlier low-load `0x381.float[0]` was near outdoor ambient; here it is about 99 F with ambient about 93 F, which is sensible for an outdoor-coil sensor in cooling.
- Earlier `0x382.float[0]` was around the mid-60s, close to the older Technician suction-temperature reference; here it is around 69.6 F.
- `0x382.float[1]` moved from roughly 69 F in the lower-load capture to about 96 F here, behavior expected from a liquid-line temperature as ambient/load rise.

However, **do not currently publish `0x381.float[1]` as psig**. In this capture the raw value is about 195 while the indoor refrigerant pair sits near 50.7/48.3 F. Treating 195 directly as R-454B psig implies a saturation temperature around 71 F, which is inconsistent with the observed cold indoor evaporator during active cooling. The field is clearly pressure-family data, but either its scaling or its exact semantic identity remains unresolved.

This is an example of why the repo should retain raw/candidate boundaries rather than force a friendly unit too early.

### `0x386.float[1]` is not vapor saturation temperature

It remains exactly 50.0 in this capture while the supposed pressure-related values and load state differ greatly from the lower-load run. A real saturation temperature would not remain pinned at the same value across those conditions.

Demote this field to raw/candidate status.

### `0x460.float[0]` is not proven liquid saturation temperature

It remains exactly about 84.37 F while the new high-side candidate moves around 391–400. R-454B saturation corresponding to 391–400 psig is around 119–121 F, not 84 F.

Therefore the old `Liquid Saturation Temperature Candidate` label is too specific. Keep `0x460.float[0]` as a generic temperature candidate until another Technician field identifies it. `ViTemp` remains one app-side search target, not a wire-level conclusion.

## Outdoor channels that survive this pass

The following mappings remain well supported:

### `0x380.float[1]` — outdoor ambient temperature

About 93.1–93.4 F in this run. `float[0]` remains the `-99` sentinel.

### `0x384`

Compound layout remains clear:

```text
bytes 0..3  float32 candidate speed/control value, about 57.8..58.0
bytes 4..5  uint16 drive DC voltage, about 340..353 Vdc
bytes 6..7  uint16 outdoor fan speed, 768..774 RPM
```

The exact semantic name of the first float remains candidate-level.

### `0x387.float[0]` — actual compressor speed

Stable 55 RPS = 3300 RPM. The second float remains a current candidate near 0.4 A.

### `0x38C.float[1]` — outdoor input-power family

About 1.62–1.70 kW in this run and strongly load-dependent. This continues to fit the Technician `MocInputPower`/input-power family.

### `0x388` / `0x389` — current family

All four values track outdoor load and sit in plausible current ranges. Exact assignment among drive current, AC current, phase current, and related channels still requires a synchronized Technician point.

Do not infer a power factor from one of these fields merely because a single operating point closes an electrical equation.

### `0x410`

The one sample in this capture is about 97.55 / 98.77 F. The Technician application exposes separate drive IPM and PFC temperatures, so this remains a good paired drive-temperature candidate. Ordering is unresolved.

### `0x430.float[0]`

About 96.8 F. `OdFanIpmTemperature` is a plausible app-side correlation target, but the wire mapping is not promoted yet.

## Indoor block strengthened by this run

### `0x281` compound blower status

All 28 frames are byte-for-byte identical:

```text
06 03 F4 01 00 00 64 01
```

As little-endian uint16 words:

```text
[774, 500, 0, 356]
```

The first and fourth fields remain the strong mappings:

```text
word0 -> actual airflow = 774 CFM
word3 -> blower speed = 356 RPM
```

`word1 = 500` remains requested/target-airflow-family candidate only. `word2 = 0` remains raw.

### `0x300` indoor refrigerant pair

This run is particularly useful because the first value changes while the second stays nearly fixed:

```text
float0: 58.90 -> about 50.7 F
float1: about 48.19 -> 48.29 F
float0 - float1: about 10.7 -> 2.4 F
```

That dynamic behavior substantially strengthens the existing interpretation:

```text
float0 -> indoor gas-temperature candidate
float1 -> indoor evaporator/liquid-temperature candidate
derived difference -> indoor superheat candidate
```

The exact Technician labels still deserve one simultaneous monitor capture before dropping `Candidate`.

### `0x308` return/supply temperatures

Stable near 76.53 / 50.8 F and still one of the strongest mappings in the capture.

### `0x310` / `0x320`

- `0x310.float[0]`: about 0.0866–0.0913, static-pressure family
- `0x320.float[0]`: about 45.4–46.8 W, blower power

The blower-power identification remains strong.

### `0x318` and the old blower electrical identity

`0x318.float[0]` is about 0.673–0.688 in this run and still follows blower operation, so blower-current remains a useful candidate.

But the earlier identity that multiplied `0x383.float[1] * 0x318.float[0] * 0x280.float[1]` to reproduce blower watts is invalidated because `0x383.float[1]` is not line voltage at this operating point. The derived `Blower V I PF Calculated Power` entity should not be treated as proof of any field.

`0x280.float[1] = 0.25` may still be a control/PF-like value during operation, but its physical meaning is unresolved.

## UX360/SC360 findings retained

### `0x490`

Still exactly 78 F plus byte 4 = 54 in this capture, supporting the zone-1 room-temperature + RH interpretation.

### `0x4B1`

Little-endian uint32 values change by exactly 60 seconds and line up with the capture clock. The sequence includes:

```text
02 38 AC 6A -> 1789671426 -> 2026-09-17 18:57:06 UTC
3E 38 AC 6A -> 1789671486 -> 2026-09-17 18:58:06 UTC
```

This confirms the Unix-epoch-seconds interpretation and shows that the bus value is refreshed on a minute boundary.

### Segmented JSON recovered from this capture

The reusable analyzer reassembles:

```json
{"Debug":{"IDBLE":"NOTADVERTISING"}}
{"Debug":{"IDBLE":"ADVERTISING"}}
{"Debug":{"IDBLE":"NOTADVERTISING"}}
{"Debug":{"IDBLE":"ADVERTISING"}}
{"IndoorStatus":{"Update":{"1":{"E":"83"}}}}
{"Ack":"200"}
```

The `IndoorStatus.Update.1.E = 83` value is retained as a compact status value. It should not be hard-mapped to percent airflow/speed until a controlled blower change proves the relationship.

## Runtime-label corrections justified by this capture

The following old labels should be treated as superseded:

```text
0x381.float[0]  "Suction Temperature"             -> outdoor-coil-temperature candidate
0x381.float[1]  "Suction Pressure" in psi         -> pressure/suction-pressure raw candidate; scaling unresolved
0x382.float[0]  "Liquid Temperature Candidate"    -> suction-temperature candidate
0x382.float[1]  "OD Coil Temperature Candidate"   -> liquid-temperature candidate
0x383.float[1]  "Line Voltage"                    -> liquid/high-side-pressure candidate
0x385.float[0]  "Outdoor EEV Position"            -> compressor-power candidate
0x386.float[1]  "Vapor Saturation Temperature"    -> raw/candidate
0x38F.float[0]  "Liquid Pressure"                 -> line-voltage candidate
0x460.float[0]  "Liquid Saturation Temperature"   -> generic temperature candidate
```

These changes are deliberately asymmetric: clearly disproven names are removed, but unresolved replacements remain candidates.

## Highest-value next capture

The next capture should synchronize Technician Monitor with the CAN log at three or more steady points while changing only one normal operating variable at a time.

Highest value fields to record simultaneously:

1. suction pressure and suction temperature;
2. liquid pressure and liquid temperature;
3. outdoor coil temperature;
4. compressor power and input power;
5. drive current average / AC input current / fan phase current;
6. outdoor EEV position;
7. indoor gas temp, indoor coil temp, indoor superheat, and indoor EEV position;
8. blower requested airflow, actual airflow, RPM, static pressure, current, and watts.

That one synchronized run should resolve the remaining pressure scaling, locate the actual outdoor EEV channel, and distinguish the current-family fields without guesswork.

## Tooling

`tools/trane_capture_analyzer.py` now provides a repeatable offline path for future captures. It:

- parses `TRANE_CAN_LIVE` records;
- reports per-ID counts, DLCs, median cadence, and last payload;
- reports typed float/u16/u32 ranges for the high-value target families;
- decodes the compound `0x281`, `0x384`, `0x490`, and `0x4B1` layouts;
- reassembles target segmented JSON on `0x601`, `0x641`, and `0x649` using the same framing rules as the ESPHome component;
- emits either human-readable output or `--json` for further correlation scripts.

It performs no CAN transmission and has no device-side side effects.
