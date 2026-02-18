#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "typer",
# ]
# ///

import json
import math
import os
from pathlib import Path
from typing import List, Any
import typer
from typing_extensions import Annotated

app = typer.Typer()

def split_list(data: List[Any], num_chunks: int) -> List[List[Any]]:
    """Splits a list into n approximately equal chunks."""
    k, m = divmod(len(data), num_chunks)
    return [
        data[i * k + min(i, m):(i + 1) * k + min(i + 1, m)]
        for i in range(num_chunks)
    ]

@app.command()
def split_json(
    input_file: Annotated[Path, typer.Argument(help="Path to the input JSON file", exists=True, file_okay=True, dir_okay=False, readable=True)],
    output_dir: Annotated[Path, typer.Argument(help="Directory to write the split files to")],
    num_files: Annotated[int, typer.Option("--num-files", "-n", help="Number of files to split into")] = 2,
):
    """
    Splits a JSON file containing a list of items into multiple smaller JSON files.
    """
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        typer.echo(f"Error decoding JSON: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error reading file: {e}", err=True)
        raise typer.Exit(code=1)

    if not isinstance(data, list):
        typer.echo("Error: The root of the JSON file must be a list.", err=True)
        raise typer.Exit(code=1)

    if not data:
        typer.echo("Warning: The JSON list is empty.")
        return

    # Adjust num_files if data length is less than num_files
    if len(data) < num_files:
        typer.echo(f"Warning: Number of items ({len(data)}) is less than requested files ({num_files}). Adjusting to {len(data)} files.")
        num_files = len(data)

    chunks = split_list(data, num_files)

    input_stem = input_file.stem
    
    for i, chunk in enumerate(chunks):
        # Format index with leading zeros based on the total number of chunks
        # e.g. if 100 files, part_001, part_010, etc.
        width = len(str(num_files))
        output_filename = output_dir / f"{input_stem}_part_{i+1:0{width}d}.json"
        
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, indent=2)
            typer.echo(f"Wrote {len(chunk)} items to {output_filename}")
        except Exception as e:
             typer.echo(f"Error writing to {output_filename}: {e}", err=True)

    typer.echo(f"Successfully split {input_file} into {num_files} files in {output_dir}")

if __name__ == "__main__":
    app()

