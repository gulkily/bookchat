"""File-based storage implementation."""

import json
import os
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class FileStorage:
    """File-based storage implementation."""

    def __init__(self, data_dir: str):
        """Initialize storage with data directory."""
        self.data_dir = Path(data_dir)
        self.messages_dir = self.data_dir / 'messages'
        self.messages_dir.mkdir(parents=True, exist_ok=True)

    def _parse_message_content(self, content: str) -> Dict[str, str]:
        """Parse message content looking for headers anywhere in the text.
        
        Headers can be in any of these formats:
        - ID: value
        - Content: value
        - Author: value
        - Timestamp: value
        """
        message_data = {
            'id': None,
            'content': None,
            'author': None,
            'timestamp': None
        }
        
        # Define header patterns
        patterns = {
            'id': r'(?:^|\n)ID:\s*(.+?)(?:\n|$)',
            'content': r'(?:^|\n)Content:\s*(.+?)(?:\n|$)',
            'author': r'(?:^|\n)Author:\s*(.+?)(?:\n|$)',
            'timestamp': r'(?:^|\n)Timestamp:\s*(.+?)(?:\n|$)'
        }
        
        # Extract values using patterns
        for field, pattern in patterns.items():
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                message_data[field] = match.group(1).strip()
        
        # If no explicit content header found, use remaining text
        if not message_data['content']:
            # Remove all known headers
            clean_content = content
            for pattern in patterns.values():
                clean_content = re.sub(pattern, '', clean_content, flags=re.MULTILINE)
            # Use remaining text as content, after cleaning
            clean_content = clean_content.strip()
            if clean_content:
                message_data['content'] = clean_content

        return message_data

    async def get_messages(self) -> List[Dict[str, Union[str, dict]]]:
        """Get all messages from storage."""
        messages = []
        try:
            # Use list to force immediate evaluation and avoid file handle issues
            message_files = list(sorted(self.messages_dir.glob('*.txt')))
            for file_path in message_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        message_data = self._parse_message_content(content)
                        # Only include messages that have required fields
                        if all(message_data[field] is not None for field in ['id', 'content', 'author']):
                            messages.append(message_data)
                except Exception as e:
                    logger.error(f"Error reading message file {file_path}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error listing message files: {e}")

        return messages

    async def save_message(self, message: Dict[str, str]) -> Optional[str]:
        """Save a message to storage.
        
        Args:
            message: Dictionary containing message data (author, content, timestamp)
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            # Generate unique ID based on timestamp
            timestamp = datetime.strptime(message['timestamp'], '%Y-%m-%dT%H:%M:%S%z')
            message_id = timestamp.strftime('%Y%m%d_%H%M%S')
            
            # Ensure unique ID by appending counter if needed
            counter = 0
            base_id = message_id
            while (self.messages_dir / f"{message_id}.txt").exists():
                counter += 1
                message_id = f"{base_id}_{counter}"
            
            message_path = self.messages_dir / f"{message_id}.txt"
            
            # Format with headers at the top for readability
            content = (
                f"ID: {message_id}\n"
                f"Content: {message['content']}\n"
                f"Author: {message['author']}\n"
                f"Timestamp: {message['timestamp']}\n"
            )
            
            with open(message_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return message_id

        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    async def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Union[str, dict]]]:
        """Get a message by its ID."""
        try:
            message_path = self.messages_dir / f"{message_id}.txt"
            if not message_path.exists():
                return None

            with open(message_path, 'r', encoding='utf-8') as f:
                content = f.read()
                message_data = self._parse_message_content(content)
                # Only return message if it has required fields
                if all(message_data[field] is not None for field in ['id', 'content', 'author']):
                    return message_data
                return None

        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None
