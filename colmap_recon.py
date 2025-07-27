#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "numpy",
#     "scipy",
#     "typer",
#     "pycolmap",
# ]
# ///

import os
import glob
import json
import numpy as np
import typer
from pathlib import Path
from scipy.spatial.transform import Rotation as R
import pycolmap
import platform

app = typer.Typer()

def normalize(v):
    return v / np.linalg.norm(v)

def gravity_to_quaternion(gravity_vec):
    # Make sure gravity points "down" in the world coordinate
    down = normalize(np.array(gravity_vec))
    
    # We'll assume camera's Z-axis is forward, Y-axis is up
    # So we want to rotate global -Z to align with gravity vector
    # That means: find rotation from [0, 0, -1] to gravity
    reference = np.array([0, 1, 0])  # local camera 'up'
    rotation_axis = np.cross(reference, down)
    if np.linalg.norm(rotation_axis) < 1e-8:
        return R.from_rotvec([0, 0, 0]).as_quat()  # already aligned
    angle = np.arccos(np.dot(reference, down))
    rotvec = normalize(rotation_axis) * angle
    quat = R.from_rotvec(rotvec).as_quat()  # returns [x, y, z, w]
    return np.roll(quat, 1)  # to [w, x, y, z]

def generate_images_txt(json_dir: Path, images_file: Path, camera_id: int = 1):
    image_id = 1
    json_files = list(json_dir.glob('*.json'))
    
    if not json_files:
        typer.echo(f"No JSON files found in {json_dir}", err=True)
        raise typer.Exit(1)
    
    with open(images_file, 'w') as f:
        for json_path in sorted(json_files):
            try:
                with open(json_path, 'r') as j:
                    data = json.load(j)
                    gravity = [data['x'], data['y'], data['z']]
                    qw, qx, qy, qz = gravity_to_quaternion(gravity)
                    image_name = json_path.stem + '.jpg'

                    # Translation is unknown; set to zeros
                    tx, ty, tz = 0, 0, 0
                    f.write(f'{image_id} {qw} {qx} {qy} {qz} {tx} {ty} {tz} {camera_id} {image_name}\n')
                    f.write('\n')  # Empty 2D points line
                    image_id += 1
            except (KeyError, json.JSONDecodeError) as e:
                typer.echo(f"Error processing {json_path}: {e}", err=True)
                continue

    typer.echo(f'Wrote COLMAP images.txt with {image_id - 1} entries to {images_file}')

def detect_gpu_device():
    """Detect available GPU device for Linux with AMD GPU."""
    # Check what devices are actually available in pycolmap
    available_devices = [attr for attr in dir(pycolmap.Device) if not attr.startswith('_')]
    typer.echo(f"Available devices: {available_devices}")
    
    # Prioritize OpenCL for AMD GPUs on Linux
    if hasattr(pycolmap.Device, 'opencl'):
        typer.echo("Using OpenCL for AMD GPU acceleration")
        return pycolmap.Device.opencl
    elif hasattr(pycolmap.Device, 'cuda'):
        typer.echo("OpenCL not available, trying CUDA")
        return pycolmap.Device.cuda
    else:
        typer.echo("No GPU acceleration available, using auto")
        return pycolmap.Device.auto

