from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = (ROOT / "components/trane_bus/trane_bus.h").read_text()
CPP = (ROOT / "components/trane_bus/trane_bus.cpp").read_text()
CANOPEN_DOC = (ROOT / "docs/CANOPEN-LINK-TRANSPORT.md").read_text()
BLOWER_DOC = (ROOT / "docs/TARGET-BLOWER-ELECTRICAL-2026-09-17.md").read_text()


def test_cold_boot_canopen_ids_are_not_reported_as_novel():
    # These IDs are all present in the target cold-boot capture. Keep the
    # public HA discovery classifier narrow: observed target IDs only, not an
    # indiscriminate CANopen-range allowlist.
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
        "can_id == 0x7E5",
    ):
        assert token in HEADER

    assert "can_id >= 0x700 && can_id <= 0x77F" not in HEADER
    assert "can_id >= 0x080 && can_id <= 0x0FF" not in HEADER


def test_target_segmented_debug_channel_remains_receive_only():
    # 0x601 is a target-observed segmented JSON receive channel. Application
    # transmission remains pinned to the separately configured command ID.
    assert "can_id == 0x601 || can_id == 0x641 || can_id == 0x649" in CPP
    assert "state = &rx_601_" in CPP
    assert "send_data(command_can_id_" in CPP
    assert "send_data(0x601" not in CPP


def test_canopen_evidence_is_documented_without_node_role_guessing():
    for phrase in (
        "0x703 00",
        "0x703 7F",
        "0x703 05",
        "0x000 81 03",
        "0x000 01 03",
        "0x7E5",
        "0x7E4",
        "SDO-like channel pairs",
    ):
        assert phrase in CANOPEN_DOC

    assert "do **not** map node 1..5" in CANOPEN_DOC


def test_blower_electrical_identity_retains_pf_sentinel_caution():
    for phrase in (
        "0x318.float[0]` — **Indoor blower input current**",
        "0x320.float[0]` — **Indoor blower real input power**",
        "0x280.float[1]` — **power-factor-like raw field**",
        "0 < PF <= 1",
        "2.5",
    ):
        assert phrase in BLOWER_DOC

    # The representative steady-running points should close the real-power
    # equation to well under one watt.
    samples = (
        (238.43, 0.4141, 0.25, 24.56),
        (233.2, 0.3970, 0.25, 22.9),
        (232.4, 0.3799, 0.25, 21.61),
    )
    for volts, amps, pf, watts in samples:
        assert abs(volts * amps * pf - watts) < 0.6
