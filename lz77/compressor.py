"""
LZ77 encoder.

This module converts input text into LZ77 tags. It does not read files,
write .lz77 files, or show the menu. File I/O lives in utils and
binary_format. Search lives in matcher.
"""

from __future__ import annotations

from lz77.matcher import (
    DEFAULT_LOOKAHEAD_SIZE,
    DEFAULT_WINDOW_SIZE,
    format_lz77_tag,
    generate_lz77_tags,
)

LZ77Tag = tuple[int, int, str | None]


def compress(
    text: str,
    window_size: int = DEFAULT_WINDOW_SIZE,
    lookahead_size: int = DEFAULT_LOOKAHEAD_SIZE,
) -> list[LZ77Tag]:
    """Convert text into LZ77 tags: (offset, length, next_symbol)."""

    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    return generate_lz77_tags(
        data=text,
        window_size=window_size,
        lookahead_size=lookahead_size,
    )


def format_tags(tags: list[LZ77Tag]) -> str:
    """Pretty-print tags for the compression discussion screen."""

    if not tags:
        return "No tags. The input file is empty."

    lines = [format_lz77_tag(tag) for tag in tags]
    return "\n".join(lines)


def compression_ratio_percent(
    original_size: int,
    compressed_size: int,
) -> float:
    """Compressed size as a percentage of original size."""

    if original_size <= 0:
        return 0.0

    return (compressed_size / original_size) * 100.0
