#!/usr/bin/env python3
"""
NFL Data Import Setup Script

This script verifies and installs the required dependencies for the NFL data import system.
It checks if the nfl_data_py package is installed and installs it if necessary.

Usage:
    python setup_nfl_data.py

Returns:
    0 if successful, 1 if there was an error
"""

import importlib.util
import subprocess
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def check_package_installed(package_name):
    """Check if a Python package is installed."""
    spec = importlib.util.find_spec(package_name)
    return spec is not None


def install_package(package_name):
    """Install a Python package using pip."""
    logger.info(f"Installing {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        logger.info(f"Successfully installed {package_name}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install {package_name}: {e}")
        return False


def update_conda_env():
    """Update the conda environment from environment.yml file."""
    logger.info("Updating conda environment from environment.yml...")
    try:
        # Get the path to the environment.yml file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(script_dir)
        env_file = os.path.join(backend_dir, "environment.yml")

        # Check if the file exists
        if not os.path.exists(env_file):
            logger.error(f"environment.yml not found at {env_file}")
            return False

        # Update the conda environment
        result = subprocess.run(
            ["conda", "env", "update", "-f", env_file], capture_output=True, text=True
        )

        if result.returncode != 0:
            logger.error(f"Failed to update conda environment: {result.stderr}")
            return False

        logger.info("Successfully updated conda environment")
        return True
    except Exception as e:
        logger.error(f"An error occurred while updating conda environment: {str(e)}")
        return False


def main():
    """Main function to verify and install required dependencies."""
    logger.info("Setting up NFL data import dependencies")

    # Check if nfl_data_py is installed
    if check_package_installed("nfl_data_py"):
        logger.info("nfl_data_py is already installed")
    else:
        logger.info("nfl_data_py is not installed")

        # Try to update conda environment first
        if update_conda_env():
            # Check again after update
            if check_package_installed("nfl_data_py"):
                logger.info("nfl_data_py was successfully installed via conda")
            else:
                # If still not installed, try pip
                if not install_package("nfl-data-py>=0.3.0"):
                    logger.error("Failed to install required dependencies")
                    return 1
        else:
            # If conda update failed, try pip
            if not install_package("nfl-data-py>=0.3.0"):
                logger.error("Failed to install required dependencies")
                return 1

    # Check for aiohttp (required for NFL API)
    if check_package_installed("aiohttp"):
        logger.info("aiohttp is already installed")
    else:
        logger.info("aiohttp is not installed")
        if not install_package("aiohttp>=3.8.0"):
            logger.error("Failed to install aiohttp")
            return 1

    logger.info("All required dependencies are installed")
    logger.info("You can now use the NFL data import functionality")
    logger.info("Example command to import data for the 2023 season:")
    logger.info("python backend/scripts/import_nfl_data.py --seasons 2023 --type full")

    return 0


if __name__ == "__main__":
    sys.exit(main())
