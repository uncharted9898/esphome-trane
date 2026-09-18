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


def test_target_sdo_json_channels_remain_receive_only():
    # 0x601 is a target-observed CANopen SDO JSON receive channel. The legacy
    # application writer is fail-closed until a qualified SDO client exists.
    assert "can_id == 0x601 || can_id == 0x641 || can_id == 0x649" in CPP
    assert "state = &rx_601_" in CPP
    assert "send_data(0x601" not in CPP
    tx = CPP.split("bool TraneBus::send_json_internal_", 1)[1].split(
        "bool TraneBus::send_json(const std::string &payload)", 1
    )[0]
    assert "CANopen SDO writer for Trane object 0x300A:00 is not yet qualified" in tx
    assert "send_frame_(" not in tx


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


def test_blower_doc_marks_old_electrical_identity_superseded():
    assert "Superseded correlation note" in BLOWER_DOC
    assert "0x281.u16[3]" in BLOWER_DOC
    assert "not literal blower RPM" in BLOWER_DOC
    assert "0x280.float[1]=2.5" in BLOWER_DOC
    assert "not a shutdown-only sentinel or literal power factor" in BLOWER_DOC
