"""User branch manager for git-based storage."""

import os
import json
import logging
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from .git_manager import GitManager

logger = logging.getLogger(__name__)

class UserBranchManager:
    """Manager for user branches in git repository."""

    def __init__(self, git_manager):
        """Initialize with GitManager instance."""
        self.git = git_manager
        self.data_dir = git_manager.repo_path
        self.messages_dir = self.data_dir / 'messages'
        self.messages_dir.mkdir(exist_ok=True)
        self.active_users_file = self.data_dir / 'active_users.json'
        self._message_cache = {}  # Cache messages per user
        self._last_fetch = {}  # Track last fetch time per user

    def _get_user_branch(self, username: str) -> str:
        """Get branch name for user."""
        return f'user/{username}'

    def _get_user_dir(self, username: str) -> Path:
        """Get directory for user's messages."""
        user_dir = self.messages_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def ensure_user_branch(self, username: str) -> bool:
        """Create user branch if it doesn't exist.
        
        Args:
            username: The username to create a branch for
            
        Returns:
            bool: True if branch was created or already exists, False on error
        """
        try:
            return self._ensure_user_branch(username)
        except Exception as e:
            logger.error(f'Error ensuring user branch: {e}')
            return False

    def _ensure_user_branch(self, username: str) -> bool:
        """Create user branch if it doesn't exist."""
        try:
            branch = self._get_user_branch(username)
            
            # Store current branch
            current_branch = self.git.get_current_branch()
            
            if not self.git.branch_exists(branch):
                # Create new branch from main
                self.git.checkout_branch('main')
                self.git.create_branch(branch)
                self.git.checkout_branch(branch)
                
                # Create user directory and README
                user_dir = self._get_user_dir(username)
                readme_path = user_dir / 'README.md'
                if not readme_path.exists():
                    with open(readme_path, 'w') as f:
                        f.write(f'# Messages for {username}\n\nThis directory contains messages for user {username}.')
                
                # Add and commit the changes
                self.git._run_git_command(['add', f'messages/{username}'])
                self.git._run_git_command(['commit', '-m', f'Initialize messages directory for user {username}'])
            
            # Return to original branch
            self.git.checkout_branch(current_branch)
            return True
            
        except Exception as e:
            logger.error(f'Error ensuring user branch for {username}: {e}')
            # Try to return to main branch on error
            try:
                self.git.checkout_branch('main')
            except:
                pass
            return False

    def save_message(self, message: Dict[str, str]) -> Optional[str]:
        """Save a message to the appropriate user branch."""
        try:
            username = message['author']
            message_id = str(uuid.uuid4())
            
            # Make sure user branch exists
            if not self.ensure_user_branch(username):
                logger.error('Failed to ensure user branch')
                return None
            
            # Store current branch
            current_branch = self.git.get_current_branch()
            
            try:
                # Switch to user branch
                user_branch = self._get_user_branch(username)
                self.git.checkout_branch(user_branch)
                
                # Create user directory if it doesn't exist
                user_dir = self._get_user_dir(username)
                
                # Save message to file
                message_path = user_dir / f'{message_id}.json'
                with open(message_path, 'w') as f:
                    json.dump(message, f, indent=2)
                
                # Add and commit
                self.git._run_git_command(['add', f'messages/{username}/{message_id}.json'])
                self.git._run_git_command(['commit', '-m', f'Add message {message_id}'])
                
                return message_id
                
            finally:
                # Return to original branch
                self.git.checkout_branch(current_branch)
                
        except Exception as e:
            logger.error(f'Error saving message: {e}')
            return None

    def get_messages(self, username: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get messages, optionally filtered by username."""
        try:
            if username:
                return self._get_user_messages(username)

            # Get all messages
            all_messages = []
            for user_dir in self.messages_dir.iterdir():
                if user_dir.is_dir() and not user_dir.name.startswith('.'):
                    messages = self._get_user_messages(user_dir.name)
                    all_messages.extend(messages)
            
            # Sort by timestamp
            all_messages.sort(key=lambda x: x.get('timestamp', ''))
            return all_messages

        except Exception as e:
            logger.error(f'Error getting messages: {e}')
            return []

    def _get_user_messages(self, username: str) -> List[Dict[str, Any]]:
        """Get messages for a specific user with caching."""
        try:
            # Check cache first
            if username in self._message_cache:
                return self._message_cache[username]

            messages = []
            user_dir = self._get_user_dir(username)
            
            # Read all message files
            for message_file in user_dir.glob('*.json'):
                if message_file.is_file():
                    try:
                        with open(message_file, 'r') as f:
                            message_data = json.load(f)
                            messages.append(message_data)
                    except Exception as e:
                        logger.error(f'Error reading message file {message_file}: {e}')

            # Sort by timestamp
            messages.sort(key=lambda x: x.get('timestamp', ''))
            
            # Update cache
            self._message_cache[username] = messages
            return messages

        except Exception as e:
            logger.error(f'Error getting messages for user {username}: {e}')
            return []
