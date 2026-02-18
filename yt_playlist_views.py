#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "typer",
#     "httpx",
#     "python-dotenv",
# ]
# ///

"""
Query YouTube Analytics for playlist video views using video IDs from yt_playlist_videos.csv.

This script:
1. Loads video IDs from yt_playlist_videos.csv
2. Chunks them into 200-video blocks (Analytics API limit)
3. Queries YouTube Analytics API for views data in specified date range
4. Exports the combined results to CSV

Auth:
- Uses OAuth 2.0 refresh token to automatically obtain access tokens
- Requires YT_REFRESH_TOKEN, YT_CLIENT_ID, and YT_CLIENT_SECRET in environment

Scopes needed (when you obtain your refresh token):
- https://www.googleapis.com/auth/yt-analytics.readonly
"""

from __future__ import annotations

import csv
import os
from datetime import date
from typing import List, Dict, Optional
from pathlib import Path

import httpx
import typer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = typer.Typer(help="YouTube Playlist Views Analytics")

ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2/reports"


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


def load_playlist_videos(csv_file: str) -> List[Dict[str, str]]:
    """Load video data from yt_playlist_videos.csv."""
    if not Path(csv_file).exists():
        typer.echo(f"Error: {csv_file} not found", err=True)
        typer.echo("Please run yt_playlists.py first to generate the playlist videos CSV", err=True)
        raise typer.Exit(1)
    
    videos = []
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                videos.append(row)
        
        typer.echo(f"Loaded {len(videos)} videos from {csv_file}")
        return videos
        
    except Exception as e:
        typer.echo(f"Error reading {csv_file}: {e}", err=True)
        raise typer.Exit(1)


def chunk_video_ids(videos: List[Dict[str, str]], chunk_size: int = 200) -> List[List[str]]:
    """Chunk video IDs into blocks of specified size for API requests."""
    video_ids = [video["video_id"] for video in videos]
    chunks = []
    
    for i in range(0, len(video_ids), chunk_size):
        chunk = video_ids[i:i + chunk_size]
        chunks.append(chunk)
    
    typer.echo(f"Split {len(video_ids)} videos into {len(chunks)} chunks of max {chunk_size} videos")
    return chunks