def run_automatic_reconstruction(
    image_dir: Path, 
    output_dir: Path, 
    images_txt: Path = None,
    quality: str = "high",
    generate_mesh: bool = False,
    use_gpu: bool = False
):
    """Run COLMAP automatic reconstruction."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set quality parameters
    quality_settings = {
        "low": {"max_image_size": 1600, "max_num_features": 4000},
        "medium": {"max_image_size": 2400, "max_num_features": 8000},
        "high": {"max_image_size": 3200, "max_num_features": 16000},
        "extreme": {"max_image_size": -1, "max_num_features": 32000}
    }
    
    settings = quality_settings.get(quality, quality_settings["high"])
    
    # Determine device
    if use_gpu:
        device = detect_gpu_device()
        typer.echo(f"Using GPU device: {device}")
    else:
        device = pycolmap.Device.cpu
        typer.echo("Using CPU")
    
    typer.echo(f"Starting automatic reconstruction with {quality} quality...")
    
    # Feature extraction
    typer.echo("Extracting features...")
    sift_options = pycolmap.SiftExtractionOptions()
    sift_options.max_image_size = settings["max_image_size"]
    sift_options.max_num_features = settings["max_num_features"]
    
    pycolmap.extract_features(
        database_path=str(output_dir / "database.db"),
        image_path=str(image_dir),
        sift_options=sift_options,
        device=device
    )
    
    # Feature matching
    typer.echo("Matching features...")
    pycolmap.match_exhaustive(database_path=str(output_dir / "database.db"))
    
    # If images.txt is provided, import it
    if images_txt and images_txt.exists():
        typer.echo(f"Importing poses from {images_txt}...")
        # Create sparse directory structure
        sparse_dir = output_dir / "sparse" / "0"
        sparse_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy images.txt to sparse directory
        import shutil
        shutil.copy2(images_txt, sparse_dir / "images.txt")
        
        # Create minimal cameras.txt and points3D.txt
        with open(sparse_dir / "cameras.txt", "w") as f:
            f.write("# Camera list with one line of data per camera:\n")
            f.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
            f.write("15001 PINHOLE 4032 3024 3000 3000 2016 1512\n")
        
        with open(sparse_dir / "points3D.txt", "w") as f:
            f.write("# 3D point list with one line of data per point:\n")
            f.write("# POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
    
    # Sparse reconstruction
    typer.echo("Running sparse reconstruction...")
    maps = pycolmap.incremental_mapping(
        database_path=str(output_dir / "database.db"),
        image_path=str(image_dir),
        output_path=str(output_dir / "sparse")
    )
    
    if not maps:
        typer.echo("Sparse reconstruction failed!", err=True)
        return
    
    typer.echo(f"Sparse reconstruction completed with {len(maps)} model(s)")
    
    # Dense reconstruction
    typer.echo("Running dense reconstruction...")
    dense_dir = output_dir / "dense"
    dense_dir.mkdir(exist_ok=True)
    
    # Use the first (usually best) sparse model
    sparse_model_path = output_dir / "sparse" / "0"
    
    pycolmap.undistort_images(
        output_path=str(dense_dir),
        input_path=str(sparse_model_path),
        image_path=str(image_dir)
    )
    
    pycolmap.patch_match_stereo(str(dense_dir))
    pycolmap.stereo_fusion(
        output_path=str(dense_dir / "fused.ply"),
        input_path=str(dense_dir)
    )
    
    if generate_mesh:
        typer.echo("Generating mesh...")
        pycolmap.poisson_mesher(
            input_path=str(dense_dir / "fused.ply"),
            output_path=str(dense_dir / "meshed-poisson.ply")
        )
        typer.echo(f"Mesh saved to {dense_dir / 'meshed-poisson.ply'}")
    
    typer.echo(f"Dense reconstruction completed! Output saved to {output_dir}")

@app.command()
def process(
    json_dir: Path = typer.Option(None, help="Directory containing JSON files with gravity data (x, y, z fields). Optional."),
    images_file: Path = typer.Option("images.txt", help="Output COLMAP images.txt file"),
    camera_id: int = typer.Option(15001, help="Camera ID to use in COLMAP format (default: iPhone 15 Pro main camera)"),
    automatic_reconstruction: bool = typer.Option(False, "--automatic-reconstruction", help="Run COLMAP automatic reconstruction"),
    image_dir: Path = typer.Option(None, help="Directory containing images for reconstruction (required with --automatic-reconstruction)"),
    reconstruction_output: Path = typer.Option("colmap_output", help="Output directory for reconstruction"),
    quality: str = typer.Option("high", help="Reconstruction quality: low, medium, high, extreme"),
    generate_mesh: bool = typer.Option(False, "--generate-mesh", help="Generate mesh from dense point cloud"),
    use_gpu: bool = typer.Option(False, "--use-gpu", help="Enable GPU acceleration (auto-detects Metal/CUDA/OpenCL)")
):
    """Generate COLMAP images.txt from gravity vector JSON files and/or run automatic reconstruction."""
    if json_dir and not json_dir.exists():
        raise typer.BadParameter(f"JSON directory does not exist: {json_dir}")
    
    if json_dir and not json_dir.is_dir():
        raise typer.BadParameter(f"JSON path is not a directory: {json_dir}")
    
    if automatic_reconstruction and not image_dir:
        raise typer.BadParameter("--image-dir is required when using --automatic-reconstruction")
    
    if automatic_reconstruction and image_dir and not image_dir.exists():
        raise typer.BadParameter(f"Image directory does not exist: {image_dir}")
    
    # Generate images.txt only if json_dir is provided
    if json_dir:
        # Ensure output directory exists
        images_file.parent.mkdir(parents=True, exist_ok=True)
        generate_images_txt(json_dir, images_file, camera_id)
        images_txt_for_recon = images_file
    else:
        images_txt_for_recon = None
    
    if automatic_reconstruction:
        run_automatic_reconstruction(
            image_dir=image_dir,
            output_dir=Path(reconstruction_output),
            images_txt=images_txt_for_recon,
            quality=quality,
            generate_mesh=generate_mesh,
            use_gpu=use_gpu
        )

if __name__ == "__main__":
    app()