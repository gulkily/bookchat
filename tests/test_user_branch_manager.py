"""Tests for user branch management functionality."""

import os
import pytest
from pathlib import Path
from server.storage.git_manager import GitManager
from server.storage.user_branch_manager import UserBranchManager
import json
import logging
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)

@pytest.fixture
def git_manager():
    """Create a GitManager instance."""
    # Use the project repository
    repo_path = Path(os.getcwd())
    manager = GitManager(repo_path, test_mode=True)
    
    # Clean up any existing state
    try:
        manager._run_git_command(['reset', '--hard', 'HEAD'])
        manager._run_git_command(['clean', '-fd'])
        manager._run_git_command(['checkout', 'main'])
    except:
        pass
        
    return manager

@pytest.fixture
def user_manager(git_manager):
    """Create a UserBranchManager instance."""
    return UserBranchManager(git_manager)

@pytest.fixture(autouse=True)
def clean_git_state(user_manager):
    """Clean up git state before and after each test."""
    # Reset any changes and clean up untracked files
    try:
        user_manager.git._run_git_command(['reset', '--hard', 'HEAD'])
        user_manager.git._run_git_command(['clean', '-fd'])
        user_manager.git._run_git_command(['checkout', 'main'])
    except:
        pass
    yield
    try:
        user_manager.git._run_git_command(['reset', '--hard', 'HEAD'])
        user_manager.git._run_git_command(['clean', '-fd'])
        user_manager.git._run_git_command(['checkout', 'main'])
    except:
        pass

@pytest.fixture(autouse=True)
def clean_active_users(user_manager):
    """Clean up active users file before each test."""
    with open(user_manager.active_users_file, 'w') as f:
        json.dump([], f)
    yield
    with open(user_manager.active_users_file, 'w') as f:
        json.dump([], f)

@pytest.mark.asyncio
async def test_ensure_user_branch(user_manager):
    """Test creating a user branch."""
    try:
        # First make sure we're on main branch
        user_manager.git._run_git_command(['checkout', 'main'])
        
        # Create user branch
        success = user_manager.ensure_user_branch('test_user')
        assert success
        
        # Verify branch exists
        result = user_manager.git._run_git_command(['branch', '--list', 'user/test_user'])
        assert 'user/test_user' in result.stdout
        
        # Verify messages directory exists
        messages_dir = Path(user_manager.messages_dir) / 'test_user'
        assert messages_dir.exists()
        assert (messages_dir / 'README.md').exists()
        
    finally:
        # Clean up - delete the test branch if it exists
        try:
            # Switch back to main before deleting
            user_manager.git._run_git_command(['checkout', 'main'])
            user_manager.git._run_git_command(['branch', '-D', 'user/test_user'])
            # Clean up test user directory
            test_user_dir = Path(user_manager.messages_dir) / 'test_user'
            if test_user_dir.exists():
                import shutil
                shutil.rmtree(test_user_dir)
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")

@pytest.mark.asyncio
async def test_message_commit(user_manager):
    """Test that messages are properly committed to git."""
    username = 'test_user'
    message = {
        'content': 'Test message',
        'author': username,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # Save message
        message_id = user_manager.save_message(message)
        assert message_id is not None
        
        # Switch to user branch and verify commit
        user_branch = f'user/{username}'
        user_manager.git._run_git_command(['checkout', user_branch])
        
        # Verify file exists in git
        message_path = Path('messages') / username / f"{message_id}.txt"
        result = user_manager.git._run_git_command(['ls-files', str(message_path)])
        assert str(message_path) in result.stdout, "Message file not tracked by git"
        
        # Verify commit exists
        result = user_manager.git._run_git_command(['log', '-1', '--pretty=format:%s'])
        expected_msg = f'Add message {message_id} from {username}'
        assert expected_msg in result.stdout, f"Expected commit message '{expected_msg}' not found in '{result.stdout}'"
        
    finally:
        # Clean up
        try:
            user_manager.git._run_git_command(['checkout', 'main'])
            user_manager.git._run_git_command(['branch', '-D', user_branch])
            # Clean up test user directory
            test_user_dir = Path(user_manager.messages_dir) / username
            if test_user_dir.exists():
                import shutil
                shutil.rmtree(test_user_dir)
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
