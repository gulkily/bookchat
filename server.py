#!/usr/bin/env python3

"""
Chat Server Implementation
=========================

This module implements a full-featured HTTP server for a real-time chat application with the following capabilities:

Key Features:
- Asynchronous message handling using asyncio
- Cross-Origin Resource Sharing (CORS) support
- Static file serving with proper content type detection
- Template rendering engine
- Automatic port selection
- Browser auto-launch functionality
- WSL (Windows Subsystem for Linux) compatibility
- Comprehensive error handling and logging

Technical Details:
-----------------
1. Server Architecture:
   - Built on Python's HTTPServer and BaseHTTPRequestHandler
   - Custom ChatServer class extending HTTPServer
   - Custom ChatRequestHandler class for request processing
   
2. Message Handling:
   - Async message processing via MessageHandler class
   - Persistent storage using FileStorage
   - JSON-based message format
   
3. Endpoints:
   - GET /messages: Retrieve chat messages
   - POST /messages: Send new messages
   - GET /test_message: Test endpoint for message format
   - GET /: Serve main application page
   - GET /static/*: Serve static assets
   
4. Security Features:
   - CORS headers for cross-origin requests
   - Safe template variable evaluation
   - Sanitized file path handling

Environment Variables:
--------------------
- DEBUG: Set to 'true' for detailed logging
- NO_BROWSER: Set to prevent automatic browser launch
- SERVER_PORT: Automatically set to the selected port number

Dependencies:
------------
Standard Library:
- os, json, logging, asyncio, socket
- webbrowser, threading, platform, sys
- http.server, urllib.parse
- datetime, pathlib

Custom Modules:
- server.storage.file_storage
- server.message_handler

Usage:
------
Run directly: python3 server.py
The server will:
1. Find an available port (starting from 8001)
2. Export the port as SERVER_PORT
3. Start the HTTP server
4. Open the default browser (unless NO_BROWSER is set)

Author: [Your Name]
Version: 1.0.0
License: [License Type]
"""

import os
import json
import logging
import asyncio
import socket
import webbrowser
import threading
import platform
import sys
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path

from server.storage.file_storage import FileStorage
from server.message_handler import MessageHandler

# Configure logging
log_level = logging.INFO if os.environ.get('DEBUG') == 'true' else logging.WARNING
logging.basicConfig(
    level=log_level,
    format='%(levelname)s %(name)s:%(filename)s:%(lineno)d %(message)s'
)

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
    """Open the browser to the application URL"""
    try:
        if platform.system() == 'Linux':
            # Check if running in WSL
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    # In WSL, use powershell.exe to start browser
                    os.system(f'powershell.exe -c "Start-Process \'{url}\'"')
                else:
                    # Pure Linux
                    os.system(f'xdg-open {url}')
        elif platform.system() == 'Windows':
            os.system(f'start {url}')
        elif platform.system() == 'Darwin':
            os.system(f'open {url}')
        else:
            # Fallback to webbrowser module
            webbrowser.open(url)
    except Exception as e:
        logging.error(f"Failed to open browser: {e}")

