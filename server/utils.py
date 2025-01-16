"""Utility functions for the server."""

import logging
import socket
import time
import webbrowser
import json
import os
from pathlib import Path

from server.config import REPO_PATH, STATIC_DIR

logger = logging.getLogger(__name__)

def find_available_port(start_port=8000, max_attempts=100):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No available ports found between {start_port} and {start_port + max_attempts}")

def open_browser(port, max_attempts=3, delay=1.0):
    """Open the browser to the server URL."""
    url = f'http://localhost:{port}'
    
    for attempt in range(1, max_attempts + 1):
        try:
            if webbrowser.open(url):
                logger.info(f"Opened browser to {url}")
                return True
            else:
                logger.warning(f"Failed to open browser (attempt {attempt})")
        except Exception as e:
            logger.warning(f"Failed to open browser (attempt {attempt}): {e}")
            
        if attempt < max_attempts:
            time.sleep(delay)
    
    return False

def ensure_directories() -> None:
    """Ensure required directories exist."""
    try:
        # Create required directories if they don't exist
        os.makedirs(REPO_PATH, exist_ok=True)
        os.makedirs(STATIC_DIR, exist_ok=True)
        os.makedirs(os.path.join(REPO_PATH, 'messages'), exist_ok=True)
        os.makedirs(os.path.join(REPO_PATH, 'identity'), exist_ok=True)
        os.makedirs(os.path.join(REPO_PATH, 'identity/public_keys'), exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating directories: {e}")
        raise

def send_json_response(handler, data: dict, status: int = 200) -> None:
    """Send a JSON response.
    
    Args:
        handler: The request handler instance
        data: The data to send as JSON
        status: HTTP status code (default: 200)
    """
    try:
        response = json.dumps(data)
        handler.send_response(status)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Content-Length', str(len(response)))
        handler.end_headers()
        handler.wfile.write(response.encode())
    except Exception as e:
        logger.error(f"Error sending JSON response: {e}")
        raise

def parse_message(message_data: dict) -> dict:
    """Parse and validate a message.
    
    Args:
        message_data: Raw message data from client
        
    Returns:
        Validated message dictionary
    """
    required_fields = ['content', 'author', 'timestamp']
    for field in required_fields:
        if field not in message_data:
            raise ValueError(f"Missing required field: {field}")
            
    return {
        'content': str(message_data['content']),
        'author': str(message_data['author']),
        'timestamp': str(message_data['timestamp'])
    }
