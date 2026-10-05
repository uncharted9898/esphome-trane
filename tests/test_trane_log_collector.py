import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import trane_log_collector as collector


class Clock:
    def __init__(self, when):
        self.when = when

    def __call__(self):
        return self.when


class TraneLogCollectorTests(unittest.TestCase):
    def test_parse_can_record_preserves_raw_and_fields(self):
        line = (
            "[21:04:11][I][trane_wire]: "
            "TRANE_CAN_LIVE,S,123456,383,8,0000044300808B43"
        )
        row = collector.parse_trane_line(line)
        self.assertIsNotNone(row)
        self.assertEqual(row["type"], "can")
        self.assertEqual(row["frame_kind"], "S")
        self.assertEqual(row["device_tick_ms"], 123456)
        self.assertEqual(row["can_id"], "0x383")
        self.assertEqual(row["can_id_int"], 0x383)
        self.assertEqual(row["dlc"], 8)
        self.assertEqual(row["data"], "0000044300808B43")
        self.assertEqual(row["raw"], line)
        self.assertNotIn("parse_warning", row)

    def test_parse_extended_can_id(self):
        row = collector.parse_trane_line(
            "TRANE_CAN_LIVE,E,77,1ABCDEFF,2,A10F"
        )
        self.assertEqual(row["can_id"], "0x1ABCDEFF")
        self.assertEqual(row["can_id_int"], 0x1ABCDEFF)
        self.assertEqual(row["frame_kind"], "E")

    def test_parse_can_dlc_mismatch_is_retained_with_warning(self):
        row = collector.parse_trane_line(
            "TRANE_CAN_LIVE,S,1000,281,8,0603F401"
        )
        self.assertEqual(row["type"], "can")
        self.assertIn("parse_warning", row)
        self.assertEqual(row["data"], "0603F401")

    def test_parse_structured_json(self):
        line = (
            '[I][trane_json]: TRANE_JSON,649,'
            '{"OdStatus":{"B":"56","CompDemandPercent":"36"}}'
        )
        row = collector.parse_trane_line(line)
        self.assertEqual(row["type"], "trane_json")
        self.assertEqual(row["can_id"], "0x649")
        self.assertEqual(
            row["json"],
            {"OdStatus": {"B": "56", "CompDemandPercent": "36"}},
        )
        self.assertNotIn("parse_error", row)

    def test_malformed_structured_json_is_not_dropped(self):
        row = collector.parse_trane_line(
            'TRANE_JSON,649,{"OdStatus":'
        )
        self.assertEqual(row["type"], "trane_json")
        self.assertEqual(row["can_id"], "0x649")
        self.assertIn("parse_error", row)
        self.assertEqual(row["json_raw"], '{"OdStatus":')

    def test_other_trane_lines_are_preserved(self):
        row = collector.parse_trane_line(
            "[I][trane_wire]: TRANE_DISCOVERY example"
        )
        self.assertEqual(row["type"], "trane_log")

    def test_non_trane_line_is_ignored_by_default_parser(self):
        self.assertIsNone(
            collector.parse_trane_line("[I][wifi]: Connected")
        )

    def test_hourly_writer_creates_hour_named_chunks(self):
        with tempfile.TemporaryDirectory() as td:
            clock = Clock(datetime(2026, 10, 5, 0, 10, tzinfo=timezone.utc))
            base = Path(td) / "trane.jsonl"
            writer = collector.HourlyArchiveWriter(
                base, "trane-link.local", now_fn=clock
            )
            writer.write({"type": "can", "can_id": "0x383"})
            writer.close()

            path = Path(td) / "trane-2026-10-05-00.jsonl"
            self.assertTrue(path.exists())
            row = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(row["source"], "trane-link.local")
            self.assertEqual(row["type"], "can")
            self.assertEqual(row["can_id"], "0x383")

    def test_hour_roll_closes_old_chunk_and_opens_new_chunk(self):
        with tempfile.TemporaryDirectory() as td:
            clock = Clock(datetime(2026, 10, 5, 0, 59, tzinfo=timezone.utc))
            base = Path(td) / "trane.jsonl"
            writer = collector.HourlyArchiveWriter(
                base, "trane-link.local", now_fn=clock
            )
            writer.write({"type": "first"})
            clock.when = datetime(2026, 10, 5, 1, 0, tzinfo=timezone.utc)
            writer.write({"type": "second"})
            writer.close()

            self.assertTrue((Path(td) / "trane-2026-10-05-00.jsonl").exists())
            self.assertTrue((Path(td) / "trane-2026-10-05-01.jsonl").exists())

    def test_day_roll_archives_completed_day_and_removes_chunks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            clock = Clock(datetime(2026, 10, 5, 23, 50, tzinfo=timezone.utc))
            base = root / "trane.jsonl"
            writer = collector.HourlyArchiveWriter(
                base, "trane-link.local", now_fn=clock
            )
            writer.write({"type": "late"})
            clock.when = datetime(2026, 10, 6, 0, 0, tzinfo=timezone.utc)
            writer.write({"type": "new-day"})
            writer.close()

            archive = root / "trane-2026-10-05.tar.gz"
            self.assertTrue(archive.exists())
            self.assertFalse((root / "trane-2026-10-05-23.jsonl").exists())
            self.assertTrue((root / "trane-2026-10-06-00.jsonl").exists())

            with tarfile.open(archive, "r:gz") as bundle:
                self.assertEqual(
                    [m.name for m in bundle.getmembers() if m.isfile()],
                    ["trane-2026-10-05-23.jsonl"],
                )

    def test_restart_archives_prior_day_chunks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = root / "trane-2026-10-04-22.jsonl"
            old.write_text('{"type":"old"}\n', encoding="utf-8")
            clock = Clock(datetime(2026, 10, 5, 7, 0, tzinfo=timezone.utc))

            writer = collector.HourlyArchiveWriter(
                root / "trane.jsonl", "trane-link.local", now_fn=clock
            )
            writer.close()

            self.assertFalse(old.exists())
            archive = root / "trane-2026-10-04.tar.gz"
            self.assertTrue(archive.exists())
            with tarfile.open(archive, "r:gz") as bundle:
                self.assertEqual(
                    [m.name for m in bundle.getmembers() if m.isfile()],
                    ["trane-2026-10-04-22.jsonl"],
                )

    def test_existing_verified_archive_allows_restart_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chunk = root / "trane-2026-10-04-22.jsonl"
            chunk.write_text('{"type":"old"}\n', encoding="utf-8")
            archive = root / "trane-2026-10-04.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                bundle.add(chunk, arcname=chunk.name)
            clock = Clock(datetime(2026, 10, 5, 7, 0, tzinfo=timezone.utc))

            writer = collector.HourlyArchiveWriter(
                root / "trane.jsonl", "trane-link.local", now_fn=clock
            )
            writer.close()

            self.assertFalse(chunk.exists())
            self.assertTrue(archive.exists())

    def test_cli_defaults_to_native_api_port_and_default_output_base(self):
        args = collector.build_parser().parse_args(["trane-link.local"])
        self.assertEqual(args.address, "trane-link.local")
        self.assertEqual(args.port, 6053)
        self.assertFalse(args.all)
        self.assertIsNone(args.output)
        self.assertEqual(
            collector.default_output_base(),
            Path("trane-capture.jsonl"),
        )


if __name__ == "__main__":
    unittest.main()
