# CANopen structure observed on the target Trane Link bus

Status: target capture evidence, 2026-09-17.

This document separates **standard CANopen transport/network-management behavior** from the proprietary Trane application objects carried on top of it. A CAN identifier being recognizable as CANopen does **not** imply that the device role or Trane payload semantics are known.

Reference system:

- 5TAMXC03AV31DB indoor unit
- 5TWV0X24A1000B outdoor unit
- UX360 + SC360 (`TLINK360A2VVUG`)
- A2L/R-454B mitigation hardware installed
- 50-kbit/s 11-bit CAN capture from the Link bus

## Standards references

CAN in Automation (CiA) documents the relevant standard services:

- Heartbeat/error control: CAN-ID `0x700 + node-ID`, one-byte NMT state payload. See <https://www.can-cia.org/can-knowledge/error-control-protocols>.
- Layer Setting Services (LSS): manager commands on `0x7E5`, server responses on `0x7E4`. See <https://www.can-cia.org/can-knowledge/cia-305-layer-setting-services-lss>.
- SDO communication uses paired client/server COB-IDs from the CANopen communication profile. See <https://can-cia.org/can-knowledge/sdo-protocol>.

These references establish the CANopen framing. They do not identify which Trane assembly owns a node-ID.

## NMT and heartbeat evidence

The cold-boot target capture contains CAN-ID `0x000` frames:

- `81 03`
- later `01 03`

Those bytes have the standard CANopen NMT shape: command byte followed by node-ID. They are consistent with reset-node and start-node operations directed at node 3.

The same boot sequence contains heartbeat/error-control traffic at `0x701` through `0x705`, proving five node-ID slots are active in this installation.

Most importantly, node 3 transitions through:

- `0x703 00` — boot-up
- `0x703 7F` — pre-operational
- `0x703 05` — operational

That sequence is standard CANopen behavior and occurs around the observed NMT traffic.

### Heartbeat state decode

For target diagnostics we decode only the standard state byte:

| Byte | State |
| ---: | --- |
| `0x00` | boot-up |
| `0x04` | stopped |
| `0x05` | operational |
| `0x7F` | pre-operational |
| other | raw/unknown |

We intentionally do **not** map node 1..5 to UX360, SC360, 5TAMX, 5TWV0X, or the mitigation board without a topology/disconnect capture.

## LSS evidence

The target bus uses the standard LSS identifiers:

- `0x7E5` — manager requests
- `0x7E4` — server responses

A complete target capture contains a positive CiA-305 Fastscan for all four
32-bit Identity Object words:

- vendor ID: `0x00000001`
- product code: `0x00000004`
- revision number: `0x00000000`
- serial number: `0xC345985F`

After the final positive Fastscan probe, the manager sends a successful node-ID
configuration for **node 3**, switches the LSS state, and the node then follows
the normal CANopen startup sequence:

```text
0x7E5 11 03 ...   configure node ID 3
0x7E4 11 00 ...   success
0x7E5 04 00 ...   switch state
0x703 00          boot-up
0x703 7F          pre-operational
0x000 01 03       NMT Start Remote Node 3
0x703 05          operational
```

The offline capture analyzer reconstructs this as one LSS identity/assignment
session.

This proves standards-backed discovery/configuration behavior, but it still does
**not** prove which physical Trane assembly owns CANopen node 3. Keep physical
node-role mapping separate until a controlled topology/disconnect capture
identifies it.

## CANopen SDO JSON transport

The target captures now identify the JSON transport as **standard CANopen SDO
download protocol**, not ISO-TP and not a proprietary Trane segmentation layer.

The application-specific portion is the NUL-terminated JSON document written to
manufacturer object **0x300A:00**.

Observed COB-ID pairs use the CANopen client/server SDO pairing pattern:

| Client/request side | Server/response side | Target observation |
| ---: | ---: | --- |
| `0x601` | `0x581` | block-download `Debug` JSON |
| `0x621` | `0x5A1` | block-download `Debug.ODBLE` JSON |
| `0x641` | `0x5C1` | segmented JSON including `{"Ack":"200"}` |
| `0x649` | `0x5C9` | block-download status/profile JSON |

