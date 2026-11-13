> **Historical evidence — 2026-09-22.** This is a point-in-time target capture/requalification note. Current authoritative meanings live in [../../TELEMETRY.md](../../TELEMETRY.md) and source/tests.

# Outdoor sensor-chain long pass — 2026-09-22

Capture set:

- active-cooling logs 16 through 21
- Home Assistant state snapshot captured after the 2026-09-20 decoder pass
- Trane 5TWV0X service documentation and the previously reconstructed Technician 3.4.0 monitor vocabulary

## Why this pass matters

The earlier decoder had most live outdoor numeric channels, but several remained generically named or were being interpreted too narrowly. The new logs add another high-load interval plus a lower-load Home Assistant snapshot, enough to separate stable sensor channels from volatile raw/control fields.

No additional major standard-CAN numeric family appears in these captures. The remaining missing data is increasingly an identity/scaling/profile-hydration problem rather than absence of wire traffic.

## Outdoor temperature / pressure chain

The 5TWV0X outdoor board has separate ambient, coil, suction-temperature, liquid-temperature, discharge-temperature, suction-pressure, and liquid-pressure sensing. The observed frame sequence now lines up coherently with that physical chain:

| Wire field | New interpretation | Representative observations |
|---|---|---|
| `0x380.float[1]` | Outdoor Air Temperature | about 87.5-89.7 F |
| `0x381.float[0]` | Outdoor Coil Temperature | about 93.1-95.3 F |
| `0x381.float[1]` | Suction Pressure Signal Raw | about 192.2-193.9 raw |
| `0x382.float[0]` | Suction Line Temperature | about 65.4-66.5 F |
| `0x382.float[1]` | Liquid Line Temperature | about 90.5-93.1 F |
| `0x383.float[0]` | Compressor Discharge Temperature | about 130-135 F |
| `0x383.float[1]` | Liquid Line Pressure Candidate | about 366-380 in the high-load logs |

The first 0x382 float is promoted to the normal **Suction Line Temperature** entity.

### Pressure-scaling boundary

The semantic role of `0x381.float[1]` is much stronger after this pass, but the raw number is deliberately **not** labeled psi.

At high load it sits near 192-194 while suction-line temperature is in the mid-60s F. Treating the raw number as literal psig does not reconcile cleanly enough with the target refrigerant pressure/temperature behavior. Technician also contains explicit suction/liquid pressure conversion paths. Preserve the raw wire value until that conversion is reconstructed or a synchronized Technician pressure reading is captured.

The entity is therefore **Suction Pressure Signal Raw**, with no pressure device class and no psi unit.

## Drive and fan thermal family

Technician exposes separate monitor identifiers for drive inverter/IPM temperature, drive PFC temperature, and outdoor-fan IPM temperature.

The target frames show a matching thermal cluster:

- `0x410.float[0]`: roughly 98 F
- `0x410.float[1]`: roughly 99-100 F
- `0x430.float[0]`: roughly 97.3-97.5 F and closely follows the 0x410 pair

These are named as disabled candidates:

- `0x410 Drive Inverter/IPM Temperature Candidate`
- `0x410 Drive Rectifier/PFC Temperature Candidate`
- `0x430 Outdoor Fan IPM Temperature Candidate`

They remain diagnostic until a synchronized Technician monitor proves the exact one-to-one wire assignment.

By contrast, `0x430.float[1]` swings roughly 260-360 during otherwise steady operation. It is raw, not temperature.

## 0x450 stale-value bug

`0x450.float[0]` was previously published only below 300 because its callback inherited a temperature-shaped validity guard.

The new logs contain legitimate finite values above 300. The old guard could therefore leave Home Assistant displaying an older sub-300 value.

The parser now publishes every finite `0x450.float[0]` value. Both 0x450 floats are explicitly raw until their physical meaning is proven.

## 0x2D0 airflow clue

At high load:

- `0x2D0.word1` is roughly 511-516;
- `0x2D0.word2` is about 775;
- delivered `0x281` airflow is about 774 CFM;
- request/feedback channels are around 490-518 CFM.

In the lower-load HA snapshot, however:

- `0x2D0.word2` remains about 771;
- actual airflow falls to about 658 CFM.

That makes word2 a poor actual-airflow mirror but a useful **airflow limit/ceiling candidate**. It remains disabled and diagnostic.

## Still unresolved

Highest-value numeric gaps after this pass:

- the exact Technician conversion/scaling for the `0x381.float[1]` suction-pressure signal;
- synchronized qualification of `0x383.float[1]` liquid-line pressure;
- exact meaning of `0x386.float[0..1]`;
- `0x430.float[1]`;
- `0x450.float[0..1]`;
- `0x460.float[0]`;
- outdoor EEV command/position;
- defrost/reversing-valve state;
- A2L mitigation sensor/control-board state.

The bridge remains passive/application-TX-disabled while receive-side mappings are refined.
