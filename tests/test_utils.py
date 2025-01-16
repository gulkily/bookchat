"""Tests for utility functions."""

import pytest
from unittest.mock import patch
from server.utils import find_available_port, ensure_directories
import os
from server.config import REPO_PATH

def test_find_available_port():
    """Test finding an available port."""
    port = find_available_port(start_port=8000)
    assert port >= 8000
    assert isinstance(port, int)

def test_find_available_port_no_ports():
    """Test error when no ports are available."""
    with patch('socket.socket') as mock_socket:
        mock_socket.return_value.__enter__.return_value.bind.side_effect = OSError()
        with pytest.raises(RuntimeError):
            find_available_port(start_port=8000, max_attempts=1)

def test_ensure_directories():
    """Test directory creation."""
    with patch('os.makedirs') as mock_makedirs:
        ensure_directories()
        assert mock_makedirs.call_count > 0
        mock_makedirs.assert_called_with(
            os.path.join(REPO_PATH, 'identity/public_keys'),
            exist_ok=True
        )
