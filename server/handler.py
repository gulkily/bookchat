"""Request handler for the chat server."""

import json
import logging
import mimetypes
import socket
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import parse_qs, urlparse

from server.config import STATIC_DIR, REPO_PATH
from server.utils import send_json_response

logger = logging.getLogger(__name__)

class ChatRequestHandler(SimpleHTTPRequestHandler):
    """Handler for chat server requests."""

    def __init__(self, *args, **kwargs):
        # Set the directory for serving static files
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_error(self, format, *args):
        """Override to handle expected errors more gracefully."""
        if len(args) == 0 or not isinstance(args[0], (BrokenPipeError, ConnectionResetError)):
            logger.error(format % args)

    def handle_error(self, status_code: int, message: str) -> None:
        """Handle errors and return appropriate response.

        This method provides centralized error handling for the server by:
        1. Logging the error with full traceback
        2. Handling broken pipe errors gracefully
        3. Sending a JSON error response to the client

        Args:
            status_code: HTTP status code to return
            message: Error message to send to client
        """
        try:
            error_trace = traceback.format_exc()
            if error_trace != "NoneType: None\n":
                logger.error(f"Error trace:\n{error_trace}")
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error_response = json.dumps({'error': message}).encode('utf-8')
            self.wfile.write(error_response)
            
        except BrokenPipeError:
            # Client disconnected, log and ignore
            logger.info("Client disconnected while sending error response")
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    def get_username_from_cookie(self) -> str:
        """Get username from cookie or return None."""
        cookies = self.headers.get('Cookie', '')
        if not cookies:
            return None
            
        for cookie in cookies.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('username='):
                return cookie[9:]  # Length of 'username='
                
        return None

    def do_GET(self) -> None:
        """Handle GET requests."""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path

            if path == '/messages':
                self.handle_get_messages()
            elif path == '/verify_username':
                from server.handler_methods import verify_username
                verify_username(self)
            elif path == '/status':
                from server.handler_methods import serve_status_page
                serve_status_page(self)
            else:
                # Use SimpleHTTPRequestHandler's file serving
                logger.debug(f"Serving static file: {path}, directory: {self.directory}")
                super().do_GET()
        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            self.handle_error(500, str(e))

    def handle_get_messages(self) -> None:
        """Handle GET /messages request."""
        try:
            messages = self.server.storage.get_messages()
            logger.debug(f"Retrieved messages from storage: {messages}")
            
            # Format response
            response = {
                'success': True,
                'data': messages,
                'messageVerificationEnabled': False,
                'reactionsEnabled': False
            }
            logger.debug(f"Sending response: {response}")
            send_json_response(self, response)
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            self.handle_error(500, "Error getting messages")

    def do_POST(self) -> None:
        """Handle POST requests."""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path

            if path == '/messages':
                from server.handler_methods import handle_message_post
                handle_message_post(self)
            else:
                self.handle_error(404, f"Unknown endpoint: {path}")
        except Exception as e:
            logger.error(f"Error handling POST request: {e}")
            self.handle_error(500, str(e))
