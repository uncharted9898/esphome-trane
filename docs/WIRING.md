# Waveshare Trane Link wiring

Reference hardware: Waveshare ESP32-S3-RS485-CAN

Target Trane Link system:

- 5TWV0X24A1000B outdoor unit
- 5TAMXC03AV31DB air handler
- SC360 system controller
- UX360 thermostat
- R-454B/A2L mitigation controller and sensor hardware

The Waveshare bridge is a **parallel CAN tap**. It is not an inline gateway and does not need to sit electrically between two OEM Trane devices.

## Recommended physical connection

The Waveshare onboard isolated CAN transceiver only needs the differential Trane Link pair:

```text
                    TRANE LINK BUS

      R  ----------------------------------------------- OEM 24 VAC
      DH ---------------------------------------------- CAN HIGH
      DL ---------------------------------------------- CAN LOW
      B  ----------------------------------------------- OEM COMMON
                |                         |
                | short parallel tap      |
                |                         |
                +----> Waveshare CAN H    |
                +----> Waveshare CAN L    |

Waveshare ESP32-S3-RS485-CAN

    USB-C / approved DC supply ---> board power

    GPIO15 ---> onboard isolated CAN TX ---> CAN transceiver
    GPIO16 <--- onboard isolated CAN RX <--- CAN transceiver

    CAN H  -------------------------------> Trane DH
    CAN L  -------------------------------> Trane DL

    Trane R  ------------------------------ NO CONNECTION
    Trane B  ------------------------------ NO CONNECTION

    Waveshare H1/R19 120-ohm CAN termination jumper: OPEN
```

Important hardware note: on this exact Waveshare ESP32-S3-RS485-CAN board, the CAN interface is the TXD2/RXD2 path on **GPIO15 TX / GPIO16 RX**. GPIO17/GPIO18 are the board's other serial path and must not be used for TWAI CAN on this product.

For first commissioning, power the Waveshare from USB-C. For permanent installation, use a properly rated HVAC 24 VAC to DC converter and feed the Waveshare within the board's documented DC-input range. Do not connect Trane 24 VAC directly to a DC input.

## Do I need another Trane Link distribution panel/port?

Not simply because the Waveshare is being added.

Trane Link is a CAN bus. A monitoring node can be connected electrically in parallel with another bus connection using a short branch/tap. The Waveshare does not need a dedicated OEM device port as long as the connection preserves the DH/DL bus and does not add termination.

For the described installation, the OEM devices consume the available connection positions:

```text
OEM communicating nodes

  UX360 thermostat
        |
      SC360
        |
      5TAMX air handler
        |
      5TWV0X outdoor unit
        |
  mitigation/A2L controller
```

If the existing four-port distribution point plus the additional air-handler Link connection gives every OEM device a proper connection, do **not** add a second distribution panel solely for the ESP bridge. Instead make a short parallel tap at an accessible Link connection.

A distribution block may still be desirable for serviceability, strain relief, or a cleaner install, but it is not inherently required just to create another electrical CAN node.

## Preferred tap locations

Use whichever location gives the shortest, cleanest branch while leaving OEM wiring intact.

### Option A - tap at the air-handler Link connection

```text
                    5TAMX LINK CONNECTION

Trane harness DH  o--------------------------- OEM DH onward
                  |
                  +--------------------------- Waveshare CAN H

Trane harness DL  o--------------------------- OEM DL onward
                  |
                  +--------------------------- Waveshare CAN L

R and B continue through the OEM harness only.
```

This is the preferred arrangement when the Waveshare will physically live at the air handler.

### Option B - share a distribution-panel bus position electrically

If the panel/harness exposes screw, spring, or splice-accessible DH/DL conductors, the Waveshare branch may share that electrical bus point:

```text
                  +---------- OEM NODE
                  |
DH BUS ------------+---------- OEM NODE
                  |
                  +---------- WAVESHARE CAN H

                  +---------- OEM NODE
                  |
DL BUS ------------+---------- OEM NODE
                  |
                  +---------- WAVESHARE CAN L
```

Do not force two conductors into a terminal that is not listed/designed for two conductors. If the connector cannot legally/mechanically accept two wires, make a proper pigtail/splice or use an appropriate distribution connector.

### Option C - short pigtail / tee

A small serviceable tee is often the cleanest option:

```text
OEM Link harness

DH --------+---------------- OEM device
           |
           +---- short pair ---- Waveshare CAN H

DL --------+---------------- OEM device
           |
           +---- short pair ---- Waveshare CAN L

R -------------------------- OEM device only
B -------------------------- OEM device only
```

The ESP is therefore electrically parallel even though the physical harness may look like an inline pigtail.

## Do not wire the ESP in series

Avoid this topology:

```text
SC360 ---> Waveshare electronics ---> air handler
```

The bridge should not be required for continuity of DH/DL. Removing or losing power to the bridge must leave the Trane system electrically intact.

Correct topology:

```text
                 +---- Waveshare
                 |
SC360 -----------+---------------- OEM Link bus -------- 5TAMX / ODU / UX360 / mitigation
```

## Termination

Do not enable the Waveshare onboard 120-ohm termination resistor.

Before adding the bridge, with HVAC power removed, measure resistance between DH and DL on the existing system and record it. The bridge should not materially change that reading.

The important rule is that the ESP bridge is **not an additional end-of-line termination point**.

## Wiring checklist

Before energizing the system:

- Waveshare H1/R19 120-ohm jumper is OPEN.
- CAN H is connected to Trane DH.
- CAN L is connected to Trane DL.
- Trane R is not connected to the Waveshare CAN terminal side.
- Trane B is not connected to the Waveshare CAN terminal side.
- Waveshare is powered separately by USB-C for first commissioning.
- DH/DL polarity is verified.
- OEM Link wiring remains continuous if the Waveshare is unplugged.
- No OEM mitigation wiring has been removed or repurposed.

## ESPHome CAN configuration

The Waveshare profile uses:

```yaml
canbus:
  - platform: esp32_can
    id: hvac_can
    tx_pin: GPIO15
    rx_pin: GPIO16
    can_id: 0x7FF
    use_extended_id: false
    bit_rate: 50kbps
    mode: NORMAL
```

`can_id` is required by ESPHome's CAN component as its default transmit identifier. Merely configuring it does not cause a CAN frame to be sent.

The Trane transport has its own explicit command ID (`0x641`). In the Home Assistant commissioning profile, application command transmission remains disabled:

```yaml
trane_bus:
  command_can_id: 0x641
  tx_enabled: false
  raw_json_enabled: false
```

NORMAL CAN mode means the CAN controller can ACK valid received CAN frames. That is deliberate so the bridge behaves like a normal attached CAN node. It is distinct from transmitting Trane thermostat/control messages.

## Home Assistant ESPHome entrypoint

Use:

```text
waveshare-trane-homeassistant.yaml
```

That file downloads the maintained `trane_bus` and `trane_hvac` external components directly from the `dev` branch during compilation and is intended for ESPHome Device Builder in Home Assistant.
