import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPP = (ROOT / "components/trane_bus/trane_bus.cpp").read_text()


class ReferenceTargetDecoder:
    """Small executable contract for the target SC360 receive framing.

    This deliberately mirrors protocol invariants, not C++ implementation
    structure. It lets regression fixtures cover final-sequence semantics,
    seven-bit rollover, idle control markers, and the short 0x641 response.
    """

    MAX_RX = 4096

    def __init__(self):
        self.mode = None
        self.expected_len = 0
        self.expected_seq = 1
        self.buf = bytearray()
        self.errors = 0

    def reset(self):
        self.mode = None
        self.expected_len = 0
        self.expected_seq = 1
        self.buf.clear()

    @staticmethod
    def wire_len(frame):
        if len(frame) < 8:
            return 0
        raw = int.from_bytes(bytes(frame[4:8]), "little")
        return raw - 1 if raw else 0

    def feed(self, frame):
        marker = frame[0]

        # State first: marker 0x21 is a legitimate long sequence number.
        if self.expected_len:
            if self.mode == "short":
                frame_type = marker & 0xF0
                sequence = marker & 0x0F
                if frame_type not in (0x00, 0x10) or sequence != self.expected_seq:
                    self.errors += 1
                    self.reset()
                    return None
                saw_nul = False
                for byte in frame[1:]:
                    if len(self.buf) >= self.expected_len:
                        break
                    if byte == 0:
                        saw_nul = True
                        break
                    self.buf.append(byte)
                final = frame_type == 0x10 or saw_nul or len(self.buf) == self.expected_len
                if final:
                    if len(self.buf) == self.expected_len:
                        out = bytes(self.buf).decode()
                        self.reset()
                        return out
                    self.errors += 1
                    self.reset()
                    return None
                self.expected_seq = (self.expected_seq + 1) & 0x0F
                return None

            if marker & 0x80:
                sequence = marker & 0x7F
                if sequence != self.expected_seq:
                    self.errors += 1
                    self.reset()
                    return None
                for byte in frame[1:]:
                    if len(self.buf) >= self.expected_len or byte == 0:
                        break
                    self.buf.append(byte)
                if len(self.buf) == self.expected_len:
                    out = bytes(self.buf).decode()
                    self.reset()
                    return out
                self.errors += 1
                self.reset()
                return None

            if marker != self.expected_seq:
                self.errors += 1
                self.reset()
                return None
            for byte in frame[1:]:
                if len(self.buf) >= self.expected_len or byte == 0:
                    break
                self.buf.append(byte)
            self.expected_seq = 1 if self.expected_seq == 0x7F else self.expected_seq + 1
            return None

        if marker == 0xC2:
            length = self.wire_len(frame)
            if not (0 < length <= self.MAX_RX):
                self.errors += 1
                return None
            self.mode = "long"
            self.expected_len = length
            self.expected_seq = 1
            return None

        if marker == 0x21:
            length = self.wire_len(frame)
            if not (0 < length <= self.MAX_RX):
                self.errors += 1
                return None
            self.mode = "short"
            self.expected_len = length
            self.expected_seq = 0
            return None

        # C1/CD/D1/D5/D9 and similar target control frames are idle metadata.
        return None


def encode_target_long(payload):
    raw = payload.encode()
    wire_len = len(raw) + 1
    frames = [[0xC2, 0x0A, 0x30, 0x00, *wire_len.to_bytes(4, "little")]]
    offset = 0
    seq = 1
    while offset < len(raw):
        chunk = list(raw[offset : offset + 7])
        offset += len(chunk)
        if offset >= len(raw):
            frames.append([0x80 | seq, *chunk, *([0] * (7 - len(chunk)))])
            break
        frames.append([seq, *chunk])
        seq = 1 if seq == 0x7F else seq + 1
    return frames


