"""Request handler module."""

import os
import json
import logging
import asyncio
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path
from aiohttp import web

from server.storage.file_storage import FileStorage
from server.message_handler import MessageHandler
from server.handler_methods import (
    serve_messages,
    handle_message_post,
    handle_username_change,
    verify_username
)

class ChatRequestHandler:
    """Handler for chat requests."""

    def __init__(self, app):
        """Initialize the handler with app."""
        self.app = app

    async def handle_request(self, request):
        """Handle incoming request."""
        if request.method == 'GET':
            if request.path == '/messages':
                return await serve_messages(request)
            elif request.path == '/verify_username':
                return await verify_username(request)
        elif request.method == 'POST':
            if request.path == '/messages':
                return await handle_message_post(request)
            elif request.path == '/change_username':
                return await handle_username_change(request)
        
        # Return 404 for unknown paths
        return web.Response(status=404, text='Not found')

class HTTPChatRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for chat requests."""
    
    def __init__(self, request, client_address, server):
        """Initialize the request handler."""
        if request is None and client_address is None and server is None:
            # For testing only
            self.server = None
            return
        super().__init__(request, client_address, server)

    def initialize(self, server):
        """Initialize request handler with storage and message handler."""
        self.message_handler = server.message_handler

    def setup(self):
        """Set up the handler."""
        super().setup()
        self.initialize(self.server)

    def _send_cors_headers(self):
        """Send CORS headers for all responses."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def send_json_response(self, data, status=200):
        """Send a JSON response with proper headers."""
        try:
            response = json.dumps(data)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(response.encode())
        except Exception as e:
            logging.error(f"Error sending JSON response: {e}")
            self.send_error(500, str(e))

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        asyncio.run(self._async_do_GET())

    async def _async_do_GET(self):
        """Async handler for GET requests."""
        try:
            # Parse URL and query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # Route request based on path
            if parsed_url.path == '/messages':
                try:
                    response = await self.message_handler.handle_get_messages()  # Don't pass self
                    # Ensure response is a dictionary with 'success' key
                    if not isinstance(response, dict) or 'success' not in response:
                        response = {
                            'success': False, 
                            'error': 'Invalid response from message handler',
                            'messages': []
                        }
                    self.send_json_response(response)
                except Exception as handler_error:
                    logging.error(f"Error in message handler: {handler_error}", exc_info=True)
                    self.send_json_response({
                        'success': False, 
                        'error': str(handler_error),
                        'messages': []
                    })
            elif parsed_url.path == '/test_message':
                # Test route to check message format
                test_message = {
                    'success': True,
                    'data': {
                        'id': 'test-123',
                        'content': 'Test message',
                        'author': 'test-user',
                        'timestamp': datetime.now().isoformat()
                    }
                }
                logging.info(f"Test message response: {test_message}")
                self.send_json_response(test_message)
            elif parsed_url.path == '/' or parsed_url.path == '/index.html':
                self.serve_file('templates/index.html', 'text/html')
            elif parsed_url.path == '/favicon.ico':
                try:
                    self.serve_file('static/favicon.ico', 'image/x-icon')
                except (BrokenPipeError, ConnectionResetError) as e:
                    # Log but don't raise for favicon request disconnections
                    logging.debug(f"Client disconnected during favicon request: {str(e)}")
                    return
            elif parsed_url.path.startswith('/static/'):
                # Remove /static/ prefix to get relative path
                rel_path = parsed_url.path[8:]  # len('/static/') == 8
                content_type = self._get_content_type(rel_path)
                self.serve_file(os.path.join('static', rel_path), content_type)
            else:
                self.send_error(404, "Path not found")
                
        except Exception as e:
            if not isinstance(e, (BrokenPipeError, ConnectionResetError)):
                logging.error(f"Error handling GET request: {str(e)}", exc_info=True)
                self.send_error(500, str(e))

    async def _async_do_POST(self):
        """Async handler for POST requests."""
        try:
            content_length = int(self.headers['Content-Length'])
            raw_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError as e:
                self.send_error(500, f"Invalid JSON: {str(e)}")
                return

            # Validate required fields
            if not all(key in data for key in ['content', 'author', 'timestamp']):
                self.send_error(500, "Missing required fields: content, author, timestamp")
                return

            result = await self.message_handler.handle_post_message(data)
            self.send_json_response(result)
        except Exception as e:
            self.send_error(500, f"Failed to process message: {str(e)}")

    def do_POST(self):
        """Handle POST requests."""
        asyncio.run(self._async_do_POST())

    def _get_content_type(self, path):
        """Get content type based on file extension."""
        ext = os.path.splitext(path)[1].lower()
        return {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.ico': 'image/x-icon',
            '.svg': 'image/svg+xml'
        }.get(ext, 'application/octet-stream')

    def serve_file(self, filepath, content_type):
        """Helper method to serve a file with specified content type"""
        try:
            # Get absolute path using server's base directory if available
            base_dir = getattr(self.server, 'base_dir', os.path.dirname(__file__))
            abs_path = os.path.join(base_dir, filepath)
            
            # Check if file exists
            if not os.path.exists(abs_path):
                self.send_error(404, f"File {filepath} not found")
                return

            # Read file and send response
            with open(abs_path, 'rb') as f:
                content = f.read()

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            logging.error(f"Error serving file {filepath}: {str(e)}")
            self.send_error(500, str(e))
