import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HA = (ROOT / "waveshare-trane-homeassistant.yaml").read_text()
TELEMETRY = (ROOT / "waveshare-trane-known-telemetry.yaml").read_text()


class KnownTelemetryContractTests(unittest.TestCase):
    def test_homeassistant_loads_remote_known_telemetry_package(self):
        self.assertIn("packages:", HA)
        self.assertIn(
            "github://uncharted9898/esphome-trane/waveshare-trane-known-telemetry.yaml@dev",
            HA,
        )

    def test_package_is_read_only(self):
        self.assertNotIn("send_data(", TELEMETRY)
        self.assertNotIn("trane_bus.set_tx_enabled", TELEMETRY)
        self.assertNotIn("trane_bus.set_mode", TELEMETRY)
        self.assertNotIn("trane_bus.set_setpoints", TELEMETRY)
        self.assertNotIn("trane_bus.get_profile", TELEMETRY)

    def test_known_system_entities_are_exposed(self):
        for name in (
            "Room Temperature",
            "Heat Setpoint",
            "Cool Setpoint",
            "Indoor Humidity",
            "System Mode",
            "System Demand Stage",
            "Indoor Blower Speed",
            "Compressor Speed",
            "Compressor Demand",
            "Outdoor Air Temperature",
            "Outdoor Fault Code",
            "Active Alarm 1",
            "Unit Firmware",
        ):
            self.assertIn(f'name: "{name}"', TELEMETRY)

    def test_candidate_channels_are_not_mislabeled_as_confirmed(self):
        for label in (
            "0x283 Float 1 Candidate ET GT",
            "0x283 Float 2 Candidate ET GT",
            "0x308 Float 1 Candidate Return Air",
            "0x308 Float 2 Candidate Supply Air",
            "0x386 Float 2 Refrigerant Temperature Candidate",
            "0x387 Float 1 Temperature Candidate",
            "0x38F Refrigerant Pressure Candidate",
            "0x410 Temperature Candidate",
            "0x430 Temperature Candidate",
            "0x450 Temperature Candidate",
        ):
            self.assertIn(f'name: "{label}"', TELEMETRY)

    def test_raw_discovery_surfaces_exist(self):
        for name in (
            "Last JSON 0x649",
            "Last JSON 0x641",
            "Last 0x490 Raw",
            "Unclassified CAN Frames",
            "Last Unknown CAN ID",
            "Last Unknown CAN Frame",
        ):
            self.assertIn(f'name: "{name}"', TELEMETRY)
        self.assertIn("can_id_mask: 0x000", TELEMETRY)

    def test_expected_target_only_features_remain_discovery_not_fake_values(self):
        # These 5TAMX/5TWV0X/R-454B concepts are expected targets, but we must
        # not publish invented values before target-system captures identify
        # their exact CAN/JSON fields.
        for fake_id in (
            "mitigation_active",
            "leak_detected",
            "requested_cfm",
            "actual_cfm",
            "eev_position",
            "superheat_actual",
            "suction_pressure",
            "liquid_pressure",
        ):
            self.assertNotIn(f"id: trane_{fake_id}", TELEMETRY)


if __name__ == "__main__":
    unittest.main()
