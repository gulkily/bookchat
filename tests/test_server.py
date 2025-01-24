import pytest
import pytest_asyncio
import aiohttp
import asyncio
import threading
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import os
import socket
from pathlib import Path
from server.storage import FileStorage
from server.message_handler import MessageHandler
from server.utils import find_available_port
from server.handler import HTTPChatRequestHandler

class ChatServer(HTTPServer):
    """Chat server implementation."""
    def __init__(self, server_address, RequestHandlerClass):
        """Initialize the server."""
        super().__init__(server_address, RequestHandlerClass)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.storage = FileStorage(self.base_dir, test_mode=True)
        self.message_handler = MessageHandler(self.storage)

@pytest_asyncio.fixture
async def test_server():
    """Fixture to create and run a test server instance."""
    port = find_available_port(start_port=8888)
    server = ChatServer(('localhost', port), HTTPChatRequestHandler)
    
    # Start server in background
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    base_url = f'http://localhost:{port}'
    await asyncio.sleep(0.1)  # Give server time to start
    
    yield base_url
    
    server.shutdown()
    server.server_close()
    server_thread.join(timeout=5)

@pytest.mark.asyncio
async def test_messages_endpoint(test_server):
    """Test the /messages GET endpoint."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{test_server}/messages') as response:
            assert response.status == HTTPStatus.OK
            data = await response.json()
            assert 'success' in data
            assert 'messages' in data

@pytest.mark.asyncio
async def test_post_message(test_server):
    """Test posting a new message."""
    test_message = {
        'content': 'Test message',
        'author': 'test-user',
        'timestamp': datetime.now().isoformat()
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{test_server}/messages',
            json=test_message
        ) as response:
            assert response.status == HTTPStatus.OK
            data = await response.json()
            assert data['success'] is True

@pytest.mark.asyncio
async def test_cors_headers(test_server):
    """Test CORS headers are properly set."""
    async with aiohttp.ClientSession() as session:
        async with session.options(f'{test_server}/messages') as response:
            assert response.status == HTTPStatus.OK
            assert 'Access-Control-Allow-Origin' in response.headers
            assert response.headers['Access-Control-Allow-Origin'] == '*'
            assert 'Access-Control-Allow-Methods' in response.headers
            assert 'GET, POST, PUT, DELETE, OPTIONS' in response.headers['Access-Control-Allow-Methods']

@pytest.mark.asyncio
async def test_static_file_serving(test_server):
    """Test serving of static files."""
    async with aiohttp.ClientSession() as session:
        # Test index.html
        async with session.get(f'{test_server}/') as response:
            assert response.status == HTTPStatus.OK
            assert 'text/html' in response.headers['Content-Type'].lower()

        # Test non-existent file
        async with session.get(f'{test_server}/nonexistent.file') as response:
            assert response.status == HTTPStatus.NOT_FOUND

@pytest.mark.asyncio
async def test_test_message_endpoint(test_server):
    """Test the /test_message endpoint."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{test_server}/test_message') as response:
            assert response.status == HTTPStatus.OK
            data = await response.json()
            assert data['success'] is True
            assert 'data' in data
            assert all(key in data['data'] for key in ['id', 'content', 'author', 'timestamp'])

def test_find_available_port():
    """Test the port finding functionality."""
    # Test normal port finding
    port = find_available_port(start_port=8888)
    assert isinstance(port, int)
    assert port >= 8888

    # Create a socket to occupy the port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', port))
    sock.listen(1)
    
    # Test that find_available_port finds a different port
    new_port = find_available_port(start_port=port)
    assert new_port != port
    assert new_port > port
    
    # Clean up
    sock.close()

    # Create a range of occupied ports
    sockets = []
    base_port = 9000
    for i in range(10):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', base_port + i))
            sock.listen(1)
            sockets.append(sock)
        except OSError:
            pass

    # Test port exhaustion in a small range
    with pytest.raises(RuntimeError):
        find_available_port(start_port=base_port, max_tries=5)

    # Clean up
    for sock in sockets:
        sock.close()

def test_content_type_detection():
    """Test content type detection for different file types."""
    # Create a minimal handler instance
    handler = HTTPChatRequestHandler(None, None, None)
    
    # Test various file extensions
    assert handler._get_content_type('test.html') == 'text/html'
    assert handler._get_content_type('test.css') == 'text/css'
    assert handler._get_content_type('test.js') == 'application/javascript'
    assert handler._get_content_type('test.json') == 'application/json'
    assert handler._get_content_type('test.png') == 'image/png'
    assert handler._get_content_type('test.jpg') == 'image/jpeg'
    assert handler._get_content_type('test.jpeg') == 'image/jpeg'
    assert handler._get_content_type('test.gif') == 'image/gif'
    assert handler._get_content_type('test.ico') == 'image/x-icon'
    assert handler._get_content_type('test.svg') == 'image/svg+xml'
    assert handler._get_content_type('test.unknown') == 'application/octet-stream'

@pytest.mark.asyncio
async def test_invalid_json_post(test_server):
    """Test handling of invalid JSON in POST requests."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{test_server}/messages',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        ) as response:
            assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR

@pytest.mark.asyncio
async def test_missing_required_fields(test_server):
    """Test handling of missing required fields in message POST."""
    test_message = {
        'content': 'Test message'
        # missing author and timestamp
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{test_server}/messages',
            json=test_message,
            headers={'Content-Type': 'application/json'}
        ) as response:
            assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR
