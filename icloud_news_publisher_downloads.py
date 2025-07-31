# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "playwright",
#     "python-dotenv",
#     "typer",
# ]
# ///

#!/usr/bin/env python
"""
Script to download Apple News monthly reports using Playwright.

This script:
1. Uses Playwright with Chrome to automate browser interactions
2. Logs into iCloud with provided credentials
3. Handles SMS OTP verification via console input
4. Navigates to the Apple News reports page
5. Finds the newest row in the reports table
6. Downloads all linked reports
"""
import os
import re
import time
import logging
from pathlib import Path
from typing import List, Optional

import typer
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

# Load environment variables
_ = load_dotenv()

# Constants
ICLOUD_ACCOUNT_ID=os.getenv("ICLOUD_ACCOUNT_ID")
ICLOUD_ANALYTICS_URL = (
    "https://www.icloud.com/#newspublisher/"
    f"{ICLOUD_ACCOUNT_ID}/analytics/reports"
)
ICLOUD_LOGIN_URL = "https://www.icloud.com/"

# Apple News credentials (from environment variables)
ICLOUD_EMAIL = os.getenv("ICLOUD_USERNAME")
ICLOUD_PASSWORD = os.getenv("ICLOUD_PASSWORD")

# Regex to parse filenames
FILENAME_RE = re.compile(
    r"^(?P<start_date>\d{8})_(?P<end_date>\d{8})_(?P<report_type>[A-Za-z_]+)\.csv$"
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("apple_news_downloader")

# Create Typer app
app = typer.Typer(help="Download Apple News monthly reports")


def setup_browser(headless: bool = False, download_dir: Optional[Path] = None) -> tuple[Browser, Page]:
    """
    Set up and configure the Playwright browser.
    
    Args:
        headless: Whether to run the browser in headless mode
        download_dir: Directory to save downloaded files
        
    Returns:
        Tuple of (Browser, Page) instances
    """
    import subprocess
    import sys
    
    # Ensure Chromium is installed for Playwright
    try:
        logger.info("Checking if Chromium is installed for Playwright...")
        result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                              capture_output=True, text=True, check=True)
        if result.stdout:
            logger.info("Chromium installation output: " + result.stdout.strip())
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to install Chromium: {e}")
        logger.warning("You may need to run 'playwright install chromium' manually")
    except FileNotFoundError:
        logger.warning("Playwright CLI not found. Make sure Playwright is properly installed.")

    playwright = sync_playwright().start()
    
    # Configure download behavior
    if download_dir:
        download_dir.mkdir(parents=True, exist_ok=True)
    
    # Launch Chrome browser
    browser = playwright.chromium.launch(headless=headless)
    
    # Create context with download path
    context_options = {}
    if download_dir:
        context_options["accept_downloads"] = True
    
    context = browser.new_context(**context_options)
    page = context.new_page()
    
    return browser, page


