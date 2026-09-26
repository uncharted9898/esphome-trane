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

**Application/control TX remains fail-closed.**

Passive captures proved the historical writer was not a valid CANopen SDO transaction. The maintained component refuses application writes until a stock UX360 setpoint/mode command is captured and a qualified nonblocking SDO writer is implemented.

The intended local-control API is preserved, but passive monitoring is the production-safe path today.

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
| `waveshare-trane-control.yaml` | Guarded control-development profile; TX still fail-closed |
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
| blower airflow request | `0x200.u16@2` candidate |
| blower airflow feedback | `0x318.u16@4` candidate |
| actual airflow | `0x281.u16@0` |
| blower speed | `0x318.u16@6` candidate |
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

A tiny foreground collector subscribes directly to the ESPHome native API and
writes long-term Trane evidence without involving Home Assistant Recorder:

```bash
python -m pip install aioesphomeapi
python tools/trane_log_collector.py trane-link-bridge.local -o /data/trane/trane.jsonl
```

The `-o` value is an **output base**, not one indefinitely growing file. With
the example above the collector creates one JSONL chunk per host-local hour:

```text
/data/trane/trane-2026-09-23-00.jsonl
/data/trane/trane-2026-09-23-01.jsonl
...
/data/trane/trane-2026-09-23-23.jsonl
```

After midnight, once a day is complete, those hourly chunks are consolidated
into:

```text
/data/trane/trane-2026-09-23.tar.gz
```

The archive contains the original hourly JSONL files. The collector verifies the
temporary tar/gzip can be reopened and contains every source chunk, atomically
renames it into place, and only then removes the hourly files. On restart it
also sweeps and archives leftover chunks from completed days.

It records `TRANE_CAN_LIVE`, `TRANE_JSON`, and other `TRANE_*` lines with a
host timestamp while preserving the original log text. The API client
automatically reconnects if the ESP32 drops off the network.

Stop the capture with **Ctrl-C**. On POSIX terminals **Ctrl-Z** is intentionally
treated as a clean stop as well, rather than suspending the recorder.

If ESPHome API encryption is enabled, provide the Noise PSK without placing it
on the command line:

```bash
export ESPHOME_NOISE_PSK='your-api-encryption-key'
python tools/trane_log_collector.py 192.0.2.10 -o /data/trane/trane.jsonl
```

If `-o` is omitted, the base defaults to `trane-capture.jsonl`, producing
`trane-capture-YYYY-MM-DD-HH.jsonl` chunks and
`trane-capture-YYYY-MM-DD.tar.gz` daily archives. Use `--all` only when
ordinary non-Trane ESPHome log lines are also wanted.
