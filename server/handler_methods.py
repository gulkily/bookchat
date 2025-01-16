"""Request handler methods for the BookChat server."""

import json
import logging
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import re
import uuid
from typing import Dict, Any, Optional
from . import config

logger = logging.getLogger('bookchat')

class MessageHandler:
    """Handles message-related HTTP requests."""
    
    def __init__(self, server):
        """Initialize the handler with server instance."""
        self.server = server
    
    def handle_get(self, query_params: Dict[str, Any]) -> None:
        """Handle GET request for messages.
        
        Args:
            query_params: Dictionary of query parameters
        """
        try:
            # Parse query parameters
            limit = int(query_params.get('limit', [50])[0])
            before = query_params.get('before', [None])[0]
            if before:
                before = datetime.fromisoformat(before)
            
            # Get messages from storage
            messages = self.server.storage.get_messages(
                limit=limit,
                before=before
            )
            
            # Prepare response
            response = {
                'success': True,
                'messages': messages or [],
                'currentUsername': self.server.get_username_from_cookie() or 'anonymous',
                'messageVerificationEnabled': config.MESSAGE_VERIFICATION_ENABLED,
                'reactionsEnabled': config.REACTIONS_ENABLED
            }
            
            send_json_response(self.server, response)
            
        except Exception as e:
            logger.error(f"Error handling GET messages: {e}")
            self._send_error(str(e))
    
    def handle_post(self, request_body: Dict[str, Any]) -> None:
        """Handle POST request for new message.
        
        Args:
            request_body: Parsed JSON request body
        """
        try:
            # Validate request
            content = request_body.get('content', '').strip()
            if not content:
                raise ValueError("Message content cannot be empty")
            
            # Get username from cookie or request
            username = self.server.get_username_from_cookie()
            if not username:
                username = request_body.get('username', 'anonymous').strip()
                if not username:
                    username = 'anonymous'
            
            # Save message
            timestamp = datetime.now()
            message_id = self.server.storage.save_message(
                author=username,
                content=content,
                timestamp=timestamp,
                metadata={
                    'verified': 'true',
                    'type': 'message'
                }
            )
            
            if not message_id:
                raise RuntimeError("Failed to save message")
            
            # Prepare response
            response = {
                'success': True,
                'data': {
                    'content': content,
                    'author': username,
                    'timestamp': timestamp.isoformat(),
                    'id': message_id,
                    'verified': 'true',
                    'type': 'message'
                }
            }
            
            send_json_response(self.server, response)
            
        except Exception as e:
            logger.error(f"Error handling POST message: {e}")
            self._send_error(str(e))
    
    def handle_update(self, message_id: str, request_body: Dict[str, Any]) -> None:
        """Handle PUT request to update message.
        
        Args:
            message_id: ID of message to update
            request_body: Parsed JSON request body
        """
        try:
            # Validate request
            if not message_id:
                raise ValueError("Message ID is required")
            
            # Update message
            success = self.server.storage.update_message(
                message_id=message_id,
                updates=request_body
            )
            
            if not success:
                raise RuntimeError(f"Failed to update message {message_id}")
            
            # Get updated message
            messages = self.server.storage.get_messages()
            updated_message = next(
                (m for m in messages if m['id'] == message_id),
                None
            )
            
            if not updated_message:
                raise RuntimeError(f"Message {message_id} not found after update")
            
            # Prepare response
            response = {
                'success': True,
                'data': updated_message
            }
            
            send_json_response(self.server, response)
            
        except Exception as e:
            logger.error(f"Error handling UPDATE message: {e}")
            self._send_error(str(e))
    
    def _send_error(self, message: str, status: int = HTTPStatus.INTERNAL_SERVER_ERROR) -> None:
        """Send error response.
        
        Args:
            message: Error message
            status: HTTP status code
        """
        response = {
            'success': False,
            'error': message
        }
        send_json_response(self.server, response, status)

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

def handle_message_post(self) -> None:
    """Handle message posting."""
    try:
        # Read and parse request body
        content_length = int(self.headers.get('Content-Length', 0))
        logger.info(f"Handling POST request with Content-Length: {content_length}")
        logger.info(f"Content-Type: {self.headers.get('Content-Type', '')}")
        logger.info(f"Headers: {self.headers}")
        
        if content_length == 0:
            logger.error("No content received in request")
            self.handle_error(400, "No content received")
            return
        
        body = self.rfile.read(content_length).decode('utf-8')
        logger.info(f"Raw request body: {body}")
        
        # Handle both JSON and form data
        content_type = self.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            try:
                data = json.loads(body)
                logger.info(f"Parsed JSON data: {data}")
                content = data.get('content')
                username = data.get('username', 'anonymous')
                timestamp = data.get('timestamp')
                logger.info(f"Extracted from JSON - content: {content!r}, username: {username!r}, timestamp: {timestamp!r}")
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON: {e}")
                self.handle_error(400, "Invalid JSON format")
                return
        else:
            # Parse form data
            form_data = parse_qs(body)
            logger.info(f"Parsed form data: {form_data}")
            content = form_data.get('content', [''])[0]
            username = form_data.get('username', ['anonymous'])[0]
            timestamp = form_data.get('timestamp', [None])[0]
            logger.info(f"Extracted from form - content: {content!r}, username: {username!r}, timestamp: {timestamp!r}")
        
        # Validate content after parsing
        if content is None:
            logger.error("Message content is None")
            self.handle_error(400, "Message content is required")
            return
        
        content = str(content).strip()
        if not content:
            logger.error("Message content is empty after stripping")
            self.handle_error(400, "Message content cannot be empty")
            return

        # Get username from cookie or request
        username = self.get_username_from_cookie() or str(username)
        logger.info(f"Final username being used: {username}")
        
        # Save message using storage backend
        try:
            if timestamp:
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            logger.info(f"About to save message - content: {content!r}, username: {username}, timestamp: {timestamp}")
            if self.server.storage.save_message(username, content, timestamp):
                # Generate a stable message ID based on timestamp and username
                message_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{timestamp.isoformat()}_{username}"))
                
                response = {
                    'success': True,
                    'data': {
                        'content': content,
                        'author': username,
                        'timestamp': timestamp.isoformat(),
                        'verified': 'true',
                        'type': 'message',
                        'id': message_id
                    }
                }
                logger.info(f"Message saved successfully, sending response: {response}")
                send_json_response(self, response)
            else:
                logger.error("Storage backend failed to save message")
                self.handle_error(500, "Failed to save message")
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            self.handle_error(500, f"Failed to save message: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error handling message post: {e}")
        self.handle_error(500, str(e))

async def serve_messages(handler) -> None:
    """Serve list of messages.
    
    Args:
        handler: The request handler instance
    """
    try:
        messages = await handler.server.storage.get_messages()
        response = {
            'success': True,
            'data': messages,
            'messageVerificationEnabled': True,
            'reactionsEnabled': True
        }
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps(response).encode('utf-8'))
    except Exception as e:
        logger.error(f"Error serving messages: {e}")
        response = {
            'success': False,
            'error': str(e)
        }
        handler.send_response(500)
        handler.send_header('Content-Type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps(response).encode('utf-8'))
