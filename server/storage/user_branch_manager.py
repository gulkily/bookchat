"""User branch management functionality for message storage."""

import os
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger('user_branch_manager')

class UserBranchManager:
    """Manages user branches and local message pooling."""

    def __init__(self, git_manager):
        """Initialize UserBranchManager.
        
        Args:
            git_manager: GitManager instance to handle Git operations
        """
        self.git_manager = git_manager
        self.repo_path = git_manager.repo_path
        self.messages_dir = git_manager.messages_dir
        self.active_users_file = self.repo_path / 'active_users.json'
        self._ensure_active_users_file()
    
    def _ensure_active_users_file(self):
        """Ensure active users metadata file exists."""
        if not self.active_users_file.exists():
            self._save_active_users({
                'last_updated': datetime.now().isoformat(),
                'users': {}
            })
    
    def _load_active_users(self) -> Dict[str, Dict[str, str]]:
        """Load active users metadata from file."""
        try:
            with open(self.active_users_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading active users: {e}")
            return {'last_updated': datetime.now().isoformat(), 'users': {}}
    
    def _save_active_users(self, data: Dict[str, Dict[str, str]]):
        """Save active users metadata to file."""
        try:
            with open(self.active_users_file, 'w') as f:
                json.dump(data, f, indent=2)
            # Commit changes to active users file
            self.git_manager.add_and_commit_file(
                str(self.active_users_file),
                "Update active users metadata",
                "BookChat Bot"
            )
        except Exception as e:
            logger.error(f"Error saving active users: {e}")
    
    def ensure_user_branch(self, username: str) -> bool:
        """Ensure user branch exists and is properly configured.
        
        Args:
            username: Username to create branch for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate username format
            if not username.isalnum() and not all(c in '-_' for c in username if not c.isalnum()):
                raise ValueError("Username must be alphanumeric with optional hyphens and underscores")
            
            branch_name = f'user/{username}'
            current_branch = self.git_manager._get_current_branch()
            
            # Check if branch exists
            branches = self.git_manager._run_git_command(['branch', '-l', branch_name])
            
            if not branches.strip():
                # Create new branch from main
                self.git_manager._run_git_command(['checkout', 'main'])
                self.git_manager._run_git_command(['checkout', '-b', branch_name])
                
                # Create user message directory
                user_messages_dir = self.messages_dir / username
                user_messages_dir.mkdir(parents=True, exist_ok=True)
                
                # Add README to user directory
                readme_path = user_messages_dir / 'README.md'
                with open(readme_path, 'w') as f:
                    f.write(f"# Messages from {username}\n\nThis branch contains messages from user {username}.\n")
                
                # Commit user directory
                self.git_manager.add_and_commit_file(
                    str(readme_path),
                    f"Initialize message branch for user: {username}",
                    "BookChat Bot"
                )
                
                # Update active users
                self._update_active_user(username)
            
            # Switch back to original branch
            self.git_manager._run_git_command(['checkout', current_branch])
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring user branch for {username}: {e}")
            return False
    
    def _update_active_user(self, username: str):
        """Update active user metadata."""
        try:
            data = self._load_active_users()
            data['users'][username] = {
                'username': username,
                'last_active': datetime.now().isoformat(),
                'message_count': self._count_user_messages(username)
            }
            data['last_updated'] = datetime.now().isoformat()
            self._save_active_users(data)
        except Exception as e:
            logger.error(f"Error updating active user {username}: {e}")
    
    def _count_user_messages(self, username: str) -> int:
        """Count number of messages from a user."""
        try:
            pattern = f"{username}_*.txt"
            return len(list(self.messages_dir.glob(pattern)))
        except Exception:
            return 0
    
    def save_message(self, message: Dict[str, str]) -> Optional[str]:
        """Save message to user's branch and local pool.
        
        Args:
            message: Message data including author and content
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            username = message['author']
            message_id = f"{int(datetime.now().timestamp())}_{os.urandom(4).hex()}"
            filename = f"{username}_{message_id}.txt"
            
            # Ensure user branch exists
            if not self.ensure_user_branch(username):
                raise Exception(f"Failed to ensure user branch for {username}")
            
            current_branch = self.git_manager._get_current_branch()
            
            # Switch to user's branch
            self.git_manager._run_git_command(['checkout', f'user/{username}'])
            
            # Save message in user's branch
            message_path = self.messages_dir / username / f"{message_id}.txt"
            self._write_message_file(message_path, message)
            
            # Commit and push user's branch
            self.git_manager.add_and_commit_file(
                str(message_path),
                f"Add message {message_id} from {username}",
                username
            )
            if self.git_manager.use_github:
                self.git_manager.push()
            
            # Switch back to original branch
            self.git_manager._run_git_command(['checkout', current_branch])
            
            # Copy to local pool
            pool_path = self.messages_dir / filename
            shutil.copy2(message_path, pool_path)
            
            # Update active users
            self._update_active_user(username)
            
            return message_id
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None
    
    def _write_message_file(self, path: Path, message: Dict[str, str]):
        """Write message data to file."""
        content = []
        for key, value in message.items():
            content.append(f"{key}: {value}")
        content.append("\n")  # Blank line before message content
        content.append(message['content'])
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
    
    def sync_user_messages(self, username: str) -> bool:
        """Sync messages from a user's branch to local pool.
        
        Args:
            username: Username to sync messages for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            current_branch = self.git_manager._get_current_branch()
            
            # Fetch latest from user's branch
            if self.git_manager.use_github:
                self.git_manager._run_git_command(['fetch', 'origin', f'user/{username}'])
            
            # Switch to user's branch
            self.git_manager._run_git_command(['checkout', f'user/{username}'])
            
            # Copy messages to local pool
            user_dir = self.messages_dir / username
            if user_dir.exists():
                for msg_file in user_dir.glob('*.txt'):
                    pool_file = self.messages_dir / f"{username}_{msg_file.name}"
                    shutil.copy2(msg_file, pool_file)
            
            # Switch back to original branch
            self.git_manager._run_git_command(['checkout', current_branch])
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing messages for user {username}: {e}")
            return False
    
    def sync_all_messages(self) -> bool:
        """Sync messages from all user branches to local pool.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get list of user branches
            branches = self.git_manager._run_git_command(['branch', '-r'])
            user_branches = [
                b.strip().split('/')[-1] 
                for b in branches.split('\n') 
                if b.strip().startswith('origin/user/')
            ]
            
            # Sync each user's messages
            for username in user_branches:
                self.sync_user_messages(username)
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing all messages: {e}")
            return False
    
    def get_active_users(self) -> List[Dict[str, str]]:
        """Get list of active users.
        
        Returns:
            List of user metadata dictionaries
        """
        try:
            data = self._load_active_users()
            return list(data['users'].values())
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
