#!/usr/bin/env python3
"""Continuously archive Trane Link ESPHome API logs as append-only JSONL."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import re
import signal
import sys
from typing import Any, Sequence

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
CAN_RE = re.compile(
    r"TRANE_CAN_LIVE,(?P<kind>[SE]),(?P<tick>\d+),(?P<canid>[0-9A-Fa-f]+),"
    r"(?P<dlc>\d+),(?P<data>[0-9A-Fa-f]*)"
)
JSON_MARKER = "TRANE_JSON,"
COLLECTOR_VERSION = 1


def now_iso() -> str:
    """Return a local offset-aware timestamp with millisecond precision."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def parse_trane_line(line: str) -> dict[str, Any] | None:
    """Parse one ESPHome log line while preserving the original line."""
    can_match = CAN_RE.search(line)
    if can_match:
        can_id = int(can_match.group("canid"), 16)
        dlc = int(can_match.group("dlc"))
        data = can_match.group("data").upper()
        record: dict[str, Any] = {
            "type": "can",
            "frame_kind": can_match.group("kind"),
            "device_tick_ms": int(can_match.group("tick")),
            "can_id": f"0x{can_id:03X}" if can_id <= 0x7FF else f"0x{can_id:08X}",
            "can_id_int": can_id,
            "dlc": dlc,
            "data": data,
            "raw": line,
        }
        if len(data) != dlc * 2:
            record["parse_warning"] = (
                f"reported DLC {dlc} but captured {len(data) // 2} data bytes"
            )
        return record

    marker = line.find(JSON_MARKER)
    if marker >= 0:
        tail = line[marker + len(JSON_MARKER) :]
        can_id_text, sep, payload = tail.partition(",")
        if not sep:
            return {
                "type": "trane_json",
                "raw": line,
                "parse_error": "missing JSON payload",
            }

        record = {
            "type": "trane_json",
            "raw": line,
            "json_raw": payload,
        }
        try:
            can_id = int(can_id_text, 16)
        except ValueError:
            record["can_id_raw"] = can_id_text
            record["parse_error"] = "invalid CAN ID"
        else:
            record["can_id"] = (
                f"0x{can_id:03X}" if can_id <= 0x7FF else f"0x{can_id:08X}"
            )
            record["can_id_int"] = can_id

        try:
            record["json"] = json.loads(payload)
        except json.JSONDecodeError as exc:
            prior = record.get("parse_error")
            detail = f"JSON decode error at column {exc.colno}: {exc.msg}"
            record["parse_error"] = f"{prior}; {detail}" if prior else detail
        return record

    if "TRANE_" in line:
        return {"type": "trane_log", "raw": line}
    return None


class JsonlWriter:
    """Small line-buffered JSONL sink."""

    def __init__(self, path: Path, source: str) -> None:
        self.path = path
        self.source = source
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("a", encoding="utf-8", buffering=1)

    def write(self, record: dict[str, Any]) -> None:
        envelope = {
            "host_ts": now_iso(),
            "source": self.source,
            **record,
        }
        self._file.write(json.dumps(envelope, separators=(",", ":"), ensure_ascii=False))
        self._file.write("\n")

    def close(self) -> None:
        self._file.flush()
        self._file.close()


def default_output_path() -> Path:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    return Path(f"trane-capture-{stamp}.jsonl")


def install_stop_handlers(stop_event: asyncio.Event) -> list[str]:
    """Map terminal stop signals to a clean collector shutdown."""
    loop = asyncio.get_running_loop()
    installed: list[str] = []

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError):
            continue
        installed.append(sig.name)

    # Ctrl-Z normally suspends a POSIX foreground process. For this foreground
    # recorder, treat it as "finish this capture" so the output file is flushed.
    sigtstp = getattr(signal, "SIGTSTP", None)
    if sigtstp is not None:
        try:
            loop.add_signal_handler(sigtstp, stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass
        else:
            installed.append(sigtstp.name)

    return installed


async def collect(args: argparse.Namespace) -> int:
    try:
        from aioesphomeapi import APIClient, LogLevel
        from aioesphomeapi.log_runner import async_run
    except ImportError:
        print(
            "aioesphomeapi is required: python -m pip install aioesphomeapi",
            file=sys.stderr,
        )
        return 2

    output = args.output or default_output_path()
    writer = JsonlWriter(output, args.address)
    stop_event = asyncio.Event()
    installed_signals = install_stop_handlers(stop_event)

    writer.write(
        {
            "type": "collector",
            "event": "start",
            "collector_version": COLLECTOR_VERSION,
            "port": args.port,
            "all_logs": args.all,
        }
    )

    api = APIClient(
        args.address,
        args.port,
        noise_psk=args.noise_psk,
        keepalive=10,
    )

    def on_log(message: Any) -> None:
        text = message.message.decode("utf-8", "backslashreplace")
        # SubscribeLogsResponse may contain multiple physical log lines. Keep
        # each line independently timestamped and preserve the original text.
        for raw_line in text.splitlines() or [text]:
            line = ANSI_RE.sub("", raw_line).strip()
            record = parse_trane_line(line)
            if record is None:
                if not args.all:
                    continue
                record = {"type": "esphome_log", "raw": line}
            record["api_log_level"] = int(message.level)
            writer.write(record)

    def on_connect() -> None:
        writer.write({"type": "collector", "event": "connected"})

    stop_logs = await async_run(
        api,
        on_log,
        log_level=LogLevel.LOG_LEVEL_VERY_VERBOSE,
        dump_config=False,
        subscribe_states=False,
        on_connect=on_connect,
    )

    signal_hint = "Ctrl-C"
    if "SIGTSTP" in installed_signals:
        signal_hint += " or Ctrl-Z"
    print(f"Recording {args.address}:{args.port} -> {output}")
    print(f"{signal_hint} to stop cleanly.")

    try:
        await stop_event.wait()
    finally:
        writer.write({"type": "collector", "event": "stop"})
        await stop_logs()
        writer.close()
        print(f"Saved {output}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address", help="ESPHome IP, hostname, or .local name")
    parser.add_argument("--port", type=int, default=6053)
    parser.add_argument(
        "--noise-psk",
        default=os.environ.get("ESPHOME_NOISE_PSK"),
        help="ESPHome API encryption key; defaults to ESPHOME_NOISE_PSK",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="JSONL file to append to; default creates a timestamped capture file",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="also retain non-TRANE ESPHome log lines",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return asyncio.run(collect(args))
    except KeyboardInterrupt:
        # Fallback for event loops/platforms where add_signal_handler is absent.
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
