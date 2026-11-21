#!/usr/bin/env python3
"""
AFDFBorderBot - Discord Bot Entry Point

This is the main entry point for the AFDFBorderBot Discord bot.
The actual bot logic is contained in the discord package.
"""

import logging
import sys
import os

logging.basicConfig(level=logging.INFO)

# Add the current directory to Python path to ensure package imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import the run_bot function from the discord package
from discord import run_bot

if __name__ == "__main__":
    run_bot()