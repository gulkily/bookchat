"""Utility functions for the BookChat server."""

import json
import logging
import os
import socket
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Union, List, Optional

from server.config import (
    REPO_PATH,
    MESSAGES_DIR,
    ARCHIVES_DIR,
    TEMPLATES_DIR,
    STATIC_DIR,
    KEYS_DIR,
    PUBLIC_KEYS_DIR
)

logger = logging.getLogger(__name__)

def find_available_port(start_port: int = 8080, max_tries: int = 100) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available ports found in range {start_port}-{start_port + max_tries}")

def ensure_directories() -> None:
    """Ensure all required directories exist."""
    directories = [
        MESSAGES_DIR,
        ARCHIVES_DIR,
        TEMPLATES_DIR,
        STATIC_DIR,
        KEYS_DIR,
        PUBLIC_KEYS_DIR
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

def get_message_path(message_id: str) -> Path:
    """Get the path to a message file.
    
    Args:
        message_id: ID of the message
        
    Returns:
        Path to message file
    """
    return MESSAGES_DIR / f"{message_id}.txt"

def get_archive_path(message_id: str) -> Path:
    """Get the path to an archived message file.
    
    Args:
        message_id: ID of the message
        
    Returns:
        Path to archived message file
    """
    return ARCHIVES_DIR / f"{message_id}.txt"

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

def send_json_response(
    handler: BaseHTTPRequestHandler,
    data: Union[Dict[str, Any], List[Any]],
    status: int = 200
) -> None:
    """Send a JSON response.
    
    Args:
        handler: HTTP request handler
        data: Data to send as JSON
        status: HTTP status code
    """
    try:
        handler.send_response(status)
        handler.send_header('Content-Type', 'application/json')
        handler.end_headers()
        
        response = json.dumps(data).encode('utf-8')
        handler.wfile.write(response)
        
    except Exception as e:
        logger.error(f"Error sending JSON response: {e}")
        handler.send_error(500, f"Internal server error: {e}")

def get_file_size(file_path: str) -> int:
    """Get size of a file in bytes."""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

def get_directory_size(directory: str) -> int:
    """Get total size of a directory in bytes."""
    total = 0
    try:
        for dirpath, _, filenames in os.walk(directory):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
    except OSError:
        pass
    return total

def bytes_to_mb(bytes_size: int) -> float:
    """Convert bytes to megabytes."""
    return bytes_size / (1024 * 1024)

def mb_to_bytes(mb_size: float) -> int:
    """Convert megabytes to bytes."""
    return int(mb_size * 1024 * 1024)

def format_size(size_in_bytes: int) -> str:
    """Format size in bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.1f}{unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.1f}TB"

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

def get_content_type(path: str) -> str:
    """Get content type based on file extension."""
    ext = os.path.splitext(path)[1].lower()
    content_types = {
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml'
    }
    return content_types.get(ext, 'application/octet-stream')

def read_template(template_name: str, templates_dir: str) -> Optional[str]:
    """Read a template file from the templates directory."""
    template_path = Path(templates_dir) / template_name
    if not template_path.exists():
        return None
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None

def ensure_directory_exists(directory: str) -> None:
    """Ensure a directory exists, creating it if necessary."""
    os.makedirs(directory, exist_ok=True)
