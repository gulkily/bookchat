"""Tests for the file storage backend."""

import json
from datetime import datetime
from pathlib import Path
import pytest
from unittest.mock import patch
from storage.file_storage import FileStorage

@pytest.fixture
def storage(tmp_path):
    """Create a test storage instance."""
    from storage.file_storage import FileStorage
    storage = FileStorage(tmp_path)
    return storage

@pytest.mark.asyncio
async def test_message_persistence_and_retrieval(storage, tmp_path):
    """Test that messages can be saved and retrieved correctly."""
    # Setup test data
    test_messages = [
        {
            'content': 'First test message',
            'username': 'user1',
            'timestamp': datetime(2025, 1, 16, 10, 45, 32)
        },
        {
            'content': 'Second test message',
            'username': 'user2',
            'timestamp': datetime(2025, 1, 16, 10, 50, 00)
        }
    ]

    # Save messages
    for msg in test_messages:
        success = await storage.save_message(
            msg['username'],
            msg['content'],
            msg['timestamp']
        )
        assert success, f"Failed to save message: {msg}"

    # Verify files were created
    messages_dir = tmp_path / 'messages'
    message_files = list(messages_dir.glob('*.txt'))
    assert len(message_files) == 2, "Not all message files were created"

    # Get messages and verify content
    saved_messages = await storage.get_messages()
    assert len(saved_messages) == 2, "Not all messages were retrieved"

    # Verify content matches
    for orig, saved in zip(test_messages, saved_messages):
        assert saved['content'] == orig['content']
        assert saved['author'] == orig['username']
        assert datetime.fromisoformat(saved['timestamp']).replace(microsecond=0) == orig['timestamp']

@pytest.mark.asyncio
async def test_message_file_format(storage, tmp_path):
    """Test that message files have the correct format."""
    # Create a test message
    username = "testuser"
    content = "Test message content"
    timestamp = datetime(2025, 1, 16, 11, 5, 51)

    # Save the message
    success = await storage.save_message(username, content, timestamp)
    assert success, "Failed to save message"

    # Find the message file
    messages_dir = tmp_path / 'messages'
    message_files = list(messages_dir.glob('*.txt'))
    assert len(message_files) == 1, "Message file not created"

    # Read the file and verify format
    with open(message_files[0]) as f:
        message_data = json.load(f)
    
    assert message_data['content'] == content
    assert message_data['author'] == username
    assert datetime.fromisoformat(message_data['timestamp']).replace(microsecond=0) == timestamp

@pytest.mark.asyncio
async def test_real_message_parsing():
    """Test parsing of real message files from the messages directory."""
    from storage.file_storage import FileStorage

    # Use the actual messages directory
    storage = FileStorage(Path("/home/wsl/bookchat"))

    # Get all messages
    messages = await storage.get_messages()
    assert len(messages) > 0, "No messages found in messages directory"

    # Verify message format
    for message in messages:
        assert 'content' in message
        assert 'author' in message
        assert 'timestamp' in message
        assert isinstance(message['content'], str)
        assert isinstance(message['author'], str)
        # Verify timestamp is ISO format
        datetime.fromisoformat(message['timestamp'])

@pytest.mark.asyncio
async def test_message_ordering():
    """Test that messages are returned in the correct order (newest first)."""
    from storage.file_storage import FileStorage

    # Use the actual messages directory
    storage = FileStorage(Path("/home/wsl/bookchat"))

    # Get all messages
    messages = await storage.get_messages()
    assert len(messages) > 0, "No messages found in messages directory"

    # Verify timestamps are in descending order
    timestamps = [datetime.fromisoformat(m['timestamp']) for m in messages]
    assert all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))

@pytest.mark.asyncio
async def test_get_messages_with_mixed_formats(tmp_path):
    """Test that get_messages can handle both JSON and Git-style formats."""
    storage = FileStorage(tmp_path)

    # Create a JSON format message
    json_msg_time = datetime(2025, 1, 16, 11, 16, 11)  # Use current time
    json_msg = {
        "user": "test_user",
        "content": "JSON message",
        "timestamp": json_msg_time.isoformat()
    }
    json_msg_path = tmp_path / "messages" / f"{json_msg_time.strftime('%Y%m%d_%H%M%S')}_test_user.txt"
    json_msg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_msg_path, "w") as f:
        json.dump(json_msg, f)

    # Create a Git-style message
    git_msg_time = datetime(2025, 1, 16, 11, 16, 12)  # 1 second later
    git_msg_content = f"Git message\n\n-- \nAuthor: test_user2\nDate: {git_msg_time.isoformat()}\n"
    git_msg_path = tmp_path / "messages" / f"{git_msg_time.strftime('%Y%m%d_%H%M%S')}_test_user2.txt"
    with open(git_msg_path, "w") as f:
        f.write(git_msg_content)

    # Get messages and verify both formats are loaded
    messages = await storage.get_messages()
    assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"

    # Verify both messages are present
    contents = [m['content'] for m in messages]
    assert "JSON message" in contents
    assert "Git message" in contents
