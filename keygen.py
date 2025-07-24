#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "cryptography",
#     "pyperclip",
#     "typer",
# ]
# ///

import os
import typer
import pyperclip
from typing import Optional
from typing_extensions import Annotated
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

app = typer.Typer()

@app.command()
def generate_keys(
    directory: Path = typer.Option(
        Path.home() / '.ssh',
        "--directory", "-d",
        help="Directory to save the key files"
    ),
    key_name: str = typer.Option(
        "key",
        "--name", "-n",
        help="Base name for the key files"
    ),
    password_prompt: Optional[bool] = typer.Option(
        False,
        "--password", "-p",
        help="Prompt for password to encrypt the private key with (default: no encryption)"
    ),
    copy: Optional[bool] = typer.Option(
        False,
        "--copy", "-c",
        help="Copy the public key to clipboard with newlines removed (for Snowflake queries)"
    )
):
    """
    Generate a private/public key pair in PKCS8 format.
    """
    # Prompt for password
    if password_prompt:
        password = typer.prompt("Password", hide_input=True, confirmation_prompt=True)
    else:
        password = None

    # Create directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Get public key
    public_key = private_key.public_key()

    # Serialize private key with password if provided
    if password:
        encryption_algorithm = serialization.BestAvailableEncryption(password.encode())
    else:
        encryption_algorithm = serialization.NoEncryption()

    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption_algorithm
    )

    # Serialize public key
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Write keys to files
    private_key_path = directory / f"{key_name}.p8"
    public_key_path = directory / f"{key_name}.pub"

    with open(private_key_path, "wb") as f:
        f.write(private_key_bytes)

    with open(public_key_path, "wb") as f:
        f.write(public_key_bytes)

    typer.echo(f"Private key saved to: {private_key_path}")
    typer.echo(f"Public key saved to: {public_key_path}")

    # Copy public key to clipboard if requested
    if copy:
        # Read the public key and remove newlines
        with open(public_key_path, "rb") as f:
            public_key_content = f.read().decode('utf-8')

        # Remove "BEGIN PUBLIC KEY" and "END PUBLIC KEY" lines if they exist
        public_key_content = public_key_content.replace('-----BEGIN PUBLIC KEY-----', '')
        public_key_content = public_key_content.replace('-----END PUBLIC KEY-----', '')
        # Clean up any leading or trailing whitespace that might remain
        public_key_content = public_key_content.strip()

        # Remove all newlines for clean pasting into Snowflake queries
        clean_key = public_key_content.replace('\n', '')

        # Copy to clipboard
        pyperclip.copy(clean_key)
        typer.echo("Public key copied to clipboard with header/footer and newlines removed")

if __name__ == "__main__":
    app()
