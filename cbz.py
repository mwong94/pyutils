#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "typer",
# ]
# ///


import shutil
import typer
from pathlib import Path

app = typer.Typer()


@app.command()
def main(
    directory: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="The directory to be archived.",
    ),
):
    """
    Creates a zip archive from a directory and renames it to a .cbz file.
    """
    if not any(directory.iterdir()):
        print(f"Error: Directory '{directory}' is empty.")
        raise typer.Exit(code=1)

    output_filename = shutil.make_archive(
        base_name=directory.name,
        format="zip",
        root_dir=directory.parent,
        base_dir=directory.name,
    )

    cbz_filename = Path(output_filename).with_suffix(".cbz")
    if cbz_filename.exists():
        print(f"Error: Target file '{cbz_filename}' already exists.")
        Path(output_filename).unlink()
        raise typer.Exit(code=1)

    Path(output_filename).rename(cbz_filename)

    print(f"Successfully created '{cbz_filename}'")


if __name__ == "__main__":
    app()
