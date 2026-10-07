"""Compact binary storage for the LZ77 project.

Version 3 keeps the public API unchanged but removes the large fixed header
and uses raw DEFLATE (zlib without the zlib wrapper).  This is important for
small files: the old format could be larger than the input even when the
input was highly repetitive.

V3 header (8 bytes):
    Magic          4 bytes: b"LZ77"
    Version        1 byte: 3
    Storage mode   1 byte: 0 = compressed LZ77 tags, 1 = compressed UTF-8 text
    Window size    1 byte
    Look-ahead     1 byte

The payload is raw DEFLATE.  For mode 0 the decompressed payload is a compact
byte token stream. For mode 1 it is simply the original UTF-8 bytes.

V1 and V2 files remain readable.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import struct
import zlib

LZ77Token = tuple[int, int, str | None]

MAGIC = b"LZ77"
VERSION = 3
LEGACY_VERSION = 1
V2_VERSION = 2
COMPRESSED_EXTENSION = ".lz77"

V3_HEADER_FORMAT = "<4sBBBB"
V3_HEADER_SIZE = struct.calcsize(V3_HEADER_FORMAT)
V2_HEADER_FORMAT = "<4sBBHHII"
V2_HEADER_SIZE = struct.calcsize(V2_HEADER_FORMAT)

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
        raise ValueError("Each LZ77 token must contain (offset, length, next_character).")
    offset, length, next_character = token
    _validate_uint(offset, MAX_UINT16, "offset")
    _validate_uint(length, MAX_UINT16, "length")
    if next_character is not None and not isinstance(next_character, str):
        raise TypeError("next_character must be a string or None.")
    if next_character is not None and len(next_character) != 1:
        raise ValueError("next_character must contain exactly one character or be None.")


def _encode_character(character: str) -> bytes:
    data = character.encode("utf-8")
    if not 1 <= len(data) <= 4:
        raise ValueError("A UTF-8 character must occupy 1 to 4 bytes.")
    return data


def _utf8_char_size(first_byte: int) -> int:
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
    try:
        character = (first + rest).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Corrupted LZ77 file: invalid UTF-8 next_character.") from error
    if len(character) != 1:
        raise ValueError("Corrupted LZ77 file: next_character must be one character.")
    return character


def encode_token(token: LZ77Token) -> bytes:
    """Compact byte representation used before DEFLATE compression."""
    _validate_token(token)
    offset, length, next_character = token

    # 0x00 = literal, followed by UTF-8 character.
    if offset == 0 and length == 0:
        if next_character is None:
            return b"\x01"
        return b"\x00" + _encode_character(next_character)

    # 0x01 = match without next character.
    # 0x02 = match with next character.
    if offset <= 255 and length <= 255:
        control = 0x02 if next_character is not None else 0x01
        data = bytearray((control, offset, length))
    else:
        # 0x03 / 0x04 = extended forms.
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
    if control == 0x01:
        pair = stream.read(2)
        if len(pair) != 2:
            raise ValueError("Corrupted LZ77 file: incomplete match token.")
        return pair[0], pair[1], None
    if control == 0x02:
        pair = stream.read(2)
        if len(pair) != 2:
            raise ValueError("Corrupted LZ77 file: incomplete match token.")
        return pair[0], pair[1], _read_character(stream)
    if control == 0x03:
        pair = stream.read(4)
        if len(pair) != 4:
            raise ValueError("Corrupted LZ77 file: incomplete extended match token.")
        return (*struct.unpack("<HH", pair), None)
    if control == 0x04:
        pair = stream.read(4)
        if len(pair) != 4:
            raise ValueError("Corrupted LZ77 file: incomplete extended match token.")
        offset, length = struct.unpack("<HH", pair)
        return offset, length, _read_character(stream)
    raise ValueError(f"Corrupted LZ77 file: unknown token control {control:#x}.")


def _decode_tokens_until_end(payload: bytes) -> list[LZ77Token]:
    stream = BytesIO(payload)
    tokens: list[LZ77Token] = []
    while stream.tell() < len(payload):
        tokens.append(decode_token(stream))
    return tokens


def _raw_deflate(data: bytes) -> bytes:
    compressor = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=-15)
    return compressor.compress(data) + compressor.flush()


def _raw_inflate(data: bytes) -> bytes:
    try:
        return zlib.decompress(data, wbits=-15)
    except zlib.error as error:
        raise ValueError("Corrupted LZ77 file: invalid compressed payload.") from error


def _reconstruct(tokens: list[LZ77Token]) -> str:
    output: list[str] = []
    for offset, length, character in tokens:
        if length:
            start = len(output) - offset
            if offset <= 0 or start < 0:
                raise ValueError("Invalid LZ77 token: offset points before the output.")
            for index in range(length):
                output.append(output[start + index])
        if character is not None:
            output.append(character)
    return "".join(output)


def write_header(file_object, window_size: int, lookahead_size: int,
                 token_count: int, payload_size: int = 0, storage_mode: int = 0) -> None:
    # Kept as a public compatibility helper. V3 stores compact 8-byte headers.
    _validate_uint(window_size, 255, "window_size")
    _validate_uint(lookahead_size, 255, "lookahead_size")
    _validate_uint(storage_mode, 1, "storage_mode")
    file_object.write(struct.pack(
        V3_HEADER_FORMAT, MAGIC, VERSION, storage_mode, window_size, lookahead_size
    ))


def write_lz77_file(file_path: str | Path, tokens: list[LZ77Token],
                    window_size: int, lookahead_size: int) -> None:
    path = Path(file_path)
    if path.suffix.lower() != COMPRESSED_EXTENSION:
        raise ValueError("LZ77 binary files must use the .lz77 extension.")
    if not isinstance(tokens, list):
        raise TypeError("tokens must be a list.")
    for token in tokens:
        _validate_token(token)

    # Reconstruct once. Candidate 0 keeps the actual LZ77 tags.
    token_payload = _raw_deflate(_encode_tokens(tokens))
    original_text = _reconstruct(tokens)
    literal_payload = _raw_deflate(original_text.encode("utf-8"))

    if len(literal_payload) < len(token_payload):
        storage_mode = 1
        payload = literal_payload
    else:
        storage_mode = 0
        payload = token_payload

    # Window/look-ahead are project settings and fit in one byte (20/15 by default).
    if window_size > 255 or lookahead_size > 255:
        raise ValueError("window_size and lookahead_size must be <= 255 for V3 files.")

    with path.open("wb") as file_object:
        write_header(file_object, window_size, lookahead_size,
                     len(tokens), len(payload), storage_mode)
        file_object.write(payload)


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
            raise ValueError("Corrupted legacy LZ77 file: character must be exactly one character.")
        tokens.append((offset, length, character))
    if file_object.read(1):
        raise ValueError("Corrupted legacy LZ77 file: unexpected trailing data.")
    return tokens, window_size, lookahead_size


def _read_v2(file_object):
    rest = file_object.read(V2_HEADER_SIZE - 5)
    if len(rest) != V2_HEADER_SIZE - 5:
        raise ValueError("Invalid LZ77 file: incomplete header.")
    storage_mode, window_size, lookahead_size, token_count, payload_size = struct.unpack("<BHHII", rest)
    compressed_payload = file_object.read(payload_size)
    if len(compressed_payload) != payload_size:
        raise ValueError("Corrupted LZ77 file: incomplete compressed payload.")
    raw_payload = zlib.decompress(compressed_payload)
    if storage_mode == 0:
        return _decode_tokens_until_end(raw_payload)[:token_count], window_size, lookahead_size
    original_text = raw_payload.decode("utf-8")
    return [(0, 0, character) for character in original_text], window_size, lookahead_size


def read_lz77_file(file_path: str | Path) -> tuple[list[LZ77Token], int, int]:
    path = Path(file_path)
    if path.suffix.lower() != COMPRESSED_EXTENSION:
        raise ValueError("Expected a .lz77 file.")
    if not path.exists():
        raise FileNotFoundError(f"LZ77 file does not exist:\n{path}")

    with path.open("rb") as file_object:
        prefix = file_object.read(5)
        if len(prefix) != 5:
            raise ValueError("Invalid LZ77 file: incomplete header.")
        magic, version = struct.unpack("<4sB", prefix)
        if magic != MAGIC:
            raise ValueError("Invalid LZ77 file: incorrect file signature.")

        if version == LEGACY_VERSION:
            return _read_legacy_v1(file_object)
        if version == V2_VERSION:
            return _read_v2(file_object)
        if version != VERSION:
            raise ValueError(f"Unsupported LZ77 file version: {version}")

        rest = file_object.read(3)
        if len(rest) != 3:
            raise ValueError("Invalid LZ77 file: incomplete V3 header.")
        storage_mode, window_size, lookahead_size = struct.unpack("<BBB", rest)
        if storage_mode not in (0, 1):
            raise ValueError(f"Unsupported LZ77 storage mode: {storage_mode}")

        compressed_payload = file_object.read()
        raw_payload = _raw_inflate(compressed_payload)

        if storage_mode == 0:
            tokens = _decode_tokens_until_end(raw_payload)
        else:
            original_text = raw_payload.decode("utf-8")
            tokens = [(0, 0, character) for character in original_text]

        return tokens, window_size, lookahead_size
