import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HA = (ROOT / "waveshare-trane-homeassistant.yaml").read_text()
TELEMETRY = (ROOT / "waveshare-trane-known-telemetry-v2.yaml").read_text()
EXTRA = (ROOT / "waveshare-trane-known-telemetry-extra.yaml").read_text()
BUS_H = (ROOT / "components" / "trane_bus" / "trane_bus.h").read_text()
BUS_CPP = (ROOT / "components" / "trane_bus" / "trane_bus.cpp").read_text()


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

    def test_target_classifier_covers_observed_link_families(self):
        self.assertIn("bool is_known_trane_id(uint32_t can_id) const", BUS_H)
        self.assertIn("if (!id(trane_link).is_known_trane_id(can_id))", HA)
        self.assertNotIn("switch (can_id)", HA)
        for token in (
            "can_id >= 0x250 && can_id <= 0x252",
            "can_id >= 0x260 && can_id <= 0x262",
            "can_id >= 0x280 && can_id <= 0x285",
            "can_id >= 0x2D0 && can_id <= 0x2D2",
            "can_id >= 0x380 && can_id <= 0x38F",
            "can_id >= 0x490 && can_id <= 0x495",
            "can_id >= 0x4B0 && can_id <= 0x4B4",
            "can_id >= 0x4C0 && can_id <= 0x4C5",
            "can_id >= 0x701 && can_id <= 0x705",
            "case 0x200:",
            "case 0x300:",
            "case 0x310:",
            "case 0x318:",
            "case 0x320:",
            "case 0x3D0:",
            "case 0x3E0:",
            "case 0x460:",
            "case 0x53D:",
            "case 0x53E:",
            "case 0x581:",
            "case 0x601:",
            "case 0x7E5:",
        ):
            self.assertIn(token, BUS_CPP)

    def test_601_segmented_json_is_receive_only_and_reassembled(self):
        self.assertIn("SegmentedRxState rx_601_{};", BUS_H)
        self.assertIn("can_id == 0x601 || can_id == 0x641 || can_id == 0x649", BUS_CPP)
        self.assertIn("state = &rx_601_;", BUS_CPP)
        self.assertIn("0x601: C2 0A 30 00 25 00 00 00", BUS_CPP)
        self.assertNotIn("command_can_id_{0x601}", BUS_H)

    def test_target_correlated_indoor_channels_are_exposed(self):
        combined = TELEMETRY + EXTRA
        for label in (
            "0x281 Actual Airflow",
            "0x281 Blower Speed",
            "0x308 Return Air Temperature",
            "0x308 Supply Air Temperature",
            "0x310 Total Static Pressure",
            "0x320 Blower Power",
            "0x300 ID Gas Temperature Candidate",
            "0x300 ID Evap Liquid Temperature Candidate",
            "0x300 ID Superheat Candidate",
            "0x200 Indoor EEV Position Candidate",
            "0x490 Zone 1 Room Temperature",
            "0x490 Zone 1 Relative Humidity",
        ):
            self.assertIn(f'name: "{label}"', combined)
        self.assertIn('unit_of_measurement: "cfm"', EXTRA)
        self.assertIn('unit_of_measurement: "inWC"', EXTRA)
        self.assertIn('unit_of_measurement: "rpm"', EXTRA)
        self.assertIn('unit_of_measurement: "W"', EXTRA)
        self.assertIn("return gas - liquid;", EXTRA)

    def test_target_correlated_outdoor_channels_are_exposed(self):
        combined = TELEMETRY + EXTRA
        for label in (
            "0x381 Suction Pressure",
            "0x38F Liquid Pressure",
            "0x383 Line Voltage",
            "0x384 Drive DC Voltage",
            "0x384 Outdoor Fan Speed",
            "0x387 Actual Compressor Speed",
            "0x387 Compressor Speed RPM",
            "0x385 Outdoor EEV Position",
            "0x385 Compressor Target Speed Candidate",
            "0x389 Input AC Current Candidate",
            "0x38C Input Power",
            "0x460 Liquid Saturation Temperature Candidate",
        ):
            self.assertIn(f'name: "{label}"', combined)

    def test_disproven_old_labels_do_not_regress(self):
        combined = TELEMETRY + EXTRA
        for label in (
            "0x283 Float 1 Candidate ET GT",
            "0x283 Float 2 Candidate ET GT",
            "0x310 Float 1 Candidate Return Static",
            "0x318 Float 1 Candidate External Static",
            "0x320 Float 1 Candidate Motor Power",
            "0x387 Float 1 Temperature Candidate",
            "0x38F Refrigerant Pressure Candidate",
            "0x430 Temperature Candidate",
            "0x450 Temperature Candidate",
            "0x385 Float 2 Candidate EEV Position",
            "0x281 U16 1 Candidate Target Airflow",
        ):
            self.assertNotIn(f'name: "{label}"', combined)

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

    def test_283_raw_temperatures_retain_historical_celsius_conversion(self):
        self.assertIn("a * 9.0f / 5.0f + 32.0f", HA)
        self.assertIn("b * 9.0f / 5.0f + 32.0f", HA)


if __name__ == "__main__":
    unittest.main()
