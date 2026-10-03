#!/usr/bin/env python3
"""Continuously archive Trane Link ESPHome API logs as hourly JSONL + daily tar.gz."""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import signal
import sys
import tarfile
from typing import Any, Callable, Sequence

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
CAN_RE = re.compile(
    r"TRANE_CAN_LIVE,(?P<kind>[SE]),(?P<tick>\d+),(?P<canid>[0-9A-Fa-f]+),"
    r"(?P<dlc>\d+),(?P<data>[0-9A-Fa-f]*)"
)
JSON_MARKER = "TRANE_JSON,"
COLLECTOR_VERSION = 2


def local_now() -> datetime:
    """Return the host-local, offset-aware wall clock."""
    return datetime.now().astimezone()


def now_iso() -> str:
    """Return a local offset-aware timestamp with millisecond precision."""
    return local_now().isoformat(timespec="milliseconds")


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


class HourlyArchiveWriter:
    """Append JSONL into hourly chunks and archive completed days safely."""

    def __init__(
        self,
        base_path: Path,
        source: str,
        *,
        now_fn: Callable[[], datetime] = local_now,
    ) -> None:
        self.base_path = base_path
        self.source = source
        self._now = now_fn
        self.directory = base_path.parent
        self.prefix = (
            base_path.name[: -len(".jsonl")]
            if base_path.name.endswith(".jsonl")
            else base_path.name
        )
        if not self.prefix:
            raise ValueError("output base must include a filename")

        self.directory.mkdir(parents=True, exist_ok=True)
        self._file: Any | None = None
        self._hour_key: str | None = None
        self.current_path: Path | None = None

        # If the recorder was stopped or the host rebooted, finish any fully
        # completed day before opening the current hour.
        self.archive_completed_days(self._now().date())

    def _hour_path(self, when: datetime) -> Path:
        return self.directory / f"{self.prefix}-{when.strftime('%Y-%m-%d-%H')}.jsonl"

    def _archive_path(self, day_text: str) -> Path:
        return self.directory / f"{self.prefix}-{day_text}.tar.gz"

    def _chunk_pattern(self) -> re.Pattern[str]:
        return re.compile(
            rf"^{re.escape(self.prefix)}-(?P<day>\d{{4}}-\d{{2}}-\d{{2}})-"
            rf"(?P<hour>\d{{2}})\.jsonl$"
        )

    def _close_current(self) -> None:
        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None

    def _ensure_hour(self, when: datetime) -> None:
        hour_key = when.strftime("%Y-%m-%d-%H")
        if self._hour_key == hour_key and self._file is not None:
            return

        self._close_current()

        # Crossing midnight makes yesterday eligible for archiving. At normal
        # hour changes this is a no-op.
        self.archive_completed_days(when.date())

        self.current_path = self._hour_path(when)
        self._file = self.current_path.open("a", encoding="utf-8", buffering=1)
        self._hour_key = hour_key

    def write(self, record: dict[str, Any]) -> None:
        when = self._now()
        self._ensure_hour(when)
        envelope = {
            "host_ts": when.isoformat(timespec="milliseconds"),
            "source": self.source,
            **record,
        }
        assert self._file is not None
        self._file.write(
            json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)
        )
        self._file.write("\n")

    def archive_completed_days(self, current_day: date) -> list[Path]:
        """Archive hourly chunks older than current_day.

        The raw JSONL chunks are removed only after the temporary tar.gz can be
        reopened successfully and has been atomically renamed into place.
        """
        pattern = self._chunk_pattern()
        grouped: dict[str, list[Path]] = {}

        for path in sorted(self.directory.glob(f"{self.prefix}-*.jsonl")):
            match = pattern.match(path.name)
            if match is None:
                continue
            day_text = match.group("day")
            try:
                chunk_day = date.fromisoformat(day_text)
            except ValueError:
                continue
            if chunk_day >= current_day:
                continue
            grouped.setdefault(day_text, []).append(path)

        archived: list[Path] = []
        for day_text, chunks in sorted(grouped.items()):
            archive = self._archive_path(day_text)

            # Recovery path: an archive may already exist if a process stopped
            # after the atomic rename but before all source chunks were removed.
            # Only delete leftovers if the existing archive contains them.
            if archive.exists():
                try:
                    with tarfile.open(archive, "r:gz") as existing:
                        names = {
                            member.name
                            for member in existing.getmembers()
                            if member.isfile()
                        }
                except (OSError, tarfile.TarError):
                    continue
                if all(chunk.name in names for chunk in chunks):
                    for chunk in chunks:
                        chunk.unlink()
                    archived.append(archive)
                continue

            temp = archive.with_name(f".{archive.name}.tmp-{os.getpid()}")
            try:
                with tarfile.open(temp, "w:gz") as bundle:
                    for chunk in chunks:
                        bundle.add(chunk, arcname=chunk.name, recursive=False)

                # Verify the gzip/tar can be reopened and that every source
                # chunk is represented before deleting any raw evidence.
                with tarfile.open(temp, "r:gz") as verify:
                    names = {
                        member.name
                        for member in verify.getmembers()
                        if member.isfile()
                    }
                if not all(chunk.name in names for chunk in chunks):
                    raise OSError("daily archive verification omitted an hourly chunk")

                os.replace(temp, archive)
                for chunk in chunks:
                    chunk.unlink()
                archived.append(archive)
            finally:
                if temp.exists():
                    temp.unlink()

        return archived

    def close(self) -> None:
        self._close_current()


def default_output_base() -> Path:
    return Path("trane-capture.jsonl")


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
    # recorder, treat it as "finish this capture" so the current hourly file is
    # flushed and closed rather than leaving a suspended recorder around.
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

    output_base = args.output or default_output_base()
    writer = HourlyArchiveWriter(output_base, args.address)
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

    print(f"Recording {args.address}:{args.port}")
    print(
        f"Hourly chunks: {writer.directory / (writer.prefix + '-YYYY-MM-DD-HH.jsonl')}"
    )
    print(
        f"Daily archives: {writer.directory / (writer.prefix + '-YYYY-MM-DD.tar.gz')}"
    )
    print(f"{signal_hint} to stop cleanly.")

    try:
        await stop_event.wait()
    finally:
        writer.write({"type": "collector", "event": "stop"})
        await stop_logs()
        writer.close()
        print("Capture stopped cleanly.")

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
        help=(
            "output base (default: trane-capture.jsonl); for example "
            "/data/trane/trane.jsonl creates trane-YYYY-MM-DD-HH.jsonl hourly "
            "chunks and trane-YYYY-MM-DD.tar.gz daily archives"
        ),
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
