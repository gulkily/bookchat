import os
import pytest
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
from server.storage.file_storage import FileStorage
from server.message_handler import MessageHandler

@pytest.fixture
def test_repo_path(tmp_path):
    """Create a temporary repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    
    # Initialize git repository
    subprocess.run(['git', 'init'], cwd=repo_path, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_path, check=True)
    subprocess.run(['git', 'branch', '-m', 'main'], cwd=repo_path, check=True)
    
    # Create initial commit
    readme_path = repo_path / "README.md"
    readme_path.write_text("# Test Repository\nThis is a test repository for BookChat.")
    subprocess.run(['git', 'add', 'README.md'], cwd=repo_path, check=True)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, check=True)
    
    # Add remote pointing to the actual GitHub repository
    subprocess.run(['git', 'remote', 'add', 'origin', 'https://github.com/gulkily/bookchat.git'], cwd=repo_path, check=True)
    
    return repo_path

@pytest.fixture
def file_storage(test_repo_path):
    """Create a FileStorage instance for testing."""
    # Set environment variables to enable GitHub sync
    os.environ['GITHUB_TOKEN'] = os.environ.get('GITHUB_TOKEN', '')  # Use actual GitHub token
    os.environ['GITHUB_REPO'] = 'gulkily/bookchat'
    os.environ['SYNC_TO_GITHUB'] = 'true'
    
    storage = FileStorage(data_dir=test_repo_path)
    return storage

@pytest.fixture
def message_handler(file_storage):
    """Create a MessageHandler instance for testing."""
    return MessageHandler(storage=file_storage)

@pytest.mark.asyncio
async def test_github_message_sync(message_handler):
    """Test that a new message is properly synced to GitHub."""
    # Create a test message
    test_content = "Test message for GitHub sync"
    test_author = "test_author"
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S-05:00')  # Include timezone offset
    
    # Create the message
    message = await message_handler.create_message(
        content=test_content,
        author=test_author,
        current_time=current_time
    )
    
    # Verify the message was created locally
    assert message is not None
    assert message["content"] == test_content
    assert message["author"] == test_author
    
    # Get the message ID and construct the filepath
    message_id = message["id"]
    assert message_id is not None
    
    # Construct the expected filepath
    message_path = message_handler.storage.messages_dir / f"{message_id}.txt"
    
    # Wait for file to be created
    await asyncio.sleep(0.1)
    
    # Verify the file exists locally
    assert message_path.exists()
    
    # Verify the file content
    with open(message_path, 'r') as f:
        content = f.read()
        assert test_content in content
        assert test_author in content
        
    # Verify that the file is committed
    result = subprocess.run(
        ['git', 'status', '--porcelain'], 
        cwd=message_handler.storage.data_dir,
        capture_output=True,
        text=True,
        check=True
    )
    assert result.stdout.strip() == "", "Working directory should be clean (file should be committed)"
    
    # Verify that GitManager is initialized
    assert message_handler.storage.git_manager is not None, "GitManager should be initialized"
    
    # Get the latest commit message
    commit_result = subprocess.run(
        ['git', 'log', '-1', '--pretty=format:%s'],
        cwd=message_handler.storage.data_dir,
        capture_output=True,
        text=True,
        check=True
    )
    assert message_id in commit_result.stdout, "Latest commit should contain the message ID"
    
    # Verify that changes were pushed to GitHub
    push_result = subprocess.run(
        ['git', 'push', 'origin', 'main'],
        cwd=message_handler.storage.data_dir,
        capture_output=True,
        text=True
    )
    assert push_result.returncode == 0, f"Push should succeed. Error: {push_result.stderr}"
