#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "typer",
# ]
# ///

'''
Convert a JSON array of objects into a CSV with a single column called "_JSON".
Each row of the CSV contains one object, encoded as a JSON string.

Usage examples
--------------
# top-level array
json_to_csv.py newsletter_mappings.json newsletter_mappings.csv

# array stored at key "data"
json_to_csv.py newsletter_mappings.json newsletter_mappings.csv --key data

# nested path, dot-notation ("payload.items")
json_to_csv.py input.json --key payload.items > output.csv
'''

from pathlib import Path
import csv
import json
import sys
import typer

app = typer.Typer(add_completion=False)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        typer.secho(f'Error: file not found: {path}', fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except json.JSONDecodeError as exc:
        typer.secho(f'Error: invalid JSON – {exc}', fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


def resolve_key(data, key: str | None):
    '''Return the array referenced by *key* (dot-delimited path) or *data* itself.'''
    if key is None:
        return data

    current = data
    for part in key.split('.'):
        if not isinstance(current, dict) or part not in current:
            typer.secho(f'Error: key path "{key}" not found', fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        current = current[part]

    return current


def write_csv(rows, dest):
    writer = csv.writer(dest)
    writer.writerow(['_JSON'])
    for obj in rows:
        writer.writerow([json.dumps(obj, ensure_ascii=False)])


@app.command()
def main(
    input_json: Path = typer.Argument(..., exists=True, readable=True,
                                      help='Path to input JSON file'),
    output_csv: Path = typer.Argument(
        None,
        file_okay=True,
        dir_okay=False,
        writable=True,
        resolve_path=True,
        help='Path to output CSV file (defaults to STDOUT)',
    ),
    key: str = typer.Option(
        None,
        '--key',
        '-k',
        help='Dot-separated path to the array inside the JSON document '
             '(e.g. "data" or "payload.items")'
    ),
):
    '''
    Convert a JSON array of objects to a single-column CSV.

    If *--key* is provided, it is treated as a dot-notation path pointing to the
    array inside the JSON object. Otherwise the top-level value must be the array.
    '''
    data = load_json(input_json)
    rows = resolve_key(data, key)

    if not isinstance(rows, list):
        typer.secho('Error: selected value is not an array of objects',
                    fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if output_csv:
        with output_csv.open('w', newline='', encoding='utf-8') as fh:
            write_csv(rows, fh)
        typer.echo(f'✓ Wrote {len(rows)} rows to {output_csv}')
    else:
        write_csv(rows, sys.stdout)


if __name__ == '__main__':
    app()