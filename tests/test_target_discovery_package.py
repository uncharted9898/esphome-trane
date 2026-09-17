from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGGREGATOR = (ROOT / "waveshare-trane-known-telemetry-extra.yaml").read_text()
BASE = (ROOT / "waveshare-trane-known-telemetry-extra-base.yaml").read_text()
TARGET = (ROOT / "waveshare-trane-target-discovery.yaml").read_text()


def test_extra_package_preserves_established_surface_and_adds_target_discovery():
    assert "waveshare-trane-known-telemetry-extra-base.yaml" in AGGREGATOR
    assert "waveshare-trane-target-discovery.yaml" in AGGREGATOR
    assert "refresh: always" in AGGREGATOR

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

    # The package is observation-only. Hardware and TX ownership remain in the
    # main HA wrapper / trane_bus component.
    for forbidden in ("canbus:", "trane_bus:", "send_data(", "tx_enabled:"):
        assert forbidden not in TARGET
