import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPP = (ROOT / "components/trane_bus/trane_bus.cpp").read_text()
HEADER = (ROOT / "components/trane_bus/trane_bus.h").read_text()
EXTRA_AGGREGATOR = (ROOT / "waveshare-trane-known-telemetry-extra.yaml").read_text()
EXTRA_BASE = (ROOT / "waveshare-trane-known-telemetry-extra-base.yaml").read_text()
TARGET_DISCOVERY = (ROOT / "waveshare-trane-target-discovery.yaml").read_text()
TARGET_RAW = (ROOT / "waveshare-trane-target-raw.yaml").read_text()
# Match the semantic surface ESPHome receives from the aggregator's children.
# The aggregator itself intentionally contains package references, not the
# child entity declarations.
EXTRA = EXTRA_BASE + "\n" + TARGET_DISCOVERY + "\n" + TARGET_RAW


class DiscoveryCensusContractTests(unittest.TestCase):
    def test_census_is_bounded_to_standard_can_space(self):
        self.assertIn("STANDARD_CAN_ID_COUNT = 0x800", HEADER)
        self.assertIn("std::array<uint32_t, STANDARD_CAN_ID_COUNT> id_counts_", HEADER)
        self.assertIn("std::array<uint8_t, STANDARD_CAN_ID_COUNT> id_last_dlc_", HEADER)
        self.assertIn("id_last_data_", HEADER)
        self.assertNotIn("std::map<uint32_t", HEADER)

    def test_standard_frames_are_observed_before_semantic_filtering(self):
        function = CPP.split("void TraneBus::on_can_frame_", 1)[1].split(
            "bool TraneBus::feed_segmented_json_", 1
        )[0]
        self.assertIn("observe_standard_frame_(can_id, data);", function)
        self.assertLess(
            function.index("observe_standard_frame_(can_id, data);"),
            function.index("is_known_trane_id_(can_id)"),
        )

    def test_aggregator_loads_all_discovery_children(self):
        for child in (
            "waveshare-trane-known-telemetry-extra-base.yaml",
            "waveshare-trane-target-discovery.yaml",
            "waveshare-trane-target-raw.yaml",
        ):
            self.assertIn(child, EXTRA_AGGREGATOR)

    def test_census_dump_is_compact_and_machine_parseable(self):
        self.assertIn("TRANE_ID_CENSUS_BEGIN", CPP)
        self.assertIn('"TRANE_ID,%03X,%lu,%u,%s"', CPP)
        self.assertIn("TRANE_ID_CENSUS_END", CPP)
        self.assertIn("Dump CAN ID Census", EXTRA)
        self.assertIn("Clear CAN ID Census", EXTRA)

    def test_generic_observation_getters_feed_candidate_entities(self):
        for getter in (
            "get_last_float_le_or_nan",
            "get_last_u16_le_or_nan",
            "get_last_byte_or_nan",
            "get_last_u32_le_or_zero",
            "get_last_frame_hex",
        ):
            self.assertIn(getter, HEADER)
            self.assertIn(getter, CPP)
        for can_id in (
            "0x281", "0x300", "0x310", "0x318", "0x320",
            "0x382", "0x385", "0x388", "0x389", "0x38C",
            "0x490", "0x4B1", "0x4B2",
        ):
            self.assertIn(can_id, EXTRA)

    def test_observed_profile_metadata_is_retained_passively(self):
        self.assertIn("last_json_root_", HEADER)
        self.assertIn("last_profile_request_", HEADER)
        self.assertIn('last_json_root_ == "GetProfile"', CPP)
        self.assertIn('"THERMOSETTINGS"', CPP)
        self.assertIn("Last Structured JSON Root", EXTRA)
        self.assertIn("Last OEM GetProfile Request", EXTRA)

    def test_structured_snapshots_are_bounded_and_raw(self):
        self.assertIn("JSON_SNAPSHOT_SLOTS = 16", HEADER)
        self.assertIn("MAX_JSON_SNAPSHOT_BYTES = 2048", HEADER)
        self.assertIn("get_last_json_value", HEADER)
        self.assertIn("remember_json_snapshot_", CPP)
        self.assertIn("Dump Structured Profile Snapshots", EXTRA)
        for token in (
            "IndoorSettings 1 A Raw",
            "IndoorSettings 1 U Raw",
            "ZoneSettings 1 ZoneMode Raw",
            "SystemSettings B Raw",
            "SystemSettings N Raw",
            "VersionDetails D Raw",
        ):
            self.assertIn(token, EXTRA)

    def test_discovery_package_remains_read_only(self):
        for package in (EXTRA_AGGREGATOR, EXTRA_BASE, TARGET_DISCOVERY, TARGET_RAW):
            self.assertNotIn("\ncanbus:", package)
            self.assertNotIn("\ntrane_bus:", package)
            self.assertNotIn("send_data(", package)
            self.assertNotIn("trane_bus.set_tx_enabled", package)
            self.assertNotIn("trane_bus.set_mode", package)
            self.assertNotIn("trane_bus.set_setpoints", package)


if __name__ == "__main__":
    unittest.main()
