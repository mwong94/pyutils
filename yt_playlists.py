#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "typer",
#     "httpx",
#     "python-dotenv",
# ]
# ///

import csv
import os
from typing import List, Dict

import httpx
import typer
from dotenv import load_dotenv

DEFAULT_PLAYLISTS = {
    "PL_wiEYr9F4elSk-aqOkOXyr83Ke1Nfiod": "San Diego News Now",
    "PL_wiEYr9F4enoTXh7GOieLMojfrX3VPjA": "Roundtable",
    "PL_wiEYr9F4emL21N3Z7bPWAzSeOE85DwC": "Midday Edition",
    "PL2BEE055A0FBFA666": "Evening Edition",
    "PL_wiEYr9F4elKt7wNE7IB34m3aLht1uZM": "News This Week",
}

app = typer.Typer(help="YouTube Playlist Data Extractor")


def exchange_refresh_token_for_access_token(refresh_token: str, client_id: str, client_secret: str) -> str:
    """Exchange refresh token for access token using OAuth 2.0."""
    url = "https://oauth2.googleapis.com/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(url, data=data)
            response.raise_for_status()
            token_data = response.json()
            return token_data["access_token"]
    except httpx.HTTPStatusError as e:
        typer.echo(f"HTTP error during token refresh: {e}", err=True)
        typer.echo(f"Response: {e.response.text}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error refreshing token: {e}", err=True)
        raise typer.Exit(1)


def get_youtube_access_token() -> str:
    """Get YouTube access token by refreshing the refresh token."""
    load_dotenv()
    
    refresh_token = os.getenv("YT_REFRESH_TOKEN")
    client_id = os.getenv("YT_CLIENT_ID")
    client_secret = os.getenv("YT_CLIENT_SECRET")
    
    if not refresh_token:
        typer.echo("Error: YT_REFRESH_TOKEN not found in environment variables", err=True)
        typer.echo("Please add YT_REFRESH_TOKEN to your .env file", err=True)
        raise typer.Exit(1)
    
    if not client_id:
        typer.echo("Error: YT_CLIENT_ID not found in environment variables", err=True)
        typer.echo("Please add YT_CLIENT_ID to your .env file", err=True)
        raise typer.Exit(1)
    
    if not client_secret:
        typer.echo("Error: YT_CLIENT_SECRET not found in environment variables", err=True)
        typer.echo("Please add YT_CLIENT_SECRET to your .env file", err=True)
        raise typer.Exit(1)
    
    typer.echo("🔄 Refreshing access token...")
    access_token = exchange_refresh_token_for_access_token(refresh_token, client_id, client_secret)
    typer.echo("✅ Access token refreshed successfully")
    
    return access_token


def fetch_playlist_items(
    client: httpx.Client, 
    playlist_id: str, 
    access_token: str,
    max_results: int = 50
) -> List[dict]:
    """Fetch all items from a YouTube playlist using pagination."""
    items = []
    next_page_token = None
    
    while True:
        url = "https://www.googleapis.com/youtube/v3/playlistItems"
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": max_results,
        }
        
        if next_page_token:
            params["pageToken"] = next_page_token
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
            
        typer.echo(f"Fetching playlist {playlist_id} (page token: {next_page_token or 'first page'})")
        
        try:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            items.extend(data.get("items", []))
            next_page_token = data.get("nextPageToken")
            
            if not next_page_token:
                break
                
        except httpx.HTTPStatusError as e:
            typer.echo(f"HTTP error fetching playlist {playlist_id}: {e}", err=True)
            typer.echo(f"Response: {e.response.text}", err=True)
            break
        except Exception as e:
            typer.echo(f"Error fetching playlist {playlist_id}: {e}", err=True)
            break
    
    typer.echo(f"Retrieved {len(items)} items from playlist {playlist_id}")
    return items


