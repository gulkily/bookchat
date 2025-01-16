"""Request handler methods for the BookChat server."""

import json
import logging
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import re
from . import config

logger = logging.getLogger('bookchat')

def serve_file(self, path: str, content_type: str) -> None:
    """Serve a file with the specified content type."""
    try:
        with open(path, 'rb') as f:
            content = f.read()
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(content)
    except Exception as e:
        self.handle_error(500, str(e))

def serve_messages(self) -> None:
    """Serve list of messages."""
    try:
        # Use storage backend to get messages
        messages = self.server.storage.get_messages()
        
        response = {
            'messages': messages,
            'messageVerificationEnabled': config.MESSAGE_VERIFICATION_ENABLED
        }
        send_json_response(self, response)
    except Exception as e:
        logger.error(f"Error serving messages: {e}")
        self.handle_error(500, str(e))

def verify_username(self) -> None:
    """Verify if username is valid and available."""
    try:
        query = parse_qs(urlparse(self.path).query)
        username = query.get('username', [''])[0]

        # Use storage backend to verify username
        if username:
            is_valid = self.server.storage.verify_username(username)
            response = {
                'valid': is_valid,
                'username': username,
                'error': None if is_valid else 'Invalid username format'
            }
        else:
            # If no username provided, return current username from session
            response = {
                'valid': True,
                'username': 'anonymous',
                'status': 'verified'
            }

        send_json_response(self, response)
    except Exception as e:
        logger.error(f"Error verifying username: {e}")
        self.handle_error(500, str(e))

def serve_status_page(self) -> None:
    """Serve server status page."""
    try:
        status = {
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'message_verification': config.MESSAGE_VERIFICATION_ENABLED
        }
        send_json_response(self, status)
    except Exception as e:
        logger.error(f"Error serving status page: {e}")
        self.handle_error(500, str(e))

def send_json_response(self, data: dict) -> None:
    """Send a JSON response."""
    try:
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    except Exception as e:
        logger.error(f"Error sending JSON response: {e}")
        self.handle_error(500, str(e))

def handle_message_post(self) -> None:
    """Handle message posting."""
    try:
        # Read and parse request body
        content_length = int(self.headers.get('Content-Length', 0))
        logger.debug(f"Content-Length: {content_length}")
        logger.debug(f"Content-Type: {self.headers.get('Content-Type', '')}")
        
        if content_length == 0:
            logger.error("No content received in request")
            self.handle_error(400, "No content received")
            return
        
        body = self.rfile.read(content_length).decode('utf-8')
        logger.debug(f"Raw request body: {body}")
        
        # Handle both JSON and form data
        content_type = self.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            try:
                data = json.loads(body)
                logger.debug(f"Parsed JSON data: {data}")
                content = data.get('content')
                username = data.get('username', 'anonymous')
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON: {e}")
                self.handle_error(400, "Invalid JSON format")
                return
        else:
            # Parse form data
            form_data = parse_qs(body)
            logger.debug(f"Parsed form data: {form_data}")
            content = form_data.get('content', [''])[0]
            username = form_data.get('username', ['anonymous'])[0]
        
        # Validate content after parsing
        if content is None:
            logger.error("Message content is None")
            self.handle_error(400, "Message content is required")
            return
        
        content = content.strip()
        if not content:
            logger.error("Message content is empty after stripping")
            self.handle_error(400, "Message content cannot be empty")
            return

        # Get username from cookie
        username = self.get_username_from_cookie()
        logger.debug(f"Using username from cookie: {username}")

        logger.debug(f"Processed content: {content!r}")
        logger.debug(f"Processed username: {username!r}")

        # Save message using storage backend
        try:
            timestamp = datetime.now()
            if self.server.storage.save_message(username, content, timestamp):
                response = {
                    'success': True,
                    'message': 'Message saved successfully',
                    'data': {
                        'content': content,
                        'author': username,
                        'createdAt': timestamp.isoformat(),
                        'verified': 'true',
                        'type': 'message'
                    }
                }
                send_json_response(self, response)
            else:
                self.handle_error(500, "Failed to save message")
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            self.handle_error(500, f"Failed to save message: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error handling message post: {e}")
        self.handle_error(500, str(e))
