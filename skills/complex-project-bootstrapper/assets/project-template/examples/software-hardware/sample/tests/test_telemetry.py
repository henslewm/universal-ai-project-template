"""Unit checks for the log summarizer."""
import unittest

from synth_bridge.telemetry import summarize


class TelemetryTests(unittest.TestCase):
    def test_counts_kinds_and_tracks_reading_range(self):
        lines = ["READING 5", "READING 40", "ERROR BAD_CHECKSUM", "", "READING 12"]
        self.assertEqual(summarize(lines), {"counts": {"ERROR": 1, "READING": 3},
                                            "reading_min": 5, "reading_max": 40})

    def test_malformed_reading_is_counted_not_raised(self):
        result = summarize(["READING not-a-number"])
        self.assertEqual(result["counts"], {"MALFORMED": 1, "READING": 1})
        self.assertIsNone(result["reading_min"])

    def test_empty_log(self):
        self.assertEqual(summarize([]), {"counts": {}, "reading_min": None, "reading_max": None})


if __name__ == "__main__":
    unittest.main()
