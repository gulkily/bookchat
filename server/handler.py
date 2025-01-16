"""Request handler for the chat server."""

import json
import logging
import mimetypes
import socket
import traceback
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any
from urllib.parse import parse_qs, urlparse

from server import config
from server.handler_methods import (
    serve_messages,
    verify_username,
    serve_status_page,
    handle_message_post
)

logger = logging.getLogger(__name__)

class ChatRequestHandler(SimpleHTTPRequestHandler):
    """Handler for chat server requests."""

    def __init__(self, *args, **kwargs):
        # Set the directory for serving static files
        super().__init__(*args, directory=config.STATIC_DIR, **kwargs)

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

    def serve_file(self, filepath: str) -> None:
        """Serve a static file."""
        try:
            # Get absolute path within static directory
            static_dir = Path(config.STATIC_DIR)
            file_path = static_dir / filepath.lstrip('/')
            
            if not file_path.is_file() or not str(file_path).startswith(str(static_dir)):
                self.handle_error(404, f"File not found: {filepath}")
                return

            # Determine content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            if content_type is None:
                content_type = 'application/octet-stream'

            try:
                # Read file content first to avoid partial headers
                content = file_path.read_bytes()
                
                # Send headers
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                
                # Send content in chunks to handle large files
                chunk_size = 8192
                for i in range(0, len(content), chunk_size):
                    try:
                        self.wfile.write(content[i:i + chunk_size])
                    except (BrokenPipeError, ConnectionResetError):
                        # Client disconnected, just return
                        logger.debug(f"Client disconnected while serving file: {filepath}")
                        return
                    except socket.error as e:
                        # Other socket errors
                        logger.warning(f"Socket error while serving file {filepath}: {e}")
                        return
                        
            except (BrokenPipeError, ConnectionResetError):
                # Client disconnected before we could send anything
                logger.debug(f"Client disconnected before serving file: {filepath}")
            except Exception as e:
                logger.error(f"Error reading or sending file: {e}")
                self.handle_error(500, str(e))
        except Exception as e:
            logger.error(f"Error preparing to serve file {filepath}: {e}")
            self.handle_error(500, str(e))

    def do_GET(self) -> None:
        """Handle GET requests."""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path

            if path == '/messages':
                serve_messages(self)
            elif path == '/verify_username':
                verify_username(self)
            elif path == '/status':
                serve_status_page(self)
            else:
                self.serve_file(path.lstrip('/'))
        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            self.handle_error(500, str(e))

    def do_POST(self) -> None:
        """Handle POST requests."""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path

            if path == '/messages':
                handle_message_post(self)
            else:
                self.handle_error(404, f"Unknown endpoint: {path}")
        except Exception as e:
            logger.error(f"Error handling POST request: {e}")
            self.handle_error(500, str(e))
