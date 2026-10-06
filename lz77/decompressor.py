"""
LZ77 Decompressor Module (Teammate 3).
"""

from __future__ import annotations


def decompress(tags: list[tuple[int, int, str | None]]) -> str:
    """
    Reconstructs original text from LZ77 tags.
    Each tag is: (offset, length, next_char)
    """
    output: list[str] = []

    for offset, length, next_char in tags:
        # Copy matching pattern from output history
        if length > 0:
            start_index = len(output) - offset
            for i in range(length):
                output.append(output[start_index + i])

        # Append next literal character
        if next_char is not None:
            output.append(next_char)

    return "".join(output)
