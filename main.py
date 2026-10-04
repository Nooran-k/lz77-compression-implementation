from __future__ import annotations
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from lz77.matcher import test_longest_match_file
# ============================================================
# # SETTINGS
# ============================================================
TEXT_EXTENSION = ".txt"
COMPRESSED_EXTENSION = ".lz77"
# ============================================================
# MENU DISPLAY
# ============================================================

def print_separator(
    character: str = "=",
    length: int = 70,
) -> None:

    print(character * length)


def print_title(
    title: str,
) -> None:

    print()
    print_separator()
    print(f"{title:^70}")
    print_separator()


# ============================================================
# FILE SELECTION
# ============================================================

def select_text_file() -> Path | None:

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


def select_compressed_file() -> Path | None:

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

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


# ============================================================
# OUTPUT PATHS
# ============================================================

def get_compressed_output_path(
    input_path: Path,
) -> Path:

    return input_path.with_suffix(
        COMPRESSED_EXTENSION
    )


def get_decompressed_output_path(
    input_path: Path,
) -> Path:

    return input_path.with_name(
        f"{input_path.stem}_decompressed.txt"
    )

# ============================================================
# MAIN MENU
# ============================================================

def show_menu() -> None:

    while True:

        print()
        print_separator()

        print(
            "LZ77 FILE COMPRESSION TOOL".center(70)
        )

        print_separator()

        print()

        print(
            "  1. Compress a .txt file"
        )

        print(
            "  2. Decompress a .lz77 file"
        )

        print(
            "  3. Test Longest Match / LZ77 Tags"
        )

        print(
            "  4. Exit"
        )

        print()

        print_separator()

        choice = input(
            "Choose an option: "
        ).strip()

        if choice == "1":

            compression_menu()

        elif choice == "2":

            decompression_menu()

        elif choice == "3":

            test_longest_match_file()

        elif choice == "4":

            print("\nGoodbye!")
            break

        else:

            print()
            print(
                "Invalid choice."
            )

            print(
                "Please choose 1, 2, 3, or 4."
            )


# ============================================================
# ENTRY POINT
# ============================================================

def main() -> None:
    show_menu()


if __name__ == "__main__":
    main()
