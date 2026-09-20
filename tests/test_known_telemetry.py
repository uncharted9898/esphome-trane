import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HA = (ROOT / "waveshare-trane-homeassistant.yaml").read_text()
TELEMETRY = (ROOT / "waveshare-trane-known-telemetry-v2.yaml").read_text()
EXTRA_AGGREGATOR = (ROOT / "waveshare-trane-known-telemetry-extra.yaml").read_text()
EXTRA_BASE = (ROOT / "waveshare-trane-known-telemetry-extra-base.yaml").read_text()
TARGET_DISCOVERY = (ROOT / "waveshare-trane-target-discovery.yaml").read_text()
# Semantic assertions should see the composed package exactly as ESPHome does.
EXTRA = EXTRA_BASE + "\n" + TARGET_DISCOVERY
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
        self.assertIn("waveshare-trane-known-telemetry-extra-base.yaml", EXTRA_AGGREGATOR)
        self.assertIn("waveshare-trane-target-discovery.yaml", EXTRA_AGGREGATOR)

    def test_normal_ha_profile_excludes_raw_can_package(self):
        self.assertNotIn("waveshare-trane-target-raw.yaml", EXTRA_AGGREGATOR)
        self.assertIn("waveshare-trane-known-telemetry-extra-base.yaml", EXTRA_AGGREGATOR)
        self.assertIn("waveshare-trane-target-discovery.yaml", EXTRA_AGGREGATOR)

    def test_candidate_and_raw_entities_default_to_disabled(self):
        for package in (TELEMETRY, EXTRA_BASE, TARGET_DISCOVERY):
            blocks = package.split("  - platform: template")
            for block in blocks:
                if 'entity_category: diagnostic' not in block:
                    continue
                if 'name: "' not in block:
                    continue
                if "Candidate" in block or " Raw" in block:
                    self.assertIn("disabled_by_default: true", block)

    def test_structured_data_status_is_visible(self):
        self.assertIn('name: "Structured Data Status"', HA)
        self.assertIn('name: "Profile Coverage"', HA)
        self.assertIn("get_json_snapshot_count()", HA)
        self.assertIn("get_last_json_age_seconds()", HA)
        for root in (
            "SystemOpStatus",
            "IndoorStatus",
            "ZoneStatus",
            "SpOverride",
            "UnitID",
            "VersionDetails",
            "IndoorSettings",
            "SystemSettings",
        ):
            self.assertIn(f'"{root}"', HA)

    def test_only_unknown_traffic_health_counter_remains_visible(self):
        idx = TELEMETRY.index("id: trane_unknown_frames")
        start = TELEMETRY.rfind("  - platform: template", 0, idx)
        end = TELEMETRY.find("  - platform:", idx + 5)
        block = TELEMETRY[start:end if end >= 0 else len(TELEMETRY)]
        self.assertNotIn("disabled_by_default: true", block)

    def test_packages_own_no_hardware_or_esphome_root(self):
        for package in (TELEMETRY, EXTRA_AGGREGATOR, EXTRA_BASE, TARGET_DISCOVERY):
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
        for package in (TELEMETRY, EXTRA_AGGREGATOR, EXTRA_BASE, TARGET_DISCOVERY):
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
            "System Demand Percent Candidate",
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

    def test_promoted_live_entities_have_clean_names(self):
        combined = TELEMETRY + EXTRA
        for name in (
            "Return Air Temperature",
            "Supply Air Temperature",
            "Actual Airflow",
            "Total Static Pressure",
            "Blower Motor Current",
            "Blower Motor Speed",
            "Blower Power",
            "Indoor Gas Temperature",
            "Indoor Evaporator Temperature",
            "Indoor Superheat",
            "Outdoor Air Temperature",
            "Outdoor Coil Temperature",
            "Liquid Line Temperature",
            "Compressor Discharge Temperature",
            "Actual Compressor Speed",
            "Compressor Target Speed",
            "Compressor Power",
            "Line Voltage",
            "Input Current",
            "Input Power",
            "Drive DC Voltage",
            "Outdoor Fan Speed",
        ):
            self.assertIn(f'name: "{name}"', combined)

    def test_system_status_d_is_demand_percent_candidate(self):
        self.assertIn('name: "System Demand Percent Candidate"', EXTRA_BASE)
        self.assertIn('unit_of_measurement: "%"', EXTRA_BASE)
        self.assertNotIn('name: "SystemOpStatus D Numeric Candidate"', EXTRA_BASE)

    def test_friendly_room_temp_uses_live_0x490_source(self):
        self.assertIn('name: "Room Temperature"', TELEMETRY)
        self.assertIn("get_last_float_le_or_nan(0x490, 0)", TELEMETRY)
        self.assertIn("value <= -90.0f", TELEMETRY)
        self.assertNotIn("id(trane_room_temp).publish_state(f);", HA)

    def test_system_status_e_no_longer_fakes_outdoor_temp_or_humidity(self):
        self.assertIn('name: "System Compressor Speed Ceiling Candidate"', TELEMETRY)
        self.assertNotIn('name: "SC360 Outdoor Temperature"', TELEMETRY)
        self.assertIn('name: "Indoor Humidity"', TELEMETRY)
        self.assertIn("get_last_byte_or_nan(0x490, 4)", TELEMETRY)
        self.assertIn("value > 100.0f", TELEMETRY)
        self.assertNotIn("id(trane_indoor_humidity).publish_state(f);", HA)
        self.assertIn("id(trane_sc360_outdoor_temp).publish_state(f);", HA)

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

        # Cold-boot CANopen traffic is deliberately kept in the public target
        # classifier so HA reports only genuinely novel IDs.
        for token in (
            "can_id == 0x000",
            "can_id == 0x081",
            "can_id == 0x083",
            "can_id >= 0x200 && can_id <= 0x210",
            "can_id == 0x496",
            "can_id == 0x540",
            "can_id == 0x560",
            "can_id == 0x5A1",
            "can_id == 0x621",
            "can_id == 0x7E4",
        ):
            self.assertIn(token, BUS_H)

    def test_601_segmented_json_is_receive_only_and_reassembled(self):
        self.assertIn("SegmentedRxState rx_601_{};", BUS_H)
        for token in (
            "case 0x601:",
            "case 0x621:",
            "case 0x641:",
            "case 0x649:",
            "sdo_state = &rx_601_;",
            "sdo_state = &rx_621_;",
            "sdo_state = &rx_641_;",
            "sdo_state = &rx_649_;",
            "feed_sdo_json_response_(*sdo_state, data);",
            "feed_segmented_json_(*sdo_state, data, complete)",
            "0x300A:00",
        ):
            self.assertIn(token, BUS_CPP)
        self.assertNotIn("command_can_id_{0x601}", BUS_H)

    def test_target_correlated_indoor_channels_are_exposed(self):
        combined = TELEMETRY + EXTRA
        for label in (
            "Actual Airflow",
            "0x281 Bytes 6-7 Composite Raw",
            "0x281 Blower Demand Candidate",
            "0x281 Blower Active Flag Candidate",
            "Return Air Temperature",
            "Supply Air Temperature",
            "Total Static Pressure",
            "Blower Power",
            "Indoor Gas Temperature",
            "Indoor Evaporator Temperature",
            "Indoor Superheat",
            "0x200 Indoor EEV Position Candidate",
            "0x490 Zone 1 Room Temperature",
            "0x490 Zone 1 Humidity Byte Raw",
            "Blower Motor Current",
            "0x318 Blower Airflow Feedback Candidate",
            "Blower Motor Speed",
        ):
            self.assertIn(f'name: "{label}"', combined)
        self.assertIn('unit_of_measurement: "cfm"', EXTRA)
        self.assertIn('unit_of_measurement: "inWC"', EXTRA)
        self.assertIn('unit_of_measurement: "rpm"', EXTRA)
        self.assertIn('unit_of_measurement: "W"', EXTRA)
        self.assertIn('unit_of_measurement: "A"', TARGET_DISCOVERY)
        self.assertIn("return gas - liquid;", EXTRA)

        # The high-load capture invalidated the earlier assumption that
        # 0x383.float[1] was line voltage, so the derived V*I*PF entity must
        # remain absent until an actual line-voltage source is qualified.
        self.assertNotIn("Blower V I PF Calculated Power", TARGET_DISCOVERY)
        self.assertNotIn("return volts * amps * pf;", TARGET_DISCOVERY)

    def test_0x490_invalid_humidity_is_not_published_as_humidity(self):
        self.assertIn('name: "0x490 Zone 1 Humidity Byte Raw"', EXTRA_BASE)
        self.assertNotIn('name: "0x490 Zone 1 Relative Humidity"', EXTRA_BASE)
        self.assertIn("value <= -90.0f", EXTRA_BASE)
        self.assertIn("value > 130.0f", EXTRA_BASE)

    def test_high_load_requalified_core_outdoor_channels_are_exposed(self):
        # Core entities should no longer claim the meanings disproved by the
        # later high-load operating point.
        for label in (
            "Outdoor Coil Temperature",
            "Compressor Discharge Temperature",
            "Line Voltage",
            "0x387 Compressor Speed Reference Limit Candidate",
        ):
            self.assertIn(f'name: "{label}"', TELEMETRY)

        for stale in (
            'name: "0x381 Suction Temperature"',
            'name: "0x386 Vapor Saturation Temperature Candidate"',
            'name: "0x38F Liquid Pressure"',
        ):
            self.assertNotIn(stale, TELEMETRY)

        # The satisfied-state capture held 0x387.f0 at 55.0 while the actual
        # equipment was idle: compressor demand 0%, compressor power/current
        # zero and outdoor fan stopped. It cannot be promoted as runtime speed.
        self.assertNotIn('name: "0x387 Actual Compressor Speed"', TELEMETRY)
        self.assertNotIn('name: "0x387 Compressor Speed RPM"', EXTRA)
        self.assertNotIn("return rps * 60.0f;", EXTRA)

        # The compound/raw extension still exposes useful channels while its
        # remaining candidates are requalified against synchronized Technician
        # data in a follow-up capture.
        for label in (
            "Drive DC Voltage",
            "Outdoor Fan Speed",
            "0x383 Liquid Pressure Candidate",
            "0x381 Pressure Family Raw",
            "Liquid Line Temperature",
            "Compressor Power",
            "Compressor Target Speed",
            "Input Current",
            "Input Power",
            "0x460 Temperature Candidate",
        ):
            self.assertIn(f'name: "{label}"', EXTRA)

    def test_active_load_requalifies_0x384_as_compressor_speed(self):
        self.assertIn('name: "Actual Compressor Speed"', EXTRA_BASE)
        self.assertNotIn('name: "0x384 Compressor Target Max Speed Candidate"', EXTRA_BASE)
        self.assertIn('name: "Compressor Target Speed"', EXTRA_BASE)
        self.assertIn('name: "0x3D0 Compressor Target Minimum Speed Candidate"', TARGET_DISCOVERY)

    def test_blower_airflow_request_feedback_pair_is_exposed(self):
        combined = TELEMETRY + EXTRA
        self.assertIn('name: "0x200 Blower Airflow Request Candidate"', combined)
        self.assertIn('name: "0x318 Blower Airflow Feedback Candidate"', combined)
        self.assertNotIn('name: "0x200 U16 1 Candidate"', combined)
        self.assertNotIn('name: "0x318 Airflow Candidate"', combined)

    def test_0x280_is_upstream_compressor_speed_request_candidate(self):
        self.assertIn('name: "0x280 Compressor Speed Request Candidate"', EXTRA_BASE)
        self.assertNotIn('name: "0x280 Float 1 Candidate"', EXTRA_BASE)

    def test_active_modulation_refines_blower_and_speed_reference_fields(self):
        self.assertIn('name: "0x281 Blower Demand Candidate"', EXTRA_BASE)
        self.assertIn('name: "0x281 Blower Active Flag Candidate"', EXTRA_BASE)
        self.assertIn('name: "0x281 Bytes 6-7 Composite Raw"', EXTRA_BASE)
        self.assertIn('name: "Actual Compressor Speed"', EXTRA_BASE)
        self.assertIn('name: "0x387 Compressor Speed Reference Limit Candidate"', TELEMETRY)
        self.assertNotIn('name: "0x281 Tail Word Raw"', EXTRA_BASE)
        self.assertNotIn('name: "0x281 Byte 6 Candidate"', EXTRA_BASE)
        self.assertNotIn('name: "0x281 Byte 7 State Candidate"', EXTRA_BASE)

    def test_structured_json_freshness_diagnostics_are_exposed(self):
        for label in (
            "Last Structured JSON Age",
            "SystemOpStatus Snapshot Age",
            "IndoorStatus Snapshot Age",
            "SpOverride Snapshot Age",
        ):
            self.assertIn(f'name: "{label}"', TARGET_DISCOVERY)
        self.assertIn("get_last_json_age_seconds()", BUS_H)
        self.assertIn("get_json_snapshot_age_seconds", BUS_H)
        self.assertIn("updated_ms{0}", BUS_H)
        self.assertIn("last_json_ms_ = millis();", BUS_CPP)
        self.assertIn("slot->updated_ms = millis();", BUS_CPP)

    def test_canopen_diagnostics_are_exposed_without_physical_role_guessing(self):
        for label in (
            "CANopen Node 1 State",
            "CANopen Node 3 State",
            "Last CANopen NMT 0x000 Raw",
            "Last CANopen EMCY Node 1 0x081 Raw",
            "Last CANopen LSS Server 0x7E4 Raw",
            "Last CANopen LSS Manager 0x7E5 Raw",
            "0x53E Active Link Nodes Candidate",
            "Debug IDBLE State",
            "Debug ODBLE State",
        ):
            self.assertIn(f'name: "{label}"', TARGET_DISCOVERY)

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
            "0x281 Blower Speed",
            "0x280 Blower Power-Factor-Like Candidate",
            "0x382 OD Coil Temperature Candidate",
            "0x383 Line Voltage",
            "0x385 Outdoor EEV Position",
            "0x460 Liquid Saturation Temperature Candidate",
        ):
            self.assertNotIn(f'name: "{label}"', combined)

    def test_curated_discovery_surfaces_exist(self):
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
