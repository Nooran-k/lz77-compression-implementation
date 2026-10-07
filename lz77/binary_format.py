"""
Compact binary format for LZ77 files.

Version 2 stores LZ77 tags using a compact control byte and then compresses
the token stream with zlib. The public API remains the same.

v2 header:
    Magic          4 bytes
    Version        1 byte
    Storage mode   1 byte (0 = LZ77 tokens, 1 = UTF-8 literal fallback)
    Window size    2 bytes
    Look-ahead     2 bytes
    Token count    4 bytes
    Payload size   4 bytes

For ordinary files, the writer compares the compressed LZ77-token stream
with a compressed UTF-8 literal stream and stores the smaller one. The
literal fallback is still represented as valid LZ77 literal tags when read.

Token stream control bytes:
    0x00 = literal: followed by one UTF-8 character
    0x01 = match: followed by offset(1 byte), length(1 byte)
    0x02 = match + next character: offset, length, UTF-8 character
    0x03 = extended match: offset(2 bytes), length(2 bytes)
    0x04 = extended match + next character: offset(2), length(2), character

This removes the old 12-byte-per-tag overhead.
Version 1 files written by the original project are still readable.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import struct
import zlib

LZ77Token = tuple[int, int, str | None]

MAGIC = b"LZ77"
VERSION = 2
LEGACY_VERSION = 1
COMPRESSED_EXTENSION = ".lz77"

HEADER_FORMAT = "<4sBBHHII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

MAX_UINT8 = 255
MAX_UINT16 = 65535
MAX_UINT32 = 2**32 - 1


def _validate_uint(value: int, maximum: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")
    if value < 0 or value > maximum:
        raise ValueError(f"{name} must be between 0 and {maximum}.")


def _validate_token(token: LZ77Token) -> None:
    if not isinstance(token, tuple) or len(token) != 3:
        raise ValueError(
            "Each LZ77 token must contain (offset, length, next_character)."
        )

    offset, length, next_character = token
    _validate_uint(offset, MAX_UINT16, "offset")
    _validate_uint(length, MAX_UINT16, "length")

    if next_character is not None and not isinstance(next_character, str):
        raise TypeError("next_character must be a string or None.")
    if next_character is not None and len(next_character) != 1:
        raise ValueError(
            "next_character must contain exactly one character or be None."
        )


def _encode_character(character: str) -> bytes:
    data = character.encode("utf-8")
    if not 1 <= len(data) <= 4:
        raise ValueError("A UTF-8 character must occupy 1 to 4 bytes.")
    return data


def _utf8_char_size(first_byte: int) -> int:
    """Return the byte count of one UTF-8 code point from its first byte."""
    if first_byte < 0x80:
        return 1
    if 0xC0 <= first_byte <= 0xDF:
        return 2
    if 0xE0 <= first_byte <= 0xEF:
        return 3
    if 0xF0 <= first_byte <= 0xF4:
        return 4
    raise ValueError("Corrupted LZ77 file: invalid UTF-8 leading byte.")


def _read_character(stream: BytesIO) -> str:
    first = stream.read(1)
    if len(first) != 1:
        raise ValueError("Corrupted LZ77 file: missing next_character.")

    size = _utf8_char_size(first[0])
    rest = stream.read(size - 1)
    if len(rest) != size - 1:
        raise ValueError("Corrupted LZ77 file: incomplete next_character.")

    data = first + rest
    try:
        character = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Corrupted LZ77 file: invalid UTF-8 next_character."
        ) from error

    if len(character) != 1:
        raise ValueError(
            "Corrupted LZ77 file: next_character must be one character."
        )
    return character


def encode_token(token: LZ77Token) -> bytes:
    """Encode one LZ77 tag using the smallest suitable representation."""
    _validate_token(token)
    offset, length, next_character = token

    if offset == 0 and length == 0:
        if next_character is None:
            # Only useful for an unusual/invalid LZ77 tag, but keep it valid.
            return b"\x01\x00\x00"
        return b"\x00" + _encode_character(next_character)

    if offset <= MAX_UINT8 and length <= MAX_UINT8:
        control = 0x02 if next_character is not None else 0x01
        data = bytearray((control, offset, length))
    else:
        control = 0x04 if next_character is not None else 0x03
        data = bytearray((control,))
        data.extend(struct.pack("<HH", offset, length))

    if next_character is not None:
        data.extend(_encode_character(next_character))

    return bytes(data)


def _encode_tokens(tokens: list[LZ77Token]) -> bytes:
    raw = bytearray()
    for token in tokens:
        raw.extend(encode_token(token))
    return bytes(raw)


def decode_token(stream: BytesIO) -> LZ77Token:
    control_data = stream.read(1)
    if len(control_data) != 1:
        raise ValueError("Corrupted LZ77 file: incomplete token.")

    control = control_data[0]

    if control == 0x00:
        return 0, 0, _read_character(stream)

    if control in (0x01, 0x02):
        pair = stream.read(2)
        if len(pair) != 2:
            raise ValueError("Corrupted LZ77 file: incomplete match token.")
        offset, length = pair
        character = _read_character(stream) if control == 0x02 else None
        return offset, length, character

    if control in (0x03, 0x04):
        pair = stream.read(4)
        if len(pair) != 4:
            raise ValueError("Corrupted LZ77 file: incomplete extended token.")
        offset, length = struct.unpack("<HH", pair)
        character = _read_character(stream) if control == 0x04 else None
        return offset, length, character

    raise ValueError(f"Corrupted LZ77 file: unknown token control {control:#x}.")


def _decode_tokens(payload: bytes, token_count: int) -> list[LZ77Token]:
    stream = BytesIO(payload)
    tokens = [decode_token(stream) for _ in range(token_count)]
    if stream.read(1):
        raise ValueError(
            "Corrupted LZ77 file: unexpected data after the last token."
        )
    return tokens


def write_header(
    file_object,
    window_size: int,
    lookahead_size: int,
    token_count: int,
    payload_size: int = 0,
    storage_mode: int = 0,
) -> None:
    _validate_uint(window_size, MAX_UINT16, "window_size")
    _validate_uint(lookahead_size, MAX_UINT16, "lookahead_size")
    _validate_uint(token_count, MAX_UINT32, "token_count")
    _validate_uint(payload_size, MAX_UINT32, "payload_size")
    _validate_uint(storage_mode, 1, "storage_mode")

    file_object.write(
        struct.pack(
            HEADER_FORMAT,
            MAGIC,
            VERSION,
            storage_mode,
            window_size,
            lookahead_size,
            token_count,
            payload_size,
        )
    )


def write_lz77_file(
    file_path: str | Path,
    tokens: list[LZ77Token],
    window_size: int,
    lookahead_size: int,
) -> None:
    path = Path(file_path)
    if path.suffix.lower() != COMPRESSED_EXTENSION:
        raise ValueError("LZ77 binary files must use the .lz77 extension.")
    if not isinstance(tokens, list):
        raise TypeError("tokens must be a list.")

    for token in tokens:
        _validate_token(token)

    # Candidate A: actual LZ77 tags.
    token_payload = _encode_tokens(tokens)
    token_compressed = zlib.compress(token_payload, level=9)

    # Candidate B: original UTF-8 text represented by literal LZ77 tags.
    # This avoids expansion on inputs where the LZ77 tag overhead is larger
    # than the source data. The reader turns it back into valid literal tags.
    # Reconstruct the source text from the LZ77 tags for the fallback
    # candidate. This keeps the binary_format module independent.
    reconstructed: list[str] = []
    for offset, length, character in tokens:
        if length:
            start = len(reconstructed) - offset
            if start < 0:
                raise ValueError(
                    "Invalid LZ77 token: offset points before the output."
                )
            for index in range(length):
                reconstructed.append(reconstructed[start + index])
        if character is not None:
            reconstructed.append(character)

    original_text = "".join(reconstructed)
    literal_compressed = zlib.compress(
        original_text.encode("utf-8"),
        level=9,
    )

    if len(literal_compressed) < len(token_compressed):
        storage_mode = 1
        compressed_payload = literal_compressed
    else:
        storage_mode = 0
        compressed_payload = token_compressed

    try:
        with path.open("wb") as file_object:
            write_header(
                file_object,
                window_size,
                lookahead_size,
                len(original_text) if storage_mode == 1 else len(tokens),
                len(compressed_payload),
                storage_mode,
            )
            file_object.write(compressed_payload)
    except OSError as error:
        raise RuntimeError(f"Could not write LZ77 file:\n{error}") from error


def _read_legacy_v1(file_object):
    legacy_token_format = "<III"
    token_header_size = struct.calcsize(legacy_token_format)

    rest = file_object.read(12)
    if len(rest) != 12:
        raise ValueError("Invalid legacy LZ77 file: incomplete header.")

    window_size, lookahead_size, token_count = struct.unpack("<III", rest)
    tokens = []

    for _ in range(token_count):
        header = file_object.read(token_header_size)
        if len(header) != token_header_size:
            raise ValueError("Corrupted legacy LZ77 file: incomplete token.")

        offset, length, char_size = struct.unpack(legacy_token_format, header)

        if char_size == 0:
            tokens.append((offset, length, None))
            continue

        char_bytes = file_object.read(char_size)
        if len(char_bytes) != char_size:
            raise ValueError("Corrupted legacy LZ77 file: incomplete character.")

        try:
            character = char_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Corrupted legacy LZ77 file: invalid UTF-8.") from error

        if len(character) != 1:
            raise ValueError(
                "Corrupted legacy LZ77 file: character must be exactly one character."
            )

        tokens.append((offset, length, character))

    if file_object.read(1):
        raise ValueError("Corrupted legacy LZ77 file: unexpected trailing data.")

    return tokens, window_size, lookahead_size


def read_lz77_file(
    file_path: str | Path,
) -> tuple[list[LZ77Token], int, int]:
    path = Path(file_path)

    if path.suffix.lower() != COMPRESSED_EXTENSION:
        raise ValueError("Expected a .lz77 file.")
    if not path.exists():
        raise FileNotFoundError(f"LZ77 file does not exist:\n{path}")

    try:
        with path.open("rb") as file_object:
            prefix = file_object.read(5)
            if len(prefix) != 5:
                raise ValueError("Invalid LZ77 file: incomplete header.")

            magic, version = struct.unpack("<4sB", prefix)
            if magic != MAGIC:
                raise ValueError("Invalid LZ77 file: incorrect file signature.")

            if version == LEGACY_VERSION:
                return _read_legacy_v1(file_object)

            if version != VERSION:
                raise ValueError(f"Unsupported LZ77 file version: {version}")

            rest = file_object.read(HEADER_SIZE - 5)
            if len(rest) != HEADER_SIZE - 5:
                raise ValueError("Invalid LZ77 file: incomplete header.")

            storage_mode, window_size, lookahead_size, token_count, payload_size = struct.unpack(
                "<BHHII", rest
            )
            if storage_mode not in (0, 1):
                raise ValueError(
                    f"Unsupported LZ77 storage mode: {storage_mode}"
                )

            compressed_payload = file_object.read(payload_size)
            if len(compressed_payload) != payload_size:
                raise ValueError(
                    "Corrupted LZ77 file: incomplete compressed payload."
                )

            if file_object.read(1):
                raise ValueError(
                    "Corrupted LZ77 file: unexpected data after compressed payload."
                )

            try:
                raw_payload = zlib.decompress(compressed_payload)
            except zlib.error as error:
                raise ValueError(
                    "Corrupted LZ77 file: invalid compressed payload."
                ) from error

            if storage_mode == 0:
                tokens = _decode_tokens(raw_payload, token_count)
            else:
                try:
                    original_text = raw_payload.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise ValueError(
                        "Corrupted LZ77 file: invalid UTF-8 fallback payload."
                    ) from error

                # Reconstruct a valid LZ77 literal-token stream.
                tokens = [(0, 0, character) for character in original_text]

                if len(tokens) != token_count:
                    raise ValueError(
                        "Corrupted LZ77 file: token count does not match fallback data."
                    )

            return tokens, window_size, lookahead_size

    except OSError as error:
        raise RuntimeError(f"Could not read LZ77 file:\n{error}") from error
