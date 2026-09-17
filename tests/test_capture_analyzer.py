import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import trane_capture_analyzer as analyzer


class CaptureAnalyzerTests(unittest.TestCase):
    def test_parse_and_typed_words(self):
        lines = [
            "[00:00:00.000][I][trane_wire]: TRANE_CAN_LIVE,S,1000,281,8,0603F40100006401",
            "[00:00:00.100][I][trane_wire]: TRANE_CAN_LIVE,S,1100,4B1,4,3E38AC6A",
        ]
        frames = analyzer.parse_frames(lines)
        self.assertEqual(len(frames), 2)
        self.assertEqual(analyzer.u16_le(frames[0].data, 0), 774)
        self.assertEqual(analyzer.u16_le(frames[0].data, 2), 500)
        self.assertEqual(analyzer.u16_le(frames[0].data, 6), 356)
        self.assertEqual(analyzer.u32_le(frames[1].data, 0), 1789671486)

    def test_short_641_ack_reassembly(self):
        lines = [
            "TRANE_CAN_LIVE,S,1000,641,8,210A30000E000000",
            "TRANE_CAN_LIVE,S,1001,641,8,007B2241636B223A",
            "TRANE_CAN_LIVE,S,1002,641,8,1122323030227D00",
        ]
        frames = analyzer.parse_frames(lines)
        messages = analyzer.reassemble_json(frames)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["can_id"], "0x641")
        self.assertEqual(messages[0]["json"], {"Ack": "200"})

    def test_malformed_short_record_is_ignored(self):
        frames = analyzer.parse_frames(
            ["TRANE_CAN_LIVE,S,1000,281,8,0603F401"]
        )
        self.assertEqual(frames, [])

    def test_report_is_json_serializable(self):
        frames = analyzer.parse_frames(
            ["TRANE_CAN_LIVE,S,1000,490,5,00009C4236"]
        )
        report = analyzer.analyze(frames)
        encoded = json.dumps(report)
        self.assertIn('"0x490"', encoded)
        self.assertEqual(report["unique_standard_ids"], 1)


if __name__ == "__main__":
    unittest.main()
