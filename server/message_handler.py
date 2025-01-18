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
            # Handle both request objects and direct data dictionaries
            if isinstance(request, dict):
                data = request
            else:
                data = await request.json()
                
            content = data.get('content', '').strip()
            author = data.get('author', '') or data.get('username', '').strip()
            timestamp = data.get('timestamp')
            
            logger.info(f"Creating message with content: {content}, author: {author}, timestamp: {timestamp}")
            message = await self.create_message(
                content=content,
                author=author,
                timestamp=timestamp
            )
            logger.info(f"Created message: {message}")
            
            return {
                'success': True,
                'data': message
            }
            
        except Exception as e:
            logger.error(f"Error handling post message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
