#!/usr/bin/env python3
"""Analyze ESPHome Trane Link live-capture logs without transmitting anything.

The analyzer intentionally separates wire decoding from HVAC semantic labels. It
parses TRANE_CAN_LIVE records, reports cadence/ranges for standard 11-bit IDs,
reassembles the proprietary segmented JSON observed on 0x601/0x641/0x649, and
decodes standards-backed CANopen management traffic without assigning physical
Trane roles to node IDs.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import re
import statistics
import struct
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

LIVE_RE = re.compile(
    r"TRANE_CAN_LIVE,(?P<kind>[SE]),(?P<tick>\d+),(?P<canid>[0-9A-Fa-f]+),"
    r"(?P<dlc>\d+),(?P<data>[0-9A-Fa-f]*)"
)

SEGMENTED_JSON_IDS = (0x601, 0x621, 0x641, 0x649)

# Target-observed CANopen SDO COB-ID pairs. The three JSON channels use the
# standard client->server / server->client pairing pattern (0x600+n / 0x580+n)
# and write their NUL-terminated JSON payload to manufacturer object 0x300A:00.
# 0x621/0x5A1 is retained because it is also observed during boot, but its
# application object semantics remain raw.
SDO_REQUEST_TO_RESPONSE = {
    0x601: 0x581,
    0x621: 0x5A1,
    0x641: 0x5C1,
    0x649: 0x5C9,
}
SDO_RESPONSE_TO_REQUEST = {response: request for request, response in SDO_REQUEST_TO_RESPONSE.items()}
TRANE_JSON_OBJECT_INDEX = 0x300A
TRANE_JSON_OBJECT_SUBINDEX = 0

HEARTBEAT_STATES = {
    0x00: "boot-up",
    0x04: "stopped",
    0x05: "operational",
    0x7F: "pre-operational",
}


@dataclasses.dataclass(frozen=True)
class Frame:
    line_no: int
    kind: str
    tick_ms: int
    can_id: int
    dlc: int
    data: bytes


@dataclasses.dataclass
class SegmentedState:
    expected_len: int = 0
    expected_seq: int = 0
    buffer: bytearray = dataclasses.field(default_factory=bytearray)

    def reset(self) -> None:
        self.expected_len = 0
        self.expected_seq = 0
        self.buffer.clear()


def parse_frames(lines: Iterable[str]) -> list[Frame]:
    frames: list[Frame] = []
    for line_no, line in enumerate(lines, 1):
        match = LIVE_RE.search(line)
        if not match:
            continue
        data_hex = match.group("data")
        data = bytes.fromhex(data_hex) if data_hex else b""
        dlc = int(match.group("dlc"))
        # Preserve the reported DLC as evidence, but reject malformed records
        # where the textual payload is shorter than the reported length.
        if len(data) < dlc:
            continue
        frames.append(
            Frame(
                line_no=line_no,
                kind=match.group("kind"),
                tick_ms=int(match.group("tick")),
                can_id=int(match.group("canid"), 16),
                dlc=dlc,
                data=data[:dlc],
            )
        )
    return frames


def f32_le(data: bytes, offset: int = 0) -> float | None:
    if offset < 0 or len(data) < offset + 4:
        return None
    value = struct.unpack_from("<f", data, offset)[0]
    return value if math.isfinite(value) else None


def u16_le(data: bytes, offset: int = 0) -> int | None:
    if offset < 0 or len(data) < offset + 2:
        return None
    return struct.unpack_from("<H", data, offset)[0]


def u32_le(data: bytes, offset: int = 0) -> int | None:
    if offset < 0 or len(data) < offset + 4:
        return None
    return struct.unpack_from("<I", data, offset)[0]


def _target_payload_length(data: bytes) -> int:
    if len(data) < 8:
        return 0
    wire_len = u32_le(data, 4) or 0
    if wire_len <= 0:
        return 0
    # Target captures include the trailing NUL in this length.
    return wire_len - 1


def _feed_segment(state: SegmentedState, data: bytes) -> str | None:
    if not data:
        return None
    marker = data[0]

    if state.expected_len:
        if state.expected_seq & 0x80:
            # Short 0x641 response framing: high nibble 0x0 continuation,
            # 0x1 final; low nibble is the sequence.
            expected = state.expected_seq & 0x0F
            frame_type = marker & 0xF0
            sequence = marker & 0x0F
            if frame_type not in (0x00, 0x10) or sequence != expected:
                state.reset()
                return None
            saw_nul = False
            for byte in data[1:]:
                if len(state.buffer) >= state.expected_len:
                    break
                if byte == 0:
                    saw_nul = True
                    break
                state.buffer.append(byte)
            final = (
                frame_type == 0x10
                or saw_nul
                or len(state.buffer) == state.expected_len
            )
            if final:
                if len(state.buffer) == state.expected_len:
                    result = state.buffer.decode("utf-8", errors="strict")
                    state.reset()
                    return result
                state.reset()
                return None
            state.expected_seq = 0x80 | ((expected + 1) & 0x0F)
            return None

        # Long framing: bit 7 marks final; lower seven bits are sequence.
        if marker & 0x80:
            sequence = marker & 0x7F
            if sequence != state.expected_seq:
                state.reset()
                return None
            for byte in data[1:]:
                if len(state.buffer) >= state.expected_len:
                    break
                if byte == 0:
                    break
                state.buffer.append(byte)
            if len(state.buffer) == state.expected_len:
                result = state.buffer.decode("utf-8", errors="strict")
                state.reset()
                return result
            state.reset()
            return None

        if marker != state.expected_seq:
            state.reset()
            return None
        for byte in data[1:]:
            if len(state.buffer) >= state.expected_len:
                break
            if byte == 0:
                break
            state.buffer.append(byte)
        state.expected_seq = 1 if state.expected_seq == 0x7F else state.expected_seq + 1
        return None

    if marker == 0xC2:
        payload_len = _target_payload_length(data)
        if payload_len <= 0 and len(data) >= 3:
            # Compatibility with the repo's oldest experimental captures.
            payload_len = data[1] | (data[2] << 8)
        if payload_len <= 0 or payload_len > 4096:
            state.reset()
            return None
        state.expected_len = payload_len
        state.expected_seq = 1
        state.buffer.clear()
        return None

    if marker == 0x21:
        payload_len = _target_payload_length(data)
        if payload_len <= 0 or payload_len > 4096:
            state.reset()
            return None
        state.expected_len = payload_len
        state.expected_seq = 0x80
        state.buffer.clear()
        return None

    return None


def reassemble_json(frames: Sequence[Frame]) -> list[dict[str, object]]:
    states = {can_id: SegmentedState() for can_id in SEGMENTED_JSON_IDS}
    messages: list[dict[str, object]] = []
    for frame in frames:
        state = states.get(frame.can_id)
        if state is None:
            continue
        try:
            complete = _feed_segment(state, frame.data)
        except UnicodeDecodeError:
            state.reset()
            continue
        if complete is None:
            continue
        try:
            parsed = json.loads(complete)
        except json.JSONDecodeError:
            continue
        messages.append(
            {
                "line": frame.line_no,
                "tick_ms": frame.tick_ms,
                "can_id": f"0x{frame.can_id:03X}",
                "json": parsed,
            }
        )
    return messages


def _finite_range(values: Iterable[float | None]) -> dict[str, float] | None:
    finite = [value for value in values if value is not None and math.isfinite(value)]
    if not finite:
        return None
    return {"min": min(finite), "max": max(finite), "last": finite[-1]}


def typed_ranges(frames: Sequence[Frame]) -> dict[str, object]:
    grouped: dict[int, list[Frame]] = defaultdict(list)
    for frame in frames:
        if frame.kind == "S":
            grouped[frame.can_id].append(frame)

    output: dict[str, object] = {}

    def floats(can_id: int) -> dict[str, object]:
        rows = grouped.get(can_id, [])
        result: dict[str, object] = {"count": len(rows)}
        for offset, label in ((0, "f32_0"), (4, "f32_1")):
            rng = _finite_range(f32_le(row.data, offset) for row in rows)
            if rng is not None:
                result[label] = rng
        return result

    for can_id in (
        0x280,
        0x283,
        0x300,
        0x308,
        0x310,
        0x318,
        0x320,
        0x380,
        0x381,
        0x382,
        0x383,
        0x385,
        0x386,
        0x387,
        0x388,
        0x389,
        0x38C,
        0x38F,
        0x410,
        0x430,
        0x450,
        0x460,
    ):
        if can_id in grouped:
            output[f"0x{can_id:03X}"] = floats(can_id)

    rows = grouped.get(0x281, [])
    if rows:
        result: dict[str, object] = {"count": len(rows)}
        for word in range(4):
            values = [u16_le(row.data, word * 2) for row in rows]
            finite = [value for value in values if value is not None]
            if finite:
                result[f"u16_{word}"] = {
                    "min": min(finite),
                    "max": max(finite),
                    "last": finite[-1],
                }
        byte6 = [row.data[6] for row in rows if len(row.data) >= 7]
        byte7 = [row.data[7] for row in rows if len(row.data) >= 8]
        if byte6:
            result["byte_6"] = {
                "min": min(byte6),
                "max": max(byte6),
                "last": byte6[-1],
            }
        if byte7:
            result["byte_7"] = {
                "min": min(byte7),
                "max": max(byte7),
                "last": byte7[-1],
            }
        output["0x281"] = result

    rows = grouped.get(0x318, [])
    if rows:
        result = output.setdefault("0x318", {"count": len(rows)})
        for word, offset in ((2, 4), (3, 6)):
            values = [u16_le(row.data, offset) for row in rows]
            finite = [value for value in values if value is not None]
            if finite:
                result[f"u16_{word}"] = {
                    "min": min(finite),
                    "max": max(finite),
                    "last": finite[-1],
                }

    rows = grouped.get(0x384, [])
    if rows:
        u16_2 = [u16_le(row.data, 4) for row in rows]
        u16_3 = [u16_le(row.data, 6) for row in rows]
        finite_2 = [value for value in u16_2 if value is not None]
        finite_3 = [value for value in u16_3 if value is not None]
        output["0x384"] = {
            "count": len(rows),
            "f32_0": _finite_range(f32_le(row.data, 0) for row in rows),
            "u16_2": {"min": min(finite_2), "max": max(finite_2), "last": finite_2[-1]},
            "u16_3": {"min": min(finite_3), "max": max(finite_3), "last": finite_3[-1]},
        }

    rows = grouped.get(0x490, [])
    if rows:
        byte4 = [row.data[4] for row in rows if len(row.data) >= 5]
        output["0x490"] = {
            "count": len(rows),
            "temperature_like": _finite_range(f32_le(row.data, 0) for row in rows),
            "byte4": {"min": min(byte4), "max": max(byte4), "last": byte4[-1]},
        }

    rows = grouped.get(0x4B1, [])
    if rows:
        values = [u32_le(row.data, 0) for row in rows]
        finite = [value for value in values if value is not None]
        output["0x4B1"] = {
            "count": len(rows),
            "u32_0": {"min": min(finite), "max": max(finite), "last": finite[-1]},
        }

    return output


def decode_canopen_sdo_transport(frames: Sequence[Frame]) -> list[dict[str, object]]:
    """Decode CANopen SDO transfers observed on the Trane Link bus.

    The JSON-bearing channels use standard CANopen SDO block or segmented
    download protocol. Trane's application-specific portion is the payload
    written to manufacturer object 0x300A:00, not the SDO transport framing.

    Physical device roles are intentionally not inferred from COB-IDs alone:
    additional SDO client/server parameter objects may use custom COB-IDs.
    """
    events: list[dict[str, object]] = []
    mode_by_request: dict[int, str] = {}

    def base_event(frame: Frame, request_id: int, direction: str) -> dict[str, object]:
        return {
            "line": frame.line_no,
            "tick_ms": frame.tick_ms,
            "can_id": f"0x{frame.can_id:03X}",
            "request_can_id": f"0x{request_id:03X}",
            "response_can_id": f"0x{SDO_REQUEST_TO_RESPONSE[request_id]:03X}",
            "direction": direction,
            "command": frame.data[0],
            "raw": frame.data.hex().upper(),
        }

    for frame in frames:
        if frame.kind != "S" or not frame.data:
            continue

        if frame.can_id in SDO_REQUEST_TO_RESPONSE:
            request_id = frame.can_id
            opcode = frame.data[0]
            event = base_event(frame, request_id, "client_to_server")

            if len(frame.data) == 8 and opcode == 0xC2:
                index = u16_le(frame.data, 1) or 0
                event.update(
                    {
                        "phase": "block_download_initiate_request",
                        "index": index,
                        "subindex": frame.data[3],
                        "size": u32_le(frame.data, 4) or 0,
                        "crc_requested": bool(opcode & 0x04),
                        "size_indicated": bool(opcode & 0x02),
                        "trane_json_object": (
                            index == TRANE_JSON_OBJECT_INDEX
                            and frame.data[3] == TRANE_JSON_OBJECT_SUBINDEX
                        ),
                    }
                )
                mode_by_request[request_id] = "block"
                events.append(event)
                continue

            if len(frame.data) == 8 and opcode == 0x21:
                index = u16_le(frame.data, 1) or 0
                event.update(
                    {
                        "phase": "segmented_download_initiate_request",
                        "index": index,
                        "subindex": frame.data[3],
                        "size": u32_le(frame.data, 4) or 0,
                        "size_indicated": True,
                        "trane_json_object": (
                            index == TRANE_JSON_OBJECT_INDEX
                            and frame.data[3] == TRANE_JSON_OBJECT_SUBINDEX
                        ),
                    }
                )
                mode_by_request[request_id] = "segmented"
                events.append(event)
                continue

            mode = mode_by_request.get(request_id)
            if mode == "block" and (opcode & 0xE3) == 0xC1:
                event.update(
                    {
                        "phase": "block_download_end_request",
                        "unused_bytes": (opcode >> 2) & 0x07,
                        "crc": u16_le(frame.data, 1) or 0,
                    }
                )
                events.append(event)
                continue

            if mode == "block":
                sequence = opcode & 0x7F
                if 1 <= sequence <= 0x7F:
                    event.update(
                        {
                            "phase": "block_download_segment",
                            "sequence": sequence,
                            "last": bool(opcode & 0x80),
                        }
                    )
                    events.append(event)
                    continue

            if mode == "segmented" and (opcode & 0xE0) == 0x00:
                event.update(
                    {
                        "phase": "segmented_download_segment",
                        "toggle": bool(opcode & 0x10),
                        "unused_bytes": (opcode >> 1) & 0x07,
                        "last": bool(opcode & 0x01),
                    }
                )
                events.append(event)
                continue

            # Retain observed request-side SDO-looking traffic even where its
            # object or transfer state has not yet been qualified.
            if request_id == 0x621:
                event["phase"] = "sdo_request_raw"
                events.append(event)
            continue

        if frame.can_id not in SDO_RESPONSE_TO_REQUEST:
            continue

        request_id = SDO_RESPONSE_TO_REQUEST[frame.can_id]
        opcode = frame.data[0]
        event = base_event(frame, request_id, "server_to_client")

        if len(frame.data) == 8 and opcode == 0xA0:
            index = u16_le(frame.data, 1) or 0
            event.update(
                {
                    "phase": "block_download_initiate_response",
                    "index": index,
                    "subindex": frame.data[3],
                    "block_size": frame.data[4],
                    "crc_supported": bool(opcode & 0x04),
                    "trane_json_object": (
                        index == TRANE_JSON_OBJECT_INDEX
                        and frame.data[3] == TRANE_JSON_OBJECT_SUBINDEX
                    ),
                }
            )
        elif len(frame.data) >= 3 and opcode == 0xA2:
            event.update(
                {
                    "phase": "block_download_subblock_response",
                    "ack_sequence": frame.data[1],
                    "next_block_size": frame.data[2],
                }
            )
        elif opcode == 0xA1:
            event["phase"] = "block_download_end_response"
            mode_by_request.pop(request_id, None)
        elif len(frame.data) == 8 and opcode == 0x60:
            index = u16_le(frame.data, 1) or 0
            event.update(
                {
                    "phase": "segmented_download_initiate_response",
                    "index": index,
                    "subindex": frame.data[3],
                    "trane_json_object": (
                        index == TRANE_JSON_OBJECT_INDEX
                        and frame.data[3] == TRANE_JSON_OBJECT_SUBINDEX
                    ),
                }
            )
        elif opcode in (0x20, 0x30):
            event.update(
                {
                    "phase": "segmented_download_segment_response",
                    "toggle": bool(opcode & 0x10),
                }
            )
            if opcode == 0x30:
                mode_by_request.pop(request_id, None)
        elif len(frame.data) == 8 and opcode == 0x80:
            event.update(
                {
                    "phase": "sdo_abort",
                    "index": u16_le(frame.data, 1) or 0,
                    "subindex": frame.data[3],
                    "abort_code": u32_le(frame.data, 4) or 0,
                }
            )
            mode_by_request.pop(request_id, None)
        else:
            event["phase"] = "sdo_response_raw"

        events.append(event)

    return events


def decode_canopen_management(frames: Sequence[Frame]) -> dict[str, object]:
    """Decode standards-backed CANopen management traffic on Trane Link.

    This deliberately does not map node IDs to physical Trane products. It only
    names protocol-level NMT heartbeat and CiA-305 LSS behavior.
    """
    heartbeats: list[dict[str, object]] = []
    lss: list[dict[str, object]] = []
    nmt: list[dict[str, object]] = []

    for frame in frames:
        if frame.kind != "S":
            continue

        if 0x701 <= frame.can_id <= 0x77F and frame.data:
            state = frame.data[0]
            heartbeats.append(
                {
                    "line": frame.line_no,
                    "tick_ms": frame.tick_ms,
                    "node_id": frame.can_id - 0x700,
                    "state": HEARTBEAT_STATES.get(state, f"0x{state:02X}"),
                    "state_raw": state,
                }
            )
            continue

        if frame.can_id == 0x000 and len(frame.data) >= 2:
            nmt.append(
                {
                    "line": frame.line_no,
                    "tick_ms": frame.tick_ms,
                    "command": frame.data[0],
                    "target_node": frame.data[1],
                }
            )
            continue

        if frame.can_id not in (0x7E4, 0x7E5) or len(frame.data) != 8:
            continue

        entry: dict[str, object] = {
            "line": frame.line_no,
            "tick_ms": frame.tick_ms,
            "can_id": f"0x{frame.can_id:03X}",
            "direction": (
                "manager_to_server" if frame.can_id == 0x7E5 else "server_to_manager"
            ),
            "command": frame.data[0],
            "raw": frame.data.hex().upper(),
        }

        # CiA-305 Fastscan request. After command specifier 0x51 the layout is
        # IDNumber[0..3], BitCheck, LSSSub, LSSNext. BitCheck 0x80 with the
        # remaining selection fields zero is the Fastscan initialization form.
        if frame.can_id == 0x7E5 and frame.data[0] == 0x51:
            id_number = u32_le(frame.data, 1) or 0
            bit_check = frame.data[5]
            lss_sub = frame.data[6]
            lss_next = frame.data[7]
            entry.update(
                {
                    "service": "lss_fastscan",
                    "id_number": id_number,
                    "bit_check": bit_check,
                    "lss_sub": lss_sub,
                    "lss_next": lss_next,
                    "phase": (
                        "initialize"
                        if id_number == 0
                        and bit_check == 0x80
                        and lss_sub == 0
                        and lss_next == 0
                        else "probe"
                    ),
                }
            )
        elif frame.can_id == 0x7E4 and frame.data[0] == 0x4F:
            entry["service"] = "lss_fastscan_response"
        else:
            entry["service"] = "lss_raw"
        lss.append(entry)

    latest_heartbeat_by_node: dict[int, dict[str, object]] = {}
    for heartbeat in heartbeats:
        latest_heartbeat_by_node[int(heartbeat["node_id"])] = heartbeat

    return {
        "nmt": nmt,
        "heartbeats_latest": [
            latest_heartbeat_by_node[node_id]
            for node_id in sorted(latest_heartbeat_by_node)
        ],
        "lss": lss,
    }


def id_summary(frames: Sequence[Frame]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int], list[Frame]] = defaultdict(list)
    for frame in frames:
        grouped[(frame.kind, frame.can_id)].append(frame)
    rows: list[dict[str, object]] = []
    for (kind, can_id), group in sorted(grouped.items()):
        deltas = [
            (right.tick_ms - left.tick_ms) / 1000.0
            for left, right in zip(group, group[1:])
            if right.tick_ms >= left.tick_ms
        ]
        rows.append(
            {
                "kind": kind,
                "can_id": f"0x{can_id:03X}" if kind == "S" else f"0x{can_id:08X}",
                "count": len(group),
                "dlc": sorted(set(frame.dlc for frame in group)),
                "median_period_s": statistics.median(deltas) if deltas else None,
                "last_data": group[-1].data.hex().upper(),
            }
        )
    return rows


def analyze(frames: Sequence[Frame]) -> dict[str, object]:
    return {
        "frame_count": len(frames),
        "standard_frame_count": sum(frame.kind == "S" for frame in frames),
        "extended_frame_count": sum(frame.kind == "E" for frame in frames),
        "unique_standard_ids": len({frame.can_id for frame in frames if frame.kind == "S"}),
        "ids": id_summary(frames),
        "typed_ranges": typed_ranges(frames),
        "structured_json": reassemble_json(frames),
        "canopen_sdo_transport": decode_canopen_sdo_transport(frames),
        "canopen_management": decode_canopen_management(frames),
    }


def _print_text(report: dict[str, object]) -> None:
    print(
        f"frames={report['frame_count']} standard={report['standard_frame_count']} "
        f"extended={report['extended_frame_count']} unique_standard_ids={report['unique_standard_ids']}"
    )
    print("\nID census:")
    for row in report["ids"]:
        period = row["median_period_s"]
        period_text = "-" if period is None else f"{period:.3f}s"
        print(
            f"  {row['kind']} {row['can_id']:>10} count={row['count']:>5} "
            f"dlc={','.join(map(str, row['dlc'])):<5} period={period_text:<9} last={row['last_data']}"
        )
    print("\nTyped ranges (wire interpretation only):")
    print(json.dumps(report["typed_ranges"], indent=2, sort_keys=True))
    print("\nCANopen SDO transport:")
    print(json.dumps(report["canopen_sdo_transport"], indent=2, sort_keys=True))
    print("\nCANopen management:")
    print(json.dumps(report["canopen_management"], indent=2, sort_keys=True))
    print("\nReassembled structured JSON:")
    print(json.dumps(report["structured_json"], indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="ESPHome log containing TRANE_CAN_LIVE records")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable JSON report")
    args = parser.parse_args(argv)

    try:
        lines = args.log.read_text(errors="replace").splitlines()
    except OSError as exc:
        parser.error(str(exc))
    frames = parse_frames(lines)
    report = analyze(frames)
    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
