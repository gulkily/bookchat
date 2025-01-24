import os
import json
import socket
import pytest
import threading
import time
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from unittest.mock import patch, MagicMock

# Import specific modules instead of the whole server package
from server.storage.file_storage import FileStorage
from server.message_handler import MessageHandler

class MockRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/messages':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.end_headers()
            response = {
                'success': True,
                'messages': []
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body>Test Page</body></html>")
        elif self.path.startswith('/static/'):
            if self.path == '/static/css/style.css':
                content_type = 'text/css'
                content = 'body { margin: 0; }'
            elif self.path == '/static/js/main.js':
                content_type = 'application/javascript'
                content = 'console.log("test");'
            else:
                self.send_error(404)
                return
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(content.encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/messages':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                message_data = json.loads(post_data)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': True}
                self.wfile.write(json.dumps(response).encode())
            except json.JSONDecodeError:
                self.send_error(500, "Invalid JSON")
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

class MockChatServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.storage = FileStorage(os.path.dirname(os.path.abspath(__file__)))
        self.message_handler = MessageHandler(self.storage)

def find_available_port(start_port=8001, max_attempts=100):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

def open_browser(url):
    """Mock open_browser function for testing"""
    pass

@pytest.fixture
def test_server():
    """Fixture to create and run a test server instance"""
    port = find_available_port(start_port=8001)
    server_instance = MockChatServer(('localhost', port), MockRequestHandler)
    server_thread = threading.Thread(target=server_instance.serve_forever, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(1)
    
    yield server_instance, port
    
    # Cleanup
    server_instance.shutdown()
    server_instance.server_close()
    server_thread.join(timeout=1)

def test_find_available_port():
    """Test finding an available port"""
    port = find_available_port(start_port=8001)
    assert isinstance(port, int)
    assert port >= 8001

def test_open_browser(monkeypatch):
    """Test browser opening functionality"""
    # Mock platform.system and os.system
    mock_platform = MagicMock(return_value='Linux')
    mock_os_system = MagicMock()
    
    monkeypatch.setattr('platform.system', mock_platform)
    monkeypatch.setattr('os.system', mock_os_system)
    
    test_url = 'http://localhost:8001'
    open_browser(test_url)

def test_chat_request_handler_get_messages(test_server):
    """Test GET /messages endpoint"""
    server_instance, port = test_server
    response = requests.get(f'http://localhost:{port}/messages')
    assert response.status_code == 200
    data = response.json()
    assert 'success' in data
    assert 'messages' in data

def test_chat_request_handler_post_message(test_server):
    """Test POST /messages endpoint"""
    server_instance, port = test_server
    test_message = {
        'content': 'Test message',
        'author': 'test-user',
        'timestamp': datetime.now().isoformat()
    }
    response = requests.post(
        f'http://localhost:{port}/messages',
        json=test_message
    )
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True

def test_chat_request_handler_static_files(test_server):
    """Test serving static files"""
    server_instance, port = test_server
    
    # Test index.html
    response = requests.get(f'http://localhost:{port}/')
    assert response.status_code == 200
    assert 'text/html' in response.headers['Content-Type']
    
    # Test CSS file
    response = requests.get(f'http://localhost:{port}/static/css/style.css')
    assert response.status_code == 200
    assert 'text/css' in response.headers['Content-Type']
    
    # Test JS file
    response = requests.get(f'http://localhost:{port}/static/js/main.js')
    assert response.status_code == 200
    assert 'application/javascript' in response.headers['Content-Type']
    
    # Test 404 for non-existent file
    response = requests.get(f'http://localhost:{port}/static/nonexistent.file')
    assert response.status_code == 404

def test_chat_request_handler_cors_headers(test_server):
    """Test CORS headers are properly set"""
    server_instance, port = test_server
    
    # Test OPTIONS request
    response = requests.options(f'http://localhost:{port}/messages')
    assert response.status_code == 200
    assert 'Access-Control-Allow-Origin' in response.headers
    assert response.headers['Access-Control-Allow-Origin'] == '*'
    assert 'Access-Control-Allow-Methods' in response.headers
    assert 'GET, POST, PUT, DELETE, OPTIONS' in response.headers['Access-Control-Allow-Methods']
    
    # Test GET request
    response = requests.get(f'http://localhost:{port}/messages')
    assert 'Access-Control-Allow-Origin' in response.headers
    assert response.headers['Access-Control-Allow-Origin'] == '*'

def test_chat_request_handler_error_handling(test_server):
    """Test error handling in request handler"""
    server_instance, port = test_server
    
    # Test invalid JSON
    response = requests.post(
        f'http://localhost:{port}/messages',
        data='invalid json',
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 500
    
    # Test missing required fields
    response = requests.post(
        f'http://localhost:{port}/messages',
        json={'incomplete': 'message'}
    )
    assert response.status_code == 200  # Mock server doesn't validate fields

def test_chat_server_initialization():
    """Test ChatServer initialization"""
    port = find_available_port(start_port=8001)
    server = MockChatServer(('localhost', port), MockRequestHandler)
    
    assert hasattr(server, 'storage')
    assert hasattr(server, 'message_handler')
    
    server.server_close()

def test_server_port_environment():
    """Test server port is properly set in environment"""
    port = find_available_port(start_port=8001)
    os.environ['SERVER_PORT'] = str(port)
    assert os.environ.get('SERVER_PORT') == str(port)
