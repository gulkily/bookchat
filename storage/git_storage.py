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

from storage import StorageBackend
from git_manager import GitManager
from key_manager import KeyManager  # Import KeyManager

# Get logger for this module
logger = logging.getLogger(__name__)

class GitStorage(StorageBackend):
    """Storage backend that uses Git repository for message storage."""
    
    def __init__(self, repo_path: str, **kwargs):
        """Initialize the Git storage backend.
        
        Args:
            repo_path: Path to the Git repository
        """
        logger.info(f"Initializing GitStorage with repo_path: {repo_path}")
        self.repo_path = Path(repo_path)
        self.messages_dir = self.repo_path / 'messages'
        self.pinned_file = self.repo_path / 'pinned_messages.json'
        self.git_manager = GitManager(str(repo_path))
        
        # Initialize key manager with the same key directories as git manager
        private_keys_dir = os.environ.get('KEYS_DIR', str(self.repo_path / 'keys'))
        public_keys_dir = os.environ.get('PUBLIC_KEYS_DIR', str(self.repo_path / 'identity/public_keys'))
        self.key_manager = KeyManager(private_keys_dir, public_keys_dir)

        # Initialize message archiver
        from storage.archive_manager import MessageArchiver
        archive_dir = self.repo_path / 'archives'
        self.archiver = MessageArchiver(
            db_path=str(self.repo_path / 'messages.db'),
            archive_dir=str(archive_dir),
            git_manager=self.git_manager
        )
        
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
        
        self.init_storage()

    def init_storage(self):
        """Initialize the storage by creating necessary directories"""
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        if not self.pinned_file.exists():
            self._save_pinned_messages({})

    def _save_pinned_messages(self, pinned_data: Dict):
        """Save pinned messages data to JSON file"""
        with open(self.pinned_file, 'w') as f:
            json.dump(pinned_data, f, indent=2)

    def _load_pinned_messages(self) -> Dict:
        """Load pinned messages data from JSON file"""
        if not self.pinned_file.exists():
            return {}
        try:
            with open(self.pinned_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def pin_message(self, message_id: str, pinned_by: str) -> bool:
        """Pin a message"""
        try:
            # Load current pinned messages
            pinned_data = self._load_pinned_messages()
            
            # Check if message exists
            message = self.get_message_by_id(message_id)
            if not message:
                return False

            # Add to pinned messages
            pinned_data[message_id] = {
                'pinned_at': datetime.now().isoformat(),
                'pinned_by': pinned_by
            }

            # Save updated pinned messages
            self._save_pinned_messages(pinned_data)
            return True
        except Exception:
            return False

    def unpin_message(self, message_id: str, unpinned_by: str) -> bool:
        """Unpin a message"""
        try:
            # Load current pinned messages
            pinned_data = self._load_pinned_messages()
            
            # Remove from pinned messages if exists
            if message_id in pinned_data:
                del pinned_data[message_id]
                self._save_pinned_messages(pinned_data)
                return True
            return False
        except Exception:
            return False

    def get_pinned_messages(self) -> List[Dict]:
        """Retrieve all pinned messages"""
        try:
            # Load pinned messages data
            pinned_data = self._load_pinned_messages()
            
            # Get all pinned message details
            pinned_messages = []
            for message_id, pin_info in pinned_data.items():
                message = self.get_message_by_id(message_id)
                if message:
                    message.update({
                        'is_pinned': True,
                        'pinned_at': pin_info['pinned_at'],
                        'pinned_by': pin_info['pinned_by']
                    })
                    pinned_messages.append(message)
            
            # Sort by pinned_at timestamp
            return sorted(pinned_messages, key=lambda x: x['pinned_at'], reverse=True)
        except Exception:
            return []

    def save_message(self, user: str, content: str, timestamp: datetime, sign: bool = True) -> bool:
        """Save a new message to the Git repository.
        
        Args:
            user: Username of the message sender
            content: Message content
            timestamp: Message timestamp
            sign: Whether to sign the message
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Saving message from user: {user}")
            
            # Format filename like existing messages: YYYYMMDD_HHMMSS_username.txt
            filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{user}.txt"
            message_path = self.messages_dir / filename
            logger.debug(f"Message will be saved to: {message_path}")
            
            # Check if messages directory exists
            if not self.messages_dir.exists():
                logger.error(f"Messages directory does not exist: {self.messages_dir}")
                return False
            
            # Sign message if requested
            signature = None
            if sign:
                try:
                    signature = self.git_manager.key_manager.sign_message(content)
                    logger.debug(f"Message signed successfully: {signature[:32]}...")
                except Exception as e:
                    logger.error(f"Failed to sign message: {e}")
                    # Continue without signature
            
            # Format message with metadata footers
            # Use RFC 3339 format that JavaScript can definitely parse
            date_str = timestamp.astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')
            # Insert colon in timezone offset (e.g. +0000 -> +00:00)
            date_str = date_str[:-2] + ':' + date_str[-2:]
            
            formatted_message = self.git_manager.format_message(
                content,
                user,
                date_str,
                signature=signature
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
                return False
            
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
                commit_msg = f'Add message from {user}'
                logger.debug(f"Running git commit with message: {commit_msg}")
                result = subprocess.run(
                    ['git', 'commit', '--no-verify', str(message_path), '-m', commit_msg],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True,
                    text=True,
                    env={**os.environ, 'GIT_AUTHOR_NAME': user, 'GIT_AUTHOR_EMAIL': f'{user}@bookchat.local'}
                )
                logger.debug(f"Git commit output: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Git commit stderr: {result.stderr}")
                
                # Try to sync to GitHub if enabled
                if os.getenv('SYNC_TO_GITHUB', '').lower() == 'true':
                    logger.debug("Attempting to sync to GitHub...")
                    try:
                        self.git_manager.sync_changes_to_github(str(message_path), user)
                        logger.debug("Successfully synced to GitHub")
                    except Exception as e:
                        logger.warning(f"Failed to sync to GitHub: {e}")
                        # Don't fail the save operation if GitHub sync fails
                
                logger.info("Message saved successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to commit message: {e}\n{traceback.format_exc()}")
                return False
        except Exception as e:
            logger.error(f"Error saving message: {e}\n{traceback.format_exc()}")
            return False
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict]:
        """Retrieve messages from the Git repository"""
        try:
            messages = []
            pinned_data = self._load_pinned_messages()
            
            # Get all message files
            message_files = sorted(self.messages_dir.glob('*.txt'), reverse=True)
            if limit:
                message_files = message_files[:limit]

            # Load each message and add pinned status
            for file_path in message_files:
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        message = self._parse_message_content(content, file_path.stem)
                        if message:
                            # Add pinned status and info if pinned
                            message_id = str(message['id'])
                            if message_id in pinned_data:
                                message.update({
                                    'is_pinned': True,
                                    'pinned_at': pinned_data[message_id]['pinned_at'],
                                    'pinned_by': pinned_data[message_id]['pinned_by']
                                })
                            else:
                                message['is_pinned'] = False
                            messages.append(message)
                except Exception as e:
                    logger.error(f"Error reading message file {file_path}: {e}")
                    continue

            return messages
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific message by ID.
        
        Args:
            message_id: ID of the message to retrieve
        
        Returns:
            Message dictionary if found, None otherwise
        """
        try:
            # Message ID is the filename
            message_path = self.messages_dir / message_id
            if not message_path.exists():
                logger.warning(f"Message not found: {message_id}")
                return None
            
            # Read and parse the message
            message = self.git_manager.read_message(message_id)
            if not message:
                logger.error(f"Failed to parse message: {message_id}")
                return None
            
            # Add file link
            message['file'] = f"messages/{message_id}"
            return message
        except Exception as e:
            logger.error(f"Error retrieving message {message_id}: {e}\n{traceback.format_exc()}")
            return None

    def archive_old_messages(self, reference_time: datetime) -> Optional[str]:
        """Archive old messages using the message archiver.
        
        Args:
            reference_time: Current time to use as reference for archiving
            
        Returns:
            Optional[str]: Path to created archive if messages were archived, None otherwise
        """
        return self.archiver.archive_messages(reference_time)
