#!/bin/bash

# Cron wrapper script for url_checker.py
# This ensures proper PATH and working directory for cron execution

# Set PATH to include user binaries
export PATH="/home/max/.local/bin:$PATH"

# Change to script directory so .env is loaded correctly
cd /home/max/Documents/pyutils/url_checker/ || exit 1

# Run the url checker
/home/max/.local/bin/uv run --script /home/max/Documents/pyutils/url_checker/url_checker.py "$@"

