# Trane Technician 3.4.0 monitor schema evidence

> **Scope note:** this is app-side schema/reference evidence, not the maintained wire mapping. Current target semantics live in [TELEMETRY.md](TELEMETRY.md). An app identifier is not promoted to a CAN/HA meaning until target capture correlation supports it.

This note records static-analysis evidence from the Trane Technician Android application that is useful when correlating the Link CAN captures from this project.

It is intentionally **not** a wire-protocol decoder. The identifiers below are app-side monitor/model keys unless and until a target-system capture proves where and how they are represented on the Link bus.

The rule remains:

> Do not promote an app identifier, short monitor tag, or inferred value to a named Home Assistant entity until it has been correlated against a known equipment state on the target system.

## Provenance and scope

Analyzed application:

- Trane Technician `3.4.0` XAPK;
- analyzed XAPK SHA-256: `6afbd91b169ce6c45b569cc42b4bdd8357ada744327682d29b9a2d904bb1b80b`;
- React Native Hermes bytecode version: `96`;
- the application binary is **not** committed to this repository.

The useful evidence falls into three confidence classes:

1. **Bytecode-constructed schema mapping** — strongest app-side evidence. The application explicitly constructs a map from a compact monitor key to a named monitor identifier.
2. **Active transformation/reference** — the application reads a named field and derives another field from it in live monitor processing.
3. **String/search alias** — useful search/correlation terminology, but string presence alone does not prove a payload field or transport.

None of these classes alone proves a literal CAN ID, JSON object name, scaling factor, byte order, or physical Link-node address.

## 24AH monitor schema

Technician 3.4.0 constructs an equipment-specific monitor map under equipment class `24AH`.

The following assignments are explicit in Hermes bytecode:

| Compact key | Technician monitor id | Correlation meaning for this project |
|---|---|---|
| `A` | `CoilTemp` | indoor evaporator/coil temperature candidate |
| `B` | `GasTemp` | indoor gas/refrigerant temperature candidate |
| `C` | `Superheat` | indoor superheat |
| `D` | `ReturnAirTemp` | return-air temperature |
| `E` | `SupplyAirTemp` | supply-air temperature |
| `F` | `RetStaticPressure` | return static pressure |
| `G` | `ExtStaticPressure` | external/total static pressure family |
| `H` | `ActualAirflow` | delivered/actual airflow; primary CFM target |
| `I` | `ActualSpeed` | indoor motor/blower speed |
| `J` | `MotorPower` | indoor motor power |
| `K` | `EevPosition` | indoor EEV position |
| `L` | `ExtSw1Status` | external switch 1 state |
| `M` | `ExtSw2Status` | external switch 2 state |
| `N` | `onOffParser` object | semantic id not reconstructed yet |
| `O` | `onOffParser` object | semantic id not reconstructed yet |

This is materially stronger than finding strings such as `ActualAirflow` or `EevPosition` in the application: the app actually builds the `24AH` decoder/schema object with these compact keys.

### What this does and does not imply

The `A`-through-`K` labels are now high-priority correlation targets when a Link monitor/profile object can be associated with the indoor air handler. They are **not** permission to interpret every object containing `A`, `B`, `C`, etc. as this schema. The object/profile context must match the equipment monitor path.

For the target 5TAMX, this gives us a particularly useful correlation set:

- `A/B/C` should move coherently with ET/GT/superheat behavior;
- `D/E` should correlate with the already suspected indoor-air temperatures;
- `F/G/H/I/J` should make a commanded blower-CFM sweep highly discriminating;
- `K` should be obvious during an indoor EEV service test if that monitor object is present in captured traffic.

## Extended/base monitor schema: A2L and outdoor-control clues

The same Technician monitor module constructs a larger compact-key map. The entries most relevant to the 5TAMX/5TWV0X project are:

| Compact key | Technician monitor id | Use here |
|---|---|---|
| `N` | `AirflowPercent` | distinguish percent airflow from actual CFM |
| `O` | `CompressorTargetMaxSpeed` | compressor target-speed envelope |
| `P` | `CompressorTargetMinSpeed` | compressor target-speed envelope |
| `Q` | `CompressorTargetSpeed` | requested compressor target speed |
| `R` | `MocDriveIpmTemperature` | drive/IPM temperature candidate |
| `S` | `MocDrivePfcTemperature` | drive/PFC temperature candidate |
| `T` | `MocStatorHeatPower` | stator/sump-heating power family |
| `U` | `MocAcCurrent` | outdoor drive/current metric |
| `V` | `MocFanPhaseCurrent` | outdoor fan phase-current metric |
| `W` | `OdFanIpmTemperature` | outdoor-fan drive temperature |
| `X` | `MocInputPower` | outdoor drive input power |
| `Y` | `A2LSensor1ConcentrationLevel` | A2L sensor-1 concentration value |
| `AE` | `A2LSensor1Status` | A2L sensor-1 status |
| `AF` | `A2LSensor2Status` | A2L sensor-2 status |
| `AJ` | `OdEEVControlType` | outdoor EEV control mode/type |
| `AK` | `ViTemp` | VI temperature candidate |

