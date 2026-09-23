import json
from datetime import datetime
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import trane_log_collector as collector


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

    def test_jsonl_writer_appends_parseable_records(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "capture.jsonl"
            writer = collector.JsonlWriter(path, "trane-link-bridge.local")
            writer.write(
                {
                    "type": "can",
                    "can_id": "0x383",
                    "data": "0000044300808B43",
                }
            )
            writer.close()

            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            self.assertEqual(row["source"], "trane-link-bridge.local")
            self.assertEqual(row["type"], "can")
            self.assertEqual(row["can_id"], "0x383")
            self.assertIn("host_ts", row)
            self.assertRegex(
                row["host_ts"],
                r"^\d{4}-\d{2}-\d{2}T.*[+-]\d{2}:\d{2}$",
            )

    def test_cli_defaults_to_native_api_port(self):
        args = collector.build_parser().parse_args(["trane-link.local"])
        self.assertEqual(args.address, "trane-link.local")
        self.assertEqual(args.port, 6053)
        self.assertFalse(args.all)
        self.assertIsNone(args.output)
        self.assertEqual(collector.default_output_base(), Path("trane-capture.jsonl"))


if __name__ == "__main__":
    unittest.main()