def login_with_otp(page: Page) -> bool:
    """
    Log in to iCloud with username, password, and SMS OTP.
    
    Args:
        page: Playwright Page instance
        
    Returns:
        True if login successful, False otherwise
    """
    # Ensure credentials are available
    if not ICLOUD_EMAIL or not ICLOUD_PASSWORD:
        logger.error("ICLOUD_USERNAME and ICLOUD_PASSWORD must be set")
        return False
        
    try:
        logger.info("Navigating to iCloud login page...")
        page.goto(ICLOUD_LOGIN_URL)

        # Wait for and click the initial "Sign In" button
        logger.info("Waiting for Sign In button...")
        try:
            sign_in_button = page.wait_for_selector("ui-button.sign-in-button", timeout=10000)
            if sign_in_button:
                logger.info("Clicking Sign In button...")
                sign_in_button.click()
        except PlaywrightTimeoutError:
            logger.info("Sign In button not found, proceeding to login form...")
        
        # Switch to the login iframe
        logger.info("Switching to login iframe...")
        iframe_page = page  # Default to main page
        try:
            iframe = page.wait_for_selector("iframe[name='aid-auth-widget']", timeout=10000)
            if iframe:
                frame = iframe.content_frame()
                if frame:
                    iframe_page = frame
                    logger.info("Successfully switched to login iframe")
                else:
                    logger.warning("Could not access iframe content, using main page...")
            else:
                logger.warning("Login iframe not found, using main page...")
        except PlaywrightTimeoutError:
            logger.warning("Login iframe not found, trying without iframe...")

        # Wait for login form to appear
        iframe_page.wait_for_selector("#account_name_text_field", timeout=10000)
        
        # Enter Apple ID (email)
        logger.info("Entering Apple ID...")
        email_field = iframe_page.locator("#account_name_text_field")
        email_field.clear()
        email_field.fill(ICLOUD_EMAIL)
        
        # Click continue/next button
        logger.info("Clicking continue button...")
        continue_btn = iframe_page.locator("#sign-in")
        continue_btn.click()
        
        # Wait for password field
        logger.info("Waiting for password field...")
        iframe_page.wait_for_selector("#password_text_field", timeout=10000)
        
        # Enter password
        logger.info("Entering password...")
        password_field = iframe_page.locator("#password_text_field")
        password_field.clear()
        password_field.fill(ICLOUD_PASSWORD)
        
        # Click sign in button
        sign_in_btn = iframe_page.locator("#sign-in")
        sign_in_btn.click()
        
        # Wait for either 2FA prompt or successful login
        try:
            # Check if 2FA/OTP is required
            iframe_page.wait_for_selector(".form-security-code-inputs", timeout=10000)
            
            logger.info("SMS verification code required")
            
            # Prompt user for OTP code
            otp_code = typer.prompt("Enter the SMS verification code")
            
            # Enter OTP code (usually 6 digits)
            code_inputs = iframe_page.locator(".form-security-code-input").all()
            for i, digit in enumerate(otp_code):
                if i < len(code_inputs):
                    code_inputs[i].fill(digit)
            
            logger.info("OTP code entered")
            
            # Wait for login to complete
            time.sleep(5)
            
        except PlaywrightTimeoutError:
            # No 2FA prompt appeared, might be already logged in
            logger.info("No 2FA prompt detected, continuing...")
        
        # Find and click "Trust" button after 2FA
        try:
            logger.info("Looking for Trust button...")
            trust_button = iframe_page.wait_for_selector("button:has-text('Trust')", timeout=10000)
            if trust_button:
                logger.info("Clicking Trust button...")
                trust_button.click()
                time.sleep(3)  # Wait for trust action to complete
            else:
                logger.info("Trust button not found, continuing...")
        except PlaywrightTimeoutError:
            logger.info("Trust button not found or not needed, continuing...")
        
        # Verify login success by checking for elements that appear after login
        try:
            page.wait_for_selector(".homepage-viewport", timeout=30000)
            logger.info("Login successful")
            return True
        except PlaywrightTimeoutError:
            logger.error("Login verification failed")
            return False
            
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return False


def navigate_to_reports_page(page: Page) -> bool:
    """
    Navigate to the Apple News reports page.
    
    Args:
        page: Playwright Page instance
        
    Returns:
        True if navigation successful, False otherwise
    """
    try:
        logger.info("Navigating to Apple News reports page...")
        page.goto(ICLOUD_ANALYTICS_URL)
        
        # Use frame locator to access the child application frame
        frame = page.frame_locator(".child-application")
        
        # Wait for the reports page to load within the frame
        frame.locator(".collection-body").wait_for(timeout=60000)
        
        logger.info("Reports page loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to navigate to reports page: {str(e)}")
        return False