There is no constructed `AD` entry in this map.

The symbolic reconstruction currently renders `AG` as `UnitPreference`, but that entry also carries an implausible `defineProperty` association and should be treated as unresolved until its register/object flow is re-qualified. It is deliberately omitted from the table above.

### A2L asymmetry matters

The bytecode explicitly constructs:

- `Y -> A2LSensor1ConcentrationLevel`;
- `AE -> A2LSensor1Status`;
- `AF -> A2LSensor2Status`.

Technician 3.4.0 does **not** contain an exact `A2LSensor2ConcentrationLevel` string. The application does contain Sensor-2 alarm/error/model/serial/version material, so Sensor 2 is clearly modeled, but we should not invent a symmetric Sensor-2 concentration key that this version of the app does not show.

During mitigation commissioning, search both the structured monitor/profile traffic and previously unseen raw CAN IDs for correlations with `Y`, `AE`, and `AF`, while retaining every unknown standard frame. A compact key is only meaningful after its enclosing monitor object has been identified.

## Active monitor transformations

The monitor reducer/processor in Technician 3.4.0 provides additional evidence that several names represent live values rather than merely UI labels.

It directly reads and derives:

- `CompressorSpeed` -> `CompressorSpeedRPM`;
- `LiquidPressure` -> `OutdoorLiquidPressureConvert`;
- `SuctionPressure` -> `OutdoorSuctionPressureConvert`;
- `ReturnAirTemp` + `SupplyAirTemp` -> `IndoorDeltaTemp`;
- `OutdoorSuctionTemp` + `IndoorGasTemp` -> `GasLineLosses`;
- `RetStaticPressure` + `ExtStaticPressure` -> `IndoorSupplyStatic`.

This strongly reinforces the hunt for **separate** suction and liquid pressures, separate indoor gas/coil temperatures, static-pressure values, actual airflow, and compressor actual/target speed.

It still does not identify the Link transport encoding or scaling by itself.

## Mitigation-control-board model evidence

The Technician websocket/system-model converter directly reads and writes `mcbInstalled`.

That is useful evidence that the application has a first-class “mitigation control board installed” state in its system model. It is not yet evidence that a Link CAN payload literally contains the text `mcbInstalled`.

Additional A2L search aliases present in Technician 3.4.0 include:

- `a2lSensor1`, `a2lSensor2`, `dataA2lSensor1`;
- `A2L Sensor 1 Model`, `A2L Sensor 1 Serial`, `A2L Sensor 1 Version`;
- `A2L Sensor 2 Model`, `A2L Sensor 2 Serial`, `A2L Sensor 2 Version`;
- explicit Sensor-1 and Sensor-2 alarm/error/not-connected/not-communicating-with-MCB text.

These are useful for profile/object discovery and equipment-inventory correlation, but remain **search aliases** rather than proven wire keys.

## Additional search aliases for refrigerant verification

Technician 3.4.0 also contains cooling/heating verification field families that line up with the refrigerant values we want. These have not been tied to a direct bytecode-constructed compact-key map in this analysis, so they remain search aliases only.

High-value examples include:

- `CcsVerIdCoilTemp`, `CcsVerIdCoilTempStatus`;
- `CcsVerIdSuperheat`, `CcsVerIdSuperheatStatus`;
- `CcsVerLiquidPressure`, `CcsVerLiquidPressureStatus`;
- `CcsVerLiquidTemp`, `CcsVerLiquidTempStatus`;
- `CcsVerOdSuperheat`, `CcsVerOdSuperheatStatus`;
- `CcsVerSubcool`, `CcsVerSubcoolStatus`;
- `CcsVerSuctionPressure`, `CcsVerSuctionPressureStatus`;
- `CcsVerSuctionTemp`, `CcsVerSuctionTempStatus`;
- corresponding `ChsVer...` heating-verification fields;
- `ChqVerIndoorGasTempStatus`.

The repeated `value` + `Status` pattern suggests the app tracks both a measurement and a verification/result state. Do not assume those names are serialized directly onto CAN.

## Wider alias set worth correlating

