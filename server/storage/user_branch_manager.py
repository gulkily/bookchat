"""User branch manager for git-based storage."""

import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import secrets

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
        user_dir.mkdir(exist_ok=True)
        return user_dir

    def ensure_user_branch(self, username: str) -> bool:
        """Create user branch if it doesn't exist.
        
        Args:
            username: The username to create a branch for
            
        Returns:
            bool: True if branch was created or already exists, False on error
        """
        try:
            self._ensure_user_branch(username)
            return True
        except Exception as e:
            logger.error(f'Error ensuring user branch: {e}')
            return False

    def _ensure_user_branch(self, username: str):
        """Create user branch if it doesn't exist."""
        try:
            branch = self._get_user_branch(username)
            
            # Store current branch
            current_branch = self.git._get_current_branch()
            
            if not self.git.branch_exists(branch):
                # Create new branch from main
                self.git._run_git_command(['checkout', 'main'])
                self.git.create_branch(branch)
                self.git.checkout_branch(branch)
                
                # Create user directory and README
                user_dir = self._get_user_dir(username)
                readme_path = user_dir / 'README.md'
                if not readme_path.exists():
                    with open(readme_path, 'w') as f:
                        f.write(f'# Messages for {username}\n\nThis directory contains messages for user {username}.')
                
                # Add and commit the changes
                self.git._run_git_command(['add', str(user_dir)])
                self.git._run_git_command(['commit', '-m', f'Initialize messages directory for user {username}'])
            
            # Return to original branch
            self.git._run_git_command(['checkout', current_branch])
            
        except Exception as e:
            logger.error(f'Error ensuring user branch for {username}: {e}')
            # Try to return to main branch on error
            try:
                self.git._run_git_command(['checkout', 'main'])
            except:
                pass
            raise

    def save_message(self, message: Dict[str, str]) -> Optional[str]:
        """Save a message to the appropriate user branch."""
        try:
            author = message['author']
            content = message['content']
            timestamp = message.get('timestamp') or datetime.utcnow().isoformat()
            message_id = secrets.token_urlsafe(8)

            # Store current branch
            current_branch = self.git._get_current_branch()

            try:
                # Ensure user branch exists and switch to it
                self._ensure_user_branch(author)
                user_branch = self._get_user_branch(author)
                self.git._run_git_command(['checkout', user_branch])

                # Prepare message data
                message_data = {
                    'id': message_id,
                    'content': content,
                    'author': author,
                    'timestamp': timestamp
                }

                # Save message to file
                user_dir = self._get_user_dir(author)
                message_file = user_dir / f'{message_id}.txt'
                message_file.write_text(json.dumps(message_data, indent=2))

                # Update cache
                if author in self._message_cache:
                    self._message_cache[author].append(message_data)

                # Add and commit changes
                self.git._run_git_command(['add', str(message_file)])
                self.git._run_git_command(['commit', '-m', f'Add message {message_id} from {author}'])

                return message_id

            finally:
                # Always try to return to original branch
                try:
                    self.git._run_git_command(['checkout', current_branch])
                except:
                    # If we can't return to original branch, at least try main
                    try:
                        self.git._run_git_command(['checkout', 'main'])
                    except:
                        pass

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
            for message_file in user_dir.glob('*.txt'):
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
