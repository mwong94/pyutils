#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx2>=2.4.0",
#     "typer>=0.27.1",
# ]
# ///
"""Generate an opencode provider block from an OpenAI-compatible /v1/models endpoint.

Queries the endpoint, turns every returned model id into a provider.models entry,
and either prints the block or merges it into an existing opencode.json in place.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Any, Final

import httpx2
import typer

DEFAULT_BASE_URL: Final[str] = "https://unsloth.wongfam.io/v1"
DEFAULT_PROVIDER_ID: Final[str] = "unsloth"
DEFAULT_PROVIDER_NAME: Final[str] = "Unsloth"
DEFAULT_NPM: Final[str] = "@ai-sdk/openai-compatible"
DEFAULT_CONTEXT: Final[int] = 131_072
DEFAULT_OUTPUT: Final[int] = 8_192
SCHEMA_URL: Final[str] = "https://opencode.ai/config.json"
DEFAULT_CONFIG: Final[Path] = Path.home() / ".config" / "opencode" / "opencode.json"

# id substring -> (context, output). First match wins, so order matters.
CONTEXT_HINTS: Final[tuple[tuple[str, tuple[int, int]], ...]] = (
    ("gemma-4", (262_144, 16_384)),
    ("qwen3", (262_144, 16_384)),
    ("llama", (131_072, 8_192)),
)

app = typer.Typer(add_completion=False, help=__doc__.splitlines()[0])


def fetch_models(base_url: str, api_key: str | None, timeout: float) -> list[str]:
    """Return the sorted list of model ids advertised by the endpoint."""
    url = f"{base_url.rstrip('/')}/models"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with httpx2.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx2.HTTPStatusError as exc:
        raise typer.BadParameter(f"{url} returned HTTP {exc.response.status_code}") from exc
    except httpx2.RequestError as exc:
        raise typer.BadParameter(f"could not reach {url}: {exc}") from exc
    except ValueError as exc:
        raise typer.BadParameter(f"{url} did not return JSON: {exc}") from exc

    entries = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise typer.BadParameter(f"unexpected payload from {url}: missing 'data' array")

    ids = sorted({str(item["id"]) for item in entries if isinstance(item, dict) and "id" in item})
    if not ids:
        raise typer.BadParameter(f"{url} returned no models")
    return ids


def limits_for(model_id: str) -> dict[str, int]:
    """Guess context and output limits for a model id using substring hints."""
    lowered = model_id.lower()
    for needle, (context, output) in CONTEXT_HINTS:
        if needle in lowered:
            return {"context": context, "output": output}
    return {"context": DEFAULT_CONTEXT, "output": DEFAULT_OUTPUT}


def display_name(model_id: str) -> str:
    """Derive a human-readable picker label from a model id."""
    stem = model_id.rsplit("/", 1)[-1]
    stem = re.sub(r"\.gguf$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"[-_]", " ", stem)
    return re.sub(r"\s+", " ", stem).strip()


def build_provider(
    model_ids: list[str],
    provider_name: str,
    base_url: str,
    api_key_ref: str,
) -> dict[str, Any]:
    """Assemble the provider fragment for the discovered models."""
    options: dict[str, Any] = {"baseURL": base_url.rstrip("/")}
    if api_key_ref:
        options["apiKey"] = api_key_ref
    return {
        "npm": DEFAULT_NPM,
        "name": provider_name,
        "options": options,
        "models": {
            model_id: {"name": display_name(model_id), "limit": limits_for(model_id)}
            for model_id in model_ids
        },
    }


def load_config(path: Path) -> dict[str, Any]:
    """Read an existing opencode config, returning an empty dict if absent."""
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"{path} is not valid JSON (JSONC is not supported): {exc}")
    if not isinstance(loaded, dict):
        raise typer.BadParameter(f"{path} does not contain a JSON object")
    return loaded


def merge_provider(
    config: dict[str, Any],
    generated: dict[str, Any],
    provider_id: str,
    prune: bool,
) -> dict[str, Any]:
    """Merge the generated provider into a config, preserving manual overrides."""
    config.setdefault("$schema", SCHEMA_URL)
    providers = config.setdefault("provider", {})
    existing: dict[str, Any] = providers.get(provider_id, {})

    existing_models: dict[str, Any] = existing.get("models", {})
    merged_models: dict[str, Any] = {}
    for model_id, defaults in generated["models"].items():
        merged_models[model_id] = {**defaults, **existing_models.get(model_id, {})}
    if not prune:
        for model_id, settings in existing_models.items():
            merged_models.setdefault(model_id, settings)

    providers[provider_id] = {
        **existing,
        **{k: v for k, v in generated.items() if k != "models"},
        "options": {**existing.get("options", {}), **generated["options"]},
        "models": dict(sorted(merged_models.items())),
    }
    return config


def write_config(path: Path, config: dict[str, Any]) -> None:
    """Write the config atomically so a crash cannot truncate the original."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


@app.command()
def main(
    base_url: Annotated[
        str,
        typer.Option(envvar="UNSLOTH_BASE_URL", help="OpenAI-compatible base URL, ending in /v1"),
    ] = DEFAULT_BASE_URL,
    provider_id: Annotated[
        str,
        typer.Option(help="key under 'provider' in opencode.json"),
    ] = DEFAULT_PROVIDER_ID,
    provider_name: Annotated[
        str,
        typer.Option(help="display name shown in the opencode model picker"),
    ] = DEFAULT_PROVIDER_NAME,
    api_key: Annotated[
        str | None,
        typer.Option(envvar="UNSLOTH_KEY", help="key to authenticate with and write to the config"),
    ] = None,
    api_key_ref: Annotated[
        str,
        typer.Option(help="options.apiKey when no key is given; pass '' to omit"),
    ] = "{env:UNSLOTH_KEY}",
    write: Annotated[
        bool,
        typer.Option("--write", help="merge into the config instead of printing"),
    ] = False,
    config: Annotated[
        Path,
        typer.Option(help="config to merge into when --write is given"),
    ] = DEFAULT_CONFIG,
    prune: Annotated[
        bool,
        typer.Option(help="drop configured models the endpoint no longer advertises"),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option(min=0.1, help="HTTP timeout in seconds"),
    ] = 15.0,
) -> None:
    """Fetch models, build the provider block, and print or merge it."""
    model_ids = fetch_models(base_url, api_key, timeout)
    generated = build_provider(model_ids, provider_name, base_url, api_key or api_key_ref)

    if not write:
        typer.echo(json.dumps({"$schema": SCHEMA_URL, "provider": {provider_id: generated}}, indent=2))
        return

    path = config.expanduser()
    write_config(path, merge_provider(load_config(path), generated, provider_id, prune))
    typer.echo(f"wrote {len(model_ids)} models to {path}", err=True)


if __name__ == "__main__":
    app()
