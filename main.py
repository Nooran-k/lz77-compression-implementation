from __future__ import annotations

from lz77.binary_format import read_lz77_file, write_lz77_file
from lz77.compressor import compress, compression_ratio_percent, format_tags
from lz77.decompressor import decompress
from lz77.matcher import (
    DEFAULT_LOOKAHEAD_SIZE,
    DEFAULT_WINDOW_SIZE,
    test_longest_match_file,
)
from utils.file_handler import (
    COMPRESSED_EXTENSION,
    TEXT_EXTENSION,
    file_size_bytes,
    get_compressed_output_path,
    get_decompressed_output_path,
    read_text_file,
    select_compressed_file,
    select_text_file,
    write_text_file,
)


def print_separator(character: str = "=", length: int = 70) -> None:
    print(character * length)


def print_title(title: str) -> None:
    print()
    print_separator()
    print(f"{title:^70}")
    print_separator()


def compression_menu() -> None:
    print_title("COMPRESS A FILE")

    input_path = select_text_file()
    if input_path is None:
        print("No file selected.")
        return

    if input_path.suffix.lower() != TEXT_EXTENSION:
        print("Please select a .txt file.")
        return

    try:
        text = read_text_file(input_path)
    except RuntimeError as error:
        print(error)
        return

    if text == "":
        print()
        print("The selected file is empty.")
        print("An empty .lz77 file will still be written.")

    window_size = DEFAULT_WINDOW_SIZE
    lookahead_size = DEFAULT_LOOKAHEAD_SIZE

    tags = compress(
        text,
        window_size=window_size,
        lookahead_size=lookahead_size,
    )

    print()
    print("LZ77 Tags:")
    print("-" * 32)
    print(format_tags(tags))
    print("-" * 32)

    output_path = get_compressed_output_path(input_path)

    try:
        write_lz77_file(
            file_path=output_path,
            tokens=tags,
            window_size=window_size,
            lookahead_size=lookahead_size,
        )
    except (ValueError, RuntimeError) as error:
        print()
        print("Could not write the compressed file:")
        print(error)
        return

    original_size = len(text.encode("utf-8"))
    compressed_size = file_size_bytes(output_path)
    ratio = compression_ratio_percent(original_size, compressed_size)

    print()
    print("Compression completed successfully!")
    print()
    print(f"Original size   : {original_size} bytes")
    print(f"Compressed size : {compressed_size} bytes")
    if ratio >= 0:
        print(f"Compression     : {ratio:.2f}% smaller")
    else:
        print(f"Compression     : {-ratio:.2f}% larger")
        print("Note: Lossless compression cannot guarantee a smaller file")
        print("for every possible input, especially very small/random files.")
    print()
    print("Output file:")
    print(output_path)


def decompression_menu() -> None:
    print_title("DECOMPRESS A FILE")

    selected = select_compressed_file()
    if selected is None:
        print("No file selected.")
        return

    if selected.suffix.lower() != COMPRESSED_EXTENSION:
        print("Invalid LZ77 file.")
        return

    try:
        # 1. Read binary file to get LZ77 tags
        tags, window_size, lookahead_size = read_lz77_file(selected)

        # 2. Decompress tags back to text
        reconstructed_text = decompress(tags)

        # 3. Save text to output file
        output_path = get_decompressed_output_path(selected)
        write_text_file(output_path, reconstructed_text)

        print()
        print("Decompression completed successfully!")
        print(f"Tags processed: {len(tags)}")
        print(f"Reconstructed   : {len(reconstructed_text)} characters")
        print()
        print("Output file:")
        print(output_path)

    except Exception as error:
        print()
        print(f"Error during decompression: {error}")

def show_menu() -> None:
    while True:
        print()
        print_separator()
        print("LZ77 COMPRESSOR".center(70))
        print_separator()
        print()
        print("  1. Compress a file")
        print("  2. Decompress a file")
        print("  3. Test Longest Match / LZ77 Tags")
        print("  4. Exit")
        print()
        print_separator()

        choice = input("Enter your choice: ").strip()

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
            print("Invalid choice.")
            print("Please choose 1, 2, 3, or 4.")


def main() -> None:
    show_menu()


if __name__ == "__main__":
    main()
