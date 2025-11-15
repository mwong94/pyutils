#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "apprise",
#     "python-dotenv",
#     "requests",
#     "typer",
# ]
# ///

"""
URL Monitor - Check for URL availability and notify via Telegram
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

import apprise
import requests
import typer
from rich.console import Console
from rich.table import Table

# Load environment variables
_ = load_dotenv()

app = typer.Typer(help="Monitor URLs for availability changes")
console = Console()

TELEGRAM_APPRISE_URL = os.getenv("TELEGRAM_APPRISE_URL")
DEFAULT_STATE_FILE = Path.home() / ".url_monitor_state.json"
DEFAULT_LOG_FILE = Path.home() / ".url_monitor.log"

# Set up logger
logger = logging.getLogger("url_monitor")


def setup_logging(log_file: Path, log_level: str = "INFO") -> None:
    """Configure logging to both file and console."""
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def load_state(state_file: Path) -> dict:
    """Load previous URL states from file."""
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                logger.info(f"Loaded state from {state_file} with {len(state)} URLs")
                return state
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load state file {state_file}: {e}")
            console.print("[yellow]Warning: Could not load state file[/yellow]")
            return {}
    logger.info(f"No existing state file found at {state_file}")
    return {}


def save_state(state_file: Path, state: dict) -> None:
    """Save current URL states to file."""
    try:
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        logger.info(f"Saved state to {state_file} with {len(state)} URLs")
    except IOError as e:
        logger.error(f"Error saving state to {state_file}: {e}")
        console.print(f"[red]Error saving state: {e}[/red]")


def check_url(url: str, timeout: int = 10) -> tuple[int, str]:
    """
    Check if a URL is accessible.
    Returns tuple of (status_code, status_description)
    """
    try:
        logger.debug(f"Checking URL: {url} with timeout {timeout}s")
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        logger.debug(f"URL {url} returned status {response.status_code}")
        return response.status_code, "OK"
    except requests.exceptions.Timeout:
        logger.warning(f"URL {url} timed out after {timeout}s")
        return -1, "Timeout"
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error for URL {url}: {e}")
        return -1, "Connection Error"
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception for URL {url}: {e}")
        return -1, str(e)


def send_notification(url: str, old_status: int, new_status: int) -> bool:
    """Send Telegram notification via Apprise."""
    apobj = apprise.Apprise()
    apobj.add(TELEGRAM_APPRISE_URL)
    
    title = "🎉 URL Now Available!"
    message = f"URL is now returning 200!\n\n{url}\n\nPrevious status: {old_status}\nCurrent status: {new_status}"
    
    logger.info(f"Sending notification for {url} (status change: {old_status} → {new_status})")
    logger.debug(f"Notification title: {title}")
    logger.debug(f"Notification message: {message}")
    logger.debug(f"Telegram URL configured: {TELEGRAM_APPRISE_URL is not None}")

    try:
        result = apobj.notify(body=message, title=title)
        if result:
            logger.info(f"Successfully sent notification for {url}")
        else:
            logger.warning(f"Failed to send notification for {url}")
        return result
    except Exception as e:
        logger.error(f"Error sending notification for {url}: {e}", exc_info=True)
        console.print(f"[red]Error sending notification: {e}[/red]")
        return False


@app.command()
def check(
    urls: Optional[List[str]] = typer.Argument(None, help="URLs to check"),
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="File containing URLs (one per line)"
    ),
    notify: bool = typer.Option(
        True, "--notify/--no-notify", help="Send notifications on status changes"
    ),
    always_notify: bool = typer.Option(
        False, "--always-notify", help="Send notifications whenever a URL returns 200, even if status hasn't changed"
    ),
    state_file: Path = typer.Option(
        DEFAULT_STATE_FILE, "--state-file", "-s", help="File to store URL states"
    ),
    timeout: int = typer.Option(
        10, "--timeout", "-t", help="Request timeout in seconds"
    ),
    log_file: Path = typer.Option(
        DEFAULT_LOG_FILE, "--log-file", "-l", help="Log file location"
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    ),
) -> None:
    """
    Check a set of URLs for availability.
    
    Sends a Telegram notification when a URL changes from 404 (or any non-200 status)
    to 200 (available). With --always-notify, sends notifications for all URLs 
    returning 200, even if the status hasn't changed.
    """
    # Setup logging
    setup_logging(log_file, log_level)
    logger.info("=" * 60)
    logger.info("Starting URL check")
    logger.info(f"Log file: {log_file}")
    logger.info(f"State file: {state_file}")
    logger.info(f"Notify: {notify}, Always notify: {always_notify}")
    
    # Collect URLs from arguments or file
    urls_to_check = []
    
    if urls:
        urls_to_check.extend(urls)
        logger.info(f"Added {len(urls)} URLs from command line arguments")
    
    if file:
        if not file.exists():
            logger.error(f"URL file not found: {file}")
            console.print(f"[red]Error: File {file} not found[/red]")
            raise typer.Exit(1)
        
        try:
            with open(file, "r") as f:
                file_urls = [line.strip() for line in f if line.strip()]
                urls_to_check.extend(file_urls)
                logger.info(f"Added {len(file_urls)} URLs from file: {file}")
        except IOError as e:
            logger.error(f"Error reading URL file {file}: {e}")
            console.print(f"[red]Error reading file: {e}[/red]")
            raise typer.Exit(1)
    
    if not urls_to_check:
        logger.error("No URLs provided")
        console.print("[red]Error: No URLs provided. Use arguments or --file option[/red]")
        raise typer.Exit(1)
    
    # Ensure all URLs are properly formatted
    formatted_urls = []
    for url in urls_to_check:
        if not url.startswith("http"):
            original_url = url
            url = f"https://{url}"
            logger.debug(f"Added https:// prefix to {original_url} → {url}")
        formatted_urls.append(url)
    
    logger.info(f"Total URLs to check: {len(formatted_urls)}")
    
    # Load previous state
    previous_state = load_state(state_file)
    current_state = {}
    notifications_sent = 0
    
    # Create results table
    table = Table(title="URL Check Results")
    table.add_column("URL", style="cyan")
    table.add_column("Previous", style="magenta")
    table.add_column("Current", style="green")
    table.add_column("Status", style="yellow")
    
    # Check each URL
    with console.status("[bold green]Checking URLs...") as status:
        for url in formatted_urls:
            status.update(f"[bold green]Checking {url}...")
            
            current_status, status_desc = check_url(url, timeout)
            previous_status = previous_state.get(url, None)
            
            # Store current state
            current_state[url] = current_status
            
            # Determine what happened
            change_indicator = ""
            should_notify = False
            
            if previous_status is None:
                change_indicator = "NEW"
            elif previous_status != 200 and current_status == 200:
                change_indicator = "✅ NOW AVAILABLE"
                should_notify = True
            elif previous_status != current_status:
                change_indicator = f"CHANGED ({previous_status} → {current_status})"
            else:
                change_indicator = "NO CHANGE"
            
            # Check if we should notify for always_notify flag
            if always_notify and current_status == 200 and previous_status == 200:
                should_notify = True
                change_indicator = "NO CHANGE (notifying)"
                logger.debug(f"Always-notify enabled for {url} (200 → 200)")
            
            # Send notification if needed
            if should_notify and notify:
                if send_notification(url, previous_status, current_status):
                    notifications_sent += 1
                    if "notified" not in change_indicator and "notifying" not in change_indicator:
                        change_indicator += " (notified)"
            
            # Log the result
            logger.info(f"URL: {url} | Previous: {previous_status} | Current: {current_status} | {change_indicator}")
            
            # Add to table
            prev_display = str(previous_status) if previous_status is not None else "N/A"
            curr_display = f"{current_status} ({status_desc})" if current_status != -1 else status_desc
            table.add_row(url, prev_display, curr_display, change_indicator)
    
    # Display results
    console.print("\n")
    console.print(table)
    
    # Save current state
    save_state(state_file, current_state)
    
    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  URLs checked: {len(formatted_urls)}")
    console.print(f"  Notifications sent: {notifications_sent}")
    console.print(f"  State file: {state_file}")
    console.print(f"  Log file: {log_file}")
    
    logger.info(f"Check complete: {len(formatted_urls)} URLs checked, {notifications_sent} notifications sent")
    logger.info("=" * 60)


@app.command()
def reset(
    state_file: Path = typer.Option(
        DEFAULT_STATE_FILE, "--state-file", "-s", help="State file to reset"
    ),
    log_file: Path = typer.Option(
        DEFAULT_LOG_FILE, "--log-file", "-l", help="Log file location"
    ),
) -> None:
    """Reset the state file (clear all stored URL statuses)."""
    setup_logging(log_file)
    
    if state_file.exists():
        state_file.unlink()
        logger.info(f"State file {state_file} has been reset")
        console.print(f"[green]State file {state_file} has been reset[/green]")
    else:
        logger.info(f"State file {state_file} does not exist (nothing to reset)")
        console.print(f"[yellow]State file {state_file} does not exist[/yellow]")


@app.command()
def show_state(
    state_file: Path = typer.Option(
        DEFAULT_STATE_FILE, "--state-file", "-s", help="State file to display"
    ),
    log_file: Path = typer.Option(
        DEFAULT_LOG_FILE, "--log-file", "-l", help="Log file location"
    ),
) -> None:
    """Show the current state of monitored URLs."""
    setup_logging(log_file)
    logger.info(f"Displaying state from {state_file}")
    
    state = load_state(state_file)
    
    if not state:
        console.print("[yellow]No state data found[/yellow]")
        logger.info("No state data found")
        return
    
    table = Table(title="Current URL States")
    table.add_column("URL", style="cyan")
    table.add_column("Last Status Code", style="green")
    
    for url, status_code in state.items():
        table.add_row(url, str(status_code))
    
    console.print(table)
    console.print(f"\n[dim]State file: {state_file}[/dim]")
    logger.info(f"Displayed state for {len(state)} URLs")


if __name__ == "__main__":
    app()

