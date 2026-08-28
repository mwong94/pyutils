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
from typing import Optional

app = typer.Typer()

DEFAULT_LIBRARY_PATH = Path("/srv/chonk/media/komga/library")


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
    destination: Optional[Path] = typer.Option(
        None,
        "--destination",
        "-d",
        help="Destination folder for the CBZ file. If relative, appended to /srv/chonk/media/komga/library.",
    ),
):
    """
    Creates a zip archive from a directory and renames it to a .cbz file.
    """
    print(f"Starting to archive directory: {directory}")

    if not any(directory.iterdir()):
        print(f"Error: Directory '{directory}' is empty.")
        raise typer.Exit(code=1)

    if destination:
        if destination.is_absolute():
            final_dest = destination
        else:
            final_dest = DEFAULT_LIBRARY_PATH / destination

        if not final_dest.exists():
            print(f"Creating destination directory: {final_dest}")
            final_dest.mkdir(parents=True, exist_ok=True)
        base_name = final_dest / directory.name
    else:
        base_name = Path.cwd() / directory.name

    # We append .cbz to the base name.
    # Note: We don't use with_suffix because directory names might contain dots
    # (e.g. "Vol.1") which we want to preserve, not replace.
    target_cbz = Path(f"{base_name}.cbz")

    if target_cbz.exists():
        print(f"Error: Target file '{target_cbz}' already exists.")
        raise typer.Exit(code=1)

    print("Creating archive...")
    output_filename = shutil.make_archive(
        base_name=str(base_name),
        format="zip",
        root_dir=directory.parent,
        base_dir=directory.name,
    )
    print(f"Archive created at: {output_filename}")

    print(f"Moving archive to: {target_cbz}")
    Path(output_filename).rename(target_cbz)

    print(f"Successfully created '{target_cbz}'")


if __name__ == "__main__":
    app()
