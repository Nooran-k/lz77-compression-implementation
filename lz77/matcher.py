
"""
LZ77 Longest-Match Search Module.

Team 1 responsibilities:
    - Search the previous window (search buffer).
    - Compare it with the look-ahead buffer.
    - Find the longest valid match.
    - Support overlapping matches.
    - Generate LZ77 tags.
    - Generate text and binary matcher results.
    - Build the complete Longest-Match report.

The main application only calls:

    test_longest_match_file()

The matcher returns:

    (offset, length)

and the tag generator produces:

    (offset, length, next_character)
"""

from __future__ import annotations

from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

from lz77.binary_format import write_lz77_file


# ============================================================
# SETTINGS
# ============================================================

TEXT_EXTENSION = ".txt"

DEFAULT_WINDOW_SIZE = 20
DEFAULT_LOOKAHEAD_SIZE = 15


# ============================================================
# LONGEST MATCH SEARCH
# ============================================================

def _validate_parameters(
    data: str,
    current_position: int,
    window_size: int,
    lookahead_size: int,
) -> None:
    """Validate arguments supplied to find_longest_match."""

    if not isinstance(data, str):
        raise TypeError("data must be a string.")

    if not isinstance(current_position, int) or isinstance(
        current_position,
        bool,
    ):
        raise TypeError(
            "current_position must be an integer."
        )

    if not isinstance(window_size, int) or isinstance(
        window_size,
        bool,
    ):
        raise TypeError(
            "window_size must be an integer."
        )

    if not isinstance(lookahead_size, int) or isinstance(
        lookahead_size,
        bool,
    ):
        raise TypeError(
            "lookahead_size must be an integer."
        )

    if current_position < 0:
        raise ValueError(
            "current_position cannot be negative."
        )

    if current_position > len(data):
        raise ValueError(
            "current_position cannot be greater "
            "than the length of data."
        )

    if window_size <= 0:
        raise ValueError(
            "window_size must be greater than zero."
        )

    if lookahead_size <= 0:
        raise ValueError(
            "lookahead_size must be greater than zero."
        )



def find_longest_match(
    data: str,
    current_position: int,
    window_size: int,
    lookahead_size: int,
) -> tuple[int, int]:
    _validate_parameters(

        data=data,
        current_position=current_position,
        window_size=window_size,
        lookahead_size=lookahead_size,
    )

    if current_position >= len(data):
        return 0, 0

   
    search_start = max(
        0,
        current_position - window_size,
    )

   
    max_match_length = min(
        lookahead_size,
        len(data) - current_position,
    )

    best_offset = 0
    best_length = 0

    for match_start in range(
        search_start,
        current_position,
    ):
        offset = current_position - match_start
        match_length = 0

        while match_length < max_match_length:

            source_index = match_start + (
                match_length % offset
            )

            current_index = current_position + match_length

            if data[source_index] != data[current_index]:
                break

            match_length += 1

        
        if match_length > best_length:
            best_length = match_length
            best_offset = offset

        elif (
            match_length == best_length
            and match_length > 0
            and offset < best_offset
        ):
            best_offset = offset

    return best_offset, best_length
# ============================================================
# FILE SELECTION
# ============================================================

