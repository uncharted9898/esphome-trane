import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WifiListFragmentNativeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("g++"), "g++ unavailable")
    def test_bounded_passive_wifi_list_reassembly(self):
        with tempfile.TemporaryDirectory(prefix="trane-wifi-rx-") as td:
            target = Path(td) / "wifi_list_test"
            subprocess.run(
                [
                    "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    "-I", str(ROOT), str(ROOT / "tests/wifi_list_fragment_assembler_test.cpp"),
                    "-o", str(target),
                ],
                check=True, cwd=ROOT, timeout=60,
            )
            subprocess.run([str(target)], check=True, cwd=ROOT, timeout=10)


if __name__ == "__main__":
    unittest.main()
