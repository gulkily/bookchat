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
def user_manager():
    """Create a UserBranchManager for testing."""
    test_dir = Path('test_repo')
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()
    
    # Create messages directory
    messages_dir = test_dir / 'messages'
    messages_dir.mkdir(exist_ok=True)
    
    git_manager = GitManager(test_dir, test_mode=True)
    manager = UserBranchManager(git_manager)
    
    # Create active_users.json
    with open(test_dir / 'active_users.json', 'w') as f:
        json.dump({}, f)
    
    # Initialize git repository
    manager.git._run_git_command(['init'])
    manager.git._run_git_command(['config', 'user.email', 'test@example.com'])
    manager.git._run_git_command(['config', 'user.name', 'Test User'])
    manager.git._run_git_command(['add', '.'])
    manager.git._run_git_command(['commit', '-m', 'Initial commit'])
    
    # Reset git state before each test
    try:
        manager.git._run_git_command(['reset', '--hard', 'HEAD'])
        manager.git._run_git_command(['clean', '-fd'])
        manager.git.checkout_branch('main')
    except:
        pass
    yield manager
    # Clean up after test
    try:
        manager.git._run_git_command(['reset', '--hard', 'HEAD'])
        manager.git._run_git_command(['clean', '-fd'])
        manager.git.checkout_branch('main')
    except:
        pass
    
    if test_dir.exists():
        shutil.rmtree(test_dir)

@pytest.fixture(autouse=True)
def clean_active_users(user_manager):
    """Clean up active users file before each test."""
    with open(user_manager.active_users_file, 'w') as f:
        json.dump({}, f)
    yield
    with open(user_manager.active_users_file, 'w') as f:
        json.dump({}, f)

@pytest.mark.asyncio
async def test_ensure_user_branch(user_manager):
    """Test creating a user branch."""
    try:
        # First make sure we're on main branch
        user_manager.git.checkout_branch('main')

        # Create user branch
        success = user_manager.ensure_user_branch('test_user')
        assert success

        # Verify branch exists
        result = user_manager.git._run_git_command(['branch', '--list', 'user/test_user'])
        assert 'user/test_user' in result.stdout

        # Create user directory
        user_dir = user_manager.messages_dir / 'test_user'
        user_dir.mkdir(parents=True, exist_ok=True)

        # Verify messages directory exists
        messages_dir = Path(user_manager.messages_dir) / 'test_user'
        assert messages_dir.exists()
    finally:
        # Clean up
        try:
            user_manager.git.checkout_branch('main')
        except:
            pass

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
        user_manager.git.checkout_branch(user_branch)
        
        # Verify file exists in git
        message_path = Path('messages') / username / f"{message_id}.json"
        result = user_manager.git._run_git_command(['ls-files', str(message_path)])
        assert str(message_path) in result.stdout, "Message file not tracked by git"
        
        # Verify commit exists
        result = user_manager.git._run_git_command(['log', '-1', '--pretty=format:%s'])
        expected_msg = f'Add message {message_id}'
        assert expected_msg in result.stdout, f"Expected commit message '{expected_msg}' not found in '{result.stdout}'"
        
    finally:
        # Clean up
        try:
            user_manager.git.checkout_branch('main')
        except:
            pass
