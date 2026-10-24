import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPP = (ROOT / "components/trane_hvac/trane_climate.cpp").read_text()


class ClimateSafetyContractTests(unittest.TestCase):
    def test_only_verified_modes_are_advertised(self):
        block = re.search(r"set_supported_modes\(\{(?P<body>.*?)\}\);", CPP, re.S)
        self.assertIsNotNone(block)
        body = block.group("body")
        self.assertIn("CLIMATE_MODE_OFF", body)
        self.assertIn("CLIMATE_MODE_HEAT", body)
        self.assertIn("CLIMATE_MODE_COOL", body)
        self.assertNotIn("CLIMATE_MODE_HEAT_COOL", body)
        self.assertNotIn("CLIMATE_MODE_FAN_ONLY", body)

    def test_control_path_is_non_optimistic(self):
        control = CPP.split("void TraneClimate::control", 1)[1]
        self.assertNotIn("this->mode = requested_mode", control)
        self.assertNotIn("this->target_temperature_low = hsp_c", control)
        self.assertNotIn("this->target_temperature_high = csp_c", control)
        self.assertIn("waiting for SC360 echo", control)

    def test_unsupported_modes_are_rejected_before_trigger(self):
        control = CPP.split("void TraneClimate::control", 1)[1]
        self.assertRegex(control, r"if \(!is_supported_control_mode_\(requested_mode\)\)")
        self.assertIn("mode_trigger_.trigger(requested_mode);", control)

    def test_presets_are_not_advertised(self):
        traits = CPP.split("climate::ClimateTraits TraneClimate::traits", 1)[1].split(
            "void TraneClimate::setup", 1
        )[0]
        self.assertNotIn("set_supported_presets", traits)


if __name__ == "__main__":
    unittest.main()
