#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "typer",
# ]
# ///

"""
GPX Concatenator - Combines multiple GPX files into a single GPX file.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

import typer

app = typer.Typer(help="Combines multiple GPX files into a single GPX file.")


@app.command()
def main(
    input_path: List[str] = typer.Argument(
        ...,
        help="Path to GPX file(s) or directory containing GPX files",
    ),
    output_file: Path = typer.Option(
        "combined.gpx",
        "--output",
        "-o",
        help="Path to the output GPX file",
    ),
):
    """
    Combines multiple GPX files into a single GPX file.
    """
    # Collect all GPX files
    gpx_files = []
    for path in input_path:
        path_obj = Path(path)
        if path_obj.is_dir():
            # If path is a directory, collect all .gpx files in it
            gpx_files.extend([str(f) for f in path_obj.glob("*.gpx")])
        elif path_obj.suffix.lower() == ".gpx":
            # If path is a .gpx file, add it to the list
            gpx_files.append(str(path_obj))
        else:
            typer.echo(f"Warning: {path} is not a GPX file or directory, skipping.")

    if not gpx_files:
        typer.echo("Error: No GPX files found.")
        sys.exit(1)

    typer.echo(f"Found {len(gpx_files)} GPX files to combine.")

    # Combine GPX files
    combined_gpx = combine_gpx_files(gpx_files)

    # Write combined GPX to output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined_gpx)

    typer.echo(f"Successfully combined {len(gpx_files)} GPX files into {output_file}")


def combine_gpx_files(gpx_files: List[str]) -> str:
    """
    Combines multiple GPX files into a single GPX file.

    Args:
        gpx_files: List of paths to GPX files

    Returns:
        String containing the combined GPX content
    """
    if not gpx_files:
        return ""

    # Parse the first GPX file to use as a base
    base_tree = ET.parse(gpx_files[0])
    base_root = base_tree.getroot()

    # Find the namespace used in the GPX file
    namespace = ""
    if "}" in base_root.tag:
        namespace = base_root.tag.split("}")[0] + "}"

    # Process the remaining GPX files
    for gpx_file in gpx_files[1:]:
        try:
            tree = ET.parse(gpx_file)
            root = tree.getroot()

            # Extract tracks and routes from the current file
            tracks = root.findall(f".//{namespace}trk") + root.findall(f".//{namespace}rte")

            # Append each track/route to the base GPX file
            for track in tracks:
                base_root.append(track)

        except Exception as e:
            typer.echo(f"Warning: Could not process {gpx_file}: {str(e)}")

    # Add XML declaration and convert the combined XML tree to a string
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    tree_str = ET.tostring(base_root, encoding="unicode")

    return xml_declaration + tree_str


if __name__ == "__main__":
    app()

