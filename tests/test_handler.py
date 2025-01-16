"""Tests for request handler."""

import pytest
from unittest.mock import MagicMock, patch
from server.handler import ChatRequestHandler

@pytest.fixture
def mock_handler():
    """Create a mock request handler."""
    # Create a mock request
    mock_request = MagicMock()
    mock_request.makefile.return_value.readline.return_value = b'GET / HTTP/1.1\r\n'
    
    # Create a mock server
    mock_server = MagicMock()
    mock_server.server_name = 'localhost'
    mock_server.server_port = 8000
    
    # Create a mock client address
    mock_client_address = ('127.0.0.1', 8000)
    
    # Create handler with mocked dependencies
    handler = ChatRequestHandler(mock_request, mock_client_address, mock_server)
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = MagicMock()
    
    return handler

class TestChatRequestHandler:
    """Test cases for ChatRequestHandler."""

    def test_handle_error_broken_pipe(self, mock_handler):
        """Test handling BrokenPipeError."""
        mock_handler.wfile.write.side_effect = BrokenPipeError()
        mock_handler.handle_error(404, "Not Found")
        # Should not raise an exception
        assert mock_handler.send_response.call_count == 1
        assert mock_handler.send_header.call_count == 1
        assert mock_handler.end_headers.call_count == 1

    def test_handle_error_normal(self, mock_handler):
        """Test normal error handling."""
        mock_handler.handle_error(404, "Not Found")
        mock_handler.send_response.assert_called_with(404)
        mock_handler.send_header.assert_called_with('Content-Type', 'application/json')
        mock_handler.end_headers.assert_called_once()

    def test_serve_file(self, mock_handler):
        """Test serving a file."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('http.server.SimpleHTTPRequestHandler.do_GET') as mock_do_get:
            
            mock_handler.path = '/test.txt'
            mock_handler.do_GET()
            
            mock_do_get.assert_called_once()
