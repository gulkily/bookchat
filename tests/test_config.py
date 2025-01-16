"""Tests for server configuration."""

import pytest
import os
from server import config

def test_default_config():
    """Test default configuration values."""
    assert isinstance(config.PORT, int)
    assert config.PORT >= 0
    assert isinstance(config.REPO_PATH, str)
    assert isinstance(config.MESSAGE_VERIFICATION_ENABLED, bool)
    assert os.path.basename(config.STATIC_DIR) == "static"
    assert os.path.basename(config.TEMPLATE_DIR) == "templates"
    assert config.DEFAULT_STORAGE_TYPE == "git"

def test_env_config(mock_env):
    """Test configuration with environment variables."""
    assert config.PORT == int(mock_env['PORT'])
    assert config.REPO_PATH == mock_env['REPO_PATH']
    assert config.MESSAGE_VERIFICATION_ENABLED == (
        mock_env['MESSAGE_VERIFICATION'].lower() == 'true'
    )

def test_invalid_port(monkeypatch):
    """Test handling of invalid PORT environment variable."""
    monkeypatch.setenv('PORT', 'invalid')
    with pytest.raises(ValueError):
        from importlib import reload
        reload(config)
