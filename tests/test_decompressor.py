"""
Simple tests for Decompressor.
"""

import unittest
from lz77.decompressor import decompress


class TestDecompressor(unittest.TestCase):
    def test_single_character(self):
        tokens = [(0, 0, "A")]
        self.assertEqual(decompress(tokens), "A")

    def test_overlapping_repetition(self):
        # (0, 0, 'A') -> "A"
        # (1, 5, None) -> repeats 'A' 5 times -> "AAAAAA"
        tokens = [(0, 0, "A"), (1, 5, None)]
        self.assertEqual(decompress(tokens), "AAAAAA")

    def test_phrase(self):
        # Decodes to "ABA"
        tokens = [(0, 0, "A"), (0, 0, "B"), (2, 1, None)]
        self.assertEqual(decompress(tokens), "ABA")


if __name__ == "__main__":
    unittest.main()