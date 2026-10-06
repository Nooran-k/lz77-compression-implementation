"""
Binary encoder tests: tags <-> .lz77, including Unicode symbols.

Run from the LZ77_Project directory:

    python -m unittest tests.test_binary_format -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lz77.binary_format import (
    MAGIC,
    VERSION,
    read_lz77_file,
    write_lz77_file,
)
from lz77.compressor import compress


class TestBinaryFormat(unittest.TestCase):
    def _round_trip_file(
        self,
        text: str,
        window_size: int = 20,
        lookahead_size: int = 15,
    ):
        tags = compress(
            text,
            window_size=window_size,
            lookahead_size=lookahead_size,
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.lz77"
            write_lz77_file(
                file_path=path,
                tokens=tags,
                window_size=window_size,
                lookahead_size=lookahead_size,
            )
            loaded, loaded_window, loaded_lookahead = read_lz77_file(path)
            self.assertEqual(loaded, tags)
            self.assertEqual(loaded_window, window_size)
            self.assertEqual(loaded_lookahead, lookahead_size)
            self.assertTrue(path.exists())
            return path.read_bytes()

    def test_empty_tokens(self):
        self._round_trip_file("")

    def test_plain_ascii(self):
        self._round_trip_file("ABCDEF")

    def test_repetitive(self):
        self._round_trip_file("AAAAAAAAAAAA")
        self._round_trip_file("ABABABABABAB")
        self._round_trip_file("HELLOHELLOHELLO")

    def test_unicode_symbol(self):
        payload = self._round_trip_file("Hello أحمد")
        self.assertTrue(payload.startswith(MAGIC))
        self.assertEqual(payload[4], VERSION)

    def test_none_next_character(self):
        self._round_trip_file("AAAAAA")

    def test_wrong_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.bin"
            with self.assertRaises(ValueError):
                write_lz77_file(path, [], 20, 15)

    def test_invalid_signature(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.lz77"
            path.write_bytes(b"XXXX" + b"\x00" * 13)
            with self.assertRaises(ValueError) as error:
                read_lz77_file(path)
            self.assertIn("signature", str(error.exception).lower())

    def test_incomplete_header(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "short.lz77"
            path.write_bytes(b"LZ77")
            with self.assertRaises(ValueError):
                read_lz77_file(path)


if __name__ == "__main__":
    unittest.main()
