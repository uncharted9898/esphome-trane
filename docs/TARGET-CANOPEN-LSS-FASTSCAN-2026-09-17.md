# Target CANopen LSS Fastscan decode — 2026-09-17

Status: protocol-level identification confirmed from passive capture plus public CANopen/CiA-305 references. No physical Trane device role is assigned to any LSS or heartbeat node by this note.

## Capture signature

The installed target repeatedly emits:

```text
CAN-ID 0x7E5 DLC 8
51 00 00 00 00 80 00 00
```

This is an exact byte-for-byte match for the standard CANopen Layer Setting Services (LSS) Fastscan initialization request.

CANopen LSS uses:

```text
0x7E5  LSS manager -> LSS server
0x7E4  LSS server  -> LSS manager
```

For Fastscan command specifier `0x51`, the request payload is:

```text
byte 0      command specifier = 0x51
bytes 1..4  IDNumber, little-endian uint32
byte 5      BitCheck
byte 6      LSSSub
byte 7      LSSNext
```

The target packet therefore decodes as:

```text
command   = 0x51  LSS Fastscan
IDNumber  = 0x00000000
BitCheck  = 0x80
LSSSub    = 0x00
LSSNext   = 0x00
phase     = Fastscan initialization/reset
```

A standards example published for CANopen sensors uses the identical initialization packet:

```text
0x7E5  51 00 00 00 00 80 00 00
```

and shows the positive Fastscan response as:

```text
0x7E4  4F 00 00 00 00 00 00 00
```

The current high-load target capture contains the manager request but no `0x7E4` response inside its roughly one-minute observation window. That absence must not be interpreted as proof that no server supports LSS; it only describes this capture window.

## Why this matters for Trane Link

This closes one of the protocol-level unknowns. `0x7E4/0x7E5` should not be treated as arbitrary Trane-private telemetry. They are standards-backed CANopen LSS traffic used for discovery/configuration of node identity and bit timing.

That also reinforces the broader architecture already visible on the bus:

- `0x701..0x705`: CANopen heartbeat producer frames; state byte `0x05` means operational in this capture.
- `0x000`: CANopen NMT command channel when present.
- `0x7E5`: LSS manager requests.
- `0x7E4`: LSS server responses when present.
- `0x581`, `0x5C1`, `0x5C9`, `0x601`, `0x641`, `0x649`: Trane/SC360 service and segmented-JSON traffic layered beside the standard CANopen management plane.

The physical device behind CANopen node 1, 2, 3, 4, or 5 remains intentionally unassigned until a controlled topology test ties a node ID to a device reboot or disconnect.

## Analyzer support

`tools/trane_capture_analyzer.py` now decodes this management layer into a separate `canopen_management` report. It exposes:

- latest heartbeat state per observed node ID;
- raw NMT command + target node when `0x000` appears;
- LSS direction (`manager_to_server` or `server_to_manager`);
- Fastscan `IDNumber`, `BitCheck`, `LSSSub`, and `LSSNext`;
- Fastscan phase (`initialize` versus a normal bit probe);
- positive `0x4F` server responses.

This decoder is passive and does not generate LSS traffic.

## Highest-value topology experiment

A later controlled test can map node IDs without transmitting anything from the ESP bridge:

1. record stable `0x701..0x705` heartbeats;
2. power-cycle exactly one known physical Link device using normal service procedures;
3. observe which heartbeat enters boot-up/pre-operational and returns to operational;
4. repeat for each device if needed;
5. record the mapping only after the same result is reproduced.

That would turn the current standards-level node-state decode into a physical Trane topology map while preserving the listen-only boundary.
