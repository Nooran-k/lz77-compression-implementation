"""
LZ77 Binary File Format
=======================

This module defines the binary format used for LZ77 results.

The binary file stores the SAME LZ77 information produced by the
text result, but in real binary form.

Each token contains:

    (offset, length, next_character)

Example:

    (0, 0, "A")
    (1, 5, None)

The binary file also stores:

    - Window size
    - Look-ahead size
    - Number of tokens

File structure
--------------

Header:
    Magic              : 4 bytes
    Version            : 1 byte
    Window size        : 4 bytes
    Look-ahead size    : 4 bytes
    Token count        : 4 bytes

Each token:
    Offset             : 4 bytes
    Length             : 4 bytes
    Next-character size: 4 bytes
    Next-character     : variable UTF-8 bytes

All integer values are unsigned 32-bit little-endian.

If next_character is None:
    next_character_size = 0
"""

from __future__ import annotations

import struct
from pathlib import Path

LZ77Token = tuple[int, int, str | None]

MAGIC = b"LZ77"
VERSION = 1
MAX_UINT32 = 2**32 - 1
COMPRESSED_EXTENSION = ".lz77"

HEADER_FORMAT = "<4sBIII"
TOKEN_HEADER_FORMAT = "<III"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
TOKEN_HEADER_SIZE = struct.calcsize(TOKEN_HEADER_FORMAT)


def _validate_uint32(value: int, name: str) -> None:
    """Validate an integer that will be stored as unsigned 32-bit."""

    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")

    if value < 0:
        raise ValueError(f"{name} cannot be negative.")

    if value > MAX_UINT32:
        raise ValueError(f"{name} is too large for the binary format.")


def _validate_token(token: LZ77Token) -> None:
    """
    Validate one LZ77 token.

    Expected format:
        (offset, length, next_character)
    """

    if not isinstance(token, tuple):
        raise TypeError("Each LZ77 token must be a tuple.")

    if len(token) != 3:
        raise ValueError(
            "Each LZ77 token must contain (offset, length, next_character)."
        )

    offset, length, next_character = token
    _validate_uint32(offset, "offset")
    _validate_uint32(length, "length")

    if next_character is not None and not isinstance(next_character, str):
        raise TypeError("next_character must be a string or None.")

    if next_character is not None and len(next_character) != 1:
        raise ValueError(
            "next_character must contain exactly one character or be None."
        )


def encode_token(token: LZ77Token) -> bytes:
    """
    Convert one LZ77 token into binary bytes.

    Example:
        (5, 3, "A")
    becomes:
        offset
        length
        character byte length
        character bytes
    """

    _validate_token(token)
    offset, length, next_character = token

    if next_character is None:
        next_character_bytes = b""
    else:
        next_character_bytes = next_character.encode("utf-8")

    next_character_length = len(next_character_bytes)
    _validate_uint32(next_character_length, "next_character byte length")

    token_header = struct.pack(
        TOKEN_HEADER_FORMAT,
        offset,
        length,
        next_character_length,
    )
    return token_header + next_character_bytes


def decode_token(file_object) -> LZ77Token:
    """Read one LZ77 token from an opened binary file."""

    header_bytes = file_object.read(TOKEN_HEADER_SIZE)
    if not header_bytes:
        raise EOFError("No more LZ77 tokens are available.")

    if len(header_bytes) != TOKEN_HEADER_SIZE:
        raise ValueError("Corrupted LZ77 file: incomplete token header.")

    offset, length, next_character_length = struct.unpack(
        TOKEN_HEADER_FORMAT,
        header_bytes,
    )

    if next_character_length == 0:
        return offset, length, None

    next_character_bytes = file_object.read(next_character_length)
    if len(next_character_bytes) != next_character_length:
        raise ValueError("Corrupted LZ77 file: incomplete next_character data.")

    try:
        next_character = next_character_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Corrupted LZ77 file: next_character is not valid UTF-8."
        ) from error

    if len(next_character) != 1:
        raise ValueError(
            "Corrupted LZ77 file: next_character must contain exactly one character."
        )

    return offset, length, next_character


def write_header(
    file_object,
    window_size: int,
    lookahead_size: int,
    token_count: int,
) -> None:
    """Write the LZ77 binary file header."""

    _validate_uint32(window_size, "window_size")
    _validate_uint32(lookahead_size, "lookahead_size")
    _validate_uint32(token_count, "token_count")

    header = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        VERSION,
        window_size,
        lookahead_size,
        token_count,
    )
    file_object.write(header)


def read_header(file_object) -> tuple[int, int, int]:
    """
    Read and validate the LZ77 binary file header.

    Returns:
        (
            window_size,
            lookahead_size,
            token_count
        )
    """

    header_bytes = file_object.read(HEADER_SIZE)
    if len(header_bytes) != HEADER_SIZE:
        raise ValueError("Invalid LZ77 file: incomplete header.")

    magic, version, window_size, lookahead_size, token_count = struct.unpack(
        HEADER_FORMAT,
        header_bytes,
    )

    if magic != MAGIC:
        raise ValueError("Invalid LZ77 file: incorrect file signature.")

    if version != VERSION:
        raise ValueError(f"Unsupported LZ77 file version: {version}")

    return window_size, lookahead_size, token_count


def write_lz77_file(
    file_path: str | Path,
    tokens: list[LZ77Token],
    window_size: int,
    lookahead_size: int,
) -> None:
    """
    Write a complete LZ77 binary file.

    The file contains:
        Header
        Token 1
        Token 2
        Token 3
        ...
        Token N
    """

    path = Path(file_path)

    if path.suffix.lower() != COMPRESSED_EXTENSION:
        raise ValueError("LZ77 binary files must use the .lz77 extension.")

    if not isinstance(tokens, list):
        raise TypeError("tokens must be a list.")

    for token in tokens:
        _validate_token(token)

    try:
        with path.open("wb") as file_object:
            write_header(
                file_object=file_object,
                window_size=window_size,
                lookahead_size=lookahead_size,
                token_count=len(tokens),
            )
            for token in tokens:
                file_object.write(encode_token(token))
    except OSError as error:
        raise RuntimeError(f"Could not write LZ77 file:\n{error}") from error


def read_lz77_file(
    file_path: str | Path,
) -> tuple[list[LZ77Token], int, int]:
    """
    Read a complete LZ77 binary file.

    Returns:
        (
            tokens,
            window_size,
            lookahead_size
        )
    """

    path = Path(file_path)

    if path.suffix.lower() != COMPRESSED_EXTENSION:
        raise ValueError("Expected a .lz77 file.")

    if not path.exists():
        raise FileNotFoundError(f"LZ77 file does not exist:\n{path}")

    try:
        with path.open("rb") as file_object:
            window_size, lookahead_size, token_count = read_header(file_object)
            tokens: list[LZ77Token] = []

            for _ in range(token_count):
                tokens.append(decode_token(file_object))

            extra_data = file_object.read()
            if extra_data:
                raise ValueError(
                    "Corrupted LZ77 file: unexpected data after the last token."
                )
    except OSError as error:
        raise RuntimeError(f"Could not read LZ77 file:\n{error}") from error

    return tokens, window_size, lookahead_size
