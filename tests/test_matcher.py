
"""
Tests for Team 1's LZ77 longest-match module.

Run from the LZ77_Project directory with:

    python -m unittest tests.test_matcher -v
"""

import unittest

from lz77.matcher import find_longest_match


class TestFindLongestMatch(unittest.TestCase):

    def test_no_match(self):
        self.assertEqual(
            find_longest_match(
                "abcdef",
                0,
                20,
                15,
            ),
            (0, 0),
        )

    def test_single_character_match(self):
        self.assertEqual(
            find_longest_match(
                "abca",
                3,
                20,
                15,
            ),
            (3, 1),
        )

    def test_repetitive_a(self):
        self.assertEqual(
            find_longest_match(
                "AAAAAA",
                1,
                20,
                15,
            ),
            (1, 5),
        )

    def test_repetitive_ab(self):
        self.assertEqual(
            find_longest_match(
                "ABABABAB",
                2,
                20,
                15,
            ),
            (2, 6),
        )

    def test_repetitive_abc(self):
        self.assertEqual(
            find_longest_match(
                "ABCABCABCABC",
                3,
                20,
                15,
            ),
            (3, 9),
        )

    def test_lookahead_limit(self):
        self.assertEqual(
            find_longest_match(
                "AAAAAAAAAAAA",
                1,
                20,
                4,
            ),
            (1, 4),
        )

    def test_window_limit(self):
        # With a window of 2, the previous "ABC" is outside
        # the searchable window.
        self.assertEqual(
            find_longest_match(
                "ABCABCABC",
                6,
                2,
                15,
            ),
            (0, 0),
        )

        # With a window of 3, the previous "ABC" becomes searchable.
        self.assertEqual(
            find_longest_match(
                "ABCABCABC",
                6,
                3,
                15,
            ),
            (3, 3),
        )

    def test_empty_data(self):
        self.assertEqual(
            find_longest_match(
                "",
                0,
                20,
                15,
            ),
            (0, 0),
        )

    def test_position_at_end(self):
        self.assertEqual(
            find_longest_match(
                "ABC",
                3,
                20,
                15,
            ),
            (0, 0),
        )

    def test_invalid_current_position(self):
        with self.assertRaises(ValueError):
            find_longest_match(
                "ABC",
                4,
                20,
                15,
            )

    def test_invalid_window_size(self):
        with self.assertRaises(ValueError):
            find_longest_match(
                "ABC",
                1,
                0,
                15,
            )

    def test_invalid_lookahead_size(self):
        with self.assertRaises(ValueError):
            find_longest_match(
                "ABC",
                1,
                20,
                0,
            )


if __name__ == "__main__":
    unittest.main()