The `0x600+n` / `0x580+n` spacing is the CANopen predefined SDO COB-ID
pattern. Do **not** infer physical device identity from the apparent `n`
alone: CANopen permits additional SDO parameter objects with configured COB-IDs,
and this installation's heartbeat node IDs are independently observed only at
1 through 5.

### Block download: 0x649 / 0x5C9 example

A target ZoneStatus update is a textbook block SDO download:

```text
0x649 C2 0A 30 00 2E 00 00 00
0x5C9 A0 0A 30 00 07 00 00 00
0x649 01 <7 data bytes>
...
0x649 87 <last data segment>
0x5C9 A2 07 00 00 00 00 00 00
0x649 CD 00 00 00 00 00 00 00
0x5C9 A1 00 00 00 00 00 00 00
```

Decoded:

- `C2` — SDO block-download initiate request, size indicated;
- `0A 30` — little-endian object index `0x300A`;
- subindex `00`;
- `2E 00 00 00` — 46-byte transfer size;
- `A0` — server block-download initiate response;
- byte 4 `07` — negotiated block size of seven segments;
- segment command bytes `01..06,87` — sequence 1..7, bit 7 set on the last;
- `A2 07` — server acknowledges sequence 7;
- `CD` — block-download end request with three unused bytes in the final
  seven-byte segment;
- `A1` — server block-download end response.

The 46 transferred bytes are 45 JSON bytes plus the terminating NUL:

```json
{"ZoneStatus":{"Update":{"1":{"H":"76.00"}}}}
```

The same arithmetic validates the `0x601` Debug captures. A 37-byte transfer
uses six seven-byte segments (42 bytes capacity), leaving five unused bytes, so
the observed end command is `D5 = C1 | (5 << 2)`. A 34-byte transfer uses five
segments and leaves one unused byte, producing the observed `C5`.

The `0x621/0x5A1` pair independently repeats the same SDO transaction shape
and the same object `0x300A:00`, carrying:

```json
{"Debug":{"ODBLE":"NOTADVERTISING"}}
{"Debug":{"ODBLE":"ADVERTISING"}}
```

while `0x601/0x581` carries the corresponding `Debug.IDBLE` states. Because
those are partial updates under the same JSON root, the runtime retains IDBLE
and ODBLE independently instead of allowing the generic `Debug` snapshot to
erase the previously observed sibling key.

### Segmented download: 0x641 / 0x5C1 example

The short application acknowledgment uses standard segmented SDO download:

```text
0x641 21 0A 30 00 0E 00 00 00
0x5C1 60 0A 30 00 00 00 00 00
0x641 00 7B 22 41 63 6B 22 3A
0x5C1 20 00 00 00 00 00 00 00
0x641 11 22 32 30 30 22 7D 00
0x5C1 30 00 00 00 00 00 00 00
```

Decoded:

- `21` — segmented-download initiate request with a 14-byte indicated size;
- `60` — initiate response for object `0x300A:00`;
- `00` — first seven-byte segment, toggle 0, not final;
- `20` — segment response, toggle 0;
- `11` — second segment, toggle 1, final;
- `30` — final segment response, toggle 1.

The transferred bytes are:

```json
{"Ack":"200"}
```

Again, the indicated SDO size includes the trailing NUL while the application
JSON parser strips it.

### What is standard vs Trane-specific

Standard CANopen:

- SDO initiate/segment/block/end command bytes;
- object index/subindex placement;
- transfer-size field;
- block-size negotiation and sequence acknowledgements;
- segmented-transfer toggle bits;
- SDO abort framing;
- COB-ID client/server pairing conventions.

Trane-specific:

- use of manufacturer object `0x300A:00` as a JSON mailbox;
- the JSON roots and compact field names (`ZoneStatus`, `IndoorStatus`,
  `SpOverride`, etc.);
- application-level request/response meaning carried inside that JSON.

This distinction is important: the transport no longer needs bespoke framing.
Active control must use a real non-blocking CANopen SDO client targeting
`0x300A:00`, with captured application JSON layered above it.

### Active-write safety status