def download_newest_reports(page: Page, download_dir: Path) -> List[Path]:
    """
    Find the newest row in the reports table and download all linked reports.
    
    Args:
        page: Playwright Page instance
        download_dir: Directory where files are downloaded
        
    Returns:
        List of paths to downloaded files
    """
    downloaded_files = []
    
    try:
        # Use frame locator to access the child application frame
        frame = page.frame_locator(".child-application")
        
        # Wait for the table to be visible
        logger.info("Waiting for reports table to load...")
        frame.locator(".collection-body").wait_for(timeout=30000)
        
        # Find all rows in the table
        rows = frame.locator(".collection-row").all()
        if not rows:
            logger.error("No report rows found in the table")
            return []

        # drop header row
        if len(rows) > 1:
            rows = rows[1:]
        
        # Find the row with "Monthly" in the first cell
        newest_row = None
        for row in rows:
            cells = row.locator('[role="cell"]').all()
            if len(cells) > 0:
                first_cell_text = cells[0].text_content()
                if first_cell_text and "Monthly" in first_cell_text:
                    newest_row = row
                    logger.info(f"Found Monthly report row: {first_cell_text}")
                    break
        
        if not newest_row:
            logger.error("No Monthly report row found")
            return []
        
        # Get the month text from the second cell
        cells = newest_row.locator('[role="cell"]').all()
        if len(cells) < 2:
            logger.error("Row doesn't have enough cells")
            return []
            
        month_text = cells[1].text_content()
        logger.info(f"Newest report is for: {month_text}")
        
        # Find download buttons in the last cell
        last_cell = cells[-1]
        download_buttons = last_cell.locator("ul li ui-button").all()
        
        if not download_buttons:
            logger.error("No download buttons found in the row")
            return []
            
        logger.info(f"Found {len(download_buttons)} download buttons")
        
        # Get the current files in the download directory to compare later
        before_files = set(download_dir.glob("*"))
        
        # Click each download button and handle downloads
        for i, button in enumerate(download_buttons):
            logger.info(f"Clicking download button {i+1}/{len(download_buttons)}")
            logger.info(button)
            
            # Set up download handler
            with page.expect_download() as download_info:
                button.click()
            
            download = download_info.value
            # Save the download to the specified directory
            download.save_as(download_dir / download.suggested_filename)
            downloaded_files.append(download_dir / download.suggested_filename)
            
            time.sleep(2)  # Give time between downloads
        
        logger.info(f"Downloaded {len(downloaded_files)} files")
        
    except Exception as e:
        logger.error(f"Error downloading reports: {str(e)}")
    
    return downloaded_files


@app.command()
def download(
    headless: bool = typer.Option(False, "--headless", "-h", help="Run browser in headless mode"),
    download_dir: Path = typer.Option(
        Path.home() / "Downloads",
        "--download-dir", "-d",
        help="Directory to save downloaded files"
    ),
    wait_time: int = typer.Option(
        10, 
        "--wait-time", "-w",
        help="Time to wait for downloads to complete in seconds"
    )
):
    """
    Download the newest Apple News monthly reports.
    """
    if not ICLOUD_EMAIL or not ICLOUD_PASSWORD:
        logger.error("ICLOUD_USERNAME and ICLOUD_PASSWORD environment variables must be set")
        raise typer.Exit(code=1)
    
    if not ICLOUD_ACCOUNT_ID:
        logger.error("ICLOUD_ACCOUNT_ID environment variable must be set")
        raise typer.Exit(code=1)
    
    logger.info(f"Setting up browser, download directory: {download_dir}")
    browser, page = setup_browser(headless=headless, download_dir=download_dir)
    
    try:
        # Login with OTP
        if not login_with_otp(page):
            logger.error("Login failed, exiting")
            raise typer.Exit(code=1)
        
        # Navigate to reports page
        if not navigate_to_reports_page(page):
            logger.error("Failed to navigate to reports page, exiting")
            raise typer.Exit(code=1)
        
        # Download reports
        downloaded_files = download_newest_reports(page, download_dir)
        
        # Wait for downloads to complete
        logger.info(f"Waiting {wait_time} seconds for downloads to complete...")
        time.sleep(wait_time)
        
        # Show results
        if downloaded_files:
            logger.info(f"Successfully downloaded {len(downloaded_files)} files:")
            for i, file in enumerate(downloaded_files):
                logger.info(f"  {i+1}. {file.name}")
        else:
            logger.warning("No files were downloaded")
            
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise typer.Exit(code=1)
    finally:
        logger.info("Closing browser")
        browser.close()


if __name__ == "__main__":
    app()
