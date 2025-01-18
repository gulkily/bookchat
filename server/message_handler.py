"""Message handling module."""

import json
import os
import uuid
import logging
from datetime import datetime
from pathlib import Path

from aiohttp import web

from server.config import STORAGE_DIR

logger = logging.getLogger(__name__)

class MessageHandler:
    """Handler for message operations."""
    
    def __init__(self, storage):
        """Initialize with storage backend."""
        self.storage = storage
    
    async def get_messages(self):
        """Get all messages from storage."""
        return await self.storage.get_messages()
    
    def _to_api_response(self, message):
        """Convert internal message format to API response format."""
        response = {
            'id': message['id'],
            'content': message['content'],
            'author': message['author'],
            'timestamp': message['timestamp']
        }
        logger.info(f"API Response format: {response}")
        return response
    
    def _get_current_time(self):
        """Get the current time in ISO format with timezone offset."""
        return datetime.now().strftime('%Y-%m-%dT%H:%M:%S-05:00')

    async def create_message(self, content, author='anonymous', timestamp=None, current_time=None):
        """Create a new message.
        
        Args:
            content: Message content
            author: Message author (default: 'anonymous')
            timestamp: Optional specific timestamp to use
            current_time: Optional override for current time (for testing)
        """
        if timestamp is None:
            timestamp = current_time if current_time is not None else self._get_current_time()
        
        logger.info(f"Creating message with timestamp: {timestamp}")
            
        message = {
            'id': await self.storage.save_message({
                'content': content,
                'author': author,
                'timestamp': timestamp
            }),
            'content': content,
            'author': author,
            'timestamp': timestamp
        }
        
        logger.info(f"Created message object: {message}")
        return self._to_api_response(message)

    async def get_message(self, message_id):
        """Get a specific message by ID."""
        message = await self.storage.get_message(message_id)
        if message:
            return self._to_api_response(message)
        return None
    
    async def handle_get_messages(self):
        """Handle GET request for messages."""
        try:
            messages = await self.get_messages()
            return {
                'success': True,
                'messages': messages
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def handle_post_message(self, request):
        """Handle POST request for creating a message."""
        try:
            logger.info("Handling post message request")
            if isinstance(request, dict):
                request_data = request
                logger.info("Using dict request data")
            else:
                try:
                    request_data = await request.json()
                    logger.info("Got JSON from request")
                except (AttributeError, json.JSONDecodeError):
                    try:
                        data = request.rfile.read()
                        logger.info(f"Read from rfile: {data}")
                        request_data = json.loads(data.decode('utf-8'))
                        logger.info(f"Parsed request data: {request_data}")
                    except Exception as e:
                        logger.error(f"Error reading request data: {e}")
                        return {
                            'success': False,
                            'error': 'Invalid request data'
                        }

            content = request_data.get('content', '').strip()
            author = request_data.get('author', '') or request_data.get('username', '').strip()
            timestamp = request_data.get('timestamp')

            logger.info(f"Creating message with content: {content}, author: {author}, timestamp: {timestamp}")
            message = await self.create_message(
                content=content,
                author=author,
                timestamp=timestamp
            )
            logger.info(f"Created message: {message}")
            
            response = {
                'success': True,
                'data': message
            }
            logger.info(f"Sending response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error handling post message: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def get_messages():
    """Get all messages from storage."""
    messages = []
    messages_dir = Path(STORAGE_DIR) / 'messages'
    if not messages_dir.exists():
        return messages

    for file_path in messages_dir.glob('*.txt'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                message_data = {}
                for line in content.split('\n'):
                    if line.startswith('ID: '):
                        message_data['id'] = line[4:]
                    elif line.startswith('Content: '):
                        message_data['content'] = line[9:]
                    elif line.startswith('Username: '):
                        message_data['author'] = line[10:]
                    elif line.startswith('Timestamp: '):
                        message_data['timestamp'] = line[11:]
                messages.append(message_data)
        except Exception as e:
            print(f"Error reading message file {file_path}: {e}")
            continue

    return sorted(messages, key=lambda x: x.get('timestamp', ''))

def create_message(content, author='anonymous', timestamp=None):
    """Create a new message."""
    message_id = str(uuid.uuid4())
    timestamp = timestamp or datetime.now().isoformat()
    
    messages_dir = Path(STORAGE_DIR) / 'messages'
    messages_dir.mkdir(parents=True, exist_ok=True)
    
    message_path = messages_dir / f"{message_id}.txt"
    
    message_content = f"ID: {message_id}\nContent: {content}\nAuthor: {author}\nTimestamp: {timestamp}"
    
    with open(message_path, 'w', encoding='utf-8') as f:
        f.write(message_content)
    
    return {
        'id': message_id,
        'content': content,
        'author': author,
        'timestamp': timestamp
    }

def handle_post_message(request_data):
    """Handle a POST request to create a new message."""
    if not isinstance(request_data, dict):
        return {'error': 'Invalid request data'}, 400
    
    content = request_data.get('content')
    author = request_data.get('author', 'anonymous')
    
    if not content:
        return {'error': 'Message content is required'}, 400
    
    message = create_message(content, author)
    return {'success': True, 'data': {'id': message['id'], 'content': message['content'], 'author': message['author'], 'timestamp': message['timestamp']}}, 200
