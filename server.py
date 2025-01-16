#!/usr/bin/env python3

import os
import json
import logging
import asyncio
import socket
import webbrowser
import threading
import platform
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path

from storage.file_storage import FileStorage
from server.message_handler import MessageHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
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
    def __init__(self, request, client_address, server):
        """Initialize request handler with storage and message handler."""
        self.message_handler = server.message_handler
        super().__init__(request, client_address, server)

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
                response = await self.message_handler.handle_get_messages(self)
                self.send_json_response(response)
            elif parsed_url.path == '/' or parsed_url.path == '/index.html':
                self.serve_file('templates/chat.html', 'text/html')
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
                logging.error(f"Error handling GET request: {str(e)}")
                self.send_error(500, str(e))

    def do_POST(self):
        """Handle POST requests."""
        asyncio.run(self._async_do_POST())

    async def _async_do_POST(self):
        """Async handler for POST requests."""
        try:
            # Parse URL
            parsed_url = urlparse(self.path)
            
            # Route request based on path
            if parsed_url.path == '/messages':
                response = await self.message_handler.handle_post_message(self)
                self.send_json_response(response)
            elif parsed_url.path == '/reactions':
                response = await self.message_handler.handle_reaction(self)
                self.send_json_response(response)
            else:
                self.send_error(404, "Path not found")
                
        except Exception as e:
            logging.error(f"Error handling POST request: {e}")
            self.send_error(500, str(e))

    def do_PUT(self):
        """Handle PUT requests."""
        asyncio.run(self._async_do_PUT())

    async def _async_do_PUT(self):
        """Async handler for PUT requests."""
        try:
            # Parse URL
            parsed_url = urlparse(self.path)
            
            # Route request based on path
            if parsed_url.path == '/messages':
                response = await self.message_handler.handle_put_message(self)
                self.send_json_response(response)
            else:
                self.send_error(404, "Path not found")
                
        except Exception as e:
            logging.error(f"Error handling PUT request: {e}")
            self.send_error(500, str(e))

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

def run(server_class=HTTPServer, handler_class=ChatRequestHandler, port=None, open_url=True):
    """Run the server."""
    # Initialize storage and message handler
    base_dir = os.path.dirname(os.path.abspath(__file__))
    storage = FileStorage(base_dir)
    
    # Find available port if none specified
    if port is None:
        port = find_available_port()
    
    try:
        # Create server
        server_address = ('', port)
        httpd = server_class(server_address, handler_class)
        
        # Attach message handler to server
        httpd.message_handler = MessageHandler(storage)
        
        url = f'http://localhost:{port}'
        print(f'Server started at {url}')
        
        # Open browser in a separate thread
        if open_url:
            threading.Thread(target=open_browser, args=(url,), daemon=True).start()
        
        httpd.serve_forever()
    except OSError as e:
        if port is not None:
            # If specific port was requested but failed, try finding another
            print(f"Port {port} not available, finding another port...")
            return run(server_class, handler_class, None, open_url)
        raise e

if __name__ == '__main__':
    run()
