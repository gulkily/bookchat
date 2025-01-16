"""Tests for handler methods."""

import pytest
import json
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode
from server.handler_methods import serve_messages, verify_username, serve_status_page
from server.handler import ChatRequestHandler
from pathlib import Path
from datetime import datetime

def send_json_response(handler, data):
    """Helper to send JSON response."""
    response = json.dumps(data).encode('utf-8')
    handler.send_response(200)
    handler.send_header('Content-Type', 'application/json')
    handler.end_headers()
    handler.wfile.write(response)

@pytest.fixture
def mock_handler():
    """Create a mock request handler."""
    handler = MagicMock()
    handler.wfile = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.send_json_response = lambda data: send_json_response(handler, data)
    
    # Mock server and storage
    mock_storage = MagicMock()
    mock_storage.get_messages.return_value = ['test1.txt', 'test2.txt']
    mock_storage.verify_username.return_value = True
    
    mock_server = MagicMock()
    mock_server.storage = mock_storage
    handler.server = mock_server
    
    return handler

def test_serve_messages(mock_handler, tmp_path):
    """Test serving message list."""
    with patch('server.config.REPO_PATH', tmp_path):
        # Create test messages
        messages_dir = tmp_path / 'messages'
        messages_dir.mkdir(parents=True)
        (messages_dir / 'test1.txt').touch()
        (messages_dir / 'test2.txt').touch()
        
        serve_messages(mock_handler)
        
        # Verify response headers
        mock_handler.send_response.assert_called_with(200)
        mock_handler.send_header.assert_called_with('Content-Type', 'application/json')
        mock_handler.end_headers.assert_called_once()
        
        # Verify response content
        call_args = mock_handler.wfile.write.call_args[0][0]
        response = json.loads(call_args.decode('utf-8'))
        assert 'messages' in response
        assert len(response['messages']) == 2
        assert 'test1.txt' in response['messages']
        assert 'test2.txt' in response['messages']

def test_verify_username(mock_handler):
    """Test username verification."""
    # Create a proper query string
    query = urlencode({'username': 'test_user'})
    mock_handler.path = f'/verify_username?{query}'
    verify_username(mock_handler)
    
    # Verify response headers
    mock_handler.send_response.assert_called_with(200)
    mock_handler.send_header.assert_called_with('Content-Type', 'application/json')
    mock_handler.end_headers.assert_called_once()
    
    # Verify response content
    call_args = mock_handler.wfile.write.call_args[0][0]
    response = json.loads(call_args.decode('utf-8'))
    assert response['valid'] is True

def test_verify_username_invalid(mock_handler):
    """Test invalid username verification."""
    # Create a proper query string with invalid username
    query = urlencode({'username': 'test/user'})
    mock_handler.path = f'/verify_username?{query}'
    
    # Update mock storage to return False for invalid username
    mock_handler.server.storage.verify_username.return_value = False
    
    verify_username(mock_handler)
    
    # Verify response headers
    mock_handler.send_response.assert_called_with(200)
    mock_handler.send_header.assert_called_with('Content-Type', 'application/json')
    mock_handler.end_headers.assert_called_once()
    
    # Verify response content
    call_args = mock_handler.wfile.write.call_args[0][0]
    response = json.loads(call_args.decode('utf-8'))
    assert response['valid'] is False

def test_serve_status_page(mock_handler):
    """Test serving status page."""
    serve_status_page(mock_handler)
    
    # Verify response headers
    mock_handler.send_response.assert_called_with(200)
    mock_handler.send_header.assert_called_with('Content-Type', 'application/json')
    mock_handler.end_headers.assert_called_once()
    
    # Verify response content
    call_args = mock_handler.wfile.write.call_args[0][0]
    response = json.loads(call_args.decode('utf-8'))
    assert response['status'] == 'running'

def test_message_persistence(mock_handler, tmp_path):
    """Test that messages are actually persisted after posting."""
    with patch('server.config.REPO_PATH', tmp_path), \
         patch('server.handler_methods.datetime') as mock_datetime:
        
        # Setup test data
        test_content = "Test message content"
        test_username = "test_user"
        test_time = datetime(2025, 1, 16, 10, 45, 32)  # Use current time from context
        mock_datetime.now.return_value = test_time
        
        # Mock request data
        mock_handler.headers = {
            'Content-Type': 'application/json',
            'Content-Length': '100'
        }
        request_body = json.dumps({
            'content': test_content,
            'username': test_username
        }).encode('utf-8')
        mock_handler.rfile = MagicMock()
        mock_handler.rfile.read.return_value = request_body
        
        # Mock storage to simulate current failing behavior
        mock_storage = MagicMock()
        mock_storage.save_message.return_value = True
        mock_handler.server.storage = mock_storage
        
        # Create messages directory
        messages_dir = tmp_path / 'messages'
        messages_dir.mkdir(parents=True)
        
        # Mock handler methods
        mock_handler.wfile = MagicMock()
        mock_handler.send_response = MagicMock()
        mock_handler.send_header = MagicMock()
        mock_handler.end_headers = MagicMock()
        mock_handler.get_username_from_cookie = MagicMock(return_value=test_username)
        mock_handler.path = '/messages'  # Set the path for POST request
        mock_handler.handle_error = MagicMock()
        
        # Call handle_message_post directly
        from server.handler_methods import handle_message_post
        handle_message_post(mock_handler)
        
        # Verify that storage.save_message was called with correct arguments
        mock_storage.save_message.assert_called_once_with(
            test_username,
            test_content,
            test_time
        )
        
        # Verify response was sent
        mock_handler.send_response.assert_called_once_with(200)
        mock_handler.send_header.assert_called_with('Content-Type', 'application/json')
        mock_handler.end_headers.assert_called_once()
        
        # Verify response content
        response_call = mock_handler.wfile.write.call_args[0][0]
        response_data = json.loads(response_call.decode('utf-8'))
        assert response_data['success'] is True
        assert response_data['data']['content'] == test_content
        assert response_data['data']['author'] == test_username
