"""Configuration module."""

import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(name)s:%(filename)s:%(lineno)d %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Environment variable names
ENV_PORT = 'PORT'
ENV_HOST = 'HOST'
ENV_DEBUG = 'DEBUG'
ENV_STORAGE_DIR = 'STORAGE_DIR'
ENV_STATIC_DIR = 'STATIC_DIR'
ENV_DATA_DIR = 'DATA_DIR'
ENV_MESSAGE_VERIFICATION = 'MESSAGE_VERIFICATION'
ENV_ENABLE_FORK_SYNC = 'ENABLE_FORK_SYNC'
ENV_GITHUB_TOKEN = 'GITHUB_TOKEN'
ENV_GITHUB_REPO_OWNER = 'GITHUB_REPO_OWNER'
ENV_GITHUB_REPO_NAME = 'GITHUB_REPO_NAME'

# Default values
DEFAULT_PORT = 8080
DEFAULT_HOST = '0.0.0.0'
DEFAULT_DEBUG = False
DEFAULT_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DEFAULT_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')

# Get values from environment variables with defaults
PORT = int(os.getenv(ENV_PORT, DEFAULT_PORT))
HOST = os.getenv(ENV_HOST, DEFAULT_HOST)
DEBUG = os.getenv(ENV_DEBUG, str(DEFAULT_DEBUG)).lower() == 'true'
STORAGE_DIR = os.getenv(ENV_STORAGE_DIR, DEFAULT_STORAGE_DIR)
STATIC_DIR = os.getenv(ENV_STATIC_DIR, DEFAULT_STATIC_DIR)

# Message verification settings
MESSAGE_VERIFICATION = os.getenv(ENV_MESSAGE_VERIFICATION, 'True').lower() == 'true'

# GitHub settings
ENABLE_FORK_SYNC = os.getenv(ENV_ENABLE_FORK_SYNC, 'False').lower() == 'true'
GITHUB_TOKEN = os.getenv(ENV_GITHUB_TOKEN)
GITHUB_REPO_OWNER = os.getenv(ENV_GITHUB_REPO_OWNER)
GITHUB_REPO_NAME = os.getenv(ENV_GITHUB_REPO_NAME)

# Create necessary directories
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Create a Path object for the project root
PROJECT_ROOT = Path(__file__).parent.parent

def get_config():
    """Get the configuration as a dictionary."""
    return {
        'PORT': PORT,
        'HOST': HOST,
        'DEBUG': DEBUG,
        'STORAGE_DIR': STORAGE_DIR,
        'STATIC_DIR': STATIC_DIR,
        'MESSAGE_VERIFICATION': MESSAGE_VERIFICATION,
        'ENABLE_FORK_SYNC': ENABLE_FORK_SYNC,
        'GITHUB_TOKEN': GITHUB_TOKEN,
        'GITHUB_REPO_OWNER': GITHUB_REPO_OWNER,
        'GITHUB_REPO_NAME': GITHUB_REPO_NAME,
        'data_dir': STORAGE_DIR,  # alias for backward compatibility
    }
