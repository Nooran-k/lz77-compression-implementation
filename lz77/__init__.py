"""LZ77 compression package."""

from lz77.compressor import compress
from lz77.binary_format import read_lz77_file, write_lz77_file

__all__ = [
    "compress",
    "write_lz77_file",
    "read_lz77_file",
]
