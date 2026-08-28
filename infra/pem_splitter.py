#!/usr/bin/env python3
import sys
from pathlib import Path

def format_pem(one_line_pem: str) -> str:
    # Clean up and extract header/footer
    one_line_pem = one_line_pem.strip()
    header = "-----BEGIN PRIVATE KEY-----"
    footer = "-----END PRIVATE KEY-----"

    # Remove any existing line breaks or headers/footers
    body = one_line_pem.replace(header, "").replace(footer, "").replace("\n", "").strip()

    # Split into 64-character chunks
    chunks = [body[i:i + 64] for i in range(0, len(body), 64)]

    # Reassemble
    formatted = f"{header}\n" + "\n".join(chunks) + f"\n{footer}"
    return formatted


def main():
    if len(sys.argv) != 2:
        print("Usage: python format_pem.py <input_file.txt>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: file not found: {file_path}")
        sys.exit(1)

    one_line_pem = file_path.read_text()
    formatted = format_pem(one_line_pem)

    output_path = file_path.with_suffix(".formatted.pem")
    output_path.write_text(formatted)
    print(f"✅ Formatted PEM written to: {output_path}")


if __name__ == "__main__":
    main()
