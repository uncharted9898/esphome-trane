import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LISTEN = (ROOT / "waveshare-trane-listenonly.yaml").read_text()
COMMISSION = (ROOT / "waveshare-trane-commissioning.yaml").read_text()
HOMEASSISTANT = (ROOT / "waveshare-trane-homeassistant.yaml").read_text()
FULL = (ROOT / "waveshare-trane-full.yaml").read_text()
BUS_CPP = (ROOT / "components/trane_bus/trane_bus.cpp").read_text()
BUS_H = (ROOT / "components/trane_bus/trane_bus.h").read_text()
BUS_PY = (ROOT / "components/trane_bus/__init__.py").read_text()


class WaveshareSafetyContractTests(unittest.TestCase):
    def test_reference_can_pins_and_rate(self):
        for config in (LISTEN, FULL, HOMEASSISTANT):
            self.assertIn("tx_pin: GPIO17", config)
            self.assertIn("rx_pin: GPIO18", config)
            self.assertNotIn("tx_pin: GPIO15", config)
            self.assertNotIn("rx_pin: GPIO16", config)
            self.assertIn("bit_rate: 50kbps", config)

    def test_homeassistant_profile_targets_s3_and_has_required_can_id(self):
        self.assertIn("variant: esp32s3", HOMEASSISTANT)
        self.assertIn("flash_size: 16MB", HOMEASSISTANT)
        self.assertIn("can_id: 0x7FF", HOMEASSISTANT)
        self.assertIn("mode: NORMAL", HOMEASSISTANT)
        self.assertIn("tx_enabled: false", HOMEASSISTANT)
        self.assertIn("raw_json_enabled: false", HOMEASSISTANT)
        self.assertIn("github://uncharted9898/esphome-trane@dev", HOMEASSISTANT)

    def test_commissioning_uses_real_full_stack_with_normal_can(self):
        self.assertIn("full_stack: !include waveshare-trane-full.yaml", COMMISSION)
        self.assertIn("mode: NORMAL", COMMISSION)
        self.assertIn("tx_enabled: false", COMMISSION)
        self.assertIn("raw_json_enabled: false", COMMISSION)
        self.assertIn("switch: !remove", COMMISSION)
        self.assertIn("button: !remove", COMMISSION)
        self.assertNotIn("trane_bus.set_tx_enabled", COMMISSION)
        self.assertNotIn("trane_bus.set_mode", COMMISSION)
        self.assertNotIn("trane_bus.set_setpoints", COMMISSION)
        self.assertNotIn("trane_bus.get_profile", COMMISSION)

    def test_commissioning_has_continuous_recorder_with_bounded_ram(self):
        self.assertIn("capture_capacity: 2048", COMMISSION)
        self.assertIn("capture_enabled: true", COMMISSION)
        self.assertIn("can_id_mask: 0x000", COMMISSION)
        self.assertIn("can_id_mask: 0x00000000", COMMISSION)
        self.assertIn("TRANE_CAN_LIVE,S", COMMISSION)
        self.assertIn("TRANE_CAN_LIVE,E", COMMISSION)
        self.assertIn("TRANE_JSON", COMMISSION)
        self.assertIn("TRANE_RECORDER_READY", COMMISSION)
        self.assertGreaterEqual(COMMISSION.count("reboot_timeout: 0s"), 2)
        self.assertIn("power_save_mode: none", COMMISSION)
        self.assertIn("rx_queue_len: 128", COMMISSION)

    def test_passive_image_is_hardware_listen_only(self):
        self.assertIn("mode: LISTENONLY", LISTEN)
        self.assertIn("tx_queue_len: 0", LISTEN)
        self.assertIn("tx_enabled: false", LISTEN)
        self.assertIn("raw_json_enabled: false", LISTEN)
        self.assertNotIn("trane_bus.set_tx_enabled", LISTEN)
        self.assertNotIn("trane_bus.set_mode", LISTEN)
        self.assertNotIn("trane_bus.set_setpoints", LISTEN)
        self.assertNotIn("trane_bus.get_profile", LISTEN)

    def test_passive_image_has_bounded_freeze_and_dump_capture(self):
        self.assertIn("capture_capacity: 2048", LISTEN)
        self.assertIn("capture_enabled: true", LISTEN)
        self.assertIn("Freeze CAN Capture", LISTEN)
        self.assertIn("Dump Frozen CAN Capture", LISTEN)
        self.assertIn("Clear And Resume CAN Capture", LISTEN)
        self.assertIn("capture_capacity_", BUS_H)
        self.assertIn("capture_overwrites_", BUS_H)
        self.assertIn("TRANE_CAPTURE_BEGIN", BUS_CPP)
        self.assertIn("TRANE_CAPTURE_END", BUS_CPP)

    def test_capture_schema_prevents_oversized_ram_ring(self):
        self.assertIn("max=4096", BUS_PY)
        for config in (LISTEN, COMMISSION, HOMEASSISTANT):
            self.assertNotIn("capture_capacity: 16384", config)
            self.assertIn("capture_capacity: 2048", config)

    def test_passive_image_continuously_logs_all_can_frames(self):
        self.assertIn("can_id_mask: 0x000", LISTEN)
        self.assertIn("can_id_mask: 0x00000000", LISTEN)
        self.assertIn("TRANE_CAN_LIVE,S", LISTEN)
        self.assertIn("TRANE_CAN_LIVE,E", LISTEN)
        self.assertIn("TRANE_RECORDER_READY", LISTEN)
        self.assertIn("TRANE_JSON", LISTEN)

    def test_passive_image_does_not_reboot_for_network_loss(self):
        self.assertGreaterEqual(LISTEN.count("reboot_timeout: 0s"), 2)
        self.assertIn("power_save_mode: none", LISTEN)
        self.assertIn("rx_queue_len: 128", LISTEN)

    def test_passive_image_exposes_discovery_counters(self):
        self.assertIn("Total CAN Frames Seen", LISTEN)
        self.assertIn("Known Trane Frames Seen", LISTEN)
        self.assertIn("Unclassified CAN Frames Seen", LISTEN)
        self.assertIn("Segmented JSON Messages", LISTEN)
        self.assertIn("RX Transport Errors", LISTEN)
        self.assertIn("get_rx_frames()", LISTEN)
        self.assertIn("get_trane_frames()", LISTEN)
        self.assertIn("get_rx_json_messages()", LISTEN)
        self.assertIn("get_rx_transport_errors()", LISTEN)

    def test_full_profile_starts_control_disarmed(self):
        self.assertIn("tx_enabled: false", FULL)
        self.assertIn("raw_json_enabled: false", FULL)
        self.assertIn("restore_mode: ALWAYS_OFF", FULL)
        self.assertIn("has_recent_trane_activity", FULL)
        self.assertIn("trane_bus_id: trane_link", FULL)

    def test_full_profile_removes_legacy_raw_surfaces(self):
        self.assertIn("on_boot: !remove", FULL)
        self.assertIn("services: !remove", FULL)

    def test_transport_requires_recent_sc360_and_serializes_writes(self):
        self.assertIn("require_sc360_before_tx_ && !has_recent_trane_activity()", BUS_CPP)
        self.assertIn("if (pending_ack_)", BUS_CPP)
        self.assertIn("pending_ack_since_ms_", BUS_CPP)
        self.assertIn("ack_timeouts_", BUS_CPP)

    def test_segmented_json_is_reassembled_in_source(self):
        self.assertIn("feed_segmented_json_", BUS_CPP)
        self.assertIn("can_id == 0x641 || can_id == 0x649", BUS_CPP)
        self.assertIn("json_trigger_.trigger(json, can_id)", BUS_CPP)
        self.assertIn('CONF_ON_JSON = "on_json"', BUS_PY)

    def test_raw_json_is_opt_in_and_typed_actions_exist(self):
        self.assertIn("cv.Optional(CONF_RAW_JSON_ENABLED, default=False)", BUS_PY)
        self.assertIn('"trane_bus.set_mode"', BUS_PY)
        self.assertIn('"trane_bus.set_setpoints"', BUS_PY)
        self.assertIn('"trane_bus.get_profile"', BUS_PY)

    def test_setpoint_validation_bounds_both_targets(self):
        setpoints = BUS_CPP.split("bool TraneBus::set_setpoints", 1)[1].split(
            "bool TraneBus::request_profile", 1
        )[0]
        self.assertIn("heat_f < setpoint_min_f_", setpoints)
        self.assertIn("heat_f > setpoint_max_f_", setpoints)
        self.assertIn("cool_f < setpoint_min_f_", setpoints)
        self.assertIn("cool_f > setpoint_max_f_", setpoints)
        self.assertIn("cool_f - heat_f < min_deadband_f_", setpoints)

    def test_supported_mode_encoder_does_not_fall_through_to_off(self):
        mode = BUS_CPP.split("bool TraneBus::set_system_mode", 1)[1].split(
            "bool TraneBus::set_setpoints", 1
        )[0]
        self.assertIn('mode == "heat"', mode)
        self.assertIn('mode == "cool"', mode)
        self.assertIn('mode == "off"', mode)
        self.assertIn("Refusing unsupported Trane system mode", mode)


if __name__ == "__main__":
    unittest.main()
