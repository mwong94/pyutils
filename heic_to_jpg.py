#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pillow",
#     "pillow-heif",
#     "typer",
# ]
# ///

# typer cli application to convert a single or a directory of heic images to jpg
# allow a user to specify input/output where input and output can be a file or a directory

import typer
from pathlib import Path
from PIL import Image
import pillow_heif

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()

app = typer.Typer()

def convert_heic_to_jpg(input_path: Path, output_path: Path, quality: int = 95):
    """Convert a single HEIC file to JPG."""
    try:
        with Image.open(input_path) as img:
            # Convert to RGB if necessary (HEIC might be in other modes)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(output_path, 'JPEG', quality=quality)
        typer.echo(f"Converted: {input_path} -> {output_path}")
    except Exception as e:
        typer.echo(f"Error converting {input_path}: {e}", err=True)

@app.command()
def convert(
    input_path: Path = typer.Argument(..., help="Input HEIC file or directory"),
    output_path: Path = typer.Argument(..., help="Output JPG file or directory"),
    quality: int = typer.Option(95, help="JPEG quality (1-100)", min=1, max=100),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Process directories recursively")
):
    """Convert HEIC images to JPG format."""
    
    if not input_path.exists():
        raise typer.BadParameter(f"Input path does not exist: {input_path}")
    
    # Handle single file conversion
    if input_path.is_file():
        if input_path.suffix.lower() not in ['.heic', '.heif']:
            raise typer.BadParameter("Input file must be a HEIC/HEIF file")
        
        if output_path.is_dir():
            # Output is directory, create JPG file with same name
            output_file = output_path / f"{input_path.stem}.jpg"
        else:
            # Output is a file path
            output_file = output_path
            output_file.parent.mkdir(parents=True, exist_ok=True)
        
        convert_heic_to_jpg(input_path, output_file, quality)
        return
    
    # Handle directory conversion
    if input_path.is_dir():
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        elif not output_path.is_dir():
            raise typer.BadParameter("When input is a directory, output must also be a directory")
        
        # Find HEIC files
        pattern = "**/*.heic" if recursive else "*.heic"
        heic_files = list(input_path.glob(pattern))
        
        # Also check for .heif extension
        heif_pattern = "**/*.heif" if recursive else "*.heif"
        heic_files.extend(input_path.glob(heif_pattern))
        
        if not heic_files:
            typer.echo("No HEIC/HEIF files found in the input directory")
            return
        
        for heic_file in heic_files:
            # Maintain directory structure in output
            if recursive:
                relative_path = heic_file.relative_to(input_path)
                output_file = output_path / relative_path.with_suffix('.jpg')
                output_file.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_file = output_path / f"{heic_file.stem}.jpg"
            
            convert_heic_to_jpg(heic_file, output_file, quality)
        
        typer.echo(f"Converted {len(heic_files)} files")

if __name__ == "__main__":
    app()
