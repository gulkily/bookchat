"""Git-based storage backend for BookChat."""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import subprocess

from server.storage import StorageBackend
from server.storage.git_manager import GitManager
from server.storage.user_branch_manager import UserBranchManager

# Get logger for this module
logger = logging.getLogger(__name__)

class GitStorage(StorageBackend):
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
        
        logger.debug(f"Messages directory: {self.messages_dir}")
        
        # Check if messages directory exists
        if not self.messages_dir.exists():
            logger.warning(f"Messages directory does not exist: {self.messages_dir}")
            self.messages_dir.mkdir(parents=True, exist_ok=True)
        else:
            logger.debug(f"Messages directory exists and contains: {list(self.messages_dir.glob('*'))}")
        
        # Initialize git repository
        self.git_manager._setup_git()
        
        # Check Git repository status
        try:
            result = subprocess.run(
                ['git', 'status'],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True
            )
            logger.debug(f"Git status output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Git status stderr: {result.stderr}")
        except Exception as e:
            logger.error(f"Failed to check Git status: {e}")
        
    async def init_storage(self):
        """Initialize the storage by creating necessary directories."""
        try:
            # Create messages directory if it doesn't exist
            self.messages_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize git repository
            self.git_manager._setup_git()
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            return False

    async def save_message(self, message: Dict[str, str]) -> Optional[str]:
        """Save a message to git storage.
        
        Args:
            message: Message to save
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            # Create UserBranchManager
            user_manager = UserBranchManager(self.git_manager.git)
            
            # Save message using UserBranchManager
            message_id = user_manager.save_message(message)
            
            # Push changes if enabled
            if self.git_manager.push_enabled:
                await self.git_manager.push()
                
            return message_id
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    async def get_messages(self) -> List[Dict[str, Any]]:
        """Retrieve messages from the Git repository."""
        try:
            messages = []
            message_files = sorted(self.messages_dir.glob('*.txt'))
            for file_path in message_files:
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
            logger.error(f"Error listing messages: {e}")
            return []

    async def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific message by ID."""
        try:
            message_path = self.messages_dir / f"{message_id}.txt"
            if not message_path.exists():
                return None

            with open(message_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return self._parse_message_content(content)

        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None
