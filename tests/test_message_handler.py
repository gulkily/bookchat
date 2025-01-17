"""Tests for message handler module."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.message_handler import MessageHandler


@pytest.fixture
def mock_storage():
    """Create a mock storage backend."""
    storage = MagicMock()
    storage.save_message = AsyncMock(return_value=1)  # Return message ID
    storage.get_messages = AsyncMock(return_value=[])
    storage.get_message = AsyncMock(return_value={
        'id': 1,
        'content': 'Test message',
        'author': 'test_user',
        'timestamp': '2025-01-17T14:04:38-05:00'
    })
    return storage


@pytest.fixture
def message_handler(mock_storage):
    """Create a message handler with mock storage."""
    return MessageHandler(mock_storage)


@pytest.mark.asyncio
async def test_get_messages(message_handler, mock_storage):
    """Test getting messages."""
    mock_messages = [
        {'id': 1, 'content': 'Message 1', 'author': 'user1',
         'timestamp': '2025-01-17T14:04:38-05:00'},
        {'id': 2, 'content': 'Message 2', 'author': 'user2',
         'timestamp': '2025-01-17T14:04:38-05:00'}
    ]
    mock_storage.get_messages.return_value = mock_messages
    
    messages = await message_handler.get_messages()
    assert len(messages) == 2
    assert messages == mock_messages


@pytest.mark.asyncio
async def test_create_message(message_handler):
    """Test creating a message."""
    message = await message_handler.create_message(
        author='test_user',
        content='Test message',
        timestamp='2025-01-17T14:04:38-05:00'
    )
    
    assert message['id'] == 1
    assert message['content'] == 'Test message'
    assert message['author'] == 'test_user'
    assert message['timestamp'] == '2025-01-17T14:04:38-05:00'


@pytest.mark.asyncio
async def test_handle_post_message(message_handler):
    """Test handling message post request."""
    request = AsyncMock()
    request.json = AsyncMock(return_value={
        'content': 'Test message',
        'author': 'test_user',
        'timestamp': '2025-01-17T14:51:18-05:00'
    })

    response = await message_handler.handle_post_message(request)
    assert response['success'] is True
    assert 'data' in response
    stored_message = response['data']
    assert stored_message['content'] == 'Test message'
    assert stored_message['author'] == 'test_user'
    assert 'timestamp' in stored_message
