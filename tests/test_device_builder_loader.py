import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOADER = (ROOT / "device-builder-dev.example.yaml").read_text()


class DeviceBuilderLoaderContractTests(unittest.TestCase):
    def test_dev_loader_refreshes_outer_package(self):
        self.assertIn("packages:", LOADER)
        self.assertIn("url: https://github.com/uncharted9898/esphome-trane", LOADER)
        self.assertIn("ref: dev", LOADER)
        self.assertIn("refresh: always", LOADER)
        self.assertIn("- waveshare-trane-homeassistant.yaml", LOADER)

    def test_dev_loader_does_not_duplicate_runtime_ownership(self):
        # The local loader should remain a thin cache boundary. Hardware,
        # entities, CAN and transport ownership belong to the fetched profile.
        for root_key in ("esphome:", "canbus:", "trane_bus:", "sensor:", "text_sensor:"):
            self.assertNotIn(f"\n{root_key}", LOADER)


if __name__ == "__main__":
    unittest.main()