class TransportSourceContractTests(unittest.TestCase):
    def test_rx_and_tx_limits_are_separate(self):
        rx = re.search(r"MAX_RX_JSON_PAYLOAD\s*=\s*(\d+)", CPP)
        tx = re.search(r"MAX_TX_JSON_PAYLOAD\s*=\s*(\d+)", CPP)
        self.assertIsNotNone(rx)
        self.assertIsNotNone(tx)
        self.assertGreaterEqual(int(rx.group(1)), 2048)
        self.assertLessEqual(int(tx.group(1)), 512)
        self.assertIn("payload.size() > MAX_TX_JSON_PAYLOAD", CPP)

    def test_target_headers_are_exact_not_generic_c_nibble(self):
        self.assertIn("if (marker == 0xC2)", CPP)
        self.assertIn("if (marker == 0x21)", CPP)
        self.assertNotIn("if ((marker & 0xF0) == 0xC0)", CPP)

    def test_active_state_is_processed_before_idle_headers(self):
        state_pos = CPP.index("if (state.expected_len != 0)")
        c2_pos = CPP.index("if (marker == 0xC2)")
        short_pos = CPP.index("if (marker == 0x21)")
        self.assertLess(state_pos, c2_pos)
        self.assertLess(state_pos, short_pos)

    def test_long_final_marker_is_sequence_not_byte_count(self):
        self.assertIn("const uint8_t sequence = marker & 0x7F", CPP)
        self.assertIn("sequence != state.expected_seq", CPP)
        self.assertNotIn("used > 7", CPP)

    def test_long_sequence_wraps_after_0x7f(self):
        self.assertIn("state.expected_seq == 0x7F ? 1", CPP)


class TargetTransportFixtureTests(unittest.TestCase):
    def decode_all(self, frames):
        decoder = ReferenceTargetDecoder()
        messages = []
        for frame in frames:
            result = decoder.feed(frame)
            if result is not None:
                messages.append(result)
        return decoder, messages

    def test_live_short_ack_fixture(self):
        frames = [
            [0x21, 0x0A, 0x30, 0x00, 0x0E, 0x00, 0x00, 0x00],
            [0x00, 0x7B, 0x22, 0x41, 0x63, 0x6B, 0x22, 0x3A],
            [0x11, 0x22, 0x32, 0x30, 0x30, 0x22, 0x7D, 0x00],
        ]
        decoder, messages = self.decode_all(frames)
        self.assertEqual(messages, ['{"Ack":"200"}'])
        self.assertEqual(decoder.errors, 0)

    def test_target_long_indoor_status(self):
        payload = '{"IndoorStatus":{"Update":{"1":{"D":"A"}}}}'
        frames = encode_target_long(payload)
        self.assertGreater(frames[-1][0], 0x80)
        decoder, messages = self.decode_all(frames)
        self.assertEqual(messages, [payload])
        self.assertEqual(decoder.errors, 0)

    def test_final_marker_above_0x88_is_valid(self):
        payload = '{"IndoorStatus":{"Update":{"1":{"E":"40","Pad":"' + ("x" * 180) + '"}}}}'
        frames = encode_target_long(payload)
        self.assertGreater(frames[-1][0] & 0x7F, 8)
        decoder, messages = self.decode_all(frames)
        self.assertEqual(messages, [payload])
        self.assertEqual(decoder.errors, 0)

    def test_sequence_0x21_inside_long_message_is_not_short_header(self):
        payload = '{"Long":"' + ("a" * 260) + '"}'
        frames = encode_target_long(payload)
        self.assertIn(0x21, [frame[0] for frame in frames])
        decoder, messages = self.decode_all(frames)
        self.assertEqual(messages, [payload])
        self.assertEqual(decoder.errors, 0)

    def test_long_sequence_rollover_0x7f_to_0x01(self):
        payload = '{"CertificateLike":"' + ("A" * 1500) + '"}'
        frames = encode_target_long(payload)
        markers = [frame[0] for frame in frames[1:]]
        rollover = markers.index(0x7F)
        self.assertEqual(markers[rollover + 1], 0x01)
        decoder, messages = self.decode_all(frames)
        self.assertEqual(messages, [payload])
        self.assertEqual(decoder.errors, 0)

    def test_idle_control_markers_do_not_count_as_errors(self):
        payload = '{"ZoneStatus":{"Update":{"1":{"H":"82.00"}}}}'
        frames = encode_target_long(payload)
        frames.extend(
            [
                [0xC1, 0, 0, 0, 0, 0, 0, 0],
                [0xCD, 0, 0, 0, 0, 0, 0, 0],
                [0xD1, 0, 0, 0, 0, 0, 0, 0],
                [0xD5, 0, 0, 0, 0, 0, 0, 0],
                [0xD9, 0, 0, 0, 0, 0, 0, 0],
            ]
        )
        decoder, messages = self.decode_all(frames)
        self.assertEqual(messages, [payload])
        self.assertEqual(decoder.errors, 0)


if __name__ == "__main__":
    unittest.main()