def select_text_file() -> Path | None:
    """Select a .txt file."""

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    try:

        file_path = filedialog.askopenfilename(
            title="Select a text file",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

    finally:

        root.destroy()

    if not file_path:
        return None

    path = Path(file_path)

    if path.suffix.lower() != TEXT_EXTENSION:

        messagebox.showerror(
            "Invalid File",
            "Please select a .txt file.",
        )

        return None

    return path


# ============================================================
# TEXT FILE READING
# ============================================================

def read_text_file(
    input_path: Path,
) -> str:
    """Read the selected text file."""

    try:

        return input_path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError as error:

        raise RuntimeError(
            "The selected file is not a valid UTF-8 "
            "text file."
        ) from error

    except OSError as error:

        raise RuntimeError(
            "Could not read the selected file:\n"
            f"{error}"
        ) from error


# ============================================================
# LZ77 TAG GENERATION
# ============================================================

def generate_lz77_tags(
    data: str,
    window_size: int,
    lookahead_size: int,
) -> list[tuple[int, int, str | None]]:
    tags = []
    current_position = 0

    while current_position < len(data):

        offset, length = find_longest_match(
            data=data,
            current_position=current_position,
            window_size=window_size,
            lookahead_size=lookahead_size,
        )

        # No match.
        if length == 0:
            next_character = data[current_position]

            tags.append(
                (0, 0, next_character)
            )

            current_position += 1
            continue

        next_position = current_position + length

        # If the match reaches the end of the input,
        # there is no next character.
        if next_position < len(data):
            next_character = data[next_position]
        else:
            next_character = None

        tags.append(
            (offset, length, next_character)
        )

        # Move past the matched text and next character.
        if next_character is None:
            current_position = len(data)
        else:
            current_position += length + 1

    return tags

# ============================================================
# TAG FORMATTING
# ============================================================

def format_lz77_tag(
    tag: tuple[int, int, str | None],
) -> str:

    offset, length, next_character = tag

    if next_character is None:

        character_text = "None"

    else:

        character_text = repr(
            next_character
        )

    return (
        f"({offset}, {length}, "
        f"{character_text})"
    )


# ============================================================
# DISPLAY HELPERS
# ============================================================

def display_character(
    character: str,
) -> str:

    if character == " ":
        return "␠"

    if character == "\n":
        return "\\n"

    if character == "\r":
        return "\\r"

    if character == "\t":
        return "\\t"

    return character


def display_buffer(
    text: str,
) -> str:

    if not text:
        return "∅"

    return "".join(
        display_character(character)
        for character in text
    )


# ============================================================
# BUFFER INFORMATION
# ============================================================

def get_buffer_positions(
    data: str,
    current_position: int,
    window_size: int,
    lookahead_size: int,
) -> tuple[
    int,
    int,
    int,
    int,
    str,
    str,
]:

    search_start = max(
        0,
        current_position - window_size,
    )

    search_end = current_position

    lookahead_start = current_position

    lookahead_end = min(
        len(data),
        current_position + lookahead_size,
    )

    search_buffer = data[
        search_start:search_end
    ]

    lookahead_buffer = data[
        lookahead_start:lookahead_end
    ]

    return (
        search_start,
        search_end,
        lookahead_start,
        lookahead_end,
        search_buffer,
        lookahead_buffer,
    )


def build_buffer_diagram(
    data: str,
    current_position: int,
    window_size: int,
    lookahead_size: int,
) -> list[str]:

    (
        search_start,
        search_end,
        lookahead_start,
        lookahead_end,
        search_buffer,
        lookahead_buffer,
    ) = get_buffer_positions(
        data=data,
        current_position=current_position,
        window_size=window_size,
        lookahead_size=lookahead_size,
    )

    search_display = display_buffer(
        search_buffer
    )

    lookahead_display = display_buffer(
        lookahead_buffer
    )

    left_width = max(
        32,
        len(search_display) + 4,
        len(
            f"positions {search_start} -> "
            f"{search_end - 1}"
        ) + 4,
    )

    right_width = max(
        36,
        len(lookahead_display) + 4,
        len(
            f"positions {lookahead_start} -> "
            f"{lookahead_end - 1}"
        ) + 4,
    )

    lines: list[str] = []

    lines.append(
        f"CURRENT POSITION = {current_position}"
    )

    lines.append("")

    arrow_left = " " * left_width

    lines.append(
        arrow_left + "↓"
    )

    lines.append(
        "─" * left_width
        + "┼"
        + "─" * right_width
    )

    lines.append(
        f"{'SEARCH BUFFER':^{left_width}}"
        + "│"
        + f"{'LOOK-AHEAD BUFFER':^{right_width}}"
    )

    if search_start < search_end:

        search_position_text = (
            f"positions {search_start} -> "
            f"{search_end - 1}"
        )

    else:

        search_position_text = (
            "positions EMPTY"
        )

    if lookahead_start < lookahead_end:

        lookahead_position_text = (
            f"positions {lookahead_start} -> "
            f"{lookahead_end - 1}"
        )

    else:

        lookahead_position_text = (
            "positions EMPTY"
        )

    lines.append(
        f"{search_position_text:^{left_width}}"
        + "│"
        + f"{lookahead_position_text:^{right_width}}"
    )

    lines.append(
        f"{search_display:^{left_width}}"
        + "│"
        + f"{lookahead_display:^{right_width}}"
    )

    lines.append(
        f"{'← max ' + str(window_size) + ' chars →':^{left_width}}"
        + "│"
        + f"{'← max ' + str(lookahead_size) + ' chars →':^{right_width}}"
    )

    lines.append(
        "─" * left_width
        + "┼"
        + "─" * right_width
    )

    lines.append(
        arrow_left + "↑"
    )

    return lines


# ============================================================
# LONGEST MATCH REPORT
# ============================================================

def build_longest_match_report(
    data: str,
    tags: list[tuple[int, int, str | None]],
    input_path: Path,
    window_size: int,
    lookahead_size: int,
) -> str:

    results: list[str] = []

    results.append("=" * 100)

    results.append(
        "LZ77 LONGEST MATCH / TAG TEST".center(100)
    )

    results.append("=" * 100)

    results.append("")

    results.append("INPUT FILE")
    results.append("-" * 100)
    results.append(str(input_path))
    results.append("")

    results.append("LZ77 SETTINGS")
    results.append("-" * 100)

    results.append(
        f"Window size          : {window_size}"
    )

    results.append(
        f"Look-ahead size      : {lookahead_size}"
    )

    results.append(
        "Window behavior      : SLIDING"
    )

    results.append(
        "Search Buffer        : moves with Current Position"
    )

    results.append(
        "Look-ahead Buffer    : moves with Current Position"
    )

    results.append(
        f"Input characters     : {len(data)}"
    )

    results.append("")

    results.append("ORIGINAL TEXT")
    results.append("-" * 100)
    results.append(repr(data))
    results.append("")

    results.append("LZ77 TAGS")
    results.append("-" * 100)

    results.append(
        "(offset, length, next_character)"
    )

    results.append("")

    if not tags:

        results.append(
            "No tags. The input file is empty."
        )

    else:

        for index, tag in enumerate(
            tags,
            start=1,
        ):

            results.append(
                f"Tag {index:<5}: "
                f"{format_lz77_tag(tag)}"
            )

    results.append("")

    results.append(
        "DETAILED TAG INFORMATION"
    )

    results.append("-" * 100)

    results.append(
        "The Search Buffer and Look-ahead Buffer slide "
        "forward with every Current Position."
    )

    results.append(
        f"Maximum Search Buffer size : {window_size}"
    )

    results.append(
        f"Maximum Look-ahead size    : {lookahead_size}"
    )

    results.append("")

    current_position = 0

    for index, tag in enumerate(
        tags,
        start=1,
    ):

        offset, length, next_character = tag

        results.append("=" * 100)

        results.append(
            f"TAG {index}"
        )

        results.append("=" * 100)

        results.append("")

        results.extend(
            build_buffer_diagram(
                data=data,
                current_position=current_position,
                window_size=window_size,
                lookahead_size=lookahead_size,
            )
        )

        results.append("")

        results.append("TAG INFORMATION")
        results.append("-" * 100)

        results.append(
            f"Tag              : "
            f"{format_lz77_tag(tag)}"
        )

        results.append(
            f"Current Position : "
            f"{current_position}"
        )

        results.append(
            f"Offset           : "
            f"{offset}"
        )

        results.append(
            f"Length           : "
            f"{length}"
        )

        results.append(
            f"Next Character   : "
            f"{next_character!r}"
        )

        results.append("")

        if length == 0:

            matched_text = ""

            if next_character is not None:

                consumed_text = next_character

            else:

                consumed_text = ""

            results.append(
                "MATCH RESULT"
            )

            results.append("-" * 100)

            results.append(
                "No previous match was found."
            )

            results.append(
                "Offset = 0"
            )

            results.append(
                "Length = 0"
            )

        else:

            matched_text = data[
                current_position:
                current_position + length
            ]

            if next_character is None:

                consumed_text = matched_text

            else:

                consumed_text = (
                    matched_text
                    + next_character
                )

            match_start = (
                current_position - offset
            )

            match_end = (
                current_position
                + length
                - 1
            )

            results.append(
                "MATCH RESULT"
            )

            results.append("-" * 100)

            results.append(
                f"Match source position : "
                f"{match_start}"
            )

            results.append(
                f"Match source end      : "
                f"{match_start + length - 1}"
            )

            results.append(
                f"Current match start   : "
                f"{current_position}"
            )

            results.append(
                f"Current match end     : "
                f"{match_end}"
            )

            results.append(
                f"Matched text          : "
                f"{matched_text!r}"
            )

        results.append("")

        results.append(
            "CONSUMPTION"
        )

        results.append("-" * 100)

        results.append(
            f"Consumed text : "
            f"{consumed_text!r}"
        )

        if next_character is None:

            results.append(
                "This tag reaches the end of the input."
            )

            results.append(
                "No next character exists."
            )

        else:

            next_position = (
                current_position
                + length
                + 1
            )

            results.append(
                f"Next Current Position : "
                f"{next_position}"
            )

        results.append("")

        if next_character is not None:

            next_position = (
                current_position
                + length
                + 1
            )

            if next_position < len(data):

                (
                    next_search_start,
                    next_search_end,
                    next_lookahead_start,
                    next_lookahead_end,
                    _,
                    _,
                ) = get_buffer_positions(
                    data=data,
                    current_position=next_position,
                    window_size=window_size,
                    lookahead_size=lookahead_size,
                )

                results.append(
                    "NEXT WINDOW POSITION"
                )

                results.append("-" * 100)

                results.append(
                    f"Next Current Position : "
                    f"{next_position}"
                )

                results.append(
                    f"Next Search Buffer     : "
                    f"positions "
                    f"{next_search_start} -> "
                    f"{next_search_end - 1}"
                )

                results.append(
                    f"Next Look-ahead       : "
                    f"positions "
                    f"{next_lookahead_start} -> "
                    f"{next_lookahead_end - 1}"
                )

                results.append("")

        if next_character is None:

            current_position = len(data)

        else:

            current_position += (
                length + 1
            )

    match_tags = [
        tag
        for tag in tags
        if tag[1] > 0
    ]

    longest_length = 0
    longest_offset = 0
    longest_tag_index = 0

    if match_tags:

        longest_length = max(
            tag[1]
            for tag in match_tags
        )

        for index, tag in enumerate(
            tags,
            start=1,
        ):

            if tag[1] == longest_length:

                longest_offset = tag[0]
                longest_tag_index = index

                break

    results.append("")

    results.append("=" * 100)

    results.append(
        "TEST SUMMARY"
    )

    results.append("=" * 100)

    results.append("")

    results.append(
        f"Total LZ77 tags      : {len(tags)}"
    )

    results.append(
        f"Tags with matches    : {len(match_tags)}"
    )

    results.append(
        f"Tags without matches : "
        f"{len(tags) - len(match_tags)}"
    )

    results.append(
        f"Original characters  : {len(data)}"
    )

    results.append(
        f"Window size          : {window_size}"
    )

    results.append(
        f"Look-ahead size      : {lookahead_size}"
    )

    results.append(
        f"Longest match length : {longest_length}"
    )

    results.append(
        f"Longest match offset : {longest_offset}"
    )

    results.append(
        f"Longest match tag    : "
        f"{longest_tag_index}"
    )

    results.append("")

    results.append("=" * 100)

    results.append(
        "END OF TEST".center(100)
    )

    results.append("=" * 100)

    return "\n".join(results)


# ============================================================
# OUTPUT FORMAT
# ============================================================

def choose_matcher_output_format() -> str | None:
    """Choose Text or Binary matcher output."""

    choice = messagebox.askyesnocancel(
        "LZ77 Matcher Result Format",
        "Choose the output format.\n\n"
        "YES  = Text Result (.txt)\n"
        "NO   = Binary Result (.lz77)\n"
        "CANCEL = Back",
    )

    if choice is True:
        return "text"

    if choice is False:
        return "binary"

    return None


# ============================================================
# OUTPUT PATHS
# ============================================================

def get_longest_match_text_output_path(
    input_path: Path,
) -> Path:

    return input_path.with_name(
        f"{input_path.stem}_longest_match.txt"
    )


def get_longest_match_binary_output_path(
    input_path: Path,
) -> Path:

    return input_path.with_name(
        f"{input_path.stem}_longest_match.lz77"
    )


# ============================================================
# TEXT RESULT
# ============================================================

def generate_text_matcher_result(
    input_path: Path,
    data: str,
    tags: list[tuple[int, int, str | None]],
    window_size: int,
    lookahead_size: int,
) -> Path:

    output_path = (
        get_longest_match_text_output_path(
            input_path
        )
    )

    report = build_longest_match_report(
        data=data,
        tags=tags,
        input_path=input_path,
        window_size=window_size,
        lookahead_size=lookahead_size,
    )

    try:

        output_path.write_text(
            report,
            encoding="utf-8",
        )

    except OSError as error:

        raise RuntimeError(
            "Could not create the text result file:\n"
            f"{error}"
        ) from error

    return output_path


# ============================================================
# BINARY RESULT
# ============================================================

def generate_binary_matcher_result(
    input_path: Path,
    tags: list[tuple[int, int, str | None]],
    window_size: int,
    lookahead_size: int,
) -> Path:

    output_path = (
        get_longest_match_binary_output_path(
            input_path
        )
    )

    try:

        write_lz77_file(
            file_path=output_path,
            tokens=tags,
            window_size=window_size,
            lookahead_size=lookahead_size,
        )

    except Exception as error:

        raise RuntimeError(
            "Could not create the binary LZ77 result:\n"
            f"{error}"
        ) from error

    return output_path


# ============================================================
# VS CODE
# ============================================================

def open_in_vscode(
    file_path: Path,
) -> None:
    """Open generated result in VS Code."""

    try:

        import subprocess

        subprocess.Popen(
            [
                "cmd.exe",
                "/c",
                "code.cmd",
                str(file_path),
            ],
            shell=False,
        )

    except FileNotFoundError:

        messagebox.showerror(
            "VS Code Not Found",
            "Visual Studio Code could not be opened.\n\n"
            "The 'code.cmd' command could not be found.",
        )

    except OSError as error:

        messagebox.showerror(
            "Open Error",
            "Could not open the file in Visual Studio Code:\n\n"
            f"{error}",
        )


def ask_open_in_vscode(
    file_path: Path,
) -> None:

    open_file = messagebox.askyesno(
        "Open in Visual Studio Code",
        "File generated successfully.\n\n"
        f"{file_path}\n\n"
        "Do you want to open it in Visual Studio Code?",
    )

    if open_file:

        open_in_vscode(
            file_path
        )


# ============================================================
# MAIN MATCHER OPERATION
# ============================================================

def test_longest_match_file() -> None:
    """
    Complete Longest-Match operation.

    This is the ONLY function that main.py needs to call.
    """

    print()
    print("=" * 70)
    print(
        "LZ77 LONGEST MATCH / TAG TEST".center(70)
    )
    print("=" * 70)

    input_path = select_text_file()

    if input_path is None:
        return

    try:

        data = read_text_file(
            input_path
        )

    except RuntimeError as error:

        messagebox.showerror(
            "Read Error",
            str(error),
        )

        return

    window_size = DEFAULT_WINDOW_SIZE
    lookahead_size = DEFAULT_LOOKAHEAD_SIZE

    output_format = (
        choose_matcher_output_format()
    )

    if output_format is None:
        return

    try:

        tags = generate_lz77_tags(
            data=data,
            window_size=window_size,
            lookahead_size=lookahead_size,
        )

    except Exception as error:

        messagebox.showerror(
            "Longest Match Error",
            "Could not generate LZ77 tags:\n\n"
            f"{error}",
        )

        return

    if output_format == "text":

        try:

            output_path = (
                generate_text_matcher_result(
                    input_path=input_path,
                    data=data,
                    tags=tags,
                    window_size=window_size,
                    lookahead_size=lookahead_size,
                )
            )

        except RuntimeError as error:

            messagebox.showerror(
                "Output Error",
                str(error),
            )

            return

        messagebox.showinfo(
            "LZ77 Text Result",
            "LZ77 matcher result generated successfully.\n\n"
            f"Total tags: {len(tags)}\n\n"
            "The report contains:\n"
            "• All tags together\n"
            "• Moving Search Buffer\n"
            "• Moving Look-ahead Buffer\n"
            "• Current Position\n"
            "• Absolute buffer positions\n"
            "• Offset / Length\n"
            "• Next Character\n"
            "• Match information\n\n"
            f"Result file:\n{output_path}",
        )

        ask_open_in_vscode(
            output_path
        )

        return

    if output_format == "binary":

        try:

            output_path = (
                generate_binary_matcher_result(
                    input_path=input_path,
                    tags=tags,
                    window_size=window_size,
                    lookahead_size=lookahead_size,
                )
            )

        except RuntimeError as error:

            messagebox.showerror(
                "Binary Output Error",
                str(error),
            )

            return

        messagebox.showinfo(
            "LZ77 Binary Result",
            "LZ77 binary matcher result generated successfully.\n\n"
            f"Total tags: {len(tags)}\n\n"
            "The binary file contains the SAME tags "
            "used by the Text Result:\n\n"
            "(offset, length, next_character)\n\n"
            f"Binary file:\n{output_path}",
        )

        return

