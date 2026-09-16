import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HA = (ROOT / "waveshare-trane-homeassistant.yaml").read_text()
TELEMETRY = (ROOT / "waveshare-trane-known-telemetry-v2.yaml").read_text()


def without_yaml_comments(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


class KnownTelemetryContractTests(unittest.TestCase):
    def test_homeassistant_loads_package_safe_known_telemetry(self):
        self.assertIn("packages:", HA)
        self.assertIn(
            "github://uncharted9898/esphome-trane/waveshare-trane-known-telemetry-v2.yaml@dev",
            HA,
        )

    def test_package_owns_no_hardware_or_esphome_root(self):
        self.assertNotIn("\nesphome:", TELEMETRY)
        self.assertNotIn("\ncanbus:", TELEMETRY)
        self.assertNotIn("\ntrane_bus:", TELEMETRY)
        self.assertNotIn("!extend hvac_can", TELEMETRY)
        self.assertNotIn("send_data(", without_yaml_comments(TELEMETRY))

    def test_parent_owns_devices_can_and_json_hook(self):
        self.assertIn("name: ${device_name}", HA)
        self.assertIn("id: dev_thermostat", HA)
        self.assertIn("id: dev_sc360", HA)
        self.assertIn("id: dev_air_handler", HA)
        self.assertIn("id: dev_heat_pump", HA)
        self.assertIn("id: dev_discovery", HA)
        self.assertIn("id: hvac_can", HA)
        self.assertIn("id: trane_link", HA)
        self.assertIn("on_json:", HA)
        self.assertIn("TRANE_JSON", HA)
        self.assertIn("can_id_mask: 0x000", HA)

    def test_package_is_read_only(self):
        self.assertNotIn("trane_bus.set_tx_enabled", TELEMETRY)
        self.assertNotIn("trane_bus.set_mode", TELEMETRY)
        self.assertNotIn("trane_bus.set_setpoints", TELEMETRY)
        self.assertNotIn("trane_bus.get_profile", TELEMETRY)
        self.assertNotIn("send_data(", without_yaml_comments(HA))

    def test_homeassistant_uses_std_finite_for_idf_gcc14(self):
        self.assertNotIn("if (isfinite(", without_yaml_comments(HA))
        self.assertIn("std::isfinite(", HA)

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
        self.assertIn("trane_last_unknown_frame", HA)
        self.assertIn("trane_490_raw", HA)

    def test_expected_target_only_features_remain_discovery_not_fake_values(self):
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

    def test_283_candidate_is_converted_from_historical_celsius_capture(self):
        self.assertIn("a * 9.0f / 5.0f + 32.0f", HA)
        self.assertIn("b * 9.0f / 5.0f + 32.0f", HA)


if __name__ == "__main__":
    unittest.main()
