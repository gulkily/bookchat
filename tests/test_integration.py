"""Integration tests for the server."""

import os
import threading
import time
from pathlib import Path

import pytest
import requests
from unittest.mock import MagicMock, patch

from server.main import main

@pytest.fixture
def server_port():
    """Get a random port for testing."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

@pytest.fixture
def server_dirs(tmp_path):
    """Create test directories."""
    # Create required directories
    static_dir = tmp_path / 'static'
    static_dir.mkdir(parents=True)
    db_dir = tmp_path / 'db'
    db_dir.mkdir(parents=True)
    messages_dir = tmp_path / 'messages'
    messages_dir.mkdir(parents=True)
    return tmp_path

@pytest.fixture
def mock_git_commands():
    """Mock git commands."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = b'test_output'
        yield mock_run

@pytest.fixture
def running_server(server_port, server_dirs, mock_git_commands, monkeypatch):
    """Start a test server in a separate thread."""
    # Set up test environment
    monkeypatch.setenv('PORT', str(server_port))
    monkeypatch.setenv('REPO_PATH', str(server_dirs))
    monkeypatch.setenv('STATIC_DIR', str(server_dirs / 'static'))
    monkeypatch.setenv('MESSAGE_VERIFICATION', 'false')

    # Mock storage backend
    mock_storage = MagicMock()
    mock_storage.get_messages.return_value = []

    # Set up server with mocked dependencies
    with patch('storage.factory.create_storage', return_value=mock_storage), \
         patch('server.config.REPO_PATH', server_dirs), \
         patch('server.config.STATIC_DIR', str(server_dirs / 'static')), \
         patch('git_manager.Github'):

        # Start server in a thread
        server_thread = threading.Thread(target=lambda: main(open_browser_on_start=False))
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to start
        max_attempts = 10
        base_url = f'http://localhost:{server_port}'
        for attempt in range(max_attempts):
            try:
                response = requests.get(f'{base_url}/status', timeout=1)
                if response.status_code == 200:
                    break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                time.sleep(0.2)
        else:
            pytest.fail("Server failed to start")

        yield base_url

def test_server_startup(running_server):
    """Test that server starts up correctly."""
    response = requests.get(f'{running_server}/status')
    assert response.status_code == 200
    assert response.json()['status'] == 'running'

def test_static_file_serving(running_server, server_dirs):
    """Test serving static files."""
    # Create a test file
    test_file = server_dirs / 'static' / 'test.txt'
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text('test content')

    # Wait a moment for the file to be written
    time.sleep(0.1)

    # Request the file
    response = requests.get(f'{running_server}/test.txt')
    assert response.status_code == 200
    assert response.text == 'test content'

def test_message_listing(running_server):
    """Test listing messages."""
    response = requests.get(f'{running_server}/messages')
    assert response.status_code == 200
    response_data = response.json()
    assert response_data['success'] is True
    assert 'data' in response_data
    assert isinstance(response_data['data'], list)
    assert 'messageVerificationEnabled' in response_data
