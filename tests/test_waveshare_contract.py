import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LISTEN = (ROOT / "waveshare-trane-listenonly.yaml").read_text()
FULL = (ROOT / "waveshare-trane-full.yaml").read_text()
BUS_CPP = (ROOT / "components/trane_bus/trane_bus.cpp").read_text()
BUS_PY = (ROOT / "components/trane_bus/__init__.py").read_text()


class WaveshareSafetyContractTests(unittest.TestCase):
    def test_reference_can_pins_and_rate(self):
        for config in (LISTEN, FULL):
            self.assertIn("tx_pin: GPIO15", config)
            self.assertIn("rx_pin: GPIO16", config)
            self.assertIn("bit_rate: 50kbps", config)

    def test_passive_image_is_hardware_listen_only(self):
        self.assertIn("mode: LISTENONLY", LISTEN)
        self.assertIn("tx_queue_len: 0", LISTEN)
        self.assertIn("tx_enabled: false", LISTEN)
        self.assertIn("raw_json_enabled: false", LISTEN)

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

    def test_raw_json_is_opt_in_and_typed_actions_exist(self):
        self.assertRegex(BUS_PY, r"CONF_RAW_JSON_ENABLED, default=False")
        self.assertIn('"trane_bus.set_mode"', BUS_PY)
        self.assertIn('"trane_bus.set_setpoints"', BUS_PY)
        self.assertIn('"trane_bus.get_profile"', BUS_PY)

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
