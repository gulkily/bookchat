"""Storage backend that uses Git repository for message storage."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from .git_manager import GitManager
from .user_branch_manager import UserBranchManager

logger = logging.getLogger('git_storage')

class GitStorage:
    """Storage backend that uses Git repository for message storage."""
    
    def __init__(self, repo_path: str):
        """Initialize the Git storage backend.
        
        Args:
            repo_path: Path to the Git repository
        """
        logger.info(f"Initializing GitStorage with repo_path: {repo_path}")
        self.repo_path = Path(repo_path)
        self.messages_dir = self.repo_path / 'messages'
        self.git_manager = GitManager(str(repo_path))
        self.user_manager = UserBranchManager(self.git_manager)
        
        logger.debug(f"Messages directory: {self.messages_dir}")
        
        # Check if messages directory exists
        if not self.messages_dir.exists():
            logger.warning(f"Messages directory does not exist: {self.messages_dir}")
            self.messages_dir.mkdir(parents=True, exist_ok=True)
        else:
            logger.debug(f"Messages directory exists and contains: {list(self.messages_dir.glob('*'))}")
        
        # Initialize git repository
        self.git_manager._setup_git()
        
        # Initial message sync
        self.user_manager.sync_all_messages()
    
    def init_storage(self):
        """Initialize the storage by creating necessary directories."""
        self.messages_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_message(self, message: Dict[str, str]) -> Optional[str]:
        """Save a new message to the Git repository.
        
        Args:
            message: Dictionary containing message data (author, content, timestamp)
        
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            # Add timestamp if not present
            if 'timestamp' not in message:
                message['timestamp'] = datetime.now().isoformat()
            
            # Save message using user branch manager
            message_id = self.user_manager.save_message(message)
            
            if not message_id:
                raise Exception("Failed to save message")
            
            return message_id
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None
    
    async def get_messages(self) -> List[Dict[str, Any]]:
        """Retrieve messages from the Git repository."""
        messages = []
        try:
            # Sync latest messages from all users
            self.user_manager.sync_all_messages()
            
            # Read all messages from local pool
            for file_path in sorted(self.messages_dir.glob('*.txt')):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        message_data = self._parse_message_content(content)
                        if message_data:
                            messages.append(message_data)
                except Exception as e:
                    logger.error(f"Error reading message file {file_path}: {e}")
                    continue
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []
    
    async def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific message by ID."""
        try:
            # First try to find in local pool
            for file_path in self.messages_dir.glob(f"*_{message_id}.txt"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return self._parse_message_content(content)
            
            # If not found, sync all messages and try again
            self.user_manager.sync_all_messages()
            
            for file_path in self.messages_dir.glob(f"*_{message_id}.txt"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return self._parse_message_content(content)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None
    
    def _parse_message_content(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse message content from file."""
        try:
            lines = content.split('\n')
            message_data = {}
            
            # Parse headers
            i = 0
            while i < len(lines) and lines[i].strip():
                if ':' in lines[i]:
                    key, value = lines[i].split(':', 1)
                    message_data[key.strip().lower()] = value.strip()
                i += 1
            
            # Get message content (everything after headers)
            message_data['content'] = '\n'.join(lines[i+1:]).strip()
            
            return message_data
            
        except Exception as e:
            logger.error(f"Error parsing message content: {e}")
            return None
