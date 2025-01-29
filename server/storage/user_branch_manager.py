"""User branch manager for git-based storage."""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import secrets

logger = logging.getLogger(__name__)

class UserBranchManager:
    """Manager for user branches in git repository."""

    def __init__(self, git_manager):
        """Initialize with GitManager instance."""
        self.git = git_manager
        self.data_dir = git_manager.repo_dir
        self.messages_dir = self.data_dir / 'messages'
        self.messages_dir.mkdir(exist_ok=True)

    def _get_user_branch(self, username: str) -> str:
        """Get branch name for user."""
        return f'user/{username}'

    def _get_user_dir(self, username: str) -> Path:
        """Get directory for user's messages."""
        user_dir = self.messages_dir / username
        user_dir.mkdir(exist_ok=True)
        return user_dir

    def _ensure_user_branch(self, username: str):
        """Create user branch if it doesn't exist."""
        branch = self._get_user_branch(username)
        if not self.git.branch_exists(branch):
            self.git.create_branch(branch)
            self.git.checkout_branch(branch)
            # Create user directory
            user_dir = self._get_user_dir(username)
            user_dir.mkdir(exist_ok=True)
            # Add and commit the directory
            self.git.add(str(user_dir))
            self.git.commit(f'Initialize messages directory for user {username}')
            # Switch back to main branch
            self.git.checkout_branch('main')

    def save_message(self, message: Dict[str, str]) -> Optional[str]:
        """Save a message to the appropriate user branch.
        
        Args:
            message: Dictionary with content, author, and optional timestamp
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            author = message['author']
            content = message['content']
            timestamp = message.get('timestamp') or datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create user branch if needed
            self._ensure_user_branch(author)
            
            # Switch to user branch
            branch = self._get_user_branch(author)
            self.git.checkout_branch(branch)
            
            # Generate message ID and path
            message_id = f"{timestamp}_{secrets.token_hex(4)}"
            message_path = self._get_user_dir(author) / f"{message_id}.txt"
            
            # Write message
            message_path.write_text(
                f"{content}\n"
                f"Author: {author}\n"
                f"Date: {timestamp}\n"
            )
            
            # Commit changes
            self.git.add(str(message_path))
            self.git.commit(f'Add message {message_id} from {author}')
            
            # Switch back to main
            self.git.checkout_branch('main')
            
            return message_id
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages from all user branches.
        
        Returns:
            List of message dictionaries
        """
        messages = []
        
        try:
            # Get all user branches
            branches = [b for b in self.git.list_branches() if b.startswith('user/')]
            
            for branch in branches:
                # Get username from branch
                username = branch.split('/', 1)[1]
                user_dir = self._get_user_dir(username)
                
                # Switch to user branch
                self.git.checkout_branch(branch)
                
                # Read all message files
                for message_file in user_dir.glob('*.txt'):
                    try:
                        lines = message_file.read_text().splitlines()
                        if len(lines) >= 3:
                            content = lines[0]
                            author = lines[1].split(': ', 1)[1]
                            timestamp = lines[2].split(': ', 1)[1]
                            message_id = message_file.stem
                            
                            messages.append({
                                'id': message_id,
                                'content': content,
                                'author': author,
                                'timestamp': timestamp
                            })
                    except Exception as e:
                        logger.error(f"Error reading message {message_file}: {e}")
                        continue
                
                # Switch back to main
                self.git.checkout_branch('main')
                
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            
        return sorted(messages, key=lambda m: m['timestamp'])
