# Target 5TAMX blower electrical correlation — 2026-09-17

> **Superseded correlation note:** the later cool-ambient target capture disproves two conclusions below. `0x281.u16[3]` is not literal blower RPM (it changed from 356 to 2116/2117 while airflow stayed about 774/775 CFM), and `0x280.float[1]=2.5` occurs during active 775-CFM blower operation, so it is not a shutdown-only sentinel or literal power factor. The former V×I×PF identity also depended on the now-disproved `0x383.float[1]` line-voltage interpretation. Preserve the historical observations below, but use `TARGET-COOL-AMBIENT-REQUALIFICATION-2026-09-17.md` for current mappings. The leading blower-speed candidate is now `0x318.u16[3]`; `0x318.u16[2]` is an airflow-family candidate.


This note records a cross-capture identity found in the target 5TAMXC03 telemetry. It is based on multiple live Link captures from the installed system and the older Trane Technician monitor point documented in `TARGET-TECHNICIAN-CORRELATION-2026-09-17.md`.

## Strong mapping

During normal blower operation the following relationship holds:

```text
0x383.float[1] * 0x318.float[0] * 0x280.float[1] ~= 0x320.float[0]
      volts              amps             PF-ish            watts
```

Representative observations:

```text
238.43 V * 0.4141 A * 0.25 = 24.68 W
reported 0x320 power             ~= 24.56 W

233.2 V * 0.3970 A * 0.25 = 23.15 W
reported 0x320 power            ~= 22.9 W

232.4 V * 0.3799 A * 0.25 = 22.07 W
reported 0x320 power            ~= 21.61 W
```

Across 32 matched normal-running samples from two captures, the calculated and reported power differ by only a few tenths of a watt on average. This is far too structured to be an incidental correlation.

### Promotion

- `0x318.float[0]` — **Indoor blower input current**, amperes. High confidence.
- `0x320.float[0]` — **Indoor blower real input power**, watts. High confidence; independently supported by the Technician monitor and blower fan-law check.
- `0x383.float[1]` — line voltage, volts. Already strongly qualified from outdoor/Technician correlation and reused here as the common line-voltage measurement.
- `0x280.float[1]` — **power-factor-like raw field** during normal running. Do not yet expose it as an unconditional power factor.

## Why 0x280.float[1] remains conditional

During established blower operation the field is consistently `0.25` and closes the electrical power equation.

During the natural shutdown/ramp capture, however, the same field changes to `2.5` while blower power/current approach zero. `2.5` is not a physical power factor.

Therefore one of these is likely true:

1. `2.5` is an explicit sentinel / inactive-state encoding;
2. the field changes interpretation by blower state;
3. the decimal/scaling contract changes in an inactive control state.

Until a second independent source confirms the contract, retain the raw field and expose a derived PF candidate only when it is finite and within the physical range `0 < PF <= 1`.

## 0x280.float[0]

This field remains unresolved but is clearly tied to blower operation:

- roughly `34.5` at the higher initial blower operating point in the cold capture;
- around `29.1–29.4` in later steady cooling;
- falls toward `20` during blower ramp-down;
- reaches `0` after blower shutdown.

It is therefore a real blower load/control measurement rather than a static configuration constant. Do not call it torque, voltage, power, or airflow yet.

## 0x318 trailing words

`0x318` is an 8-byte compound frame:

```text
bytes 0..3: float32 blower input current (qualified)
bytes 4..5: uint16 candidate A
bytes 6..7: uint16 candidate B
```

Observed examples:

```text
current ~0.4756 A -> words ~544 / 363
current ~0.4155 A -> words ~508 / 335
current ~0.3467 A -> words ~457 / 305
current 0 A       -> words 0 / 0

newer steady point:
0.3799 A -> 464 / 330
```

Both words clearly track blower operation. Their exact meanings are not proven. Requested/target airflow and target/feedback motor-speed quantities are leading hypotheses because the Technician schema has separate `actualAirflow`, `requestedAirflow`, `targetAirflow`, `ActualSpeed`, and `MotorPower` concepts.

Do not promote units for these two words until synchronized Technician data distinguishes them.

## 0x281 requested-airflow evidence

`0x281` currently behaves as:

```text
word0 = actual airflow CFM                 (strong)
word1 = 500 during the observed cooling run
word2 = 0
word3 = blower RPM                         (strong)
```

The earlier idea that word1 means `100%` encoded as `500/5` is not strong enough. In a previous target capture `IndoorStatus.E` reported about 63–64% while `0x281.word1` remained 500. A 500-CFM requested/target value is consistent with that percent on a nominal ~800-CFM two-ton airflow scale.

Retain word1 as a **requested/target airflow CFM candidate** until a Technician airflow-command change is captured.

## Useful next qualification

Run a safe, normal blower-speed/airflow change while recording both:

- Technician Monitor `Actual Airflow`, `Target Airflow %`, `Blower Speed`, `Blower Power`, `Total Static Pressure`;
- raw `0x280`, `0x281`, `0x310`, `0x318`, `0x320`, and line voltage.

Three or more distinct steady operating points should be enough to identify the two trailing `0x318` words and resolve `0x280.float[0]`.