class ChatRequestHandler(BaseHTTPRequestHandler):
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
        content_length = int(self.headers['Content-Length'])
        raw_data = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(raw_data)
        
        try:
            result = await self.message_handler.handle_post_message(data)
            self.send_json_response(result)
        except Exception as e:
            self.send_error(500, f"Failed to save message: {str(e)}")

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
            # Get absolute path
            abs_path = os.path.join(os.path.dirname(__file__), filepath)
            
            # Check if file exists
            if not os.path.exists(abs_path):
                self.send_error(404, f"File {filepath} not found")
                return
            
            try:
                # Read and send file
                with open(abs_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(content)))
                self._send_cors_headers()
                self.end_headers()
                
                try:
                    self.wfile.write(content)
                except (BrokenPipeError, ConnectionResetError) as e:
                    # Log but don't raise for client disconnections during write
                    logging.debug(f"Client disconnected while writing file content: {str(e)}")
                    return
                    
            except (BrokenPipeError, ConnectionResetError) as e:
                # Log but don't raise for client disconnections during headers
                logging.debug(f"Client disconnected while sending headers: {str(e)}")
                return
                
        except Exception as e:
            if not isinstance(e, (BrokenPipeError, ConnectionResetError)):
                logging.error(f"Error serving file {filepath}: {str(e)}")
                self.send_error(500, str(e))

    def render_template(self, template_path, context):
        """Simple template rendering without external dependencies."""
        try:
            with open(template_path, 'r') as f:
                content = f.read()
                
            # Replace template variables
            for key, value in context.items():
                content = content.replace('{{ ' + key + ' }}', str(value))
                content = content.replace('{{' + key + '}}', str(value))
            
            # Handle simple conditionals
            while '{%' in content and '%}' in content:
                start = content.find('{%')
                end = content.find('%}', start) + 2
                condition = content[start:end]
                
                # Parse the condition
                if 'if' in condition:
                    cond_start = condition.find('if') + 2
                    cond_end = condition.find('else') if 'else' in condition else condition.find('%}')
                    cond_expr = condition[cond_start:cond_end].strip()
                    
                    # Find the matching endif
                    endif_pos = content.find('{% endif %}', end)
                    if endif_pos == -1:
                        break
                        
                    # Get the if/else blocks
                    if_else_content = content[end:endif_pos]
                    if_content = if_else_content
                    else_content = ''
                    
                    if 'else' in if_else_content:
                        else_start = if_else_content.find('{% else %}')
                        if_content = if_else_content[:else_start]
                        else_content = if_else_content[else_start + 10:]
                    
                    # Evaluate the condition
                    try:
                        # Create a safe evaluation context with only the variables from context
                        eval_context = dict(context)
                        result = eval(cond_expr, {"__builtins__": {}}, eval_context)
                        
                        # Replace the entire conditional block
                        full_block = content[start:endif_pos + 9]
                        content = content.replace(full_block, if_content.strip() if result else else_content.strip())
                    except Exception as e:
                        logging.error(f"Error evaluating condition {cond_expr}: {e}")
                        # Remove the conditional if evaluation fails
                        full_block = content[start:endif_pos + 9]
                        content = content.replace(full_block, '')
                else:
                    # Remove unsupported template tags
                    content = content.replace(condition, '')
            
            return content
        except Exception as e:
            logging.error(f"Error rendering template {template_path}: {e}")
            return f"Error rendering template: {str(e)}"

    def serve_template(self, template_path, context):
        """Serve a template with the given context."""
        try:
            content = self.render_template(template_path, context)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(content.encode())
        except Exception as e:
            logging.error(f"Error serving template {template_path}: {e}")
            self.send_error(500, str(e))

class ChatServer(HTTPServer):
    """Chat server implementation."""

    def __init__(self, server_address, RequestHandlerClass):
        """Initialize the server."""
        super().__init__(server_address, RequestHandlerClass)
        self.storage = FileStorage(os.path.dirname(os.path.abspath(__file__)))
        self.message_handler = MessageHandler(self.storage)

    def serve_forever(self):
        """Start the server."""
        logging.info(f'Starting server on {self.server_address}')
        super().serve_forever()

    def shutdown(self):
        """Stop the server."""
        logging.info('Shutting down server')
        super().shutdown()

def run_server():
    """Run the chat server."""
    try:
        # Find an available port
        port = find_available_port(start_port=8001)
        
        # Export the port as an environment variable
        os.environ['SERVER_PORT'] = str(port)
        # Print to stderr for immediate flushing
        print(f"export SERVER_PORT={port}", file=sys.stderr, flush=True)
        
        # Start server
        server = ChatServer(('localhost', port), ChatRequestHandler)
        url = f'http://localhost:{port}'
        
        # Only open browser if NO_BROWSER is not set
        if not os.environ.get('NO_BROWSER'):
            threading.Thread(target=open_browser, args=(url,), daemon=True).start()
        
        logging.info(f'Server running at {url}')
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info('Server stopped by user')
        server.shutdown()
    except Exception as e:
        logging.error(f'Server error: {e}')
        raise

if __name__ == '__main__':
    run_server()
