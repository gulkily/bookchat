"""Tests for file storage implementation."""

import os
import pytest
from pathlib import Path
from server.storage.file_storage import FileStorage

@pytest.fixture
def temp_storage(tmp_path):
    """Create a temporary storage directory."""
    return FileStorage(str(tmp_path))

@pytest.mark.asyncio
async def test_parse_message_standard_format(temp_storage):
    """Test parsing message with standard header format."""
    content = """ID: test_user_123
Content: Hello World
Author: test_user
Timestamp: 2025-01-17T14:54:28-05:00"""

    message = temp_storage._parse_message_content(content)
    assert message['id'] == 'test_user_123'
    assert message['content'] == 'Hello World'
    assert message['author'] == 'test_user'
    assert message['timestamp'] == '2025-01-17T14:54:28-05:00'

@pytest.mark.asyncio
async def test_parse_message_headers_anywhere(temp_storage):
    """Test parsing message with headers in random order and positions."""
    content = """Some initial text that should be ignored

Author: test_user
This is some text between headers
ID: test_user_123
More text between headers
Content: Hello World
Even more text
Timestamp: 2025-01-17T14:54:28-05:00
Final text"""

    message = temp_storage._parse_message_content(content)
    assert message['id'] == 'test_user_123'
    assert message['content'] == 'Hello World'
    assert message['author'] == 'test_user'
    assert message['timestamp'] == '2025-01-17T14:54:28-05:00'

@pytest.mark.asyncio
async def test_parse_message_no_content_header(temp_storage):
    """Test parsing message with no explicit content header."""
    content = """ID: test_user_123
Author: test_user
Timestamp: 2025-01-17T14:54:28-05:00

This is the actual message content
It can span multiple lines
And should all be captured"""

    message = temp_storage._parse_message_content(content)
    assert message['id'] == 'test_user_123'
    assert message['content'] == 'This is the actual message content\nIt can span multiple lines\nAnd should all be captured'
    assert message['author'] == 'test_user'
    assert message['timestamp'] == '2025-01-17T14:54:28-05:00'

@pytest.mark.asyncio
async def test_save_and_retrieve_message(temp_storage):
    """Test saving and retrieving a message."""
    # Create test message
    message = {
        'content': 'Test message',
        'author': 'test_user',
        'timestamp': '2025-01-17T14:54:28-05:00'
    }
    
    # Save message
    message_id = await temp_storage.save_message(message)
    assert message_id is not None
    
    # Retrieve message
    retrieved = await temp_storage.get_message_by_id(message_id)
    assert retrieved is not None
    assert retrieved['content'] == message['content']
    assert retrieved['author'] == message['author']
    assert retrieved['timestamp'] == message['timestamp']
    assert retrieved['id'] == message_id

@pytest.mark.asyncio
async def test_get_all_messages(temp_storage):
    """Test retrieving all messages."""
    # Create test messages
    messages = [
        {
            'content': 'Message 1',
            'author': 'user1',
            'timestamp': '2025-01-17T14:54:28-05:00'
        },
        {
            'content': 'Message 2',
            'author': 'user2',
            'timestamp': '2025-01-17T14:54:29-05:00'
        }
    ]
    
    # Save messages
    message_ids = []
    for message in messages:
        message_id = await temp_storage.save_message(message)
        assert message_id is not None
        message_ids.append(message_id)
    
    # Retrieve all messages
    retrieved = await temp_storage.get_messages()
    assert len(retrieved) == len(messages)
    
    # Verify message contents
    for i, message in enumerate(messages):
        assert any(
            m['content'] == message['content'] and
            m['author'] == message['author'] and
            m['timestamp'] == message['timestamp'] and
            m['id'] == message_ids[i]
            for m in retrieved
        )
