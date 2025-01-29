"""Tests for user branch management functionality."""

import os
import pytest
from pathlib import Path
from datetime import datetime
from server.storage.git_manager import GitManager
from server.storage.user_branch_manager import UserBranchManager

@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary Git repository."""
    repo_path = tmp_path / 'test_repo'
    repo_path.mkdir()
    return str(repo_path)

@pytest.fixture
def git_manager(temp_repo):
    """Create a GitManager instance in test mode."""
    return GitManager(temp_repo, test_mode=True)

@pytest.fixture
def user_manager(git_manager):
    """Create a UserBranchManager instance."""
    return UserBranchManager(git_manager)

@pytest.mark.asyncio
async def test_ensure_user_branch(user_manager, temp_repo):
    """Test creating a user branch."""
    # Create user branch
    success = user_manager.ensure_user_branch('test_user')
    assert success
    
    # Verify branch exists
    branch_path = Path(temp_repo) / '.git' / 'refs' / 'heads' / 'user' / 'test_user'
    assert branch_path.exists()
    
    # Verify messages directory exists
    messages_dir = Path(temp_repo) / 'messages' / 'test_user'
    assert messages_dir.exists()
    assert (messages_dir / 'README.md').exists()

@pytest.mark.asyncio
async def test_save_message_branch_location(user_manager, temp_repo):
    """Test that messages are saved to the correct branch and location."""
    username = 'test_user'
    message = {
        'content': 'Test message',
        'author': username,
        'timestamp': datetime.now().isoformat()
    }
    
    # Save message
    message_id = user_manager.save_message(message)
    assert message_id is not None
    
    # Get current branch before checking
    original_branch = user_manager.git_manager._get_current_branch()
    
    try:
        # Switch to user branch and verify message exists
        user_manager.git_manager._run_git_command(['checkout', f'user/{username}'])
        
        # Check message exists in user's branch directory
        user_message_path = user_manager.messages_dir / username / f"{message_id}.txt"
        assert user_message_path.exists(), f"Message not found in user branch at {user_message_path}"
        
        # Verify message content
        with open(user_message_path, 'r') as f:
            content = f.read()
            assert message['content'] in content
            assert message['author'] in content
            assert message['timestamp'] in content
        
        # Verify branch is properly tracked
        branches = user_manager.git_manager._run_git_command(['branch', '-vv'])
        branch_info = next(line for line in branches.split('\n') if f'user/{username}' in line)
        assert '[origin/user/' in branch_info, "Branch not properly tracked with remote"
        
        # Verify commit history
        log = user_manager.git_manager._run_git_command(['log', '--oneline', '-1'])
        assert f"Add message {message_id}" in log, "Commit message not found"
        assert username in log, "Author not found in commit"
        
    finally:
        # Switch back to original branch
        user_manager.git_manager._run_git_command(['checkout', original_branch])
    
    # Verify message exists in local pool
    pool_message_path = user_manager.messages_dir / f"{username}_{message_id}.txt"
    assert pool_message_path.exists(), f"Message not found in local pool at {pool_message_path}"

@pytest.mark.asyncio
async def test_save_message(user_manager):
    """Test saving a message to a user branch."""
    message = {
        'content': 'Test message',
        'author': 'test_user',
        'timestamp': datetime.now().isoformat()
    }
    
    # Save message
    message_id = user_manager.save_message(message)
    assert message_id is not None
    
    # Verify message exists in user branch
    user_manager.git_manager._run_git_command(['checkout', 'user/test_user'])
    message_path = user_manager.messages_dir / 'test_user' / f"{message_id}.txt"
    assert message_path.exists()
    
    # Verify message exists in local pool
    pool_path = user_manager.messages_dir / f"test_user_{message_id}.txt"
    assert pool_path.exists()

@pytest.mark.asyncio
async def test_sync_user_messages(user_manager):
    """Test syncing messages from a user branch."""
    # Create test messages
    messages = [
        {
            'content': 'Message 1',
            'author': 'test_user',
            'timestamp': datetime.now().isoformat()
        },
        {
            'content': 'Message 2',
            'author': 'test_user',
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    # Save messages
    message_ids = []
    for message in messages:
        message_id = user_manager.save_message(message)
        assert message_id is not None
        message_ids.append(message_id)
    
    # Clear local pool
    for file in user_manager.messages_dir.glob('*.txt'):
        file.unlink()
    
    # Sync messages
    success = user_manager.sync_user_messages('test_user')
    assert success
    
    # Verify messages exist in local pool
    for message_id in message_ids:
        pool_path = user_manager.messages_dir / f"test_user_{message_id}.txt"
        assert pool_path.exists()

@pytest.mark.asyncio
async def test_sync_all_messages(user_manager):
    """Test syncing messages from all user branches."""
    # Create test messages for multiple users
    users = ['user1', 'user2']
    messages = {
        user: [
            {
                'content': f'Message 1 from {user}',
                'author': user,
                'timestamp': datetime.now().isoformat()
            },
            {
                'content': f'Message 2 from {user}',
                'author': user,
                'timestamp': datetime.now().isoformat()
            }
        ]
        for user in users
    }
    
    # Save messages for each user
    message_ids = {}
    for user, user_messages in messages.items():
        message_ids[user] = []
        for message in user_messages:
            message_id = user_manager.save_message(message)
            assert message_id is not None
            message_ids[user].append(message_id)
    
    # Clear local pool
    for file in user_manager.messages_dir.glob('*.txt'):
        file.unlink()
    
    # Sync all messages
    success = user_manager.sync_all_messages()
    assert success
    
    # Verify all messages exist in local pool
    for user, user_message_ids in message_ids.items():
        for message_id in user_message_ids:
            pool_path = user_manager.messages_dir / f"{user}_{message_id}.txt"
            assert pool_path.exists()

@pytest.mark.asyncio
async def test_get_active_users(user_manager):
    """Test getting list of active users."""
    # Create messages from multiple users
    users = ['user1', 'user2']
    for user in users:
        message = {
            'content': f'Message from {user}',
            'author': user,
            'timestamp': datetime.now().isoformat()
        }
        message_id = user_manager.save_message(message)
        assert message_id is not None
    
    # Get active users
    active_users = user_manager.get_active_users()
    assert len(active_users) == len(users)
    
    # Verify user data
    for user in users:
        user_data = next((u for u in active_users if u['username'] == user), None)
        assert user_data is not None
        assert user_data['message_count'] == 1