The app contains additional identifiers that should be kept in search notebooks and capture-analysis tooling.

### Indoor / airflow

- `actualAirflow`, `dataActualAirflow`;
- `requestedAirflow`, `targetAirflow`, `dataTargetAirflow`;
- `supplyStaticPressure`, `returnStaticPressure`, `totalStaticPressure`, `staticPressure`;
- `idEevPosition`, `idEevSteps`, `dataIdEevPosition`, `extendedIndoorEevStepPosition`;
- `idSuperheat`, `dataIdSuperheat`, `actualSuperheat`, `extendedIndoorGasSuperheat`;
- `idGasTemp`, `dataIdGasTemp`;
- `idEvapLiquidTemp`, `dataIdEvapliquid`;
- `extendedIndoorCoilTemp`, `extendedIndoorGasTemp`.

### Outdoor / refrigerant circuit

- `odEevPosition`, `dataOdEevPosition`, `extendedOutdoorEevStepPosition`;
- `odSuperheat`, `dataOdSuperheat`, `extendedOutdoorSuperheat`;
- `extendedOutdoorSubcool`;
- `suctionLinePressure`, `liquidLinePressure`, `SuctionPressure`, `LiquidPressure`;
- `dataLiquidPressure` and extended pressure aliases;
- `dataOdCoilTemp`, `odCoilTemp`, `extendedOutdoorCoilTemp`;
- `extendedOutdoorSuctionTemp`, `extendedOutdoorLiquidTemp`;
- `extendedOutdoorCompressorDischargeTemp`;
- `actualCompressorSpeed`, `CompressorSpeedRPM`, `compressorSpeed`;
- `compTargetSpeed`, `compTargetMinSpeed`, `compTargetMaxSpeed` and their data/extended variants.

Again: this wider list is vocabulary for searching and correlation, not a decoded protocol contract.

## How this changes the capture plan

### 1. Cold boot / private-profile capture

For `0x5C1`, `0x5C9`, `0x641`, and `0x649` reassembled data, preserve the complete object path/context around compact keys. Search for the known monitor object names as well as the app identifiers above.

Do not globally translate a short key such as `A` or `Y`; only apply a compact-key map after its equipment/profile context is proven.

### 2. 5TAMX blower sweep

The `24AH` map makes this a particularly strong experiment. During known commanded-CFM points, correlate candidate fields against:

- `H / ActualAirflow`;
- `I / ActualSpeed`;
- `J / MotorPower`;
- `F / RetStaticPressure`;
- `G / ExtStaticPressure`.

A single sweep can therefore separate actual CFM, motor speed/load, return static, and external static if the compact monitor object appears on Link traffic.

### 3. 5TAMX refrigerant/EEV correlation

Correlate:

- `A / CoilTemp`;
- `B / GasTemp`;
- `C / Superheat`;
- `K / EevPosition`.

The already suspected `0x283` ET/GT pair should be compared directly against `A` and `B`, while a qualified service-mode EEV movement gives a strong discriminator for `K` and superheat response.

### 4. 5TWV0X compressor/refrigerant correlation

Keep actual and requested compressor behavior separate:

- `CompressorSpeed` / `CompressorSpeedRPM`;
- `CompressorTargetMinSpeed`;
- `CompressorTargetMaxSpeed`;
- `CompressorTargetSpeed`;
- separate `SuctionPressure` and `LiquidPressure`.

This should help disambiguate the unresolved `0x380`-`0x38F` fields rather than forcing the old single generic pressure mapping onto the new outdoor unit.

### 5. Required A2L mitigation verification

Capture the entire required verification in listen-only mode and correlate:

- installation/presence state (`mcbInstalled` in the app model);
- `Y / A2LSensor1ConcentrationLevel`;
- `AE / A2LSensor1Status`;
- `AF / A2LSensor2Status`;
- any new device identity/profile objects;
- any previously unseen raw CAN IDs and state transitions;
- blower/airflow changes caused by mitigation.

Do not synthesize an additional refrigerant-leak event solely for reverse engineering.

## Promotion criteria for runtime entities

An app-side name can become a friendly runtime entity only after at least one of these is true:

1. a structured Link object is captured repeatedly with an unambiguous object path and the value follows a controlled test;
2. a raw CAN field has a stable encoding/scaling and follows at least two controlled state points plus an idle/return point;
3. the target equipment/Technician monitor value and the captured field agree over a sufficiently varied operating interval to rule out a coincidental correlation.

For pressure, CFM, EEV position, and A2L concentration, prefer multiple numeric points rather than a single matching value.

Until then, keep the raw candidate visible only as diagnostic/discovery data.
