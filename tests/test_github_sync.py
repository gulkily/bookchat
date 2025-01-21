import os
import pytest
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
from server.storage.file_storage import FileStorage
from server.message_handler import MessageHandler
from server.storage.git_manager import GitManager

@pytest.fixture
def message_handler():
    """Create a MessageHandler instance for testing."""
    # Set environment variables to enable GitHub sync
    os.environ['SYNC_TO_GITHUB'] = 'true'
    
    # Create FileStorage with the actual repository
    storage = FileStorage(data_dir=os.getcwd())
    return MessageHandler(storage=storage)

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
    
    # Wait for file to be created and synced
    await asyncio.sleep(0.5)
    
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
