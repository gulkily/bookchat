"""File-based storage implementation."""

import json
import os
import logging
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

    async def get_messages(self) -> List[Dict[str, Union[str, dict]]]:
        """Get all messages from storage."""
        messages = []
        try:
            for file_path in sorted(self.messages_dir.glob('*.txt')):
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
                                message_data['username'] = line[10:]
                            elif line.startswith('Timestamp: '):
                                message_data['timestamp'] = line[11:]
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
            message: Dictionary containing message data (username, content, timestamp)
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            message_id = message.get('id', datetime.now().strftime('%Y%m%d_%H%M%S'))
            message_path = self.messages_dir / f"{message_id}.txt"
            
            content = (
                f"ID: {message_id}\n"
                f"Content: {message['content']}\n"
                f"Username: {message['username']}\n"
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
                message_data = {}
                for line in content.split('\n'):
                    if line.startswith('ID: '):
                        message_data['id'] = line[4:]
                    elif line.startswith('Content: '):
                        message_data['content'] = line[9:]
                    elif line.startswith('Username: '):
                        message_data['username'] = line[10:]
                    elif line.startswith('Timestamp: '):
                        message_data['timestamp'] = line[11:]
                return message_data

        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None
