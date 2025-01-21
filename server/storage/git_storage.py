"""Git-based storage backend for BookChat."""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import uuid
import subprocess
import traceback

from server.storage import StorageBackend
from server.storage.git_manager import GitManager
from server.key_manager import KeyManager  # Import KeyManager

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
        
        # Initialize key manager with the same key directories as git manager
        private_keys_dir = os.environ.get('KEYS_DIR', str(self.repo_path / 'keys'))
        public_keys_dir = os.environ.get('PUBLIC_KEYS_DIR', str(self.repo_path / 'identity/public_keys'))
        self.key_manager = KeyManager(private_keys_dir, public_keys_dir)

        logger.debug(f"Messages directory: {self.messages_dir}")
        
        # Check if messages directory exists
        if not self.messages_dir.exists():
            logger.warning(f"Messages directory does not exist: {self.messages_dir}")
        else:
            logger.debug(f"Messages directory exists and contains: {list(self.messages_dir.glob('*'))}")
        
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
        
    async def init_storage(self) -> bool:
        """Initialize the storage by creating necessary directories."""
        try:
            # Create messages directory if it doesn't exist
            logger.debug(f"Ensuring messages directory exists: {self.messages_dir}")
            os.makedirs(self.messages_dir, exist_ok=True)
            
            # Initialize git and pull latest changes
            if self.git_manager.use_github:
                self.git_manager.pull_from_github()
            
            # Check if directory was created successfully
            if not self.messages_dir.exists():
                logger.error("Failed to create messages directory")
                return False
            
            # Check directory permissions
            logger.debug(f"Messages directory permissions: {oct(os.stat(self.messages_dir).st_mode)}")
            
            # List directory contents
            logger.debug(f"Messages directory contents: {list(self.messages_dir.glob('*'))}")
            
            logger.info("Storage initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}\n{traceback.format_exc()}")
            return False
    
    async def save_message(self, message: Dict[str, str]) -> Optional[str]:
        """Save a new message to the Git repository.
        
        Args:
            message: Dictionary containing message data (author, content, timestamp)
        
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            logger.info(f"Saving message from user: {message['author']}")
            
            # Format filename like existing messages: YYYYMMDD_HHMMSS_username.txt
            timestamp = datetime.strptime(message['timestamp'], '%Y-%m-%dT%H:%M:%S%z')
            filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{message['author']}.txt"
            message_path = self.messages_dir / filename
            logger.debug(f"Message will be saved to: {message_path}")
            
            # Check if messages directory exists
            if not self.messages_dir.exists():
                logger.error(f"Messages directory does not exist: {self.messages_dir}")
                return None
            
            # Format message with metadata footers
            formatted_message = (
                f"ID: {filename}\n"
                f"Content: {message['content']}\n"
                f"Author: {message['author']}\n"
                f"Timestamp: {message['timestamp']}\n"
            )
            
            # Write message to file
            logger.info(f"Writing message to: {message_path}")
            try:
                with open(message_path, 'w') as f:
                    f.write(formatted_message)
                logger.debug(f"Successfully wrote message to file: {message_path}")
                logger.debug(f"File exists after write: {message_path.exists()}")
                logger.debug(f"File contents after write: {message_path.read_text() if message_path.exists() else 'FILE NOT FOUND'}")
            except Exception as e:
                logger.error(f"Failed to write message file: {e}\n{traceback.format_exc()}")
                return None
            
            # Stage and commit the file
            logger.info("Committing message to Git repository")
            try:
                # Add only the specific message file
                result = subprocess.run(
                    ['git', 'add', str(message_path)],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.debug(f"Git add output: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Git add stderr: {result.stderr}")
                
                # Commit the specific file
                commit_msg = f'Add message from {message["author"]}'
                logger.debug(f"Running git commit with message: {commit_msg}")
                result = subprocess.run(
                    ['git', 'commit', '--no-verify', str(message_path), '-m', commit_msg],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True,
                    text=True,
                    env={**os.environ, 'GIT_AUTHOR_NAME': message['author'], 'GIT_AUTHOR_EMAIL': f'{message["author"]}@bookchat.local'}
                )
                logger.debug(f"Git commit output: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Git commit stderr: {result.stderr}")
                
                # Always sync to GitHub as per spec
                logger.debug("Syncing message to GitHub...")
                try:
                    self.git_manager.sync_changes_to_github(str(message_path), message['author'], commit_msg)
                    logger.debug("Successfully synced to GitHub")
                except Exception as e:
                    logger.error(f"Failed to sync to GitHub: {e}")
                    # Fail the save operation if GitHub sync fails since it's required by spec
                    return None
                
                logger.info("Message saved successfully")
                return filename.replace('.txt', '')
            except Exception as e:
                logger.error(f"Failed to commit message: {e}\n{traceback.format_exc()}")
                return None
        except Exception as e:
            logger.error(f"Error saving message: {e}\n{traceback.format_exc()}")
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
