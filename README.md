# esphome-trane

Local ESPHome monitoring and reverse engineering for modern **Trane Link** HVAC systems.

The current target is a fully communicating R-454B system:

- outdoor unit: **5TWV0X24A1000B**
- air handler: **5TAMXC03AV31DB**
- thermostat/controller: **UX360 + SC360**
- bridge: **Waveshare ESP32-S3-RS485-CAN**
- bus: **50 kbit/s classic CAN**

The bridge is a **parallel CAN tap**, not a replacement thermostat or inline gateway. The stock UX360/SC360 remain installed and authoritative.

## Current status

### Working

- passive Trane Link CAN capture;
- CANopen NMT heartbeat/state decode;
- CANopen LSS Fastscan/session reconstruction;
- CANopen SDO receive/reassembly for Trane JSON mailbox object `0x300A:00`;
- structured profile/status decoding;
- target-observed indoor/outdoor binary telemetry;
- Home Assistant device grouping for thermostat, controller, air handler, and heat pump;
- live environmental telemetry:
  - room temperature from `0x490.float[0]`;
  - indoor humidity from `0x490.byte4` with invalid-value filtering;
  - outdoor ambient from `0x380.float[1]`;
- blower request/feedback/actual airflow telemetry;
- compressor request/actual/target speed families;
- raw CAN census/capture tooling;
- structured JSON freshness diagnostics.

### Deliberately not enabled

**Application/control TX remains opt-in and fail-closed by default.**

Passive captures proved the historical writer was not a valid CANopen SDO transaction. The October 3 and October 5 captures then supplied five complete stock UX360 `SpOverride.Put` transactions, including the `0x641/0x5C1` CANopen block-SDO handshake and application `{"Ack":"200"}`. The October 6 Technician session independently captured the indoor-fan `IndoorSettings.Put` family for enable/disable plus 50% and 100% requests. The maintained component now has one response-driven nonblocking SDO client shared by those two narrowly qualified write families.

`tx_enabled` still defaults to `false`. Setpoints additionally require `qualified_setpoint_tx_enabled: true`; indoor-fan writes independently require `qualified_indoor_fan_tx_enabled: true`. Both qualification gates default to `false`, preventing an older development config containing `tx_enabled: true` from silently gaining write capability after an update. Fan percentage is intentionally limited to the captured 50/100 values. Mode writes, profile requests and arbitrary JSON TX remain blocked because their stock request transactions have not been qualified. Passive monitoring remains the production-safe default.

## Hardware

Reference bridge:

**Waveshare ESP32-S3-RS485-CAN**

CAN pins on this board:

```yaml
tx_pin: GPIO15
rx_pin: GPIO16
bit_rate: 50kbps
```

Connect only the Trane differential pair to the isolated CAN interface:

- Trane **DH** -> Waveshare CAN H
- Trane **DL** -> Waveshare CAN L
- leave the Waveshare 120-ohm termination **open**
- do not place the bridge in series with the OEM Link wiring

For wiring details, power guidance, and tap topology see [docs/WIRING.md](docs/WIRING.md).

## ESPHome profiles

| File | Purpose |
|---|---|
| `waveshare-trane-listenonly.yaml` | Safest first-connect profile; listen-only capture/discovery |
| `waveshare-trane-commissioning.yaml` | Commissioning/census workflow |
| `waveshare-trane-homeassistant.yaml` | Curated Home Assistant monitoring profile |
| `waveshare-trane-homeassistant-debug.yaml` | Opt-in raw/debug HA profile for protocol work |
| `waveshare-trane-control.yaml` | Guarded control-development profile; qualified setpoint and indoor-fan writers available only when their separate TX gates are explicitly armed |
| `waveshare-trane-full.yaml` | Full decoder/integration profile |
| `esphome-trane.yaml` | Legacy full decoder retained for compatibility/testing |

## Protocol architecture

The target bus contains standard CANopen network/transport behavior plus Trane-specific application objects.

| CAN ID / range | Current interpretation |
|---|---|
| `0x000` | CANopen NMT |
| `0x701`-`0x705` | observed heartbeat/error-control nodes |
| `0x7E5 / 0x7E4` | CANopen LSS manager/server |
| `0x601/0x581` | observed SDO JSON pair |
| `0x621/0x5A1` | observed SDO JSON pair |
| `0x641/0x5C1` | segmented SDO JSON / application Ack path |
| `0x649/0x5C9` | block-SDO structured status/profile path |
| `0x280`-`0x320` | indoor/blower/refrigerant family |
| `0x380`-`0x38F` | outdoor/inverter/refrigerant family |
| `0x490`-`0x495` | zone sensor/status family |

