#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pillow",
#     "typer",
# ]
# ///

import typer
from pathlib import Path
from PIL import Image

app = typer.Typer()

DEFAULT_SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]

@app.command()
def generate_icons(
    input_path: Path = typer.Argument(..., help="Path to the input PNG image."),
    output_dir: Path = typer.Option(None, help="Directory to save output PNGs. Default: '<filename>_icons'."),
    sizes: str = typer.Option(None, help="Comma-separated list of output widths (e.g. '16,32,128')")
):
    """Generate PNG icons of various sizes from a PNG image, scaling by width."""
    img = Image.open(input_path)
    max_size = img.width
    if sizes:
        try:
            requested_sizes = [int(s.strip()) for s in sizes.split(",") if s.strip()]
        except ValueError:
            raise typer.BadParameter("Sizes must be a comma-separated list of integers.")
    else:
        requested_sizes = DEFAULT_SIZES
    if output_dir is None:
        stem = input_path.stem
        output_dir = input_path.parent / f"{stem}_icons"
    output_dir.mkdir(parents=True, exist_ok=True)
    for size in requested_sizes:
        if size > max_size:
            continue
        # Calculate height to maintain aspect ratio
        aspect_ratio = img.height / img.width
        new_height = int(size * aspect_ratio)
        resized = img.resize((size, new_height), Image.Resampling.LANCZOS)
        out_path = output_dir / f"icon_{size}.png"
        resized.save(out_path, format="PNG")
        typer.echo(f"Saved {out_path}")

if __name__ == "__main__":
    app()
if __name__ == "__main__":
    app()