The repository's historical transmitter pre-dated this SDO decode and emitted a
guessed `C2`/sequence stream without object index `0x300A` or the mandatory
SDO server handshakes. That sequence remains removed.

The October 3 and October 5 captures qualify the stock zone-1
`SpOverride.Put` setpoint path: five independent UX360 writes use request
COB-ID `0x641`, response COB-ID `0x5C1`, object `0x300A:00`, CANopen
block download, and an application `{"Ack":"200"}`.

The October 6 Technician session independently qualifies a second narrow
application family on the same transport:

```json
{"IndoorSettings":{"Put":{"1":{"A":"1"}}}}
{"IndoorSettings":{"Put":{"1":{"C":"100"}}}}
{"IndoorSettings":{"Put":{"1":{"C":"50"}}}}
{"IndoorSettings":{"Put":{"1":{"A":"0"}}}}
```

Each write completes the response-driven SDO handshake, produces a matching
`IndoorSettings.Update`, and is followed by application `{"Ack":"200"}`.

The maintained `trane_bus` implements both qualified families with one
nonblocking, response-driven SDO client. It waits for `A0`, honors the
negotiated block size, waits for matching `A2`, sends the encoded block-end
request, waits for `A1`, and only then starts the application-ACK timer.

`tx_enabled` remains false by default. Setpoints additionally require
`qualified_setpoint_tx_enabled: true`; Technician fan control independently
requires `qualified_indoor_fan_tx_enabled: true`. Both qualification flags
default false and both paths require recent SC360 activity plus 100 ms of quiet
on the stock `0x641/0x5C1` SDO pair so local traffic cannot interleave with
an in-progress stock transaction.

The fan writer accepts only the captured `A=0/1` enable states and
`C=50/100` request values. Mode, profile and arbitrary JSON writes remain
fail-closed because no equivalent request capture has qualified them.

All five stock writes used this exact application field order and policy:

```json
{"SpOverride":{"Put":{"1":{"Csp":"77","Hsp":"62","HoldType":"1","Source":"1"}}}}
```

Across the captures, `Csp` is observed at 77, 78 and 79 F; `Hsp` remains
62 F and every write retains `HoldType:"1"`, `Source:"1"`, zone 1 and the
same JSON field order. The qualified writer therefore rejects zones other than
1 and hold/source values other than 1 rather than extrapolating uncaptured
semantics.


## Emergency-like identifiers

Cold boot contains `0x081` and `0x083`, which lie in the standard CANopen EMCY identifier range for nodes 1 and 3. Their raw payloads are retained. Exact Trane emergency/error-code semantics are not promoted until the payload is correlated with an actual reported condition.

## Cold-boot configuration/PDO-looking block

The cold capture contains a one-shot cluster around node-3 initialization:

- `0x202`, `0x204`, `0x205`, `0x206`, `0x207`
- `0x209` through `0x210`
- plus `0x496`, `0x540`, `0x560`

These are target-observed Link traffic and are now classified so they do not pollute the novel-ID counter. Their field semantics remain raw.

Representative payloads include:

```text
0x202 FFFFFFFFFF63FF63
0x204 FF63636363
0x205 6363
0x206 000000000000
0x207 0000000000051E00
0x20E 1828000C18002038
0x20F 001E1E000F0F00
0x210 0000B2998F0000
0x496 00
0x540 0000
0x560 1F0000
```

Do not assign HVAC semantics merely from the CANopen identifier range.

## 0x53D / 0x53E network-status hypothesis

These frames had initially been tempting to call A2L traffic because the target has a mitigation board. The CANopen startup evidence argues for caution.

Steady state:

```text
0x53D 01 00 00 00 00
0x53E 00 00 00 00 01 05
```

During cold boot, the final byte of `0x53E` temporarily changes from `05` to `04`, then returns to `05` after the node-3 boot/pre-operational/operational sequence completes.

Because five heartbeat node IDs (`0x701`..`0x705`) are present, `0x53E.byte5` is a strong **active/available Link node-count candidate**. It is exposed as a candidate only; ownership and exact contract remain unresolved.

`0x53D` remains raw network/status evidence.

## Six-slot 0x4C0..0x4C5 family

