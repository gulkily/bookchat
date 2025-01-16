"""Integration tests for the server."""

import os
import threading
import time
from pathlib import Path
from datetime import datetime
import logging

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
    static_dir.mkdir(parents=True, exist_ok=True)
    db_dir = tmp_path / 'db'
    db_dir.mkdir(parents=True, exist_ok=True)
    messages_dir = tmp_path / 'messages'
    messages_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path

@pytest.fixture
def mock_git_commands():
    """Mock git commands."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = b'test_output'
        yield mock_run

@pytest.fixture
def running_server(tmp_path, server_port, mock_git_commands, monkeypatch):
    """Start a test server in a separate thread."""
    # Set up test environment
    monkeypatch.setenv('PORT', str(server_port))
    monkeypatch.setenv('REPO_PATH', str(tmp_path))
    monkeypatch.setenv('STATIC_DIR', str(tmp_path / 'static'))
    monkeypatch.setenv('MESSAGE_VERIFICATION', 'false')

    # Set up logging
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    root.addHandler(handler)

    # Create required directories
    (tmp_path / 'messages').mkdir()
    (tmp_path / 'identity').mkdir()
    (tmp_path / 'identity/public_keys').mkdir()
    
    # Create static directory and copy files
    static_dir = tmp_path / 'static'
    static_dir.mkdir()
    (static_dir / 'css').mkdir()
    (static_dir / 'js').mkdir()
    
    # Create index.html
    with open(static_dir / 'index.html', 'w') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>BookChat</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <div id="messages"></div>
    <script src="/js/main.js"></script>
</body>
</html>""")

    # Mock storage backend
    mock_storage = MagicMock()
    mock_storage.get_messages.return_value = []
    mock_storage.save_message = MagicMock()
    mock_storage.verify_username = MagicMock(return_value=True)
    
    # Add message tracking to mock
    stored_messages = []
    def mock_save_message(content, username, timestamp):
        # Create message content in Git-style format
        message_content = f"{content}\n\n-- \nAuthor: {username}\nDate: {timestamp.isoformat()}\n"
        
        # Add to stored messages in parsed format
        stored_messages.append({
            'content': content,
            'author': username,
            'timestamp': timestamp.isoformat(),
            'verified': 'true'
        })
        return True
    def mock_get_messages():
        # Return messages sorted by timestamp (newest first)
        sorted_messages = sorted(stored_messages, key=lambda x: datetime.fromisoformat(x['timestamp']).replace(tzinfo=None), reverse=True)
        return sorted_messages
        
    mock_storage.save_message.side_effect = mock_save_message
    mock_storage.get_messages.side_effect = mock_get_messages
    mock_storage.verify_username = MagicMock(return_value=True)
    
    # Set up server with mocked dependencies
    with patch('storage.factory.create_storage', return_value=mock_storage), \
         patch('server.config.REPO_PATH', tmp_path), \
         patch('server.config.STATIC_DIR', str(tmp_path / 'static')), \
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
    # Get static dir from environment
    static_dir = os.environ.get('STATIC_DIR')
    
    # Create a test file
    test_file = Path(static_dir) / 'test.txt'
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

def test_messages_appear_on_homepage(running_server):
    """Test that messages are displayed on the homepage."""
    # First create a test message
    test_message = "Test message for homepage display"
    response = requests.post(
        f'{running_server}/messages',
        json={
            'content': test_message,
            'username': 'test_user',
            'timestamp': '2025-01-16T11:21:31-05:00'  # Current time
        }
    )
    assert response.status_code == 200, f"Failed to create message: {response.text}"
    
    # Get the homepage
    response = requests.get(running_server)
    assert response.status_code == 200, "Failed to get homepage"
    
    # Wait for messages to load via JavaScript
    time.sleep(0.5)  # Give time for messages to load
    
    # Get messages from API
    response = requests.get(f'{running_server}/messages')
    assert response.status_code == 200, "Failed to get messages"
    response_data = response.json()
    print(f"API Response: {response_data}")  # Debug print
    messages = response_data['data']
    assert len(messages) > 0, "No messages returned from API"
    
    # Verify message content
    found_message = False
    for message in messages:
        if message['content'] == test_message and message['author'] == 'test_user':
            found_message = True
            break
    assert found_message, "Test message not found in API response"
