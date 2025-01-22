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
            
            # Export public key for anonymous users
            public_keys_dir = self.repo_path / 'identity/public_keys'
            public_keys_dir.mkdir(parents=True, exist_ok=True)
            self.key_manager.export_public_key(public_keys_dir / 'anonymous.pub')
            
            # Sync public key if GitHub is enabled
            if os.environ.get('SYNC_TO_GITHUB', 'false').lower() == 'true':
                self.git_manager.sync_changes_to_github(public_keys_dir / 'anonymous.pub', "System")
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            return False

    async def save_message(self, message: Dict[str, str]) -> Optional[str]:
        """Save a new message to the Git repository.
        
        Args:
            message: Dictionary containing message data (author, content, timestamp)
        
        Returns:
            Message ID if successful, None otherwise
        """
        try:
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
                
                # Add and commit the file
                self.git_manager.add_and_commit_file(str(message_path), f'Add message from {message["author"]}', message['author'])
                
                # Push changes to GitHub
                self.git_manager.push()
                
                logger.info("Message saved and synced successfully")
                return filename.replace('.txt', '')
            except Exception as e:
                logger.error(f"Failed to save message: {e}\n{traceback.format_exc()}")
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
