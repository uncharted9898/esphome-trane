# Waveshare ESP32-S3-RS485-CAN reference hardware

This is the preferred reference board for the Trane Link bridge.

## Why this board

- ESP32-S3 with native TWAI/CAN controller.
- Onboard isolated CAN physical layer.
- CAN field side is isolated from the ESP32 side.
- Screw terminals for CAN H/L.
- Selectable 120 ohm termination resistor.
- USB-C can power the board for commissioning without using HVAC power.

## Trane Link connection

For initial commissioning connect only:

| Waveshare | Trane Link |
| --- | --- |
| CAN H | DH |
| CAN L | DL |

Do **not** connect Trane R or B to the CAN terminals. The CAN field side is isolated.

Power the board from USB-C during initial commissioning.

## Termination

Leave the Waveshare CAN 120 ohm termination jumper **OPEN / disabled**.

The Trane Link system is already terminated by its equipment topology. This bridge is a parallel high-impedance node, not a new end-of-line terminator.

Before first connection, power the HVAC off and verify the Waveshare board does not present approximately 120 ohms across CAN H/L by itself.

## CAN pins

Reference configuration:

- CAN TX: GPIO15
- CAN RX: GPIO16
- Bus speed: 50 kbit/s

These pins drive the onboard isolated CAN interface; no external MCP2515 or transceiver is required.

## Commissioning stages

### Stage 1: passive capture

Flash `waveshare-trane-listenonly.yaml`.

The ESP32 TWAI peripheral runs in `LISTENONLY` mode. It receives frames without ACKing the bus and ESPHome will not transmit frames in this mode.

Acceptance criteria before leaving this stage:

- stable 50 kbit/s traffic;
- repeated SC360 traffic on 0x649 and related IDs;
- UX360 operates normally;
- no new HVAC faults caused by attaching the bridge;
- expected outdoor and indoor CAN ranges are observed.

### Stage 2: active monitor

Flash `waveshare-trane.yaml` with `tx_enabled: false` in the `trane_bus` component.

TWAI is in normal mode, so the bridge participates electrically in CAN arbitration/ACK, but Trane application command TX remains blocked in software.

### Stage 3: local control

Enable Trane command TX only after the exact installed system has been characterized.

The bridge still:

- requires recent SC360 traffic before writes;
- validates mode/setpoint commands;
- serializes write commands while waiting for an ACK;
- treats SC360-reported state as authoritative;
- never continuously reasserts Home Assistant state.

## Power for permanent installation

The board's wide-voltage input is DC. Do not feed Trane 24 VAC directly into it.

For a permanent HVAC-powered install use a properly rated 24 VAC to DC converter and feed the Waveshare board within its documented DC input range. USB-C remains the preferred power source for commissioning.

## Recovery rule

Removing or losing power to this bridge must have no effect on normal UX360/SC360/equipment operation. Do not cut or route the Trane Link bus through the bridge in series.
