from pathlib import Path
import sys
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import trane_log_collector as collector


class TraneLogCollectorTests(unittest.TestCase):
    def test_parse_can_record(self):
        row = collector.parse_trane_line(
            "[I][trane_wire]: TRANE_CAN_LIVE,S,123456,383,8,0000804200001743"
        )
        self.assertEqual(row["type"], "can")
        self.assertEqual(row["device_tick_ms"], 123456)
        self.assertEqual(row["can_id"], "0x383")
        self.assertEqual(row["can_id_int"], 0x383)
        self.assertEqual(row["dlc"], 8)
        self.assertEqual(row["data"], "0000804200001743")

    def test_parse_structured_json(self):
        row = collector.parse_trane_line(
            '[I][trane_json]: TRANE_JSON,649,{"OdStatus":{"B":"56"}}'
        )
        self.assertEqual(row["type"], "trane_json")
        self.assertEqual(row["can_id"], "0x649")
        self.assertEqual(row["json"], {"OdStatus": {"B": "56"}})

    def test_unrelated_line_is_ignored(self):
        self.assertIsNone(collector.parse_trane_line("[I][wifi]: connected"))

    def test_other_trane_line_is_preserved(self):
        row = collector.parse_trane_line("[W][trane_bus]: TRANE_SOMETHING,abc")
        self.assertEqual(row["type"], "trane_log")
        self.assertIn("TRANE_SOMETHING", row["raw"])

    def test_jsonl_writer_emits_timestamp_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.jsonl"
            writer = collector.JsonlWriter(path, "trane-link.local")
            writer.write({"type": "test", "value": 7})
            writer.close()
            row = json.loads(path.read_text().strip())
            self.assertEqual(row["source"], "trane-link.local")
            self.assertEqual(row["type"], "test")
            self.assertEqual(row["value"], 7)
            self.assertIn("host_ts", row)


if __name__ == "__main__":
    unittest.main()
