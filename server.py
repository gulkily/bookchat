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

from server.storage.file_storage import FileStorage
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
                try:
                    response = await self.message_handler.handle_get_messages(self)
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
                logging.error(f"Error handling GET request: {str(e)}", exc_info=True)
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
            else:
                self.send_error(404, "Path not found")
                
        except Exception as e:
            logging.error(f"Error handling POST request: {e}")
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
        server = ChatServer(('localhost', 8001), ChatRequestHandler)
        threading.Thread(target=open_browser, args=('http://localhost:8001',), daemon=True).start()
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info('Server stopped by user')
        server.shutdown()
    except Exception as e:
        logging.error(f'Server error: {e}')
        raise

if __name__ == '__main__':
    run_server()