The JSON payload is carried through CANopen SDO download transactions targeting manufacturer object **`0x300A:00`**.

See [docs/CANOPEN-LINK-TRANSPORT.md](docs/CANOPEN-LINK-TRANSPORT.md) for the byte-level transport decode.

## Key target-observed telemetry

A small subset of the current map:

| Signal | Current source |
|---|---|
| room temperature | `0x490.float[0]` |
| indoor humidity | `0x490.byte4`, values 0-100 only |
| outdoor ambient | `0x380.float[1]` |
| return/supply air | `0x308.float[0..1]` |
| total static pressure | `0x310.float[0]` |
| blower speed request | `0x200.u16@2` strong candidate |
| blower motor speed feedback | `0x318.u16@4` strong candidate |
| airflow target/command | `0x281.u16@0` strong candidate |
| blower-adjacent raw field | `0x318.u16@6` candidate |
| blower power | `0x320.float[0]` |
| compressor speed request | `0x280.float[0]` |
| actual compressor speed | `0x384.float[0]` candidate |
| compressor speed ceiling | `0x385.float[1]` candidate |
| line voltage | `0x38F.float[0]` candidate |
| input power | `0x38C.float[1]` |
| outdoor fan speed | `0x384.u16@6` |
| drive DC bus | `0x384.u16@4` |

For the maintained map, confidence levels, and unresolved fields see [docs/TELEMETRY.md](docs/TELEMETRY.md).

## Documentation

Start at [docs/README.md](docs/README.md). For the HA entity layout, see [docs/HOME-ASSISTANT.md](docs/HOME-ASSISTANT.md).

The docs are intentionally split between:

- **maintained reference documents** for current behavior and mappings;
- **dated evidence** under [docs/evidence/](docs/evidence/) preserving the reverse-engineering trail, including mappings later disproved.

Do not treat an older evidence note as authoritative when it conflicts with `TELEMETRY.md` or current source/tests.

## Development principles

- stock Trane controls stay installed and usable;
- bridge removal/failure must not interrupt HVAC operation;
- passive decode first;
- no guessed application writes;
- preserve raw evidence when semantics are uncertain;
- use Candidate/Raw labels until independently correlated;
- keep historical comments/evidence rather than deleting inconvenient observations;
- no build-time source patching or generated-source mutation layers.

## Quick start

For a new bridge:

1. read [docs/WIRING.md](docs/WIRING.md);
2. flash `waveshare-trane-listenonly.yaml`;
3. establish a baseline CAN census;
4. follow [docs/COMMISSIONING.md](docs/COMMISSIONING.md);
5. move to `waveshare-trane-homeassistant.yaml` after the bus/hardware baseline is clean.

For current architecture and outstanding engineering work, see [docs/CONTEXT.md](docs/CONTEXT.md).

## Long-term capture

A tiny foreground collector can subscribe directly to the ESPHome native API and
retain Trane records without involving Home Assistant Recorder:

```bash
python -m pip install aioesphomeapi
python tools/trane_log_collector.py trane-link-bridge.local -o /data/trane/trane.jsonl
```

The output is split automatically by the host's local clock:

```text
/data/trane/trane-2026-10-05-00.jsonl
/data/trane/trane-2026-10-05-01.jsonl
...
/data/trane/trane-2026-10-05-23.jsonl
```

At the first write after midnight, all completed hourly chunks from the prior day
are packed into one archive:

```text
/data/trane/trane-2026-10-05.tar.gz
```

The hourly source files are deleted **only after** the temporary tar.gz can be
reopened successfully and is atomically renamed into place. On startup the
collector also finds complete older-day chunks left by an interrupted run and
finishes archiving them. The current day's active/hourly files are never packed
early.

Each JSONL row records `TRANE_CAN_LIVE`, `TRANE_JSON`, or another `TRANE_*`
line with a host timestamp while preserving the original log text. The ESPHome
API client automatically reconnects if the ESP32 drops off the network.

Stop the foreground capture with **Ctrl-C**. On POSIX terminals **Ctrl-Z** is
intentionally treated as a clean stop as well, rather than suspending the
recorder.

If ESPHome API encryption is enabled, provide the Noise PSK without placing it
on the command line:

```bash
export ESPHOME_NOISE_PSK='your-api-encryption-key'
python tools/trane_log_collector.py 192.0.2.10 -o /data/trane/trane.jsonl
```

If `-o` is omitted, the base name is `trane-capture.jsonl`, producing hourly
`trane-capture-YYYY-MM-DD-HH.jsonl` files and daily
`trane-capture-YYYY-MM-DD.tar.gz` archives. Use `--all` only when ordinary
non-Trane ESPHome log lines are also wanted.
