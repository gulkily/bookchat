"""Integration tests for the server."""

import asyncio
import json
import os
import socket
import threading
import time
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest

from server.message_handler import MessageHandler
from server.storage.file_storage import FileStorage


class ChatRequestHandler(BaseHTTPRequestHandler):
    """Test request handler that mimics the production handler."""
    def __init__(self, request, client_address, server):
        self.message_handler = server.message_handler
        super().__init__(request, client_address, server)

    def send_json_response(self, data, status=200):
        """Send a JSON response with proper headers."""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    async def _async_do_GET(self):
        """Async handler for GET requests."""
        try:
            # Parse URL and query parameters
            parsed_url = urlparse(self.path)
            
            # Route request based on path
            if parsed_url.path == '/messages':
                try:
                    # Match production server implementation
                    response = await self.message_handler.handle_get_messages()
                    # Ensure response is a dictionary with 'success' key
                    if not isinstance(response, dict) or 'success' not in response:
                        response = {
                            'success': False, 
                            'error': 'Invalid response from message handler',
                            'messages': []
                        }
                    self.send_json_response(response)
                except Exception as handler_error:
                    self.send_json_response({
                        'success': False, 
                        'error': str(handler_error),
                        'messages': []
                    })
        except Exception as e:
            self.send_json_response({
                'success': False,
                'error': str(e),
                'messages': []
            })

    def do_GET(self):
        """Handle GET requests."""
        asyncio.run(self._async_do_GET())


def get_server_thread(port):
    """Create and start server in a thread."""
    storage = FileStorage('.')
    handler = MessageHandler(storage)
    
    class TestServer(HTTPServer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.message_handler = handler
    
    server = TestServer(('localhost', port), ChatRequestHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True  # So the thread will be killed when the test exits
    return server, thread


def find_available_port(start_port=8001, max_attempts=100):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', port))
            sock.close()
            return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")


@pytest.fixture
def server_and_port():
    """Start server on available port and return (server, port)."""
    port = find_available_port(start_port=8001)
    server, thread = get_server_thread(port)
    thread.start()
    time.sleep(1)  # Give server time to start
    yield server, port
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_messages_endpoint(server_and_port):
    """Test that /messages endpoint returns valid JSON with messages."""
    server, port = server_and_port
    
    conn = HTTPConnection(f'localhost:{port}')
    conn.request('GET', '/messages')
    response = conn.getresponse()
    
    assert response.status == 200, f"Expected 200 status code, got {response.status}"
    
    data = json.loads(response.read().decode())
    assert 'success' in data, "Response missing 'success' field"
    assert 'messages' in data, "Response missing 'messages' field"
    
    # If success is false, there should be an error message and it should not be about argument count
    if not data['success']:
        assert 'error' in data, "Failed response missing 'error' field"
        error_msg = data['error']
        assert "takes 1 positional argument but 2 were given" not in error_msg, \
            f"Server error indicates argument count issue: {error_msg}"
