## pyutils

This repository is a collection of generally useful, but unrelated, utility scripts written in Python. Each tool is designed to solve a specific problem or automate a common task. Kinda expanded into shell scripts, but that's fine too.

Python utilities in this repo use [Typer](https://typer.dev/) to provide a modern and user-friendly command-line interface (CLI), and [uv](https://docs.astral.sh/uv/) PEP 723 inline script metadata for dependencies.

### Layout
- `media/`: `cbz.py`, `heic_to_jpg.py`, `png_icon_generator.py`, `gpx_concat.py`
- `youtube/`: `yt_playlists.py`, `yt_playlist_views.py`
- `data/`: `json_to_csv.py`, `json_splitter.py`, `icloud_news_publisher_downloads.py`
- `infra/`: `keygen.py`, `pem_splitter.py`, `uv_setup.sh`, `jupyterlab_setup.sh`, `gen_opencode_provider.py`
- `photogrammetry/`: `colmap_recon.py`, `manifold_generator.py`
- `url_checker/`: URL availability checker + cron wrapper

### Usage
Run scripts directly (uv resolves deps from the inline metadata), or put them all on your PATH:

```sh
just link          # generates symlinks in bin/
export PATH="$PATH:/path/to/pyutils/bin"
```

