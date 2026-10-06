"""
File browser and text I/O.

The encoder uses this module to pick a .txt file, read UTF-8 text,
and choose the .lz77 output path. It does not run LZ77 itself.
"""

from __future__ import annotations

from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

TEXT_EXTENSION = ".txt"
COMPRESSED_EXTENSION = ".lz77"


def _hidden_root() -> tk.Tk:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def select_text_file() -> Path | None:
    """Open a Windows file picker for a .txt file."""

    root = _hidden_root()
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


def select_compressed_file() -> Path | None:
    """Open a Windows file picker for a .lz77 file (decoder team)."""

    root = _hidden_root()
    try:
        file_path = filedialog.askopenfilename(
            title="Select an LZ77 compressed file",
            filetypes=[
                ("LZ77 compressed files", "*.lz77"),
                ("All files", "*.*"),
            ],
        )
    finally:
        root.destroy()

    if not file_path:
        return None

    path = Path(file_path)
    if path.suffix.lower() != COMPRESSED_EXTENSION:
        messagebox.showerror(
            "Invalid File",
            "Please select a .lz77 file.",
        )
        return None

    return path


def read_text_file(input_path: Path) -> str:
    """Read UTF-8 text. Raises RuntimeError on invalid text or I/O errors."""

    try:
        return input_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError(
            "The selected file is not a valid UTF-8 text file."
        ) from error
    except OSError as error:
        raise RuntimeError(
            f"Could not read the selected file:\n{error}"
        ) from error


def write_text_file(output_path: Path, text: str) -> None:
    """Write UTF-8 text. Used later by decompression."""

    try:
        output_path.write_text(text, encoding="utf-8")
    except OSError as error:
        raise RuntimeError(
            f"Could not write the text file:\n{error}"
        ) from error


def get_compressed_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(COMPRESSED_EXTENSION)


def get_decompressed_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_decompressed.txt")


def file_size_bytes(path: Path) -> int:
    return path.stat().st_size
