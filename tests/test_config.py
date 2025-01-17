"""Tests for configuration module."""

import os
import pytest
import server.config

def test_default_config():
    """Test default configuration values."""
    assert server.config.MESSAGE_VERIFICATION is True
    assert server.config.ENABLE_FORK_SYNC is False
    assert os.path.exists(server.config.STATIC_DIR)
    assert os.path.exists(server.config.STORAGE_DIR)

def test_env_config():
    """Test configuration from environment variables."""
    # Set environment variables
    os.environ.update({
        'MESSAGE_VERIFICATION': 'false',
        'ENABLE_FORK_SYNC': 'true',
        'GITHUB_TOKEN': 'test_token',
        'GITHUB_REPO_OWNER': 'test_owner',
        'GITHUB_REPO_NAME': 'test_repo'
    })

    # Reload config
    import importlib
    importlib.reload(server.config)

    # Check values
    assert server.config.MESSAGE_VERIFICATION is False
    assert server.config.ENABLE_FORK_SYNC is True
    assert server.config.GITHUB_TOKEN == 'test_token'
    assert server.config.GITHUB_REPO_OWNER == 'test_owner'
    assert server.config.GITHUB_REPO_NAME == 'test_repo'

def test_server_config():
    """Test server configuration."""
    # Test default values
    assert server.config.HOST == '0.0.0.0'
    assert server.config.PORT == 8080
    assert server.config.DEBUG is False

    # Test custom values
    os.environ.update({
        'HOST': 'localhost',
        'PORT': '9000',
        'DEBUG': 'true'
    })

    # Reload config
    import importlib
    importlib.reload(server.config)

    # Check values
    assert server.config.HOST == 'localhost'
    assert server.config.PORT == 9000
    assert server.config.DEBUG is True