def fetch_analytics_for_chunk(
    access_token: str,
    video_ids: List[str],
    start_date: str,
    end_date: str,
    timeout: float = 30.0,
) -> List[List]:
    """
    Fetch analytics data for a chunk of video IDs.
    
    Uses the video filter with comma-separated video IDs.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create filter string with video IDs
    video_filter = "video==" + ",".join(video_ids)
    
    params = {
        "ids": "channel==MINE",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,comments,likes,dislikes,estimatedMinutesWatched,averageViewDuration",
        "dimensions": "video",
        "filters": video_filter,
        "sort": "-views",
        "maxResults": "200",
    }
    
    typer.echo(f"Fetching analytics for {len(video_ids)} videos ({start_date} to {end_date})")
    
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(ANALYTICS_BASE, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            rows = data.get("rows", []) or []
            
            typer.echo(f"Retrieved {len(rows)} video analytics records")
            return rows
            
    except httpx.HTTPStatusError as e:
        typer.echo(f"HTTP error fetching analytics: {e}", err=True)
        if e.response.status_code == 400:
            typer.echo(f"Response: {e.response.text}", err=True)
        raise
    except Exception as e:
        typer.echo(f"Error fetching analytics: {e}", err=True)
        raise


def validated_date(s: Optional[str], fallback: date) -> str:
    """Validate and return date string in YYYY-MM-DD format."""
    if not s:
        return fallback.isoformat()
    try:
        # Parse YYYY-MM-DD or YYMMDD format
        if len(s) == 6 and s.isdigit():
            # Convert YYMMDD to YYYY-MM-DD
            year = "20" + s[:2]
            month = s[2:4]
            day = s[4:6]
            date_str = f"{year}-{month}-{day}"
            # Validate the date
            _ = date.fromisoformat(date_str)
            return date_str
        else:
            # Accept YYYY-MM-DD
            _ = date.fromisoformat(s)
            return s
    except ValueError:
        typer.echo(f"Invalid date: {s}. Use YYYY-MM-DD or YYMMDD format.", fg="red", err=True)
        raise typer.Exit(2)


@app.command()
def main(
    input_file: str = typer.Option(
        "yt_playlist_videos.csv",
        "--input", "-i",
        help="Input CSV file with playlist videos (from yt_playlists.py)"
    ),
    output_file: str = typer.Option(
        "yt_playlist_views.csv",
        "--output", "-o",
        help="Output CSV file for analytics data"
    ),
    start_date: Optional[str] = typer.Option(
        "240701",
        "--start-date", "-s",
        help="Start date (YYYY-MM-DD or YYMMDD format, default: 240701 for FY2024)"
    ),
    end_date: Optional[str] = typer.Option(
        "250630", 
        "--end-date", "-e",
        help="End date (YYYY-MM-DD or YYMMDD format, default: 250630 for FY2024)"
    ),
    chunk_size: int = typer.Option(
        200,
        "--chunk-size", "-c",
        help="Number of videos per API request (max 200)"
    ),
):
    """
    Query YouTube Analytics for playlist video views.
    
    Loads video IDs from yt_playlist_videos.csv, chunks them into API-friendly sizes,
    and queries YouTube Analytics for views data in the specified date range.
    
    Uses OAuth 2.0 refresh token authentication to automatically obtain access tokens.
    """
    if not (1 <= chunk_size <= 200):
        typer.echo("Error: chunk_size must be between 1 and 200", err=True)
        raise typer.Exit(1)
    
    # Validate dates
    default_start = date(2024, 7, 1)  # FY2024 start
    default_end = date(2025, 6, 30)   # FY2024 end
    s_date = validated_date(start_date, default_start)
    e_date = validated_date(end_date, default_end)
    
    # Validate date range
    start_date_obj = date.fromisoformat(s_date)
    end_date_obj = date.fromisoformat(e_date)
    if start_date_obj > end_date_obj:
        typer.echo(f"Error: Start date ({s_date}) cannot be after end date ({e_date})", err=True)
        raise typer.Exit(1)
    
    # Get access token using refresh token
    token = get_youtube_access_token()
    
    # Load playlist videos
    videos = load_playlist_videos(input_file)
    if not videos:
        typer.echo("No videos found in input file", err=True)
        raise typer.Exit(1)
    
    # Create video metadata mapping
    video_metadata = {}
    for video in videos:
        video_metadata[video["video_id"]] = {
            "playlist_id": video["playlist_id"],
            "playlist_title": video["playlist_title"],
            "video_title": video["video_title"],
            "video_published_at": video["video_published_at"]
        }
    
    # Chunk video IDs
    video_chunks = chunk_video_ids(videos, chunk_size)
    
    # Fetch analytics for each chunk
    all_analytics_rows = []
    
    for i, chunk in enumerate(video_chunks, 1):
        typer.echo(f"\nProcessing chunk {i}/{len(video_chunks)}...")
        
        try:
            rows = fetch_analytics_for_chunk(
                access_token=token,
                video_ids=chunk,
                start_date=s_date,
                end_date=e_date
            )
            all_analytics_rows.extend(rows)
            
        except Exception as e:
            typer.echo(f"Failed to fetch chunk {i}: {e}", err=True)
            typer.echo("Continuing with remaining chunks...", err=True)
            continue
    
    # Save results to CSV
    if all_analytics_rows:
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                
                # Write header
                writer.writerow([
                    "playlist_id",
                    "playlist_title",
                    "video_id",
                    "video_title",
                    "video_published_at",
                    "views", 
                    "comments", 
                    "likes", 
                    "dislikes", 
                    "estimated_minutes_watched", 
                    "average_view_duration"
                ])
                
                # Write data rows
                for row in all_analytics_rows:
                    # Ensure we have enough columns, pad with empty strings if needed
                    padded_row = row + [""] * (7 - len(row))
                    video_id = padded_row[0] if len(padded_row) > 0 else ""
                    
                    # Get metadata for this video
                    metadata = video_metadata.get(video_id, {
                        "playlist_id": "",
                        "playlist_title": "",
                        "video_title": "",
                        "video_published_at": ""
                    })
                    
                    # Combine metadata and analytics data
                    output_row = [
                        metadata["playlist_id"],
                        metadata["playlist_title"],
                        video_id,
                        metadata["video_title"],
                        metadata["video_published_at"],
                        padded_row[1] if len(padded_row) > 1 else "",  # views
                        padded_row[2] if len(padded_row) > 2 else "",  # comments
                        padded_row[3] if len(padded_row) > 3 else "",  # likes
                        padded_row[4] if len(padded_row) > 4 else "",  # dislikes
                        padded_row[5] if len(padded_row) > 5 else "",  # estimated_minutes_watched
                        padded_row[6] if len(padded_row) > 6 else "",  # average_view_duration
                    ]
                    writer.writerow(output_row)
            
            typer.echo(f"\n✅ Successfully exported {len(all_analytics_rows)} video analytics records")
            typer.echo(f"📊 Date range: {s_date} to {e_date}")
            typer.echo(f"📁 Output file: {output_file}")
            
        except Exception as e:
            typer.echo(f"❌ Failed to write CSV: {e}", err=True)
            raise typer.Exit(1)
    else:
        typer.echo("\n⚠️ No analytics data retrieved", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