def fetch_video_titles(
    client: httpx.Client,
    video_ids: List[str],
    access_token: str
) -> Dict[str, str]:
    """
    Fetch video titles from YouTube Data API.
    
    Returns a dictionary mapping video_id to title.
    Batches requests to handle up to 50 video IDs per request.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    titles = {}
    
    # Batch video IDs into groups of 50 (Data API limit)
    batch_size = 50
    
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i + batch_size]
        video_ids_str = ",".join(batch)
        
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet",
            "id": video_ids_str,
        }
        
        typer.echo(f"Fetching titles for {len(batch)} videos...")
        
        try:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", [])
            
            for item in items:
                video_id = item.get("id")
                title = item.get("snippet", {}).get("title", "")
                if video_id:
                    titles[video_id] = title
            
            typer.echo(f"Retrieved {len(items)} video titles")
            
        except httpx.HTTPStatusError as e:
            typer.echo(f"HTTP error fetching video titles: {e}", err=True)
            typer.echo(f"Response: {e.response.text}", err=True)
            # Continue with remaining batches
            continue
        except Exception as e:
            typer.echo(f"Error fetching video titles: {e}", err=True)
            continue
    
    return titles


def process_playlist_items(playlist_id: str, playlist_title: str, items: List[dict]) -> List[dict]:
    """Process playlist items into the desired CSV format."""
    processed_items = []
    
    for item in items:
        snippet = item.get("snippet", {})
        video_id = snippet.get("resourceId", {}).get("videoId")
        published_at = snippet.get("publishedAt")
        
        if video_id and published_at:
            processed_items.append({
                "playlist_id": playlist_id,
                "playlist_title": playlist_title,
                "video_id": video_id,
                "video_published_at": published_at
            })
    
    return processed_items


@app.command()
def main(
    playlists: List[str] = typer.Option(
        list(DEFAULT_PLAYLISTS.keys()),
        "--playlist",
        "-p",
        help="YouTube playlist IDs to process"
    ),
    output_file: str = typer.Option(
        "yt_playlist_videos.csv",
        "--output",
        "-o",
        help="Output CSV file path"
    ),
    max_results: int = typer.Option(
        50,
        "--max-results",
        "-m",
        help="Maximum results per API request (1-50)"
    )
):
    """
    Extract video data from YouTube playlists and save to CSV.
    
    Retrieves all videos from specified playlists using the YouTube Data API v3
    and exports the data to a CSV file with columns: playlist_id, playlist_title, video_id, video_title, video_published_at.
    """
    if not (1 <= max_results <= 50):
        typer.echo("Error: max_results must be between 1 and 50", err=True)
        raise typer.Exit(1)
    
    # Get access token
    access_token = get_youtube_access_token()
    
    # Initialize HTTP client
    with httpx.Client(timeout=30.0) as client:
        all_processed_items = []
        
        typer.echo(f"Processing {len(playlists)} playlist(s)...")
        
        for playlist_id in playlists:
            playlist_title = DEFAULT_PLAYLISTS.get(playlist_id, "Unknown Playlist")
            typer.echo(f"\nProcessing playlist: {playlist_id} ({playlist_title})")
            
            # Fetch all items for this playlist
            items = fetch_playlist_items(client, playlist_id, access_token, max_results)
            
            # Process items into CSV format
            processed_items = process_playlist_items(playlist_id, playlist_title, items)
            all_processed_items.extend(processed_items)
            
            typer.echo(f"Processed {len(processed_items)} valid items from playlist {playlist_id}")
        
        # Get all unique video IDs for title fetching
        all_video_ids = list(set(item["video_id"] for item in all_processed_items))
        typer.echo(f"\n🎬 Fetching titles for {len(all_video_ids)} unique videos...")
        
        # Fetch video titles
        video_titles = fetch_video_titles(client, all_video_ids, access_token)
        typer.echo(f"Retrieved titles for {len(video_titles)} videos")
    
    # Write to CSV
    if all_processed_items:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["playlist_id", "playlist_title", "video_id", "video_title", "video_published_at"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            
            writer.writeheader()
            
            # Add titles to each item
            for item in all_processed_items:
                item["video_title"] = video_titles.get(item["video_id"], "")
            
            writer.writerows(all_processed_items)
        
        typer.echo(f"\n✅ Successfully exported {len(all_processed_items)} items to {output_file}")
    else:
        typer.echo("\n⚠️  No valid items found to export", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
