"""
Encoder tests: LZ77 tags, overlapping matches, and tag reconstruction.

Run from the LZ77_Project directory:

    python -m unittest tests.test_compressor -v
"""

from __future__ import annotations

import unittest

from lz77.compressor import compress, format_tags
from lz77.matcher import DEFAULT_LOOKAHEAD_SIZE, DEFAULT_WINDOW_SIZE


def reconstruct(tags: list[tuple[int, int, str | None]]) -> str:
    """Rebuild text from tags. Used only to prove encoder tags are valid."""

    output: list[str] = []

    for offset, length, next_symbol in tags:
        if length > 0:
            start = len(output) - offset
            if start < 0:
                raise AssertionError(
                    f"offset {offset} is larger than the output so far"
                )
            for index in range(length):
                output.append(output[start + index])
        if next_symbol is not None:
            output.append(next_symbol)

    return "".join(output)


class TestCompressor(unittest.TestCase):
    def _round_trip(self, text: str) -> list[tuple[int, int, str | None]]:
        tags = compress(text)
        self.assertEqual(reconstruct(tags), text)
        return tags

    def test_empty_file(self):
        tags = self._round_trip("")
        self.assertEqual(tags, [])
        self.assertIn("empty", format_tags(tags).lower())

    def test_no_repetition(self):
        tags = self._round_trip("ABCDEF")
        self.assertTrue(all(length == 0 for _, length, _ in tags))

    def test_repetitive_a(self):
        tags = self._round_trip("AAAAAA")
        self.assertTrue(any(length > 0 for _, length, _ in tags))
        self.assertLess(len(tags), 6)

    def test_long_run_of_a(self):
        self._round_trip("A" * 16)

    def test_repetitive_ab(self):
        tags = self._round_trip("ABABABABABAB")
        self.assertTrue(any(length > 0 for _, length, _ in tags))

    def test_repetitive_abc(self):
        tags = self._round_trip("ABCABCABCABC")
        self.assertTrue(any(length > 0 for _, length, _ in tags))

    def test_hello_repeat(self):
        self._round_trip("HELLOHELLOHELLO")

    def test_overlapping_single_character(self):
        tags = compress("AAAAAA")
        offset, length, next_symbol = tags[-1]
        self.assertGreaterEqual(length, 1)
        self.assertGreaterEqual(offset, 1)
        self.assertLessEqual(offset, length)
        self.assertIsNone(next_symbol)

    def test_unicode_arabic(self):
        self._round_trip("مرحبا بالعالم")

    def test_mixed_unicode(self):
        self._round_trip("Hello أحمد")

    def test_rejects_non_string(self):
        with self.assertRaises(TypeError):
            compress(b"ABC")  # type: ignore[arg-type]

    def test_custom_window_still_round_trips(self):
        text = "ABCABCABCABC"
        tags = compress(text, window_size=4, lookahead_size=4)
        self.assertEqual(reconstruct(tags), text)
        self.assertEqual(DEFAULT_WINDOW_SIZE, 20)
        self.assertEqual(DEFAULT_LOOKAHEAD_SIZE, 15)


if __name__ == "__main__":
    unittest.main()
