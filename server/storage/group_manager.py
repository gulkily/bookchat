"""Group management functionality for message storage."""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger('group_manager')

class GroupManager:
    """Manages message groups using Git branches."""

    def __init__(self, git_manager):
        """Initialize GroupManager.
        
        Args:
            git_manager: GitManager instance to handle Git operations
        """
        self.git_manager = git_manager
        self.groups_file = self.git_manager.repo_path / 'groups.json'
        self._ensure_groups_file()
    
    def _ensure_groups_file(self):
        """Ensure groups metadata file exists."""
        if not self.groups_file.exists():
            self._save_groups({
                'general': {
                    'id': 'general',
                    'name': 'General',
                    'description': 'Default message group',
                    'created_at': datetime.now().isoformat(),
                }
            })
    
    def _load_groups(self) -> Dict[str, Dict[str, str]]:
        """Load groups metadata from file."""
        try:
            with open(self.groups_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading groups: {e}")
            return {}
    
    def _save_groups(self, groups: Dict[str, Dict[str, str]]):
        """Save groups metadata to file."""
        try:
            with open(self.groups_file, 'w') as f:
                json.dump(groups, f, indent=2)
            # Commit changes to groups file
            self.git_manager.add_and_commit_file(
                str(self.groups_file),
                "Update groups metadata",
                "BookChat Bot"
            )
        except Exception as e:
            logger.error(f"Error saving groups: {e}")
    
    def create_group(self, group_id: str, name: str, description: str) -> bool:
        """Create a new message group.
        
        Args:
            group_id: Unique identifier for the group
            name: Display name for the group
            description: Group description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate group_id format
            if not group_id.isalnum() and not all(c in '-_' for c in group_id if not c.isalnum()):
                raise ValueError("Group ID must be alphanumeric with optional hyphens and underscores")
            
            # Create group branch
            branch_name = f'group/{group_id}'
            self.git_manager._run_git_command(['checkout', '-b', branch_name])
            
            # Create group message directory
            group_dir = self.git_manager.messages_dir / group_id
            group_dir.mkdir(parents=True, exist_ok=True)
            
            # Add README to group directory
            readme_path = group_dir / 'README.md'
            with open(readme_path, 'w') as f:
                f.write(f"# {name}\n\n{description}\n")
            
            # Commit group directory
            self.git_manager.add_and_commit_file(
                str(readme_path),
                f"Initialize message group: {name}",
                "BookChat Bot"
            )
            
            # Switch back to main branch
            self.git_manager._run_git_command(['checkout', 'main'])
            
            # Update groups metadata
            groups = self._load_groups()
            groups[group_id] = {
                'id': group_id,
                'name': name,
                'description': description,
                'created_at': datetime.now().isoformat(),
            }
            self._save_groups(groups)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating group {group_id}: {e}")
            return False
    
    def delete_group(self, group_id: str) -> bool:
        """Delete a message group.
        
        Args:
            group_id: ID of the group to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Cannot delete default group
            if group_id == 'general':
                raise ValueError("Cannot delete default group")
            
            # Delete group branch
            branch_name = f'group/{group_id}'
            self.git_manager._run_git_command(['branch', '-D', branch_name])
            
            # Update groups metadata
            groups = self._load_groups()
            if group_id in groups:
                del groups[group_id]
                self._save_groups(groups)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting group {group_id}: {e}")
            return False
    
    def list_groups(self) -> List[Dict[str, str]]:
        """List all message groups.
        
        Returns:
            List of group metadata dictionaries
        """
        try:
            groups = self._load_groups()
            return list(groups.values())
        except Exception as e:
            logger.error(f"Error listing groups: {e}")
            return []
    
    def get_group(self, group_id: str) -> Optional[Dict[str, str]]:
        """Get metadata for a specific group.
        
        Args:
            group_id: ID of the group
            
        Returns:
            Group metadata dictionary if found, None otherwise
        """
        try:
            groups = self._load_groups()
            return groups.get(group_id)
        except Exception as e:
            logger.error(f"Error getting group {group_id}: {e}")
            return None
    
    def switch_to_group(self, group_id: str) -> bool:
        """Switch to a group's branch.
        
        Args:
            group_id: ID of the group to switch to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.get_group(group_id):
                raise ValueError(f"Group {group_id} does not exist")
            
            branch_name = f'group/{group_id}'
            self.git_manager._run_git_command(['checkout', branch_name])
            return True
            
        except Exception as e:
            logger.error(f"Error switching to group {group_id}: {e}")
            return False
