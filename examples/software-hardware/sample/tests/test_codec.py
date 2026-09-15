"""Unit and contract checks for the SYNTH-FRAME-1 codec. Fixture-only; no device."""
import unittest

from synth_bridge import codec

# Golden vectors from the synthetic specification (SRC-SYNTH-SPEC). They are invented.
VALID = {
    bytes([0xA1, 0x01, 0x01, 0xA1]): bytes([0x01]),
    bytes([0xA1, 0x02, 0x12, 0x34, 0x85]): bytes([0x12, 0x34]),
    bytes([0xA1, 0x00, 0xA1]): b"",
}
INVALID = {
    b"": "SHORT",
    bytes([0xA1, 0x01]): "SHORT",
    bytes([0xA0, 0x01, 0x01, 0xA0]): "BAD_TAG",
    bytes([0xA1, 0x02, 0x01, 0xA2]): "BAD_LENGTH",
    bytes([0xA1, 0x11] + [0] * 17 + [0xB0]): "BAD_LENGTH",
    bytes([0xA1, 0x01, 0x01, 0x00]): "BAD_CHECKSUM",
}


class CodecUnitTests(unittest.TestCase):
    def test_encode_round_trips_through_decode(self):
        for payload in (b"", b"\x01", bytes(range(16))):
            with self.subTest(payload=payload):
                self.assertEqual(codec.decode(codec.encode(payload)), (payload, None))

    def test_encode_refuses_oversized_payload(self):
        with self.assertRaises(ValueError):
            codec.encode(bytes(17))

    def test_read_request_is_the_specified_frame(self):
        self.assertEqual(codec.encode_read_request(), bytes([0xA1, 0x01, 0x01, 0xA1]))

    def test_reading_requires_exactly_two_payload_bytes(self):
        self.assertEqual(codec.decode_reading(codec.encode(bytes([0x12, 0x34]))), codec.Reading(0x1234))
        self.assertEqual(codec.decode_reading(codec.encode(bytes([0x12]))), codec.FrameError("BAD_PAYLOAD"))


class CodecContractTests(unittest.TestCase):
    def test_every_valid_golden_vector_decodes(self):
        for frame, payload in VALID.items():
            with self.subTest(frame=frame.hex()):
                self.assertEqual(codec.decode(frame), (payload, None))

    def test_every_invalid_golden_vector_is_named_without_raising(self):
        for frame, code in INVALID.items():
            with self.subTest(frame=frame.hex()):
                payload, error = codec.decode(frame)
                self.assertIsNone(payload)
                self.assertEqual(error, codec.FrameError(code))


if __name__ == "__main__":
    unittest.main()