The system emits six five-byte records at `0x4C0` through `0x4C5`. All are zero in the observed single-zone cooling captures. The six-slot structure is notable, but there is no causal evidence yet for zone demand, airflow, fault, or another specific meaning. Keep the slots raw/disabled by default.

## Discovery policy

`is_known_trane_id()` means **observed/classified as part of this target Link network**, not “fully semantically decoded.”

This distinction matters because the old HA callback counted thousands of normal telemetry/heartbeat/control frames as `Unclassified CAN Frames`. Target-observed CANopen management, transport, status, and telemetry IDs should be recognized while their unresolved bytes stay raw.

A genuinely new ID should therefore remain a useful discovery signal.

## Highest-value next captures

1. Listener running before a complete cold boot, preserving NMT/LSS/heartbeat/SDO-like startup order.
2. Deliberate, safe topology observation (for example service power sequencing documented by the OEM) to map node IDs to physical assemblies; do not randomly unplug communicating equipment under load.
3. Synchronized Technician Monitor + CAN while blower airflow changes to resolve the remaining `0x281`/`0x318` command-vs-feedback words.
4. A natural/documented A2L self-test or state transition to identify mitigation frames without inducing a refrigerant leak.
5. Heat/defrost captures to separate outdoor temperature/valve/current channels that are degenerate in steady cooling.


## Optional trailing NUL in 0x300A payloads

The indicated CANopen transfer size for Trane object `0x300A:00` is not
uniformly a C-string size.

Most captured JSON transfers include a trailing NUL in the indicated size.
However, the 2026-09-30 capture contains a valid block download for:

```json
{"DebugUI":{"HiHeapRemaining":"33054720"}}
```

whose initiate request reports **42 bytes**, exactly the UTF-8 JSON length,
with no trailing NUL. The final payload segment supplies the second closing
brace as byte 42.

The receiver must therefore accept both forms:

1. `wire_size == JSON_bytes + 1` with an observed trailing NUL; and
2. `wire_size == JSON_bytes` with no trailing NUL.

Subtracting one from every indicated size is incorrect and caused the bridge to
emit this message one segment early as malformed JSON. Firmware and the offline
capture analyzer now preserve the indicated wire size and decide completion
only after the final segment.


### Repeated exact-length observations

The exact-length/no-trailing-NUL form has now been observed independently across
five capture days:

- 2026-09-30: `HiHeapRemaining = 33054720`
- 2026-10-01: `HiHeapRemaining = 32538624`
- 2026-10-03: `HiHeapRemaining = 32022528`
- 2026-10-04: `HiHeapRemaining = 31506432`
- 2026-10-06: `HiHeapRemaining = 30900224`

All five advertise 42 bytes, exactly the UTF-8 JSON length. This confirms the
optional-NUL rule is a normal Trane wire form rather than a one-off malformed
sender.

The 2026-10-03 archive was still captured with the pre-fix receiver. It emits
one malformed `TRANE_JSON` line after 41 bytes, while the underlying CAN
transaction is valid and the next block segment carries the final closing
brace. The maintained receiver/analyzer fix accepts all five captures.


### Long structured JSON logger capacity

The October 6 Technician profile sweep proves that CANopen reassembly and
ESPHome log formatting have different size ceilings.

Target-observed complete JSON bodies include:

- `ZoneStatus`: 596 bytes, 597 indicated bytes with trailing NUL;
- `EquipSummary`: 1,377 bytes, 1,378 indicated bytes with trailing NUL;
- `WifiList`: 1,680 bytes, 1,681 indicated bytes with trailing NUL.

`trane_bus` accepts RX JSON payloads up to 4,096 bytes and reconstructs all of
those bodies correctly. The HA profile previously used ESPHome logger's
512-byte default TX buffer, so the emitted `TRANE_JSON` line clipped large
payloads at about 468 JSON characters after logger metadata.

The production profile now sets:

```yaml
logger:
  tx_buffer_size: 4608
```

which covers the component's 4,096-byte RX envelope plus logger prefix/header
overhead. This is a logging-layer fix only; it does not alter CAN transport or
JSON reassembly.
