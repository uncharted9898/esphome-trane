# Documentation

This directory is split into **maintained reference documentation** and **dated evidence**.

If a dated capture note conflicts with a maintained reference document, the maintained reference is authoritative. Dated notes are preserved because the false starts, disproved mappings, and raw observations are useful reverse-engineering evidence.

## Start here

| Document | Purpose |
|---|---|
| [WIRING.md](WIRING.md) | Physical Waveshare/Trane Link wiring, pins, termination, and safe tap topology |
| [COMMISSIONING.md](COMMISSIONING.md) | First-connect, capture, qualification, and guarded-control workflow |
| [TELEMETRY.md](TELEMETRY.md) | **Current authoritative telemetry map**, confidence levels, and unresolved fields |
| [CANOPEN-LINK-TRANSPORT.md](CANOPEN-LINK-TRANSPORT.md) | CANopen NMT/LSS/SDO transport decode and Trane JSON mailbox framing |
| [CONTEXT.md](CONTEXT.md) | Current architecture, repo state, safety boundaries, and next engineering work |
| [FIRMWARE.md](FIRMWARE.md) | SC360/UX360 firmware observations and capture guidance |
| [TECHNICIAN-3.4.0-MONITOR-SCHEMA.md](TECHNICIAN-3.4.0-MONITOR-SCHEMA.md) | Extracted Technician 3.4.0 monitor/schema evidence used for correlation |
| [evidence/README.md](evidence/README.md) | Chronological target captures and requalification notes |

## Authority hierarchy

Use documentation in this order:

1. **Current source/tests** — what the firmware actually exposes and enforces.
2. **TELEMETRY.md** — maintained semantic map for target-observed fields.
3. **CANOPEN-LINK-TRANSPORT.md** — maintained transport/network decode.
4. **WIRING.md / COMMISSIONING.md / CONTEXT.md** — maintained operational guidance.
5. **evidence/** — dated point-in-time observations; may contain mappings later disproved.

The evidence archive is intentionally not rewritten to make old conclusions look correct in hindsight.

## Target system

Current target/reference installation:

- outdoor unit: **5TWV0X24A1000B**
- air handler: **5TAMXC03AV31DB**
- thermostat/controller: **UX360 + SC360**
- refrigerant: **R-454B / A2L**
- bridge hardware: **Waveshare ESP32-S3-RS485-CAN**
- Trane Link bus: **50 kbit/s classic CAN**
- bridge topology: **parallel tap**, not inline gateway

## Current project status

Passive decode is the production-safe path.

Working/qualified areas include:

- CANopen NMT heartbeat decode;
- CANopen LSS Fastscan/session reconstruction;
- CANopen SDO JSON receive at Trane object `0x300A:00`;
- indoor/outdoor binary telemetry;
- live room temperature, indoor humidity, and outdoor ambient temperature;
- blower request/feedback/actual airflow;
- compressor request/actual/target speed families;
- structured profile/status snapshots with freshness ages;
- bounded raw CAN capture and unknown-ID census.

Application/control TX remains **fail-closed** until a stock UX360 setpoint/mode write is captured and the originating SDO transaction is qualified.

## Documentation maintenance rules

- Preserve historical capture notes under `evidence/`.
- Do not promote a Candidate field without independent correlation.
- If a mapping is disproved, update `TELEMETRY.md` and the runtime label/tests; leave the dated evidence note intact with its historical banner.
- Avoid duplicating full protocol tables in multiple maintained files.
- Put transport mechanics in `CANOPEN-LINK-TRANSPORT.md`.
- Put semantic field meanings in `TELEMETRY.md`.
- Put install/test procedures in `COMMISSIONING.md`.
