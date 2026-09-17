from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGGREGATOR = (ROOT / "waveshare-trane-known-telemetry-extra.yaml").read_text()
BASE = (ROOT / "waveshare-trane-known-telemetry-extra-base.yaml").read_text()
TARGET = (ROOT / "waveshare-trane-target-discovery.yaml").read_text()
RAW = (ROOT / "waveshare-trane-target-raw.yaml").read_text()


def test_extra_package_preserves_established_surface_and_adds_target_discovery():
    assert "waveshare-trane-known-telemetry-extra-base.yaml" in AGGREGATOR
    assert "waveshare-trane-target-discovery.yaml" in AGGREGATOR
    assert "waveshare-trane-target-raw.yaml" in AGGREGATOR
    assert AGGREGATOR.count("refresh: always") >= 3

    # Representative historical declarations prove that the original package
    # was preserved instead of being replaced by a reduced discovery-only file.
    for token in (
        'id: trane_system_status_d_numeric',
        'id: trane_heat_setpoint_z2',
        'id: trane_490_float1',
        'id: trane_indoor_settings_a',
    ):
        assert token in BASE


def test_target_discovery_exposes_qualified_blower_electrical_fields():
    for token in (
        'name: "0x318 Blower Input Current"',
        'name: "0x280 Blower Power Factor Candidate"',
        'name: "Blower V I PF Calculated Power"',
        'name: "0x318 U16 2 Candidate"',
        'name: "0x318 U16 3 Candidate"',
    ):
        assert token in TARGET

    assert 'pf <= 0.0f || pf > 1.0f' in TARGET
    assert 'return volts * amps * pf;' in TARGET


def test_target_discovery_surfaces_canopen_without_guessing_device_roles():
    for token in (
        'name: "CANopen Node 1 State"',
        'name: "CANopen Node 3 State"',
        'name: "Last CANopen NMT 0x000 Raw"',
        'name: "Last CANopen EMCY Node 1 0x081 Raw"',
        'name: "Last CANopen LSS Server 0x7E4 Raw"',
        'name: "Last CANopen LSS Manager 0x7E5 Raw"',
        'name: "0x53E Active Link Nodes Candidate"',
        'name: "Debug IDBLE State"',
    ):
        assert token in TARGET


def test_unresolved_target_families_stay_raw_and_disabled():
    for token in (
        'name: "Last 0x202 Cold Boot Raw"',
        'name: "Last 0x20E Cold Boot Raw"',
        'name: "Last 0x2D0 Raw"',
        'name: "Last 0x420 Raw"',
        'name: "Last 0x430 Raw"',
        'name: "Last 0x450 Raw"',
        'name: "Last 0x4C0 Raw"',
        'name: "Last 0x4C5 Raw"',
        'name: "Last 0x540 Cold Boot Raw"',
        'name: "Last SDO-like 0x5A1 Raw"',
        'name: "Last SDO-like 0x621 Raw"',
    ):
        assert token in RAW
    assert RAW.count("disabled_by_default: true") >= 30


def test_all_target_packages_are_observation_only():
    # Hardware and TX ownership remain in the main HA wrapper / trane_bus
    # component; discovery packages can only read the observation cache.
    for package in (TARGET, RAW):
        for forbidden in ("canbus:", "trane_bus:", "send_data(", "tx_enabled:"):
            assert forbidden not in package
