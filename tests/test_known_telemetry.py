import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HA = (ROOT / "waveshare-trane-homeassistant.yaml").read_text()
TELEMETRY = (ROOT / "waveshare-trane-known-telemetry-v2.yaml").read_text()
EXTRA = (ROOT / "waveshare-trane-known-telemetry-extra.yaml").read_text()


def without_yaml_comments(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


class KnownTelemetryContractTests(unittest.TestCase):
    def test_homeassistant_loads_package_safe_known_telemetry(self):
        self.assertIn("packages:", HA)
        self.assertGreaterEqual(
            HA.count("url: https://github.com/uncharted9898/esphome-trane"), 2
        )
        self.assertGreaterEqual(HA.count("ref: dev"), 2)
        self.assertGreaterEqual(HA.count("refresh: always"), 3)
        self.assertIn("- waveshare-trane-known-telemetry-v2.yaml", HA)
        self.assertIn("- waveshare-trane-known-telemetry-extra.yaml", HA)

    def test_packages_own_no_hardware_or_esphome_root(self):
        for package in (TELEMETRY, EXTRA):
            self.assertNotIn("\nesphome:", package)
            self.assertNotIn("\ncanbus:", package)
            self.assertNotIn("\ntrane_bus:", package)
            self.assertNotIn("!extend hvac_can", package)
            self.assertNotIn("send_data(", without_yaml_comments(package))

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
        for package in (TELEMETRY, EXTRA):
            self.assertNotIn("trane_bus.set_tx_enabled", package)
            self.assertNotIn("trane_bus.set_mode", package)
            self.assertNotIn("trane_bus.set_setpoints", package)
            self.assertNotIn("trane_bus.get_profile", package)
        self.assertNotIn("send_data(", without_yaml_comments(HA))

    def test_homeassistant_uses_std_finite_for_idf_gcc14(self):
        self.assertNotIn("if (isfinite(", without_yaml_comments(HA))
        self.assertIn("std::isfinite(", HA)

    def test_known_system_entities_are_exposed(self):
        combined = TELEMETRY + EXTRA
        for name in (
            "Room Temperature",
            "Heat Setpoint",
            "Cool Setpoint",
            "Indoor Humidity",
            "System Mode",
            "System State Raw",
            "System Demand Stage",
            "SystemOpStatus D Numeric Candidate",
            "Indoor Blower Speed",
            "Compressor Speed",
            "Compressor Demand",
            "Outdoor Air Temperature",
            "Outdoor Fault Code",
            "Active Alarm 1",
            "Active Alarm 2 Level",
            "Unit Firmware",
            "Thermostat Display Name",
            "Outdoor Temperature User Offset",
        ):
            self.assertIn(f'name: "{name}"', combined)

    def test_restored_profiles_are_actually_published(self):
        for token in (
            "id(trane_system_state).publish_state",
            "id(trane_system_status_d_numeric).publish_state",
            "id(trane_outdoor_active).publish_state",
            "id(trane_alarm_id_1).publish_state",
            "id(trane_alarm_level_2).publish_state",
            "id(trane_preset_home_heat).publish_state",
            "id(trane_preset_away_cool).publish_state",
            "id(trane_preset_sleep_heat).publish_state",
            "id(trane_zone_name_1).publish_state",
            "id(trane_zone_name_6).publish_state",
            "id(trane_thermostat_display_name).publish_state",
            "id(trane_timezone_local_offset).publish_state",
            "id(trane_weather_country).publish_state",
            "id(trane_weather_region).publish_state",
            "id(trane_od_temp_user_offset).publish_state",
        ):
            self.assertIn(token, HA)

    def test_zones_two_through_six_setpoints_are_restored_disabled(self):
        for zone in range(2, 7):
            self.assertIn(f'id: trane_heat_setpoint_z{zone}', EXTRA)
            self.assertIn(f'id: trane_cool_setpoint_z{zone}', EXTRA)
            self.assertIn(f'id(trane_heat_setpoint_z{zone}).publish_state', HA)
            self.assertIn(f'id(trane_cool_setpoint_z{zone}).publish_state', HA)
        self.assertGreaterEqual(EXTRA.count("disabled_by_default: true"), 10)

    def test_private_transport_raw_surfaces_are_exposed(self):
        for name in ("Last 0x5C1 Raw", "Last 0x5C9 Raw"):
            self.assertIn(f'name: "{name}"', EXTRA)
        self.assertIn("can_id: 0x5C1", HA)
        self.assertIn("can_id: 0x5C9", HA)
        self.assertIn("id(trane_last_5c1_raw).publish_state", HA)
        self.assertIn("id(trane_last_5c9_raw).publish_state", HA)

    def test_unresolved_outdoor_ids_remain_discoverable(self):
        # Only decoded outdoor IDs are excluded from the generic unknown-frame
        # path. These unresolved IDs must not be swallowed merely because they
        # live inside the broad 0x380-0x38F family.
        switch_block = HA.split("switch (can_id)", 1)[1].split("default:", 1)[0]
        for unresolved in (
            "0x382", "0x384", "0x385", "0x388", "0x389", "0x38A",
            "0x38B", "0x38C", "0x38D", "0x38E",
        ):
            self.assertNotIn(f"case {unresolved}", switch_block)

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
        combined = TELEMETRY + EXTRA
        for name in (
            "Last JSON 0x649",
            "Last JSON 0x641",
            "Last 0x490 Raw",
            "Last 0x5C1 Raw",
            "Last 0x5C9 Raw",
            "Unclassified CAN Frames",
            "Last Unknown CAN ID",
            "Last Unknown CAN Frame",
        ):
            self.assertIn(f'name: "{name}"', combined)
        self.assertIn("trane_last_unknown_frame", HA)
        self.assertIn("trane_490_raw", HA)

    def test_expected_target_only_features_remain_discovery_not_fake_values(self):
        combined = TELEMETRY + EXTRA
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
            self.assertNotIn(f"id: trane_{fake_id}", combined)

    def test_283_candidate_is_converted_from_historical_celsius_capture(self):
        self.assertIn("a * 9.0f / 5.0f + 32.0f", HA)
        self.assertIn("b * 9.0f / 5.0f + 32.0f", HA)


if __name__ == "__main__":
    unittest.main()
