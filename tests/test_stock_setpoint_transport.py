import unittest


def build_stock_block_frames(payload: str, block_size: int = 12):
    wire = payload.encode("ascii") + b"\x00"
    initiate = bytes(
        [0xC2, 0x0A, 0x30, 0x00]
        + list(len(wire).to_bytes(4, "little"))
    )
    segments = []
    offset = 0
    seq = 1
    while offset < len(wire):
        chunk = wire[offset : offset + 7]
        offset += len(chunk)
        final = offset == len(wire)
        marker = seq | (0x80 if final else 0)
        segments.append(bytes([marker]) + chunk.ljust(7, b"\x00"))
        if final or seq == block_size:
            break
        seq += 1
    unused = (7 - (len(wire) % 7)) % 7
    end = bytes([0xC1 | (unused << 2)]) + b"\x00" * 7
    return initiate, segments, end


class StockSetpointTransportEvidenceTests(unittest.TestCase):
    def test_oct3_77f_stock_request_reconstructs_exact_wire_frames(self):
        payload = (
            '{"SpOverride":{"Put":{"1":{"Csp":"77","Hsp":"62",'
            '"HoldType":"1","Source":"1"}}}}'
        )
        self.assertEqual(len(payload), 80)
        initiate, segments, end = build_stock_block_frames(payload)
        self.assertEqual(initiate.hex().upper(), "C20A300051000000")
        self.assertEqual(
            [frame.hex().upper() for frame in segments],
            [
                "017B2253704F7665",
                "027272696465223A",
                "037B22507574223A",
                "047B2231223A7B22",
                "05437370223A2237",
                "0637222C22487370",
                "07223A223632222C",
                "0822486F6C645479",
                "097065223A223122",
                "0A2C22536F757263",
                "0B65223A2231227D",
                "8C7D7D7D00000000",
            ],
        )
        self.assertEqual(end.hex().upper(), "CD00000000000000")

    def test_oct3_78f_request_has_same_stock_transport_shape(self):
        payload = (
            '{"SpOverride":{"Put":{"1":{"Csp":"78","Hsp":"62",'
            '"HoldType":"1","Source":"1"}}}}'
        )
        initiate, segments, end = build_stock_block_frames(payload)
        self.assertEqual(len(payload), 80)
        self.assertEqual(initiate.hex().upper(), "C20A300051000000")
        self.assertEqual(len(segments), 12)
        self.assertEqual(segments[-1][0], 0x8C)
        self.assertEqual(end[0], 0xCD)

    def test_captured_server_handshake_is_the_expected_final_block_form(self):
        self.assertEqual(bytes.fromhex("A00A30000C000000")[4], 12)
        final_ack = bytes.fromhex("A20C000000000000")
        self.assertEqual(final_ack[0], 0xA2)
        self.assertEqual(final_ack[1], 12)
        self.assertEqual(final_ack[2], 0)
        self.assertEqual(bytes.fromhex("A100000000000000")[0], 0xA1)

    def test_application_ack_payload_is_exact(self):
        ack = '{"Ack":"200"}'
        self.assertEqual(len(ack), 13)
        self.assertEqual((ack + "\x00").encode().hex().upper(), "7B2241636B223A22323030227D00")


if __name__ == "__main__":
    unittest.main()
