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
        ranges = analyzer.typed_ranges(frames)
        self.assertEqual(ranges["0x281"]["byte_6"]["last"], 100)
        self.assertEqual(ranges["0x281"]["byte_7"]["last"], 1)
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

    def test_zone_status_is_canopen_sdo_block_download(self):
        lines = [
            "TRANE_CAN_LIVE,S,1000,649,8,C20A30002E000000",
            "TRANE_CAN_LIVE,S,1002,5C9,8,A00A300007000000",
            "TRANE_CAN_LIVE,S,1005,649,8,017B225A6F6E6553",
            "TRANE_CAN_LIVE,S,1008,649,8,027461747573223A",
            "TRANE_CAN_LIVE,S,1011,649,8,037B225570646174",
            "TRANE_CAN_LIVE,S,1014,649,8,0465223A7B223122",
            "TRANE_CAN_LIVE,S,1017,649,8,053A7B2248223A22",
            "TRANE_CAN_LIVE,S,1020,649,8,0637362E3030227D",
            "TRANE_CAN_LIVE,S,1023,649,8,877D7D7D0030227D",
            "TRANE_CAN_LIVE,S,1026,5C9,8,A207000000000000",
            "TRANE_CAN_LIVE,S,1029,649,8,CD00000000000000",
            "TRANE_CAN_LIVE,S,1032,5C9,8,A100000000000000",
        ]
        frames = analyzer.parse_frames(lines)
        messages = analyzer.reassemble_json(frames)
        self.assertEqual(
            messages[0]["json"],
            {"ZoneStatus": {"Update": {"1": {"H": "76.00"}}}},
        )

        sdo = analyzer.decode_canopen_sdo_transport(frames)
        self.assertEqual(sdo[0]["phase"], "block_download_initiate_request")
        self.assertEqual(sdo[0]["index"], 0x300A)
        self.assertEqual(sdo[0]["subindex"], 0)
        self.assertEqual(sdo[0]["size"], 46)
        self.assertTrue(sdo[0]["trane_json_object"])

        init_rsp = next(row for row in sdo if row["phase"] == "block_download_initiate_response")
        self.assertEqual(init_rsp["block_size"], 7)
        self.assertTrue(init_rsp["trane_json_object"])

        segments = [row for row in sdo if row["phase"] == "block_download_segment"]
        self.assertEqual([row["sequence"] for row in segments], list(range(1, 8)))
        self.assertFalse(any(row["last"] for row in segments[:-1]))
        self.assertTrue(segments[-1]["last"])

        block_ack = next(row for row in sdo if row["phase"] == "block_download_subblock_response")
        self.assertEqual(block_ack["ack_sequence"], 7)

        end_req = next(row for row in sdo if row["phase"] == "block_download_end_request")
        self.assertEqual(end_req["unused_bytes"], 3)
        self.assertEqual(sdo[-1]["phase"], "block_download_end_response")

    def test_short_ack_is_canopen_sdo_segmented_download(self):
        lines = [
            "TRANE_CAN_LIVE,S,1000,641,8,210A30000E000000",
            "TRANE_CAN_LIVE,S,1002,5C1,8,600A300000000000",
            "TRANE_CAN_LIVE,S,1004,641,8,007B2241636B223A",
            "TRANE_CAN_LIVE,S,1006,5C1,8,2000000000000000",
            "TRANE_CAN_LIVE,S,1008,641,8,1122323030227D00",
            "TRANE_CAN_LIVE,S,1010,5C1,8,3000000000000000",
        ]
        sdo = analyzer.decode_canopen_sdo_transport(analyzer.parse_frames(lines))
        self.assertEqual(
            [row["phase"] for row in sdo],
            [
                "segmented_download_initiate_request",
                "segmented_download_initiate_response",
                "segmented_download_segment",
                "segmented_download_segment_response",
                "segmented_download_segment",
                "segmented_download_segment_response",
            ],
        )
        self.assertEqual(sdo[0]["index"], 0x300A)
        self.assertEqual(sdo[0]["subindex"], 0)
        self.assertEqual(sdo[0]["size"], 14)
        self.assertTrue(sdo[0]["trane_json_object"])
        self.assertFalse(sdo[2]["toggle"])
        self.assertFalse(sdo[2]["last"])
        self.assertTrue(sdo[4]["toggle"])
        self.assertTrue(sdo[4]["last"])

    def test_canopen_lss_fastscan_initialize_decode(self):
        frames = analyzer.parse_frames(
            ["TRANE_CAN_LIVE,S,1000,7E5,8,5100000000800000"]
        )
        management = analyzer.decode_canopen_management(frames)
        self.assertEqual(len(management["lss"]), 1)
        event = management["lss"][0]
        self.assertEqual(event["direction"], "manager_to_server")
        self.assertEqual(event["service"], "lss_fastscan")
        self.assertEqual(event["phase"], "initialize")
        self.assertEqual(event["id_number"], 0)
        self.assertEqual(event["bit_check"], 0x80)
        self.assertEqual(event["lss_sub"], 0)
        self.assertEqual(event["lss_next"], 0)

    def test_canopen_lss_fastscan_response_decode(self):
        frames = analyzer.parse_frames(
            ["TRANE_CAN_LIVE,S,1000,7E4,8,4F00000000000000"]
        )
        management = analyzer.decode_canopen_management(frames)
        self.assertEqual(len(management["lss"]), 1)
        event = management["lss"][0]
        self.assertEqual(event["direction"], "server_to_manager")
        self.assertEqual(event["service"], "lss_fastscan_response")

    def test_canopen_heartbeat_state_decode(self):
        frames = analyzer.parse_frames(
            [
                "TRANE_CAN_LIVE,S,1000,701,1,05",
                "TRANE_CAN_LIVE,S,1100,703,1,7F",
            ]
        )
        management = analyzer.decode_canopen_management(frames)
        self.assertEqual(
            [(row["node_id"], row["state"]) for row in management["heartbeats_latest"]],
            [(1, "operational"), (3, "pre-operational")],
        )

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
        self.assertIn('"canopen_management"', encoded)
        self.assertIn('"canopen_sdo_transport"', encoded)
        self.assertEqual(report["unique_standard_ids"], 1)


if __name__ == "__main__":
    unittest.main()
