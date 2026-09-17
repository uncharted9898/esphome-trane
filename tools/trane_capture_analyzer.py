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

SEGMENTED_JSON_IDS = (0x601, 0x641, 0x649)

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
        output["0x281"] = result

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
