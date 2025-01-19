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


@pytest.mark.asyncio
async def test_handle_get_messages_no_extra_args(message_handler):
    """Test that handle_get_messages doesn't accept extra arguments."""
    with pytest.raises(TypeError, match="takes 1 positional argument but 2 were given"):
        await message_handler.handle_get_messages("extra_arg")


@pytest.mark.asyncio
async def test_handle_post_message_with_dict(message_handler):
    """Test handling message post with direct dictionary input."""
    message_data = {
        'content': 'Test message',
        'author': 'test_user',
        'timestamp': '2025-01-17T14:51:18-05:00'
    }

    response = await message_handler.handle_post_message(message_data)
    assert response['success'] is True
    assert 'data' in response
    stored_message = response['data']
    assert stored_message['content'] == 'Test message'
    assert stored_message['author'] == 'test_user'
    assert 'timestamp' in stored_message


@pytest.mark.asyncio
async def test_handle_post_message_missing_content(message_handler):
    """Test handling message post with missing content."""
    request = AsyncMock()
    request.json = AsyncMock(return_value={
        'author': 'test_user',
        'timestamp': '2025-01-17T14:51:18-05:00'
    })

    response = await message_handler.handle_post_message(request)
    assert response['success'] is False
    assert 'error' in response


@pytest.mark.asyncio
async def test_handle_post_message_missing_author(message_handler):
    """Test handling message post with missing author."""
    request = AsyncMock()
    request.json = AsyncMock(return_value={
        'content': 'Test message',
        'timestamp': '2025-01-17T14:51:18-05:00'
    })

    response = await message_handler.handle_post_message(request)
    assert response['success'] is True
    assert 'data' in response
    stored_message = response['data']
    assert stored_message['content'] == 'Test message'
    assert stored_message['author'] == 'anonymous'  # Should default to 'anonymous'


@pytest.mark.asyncio
async def test_handle_post_message_missing_timestamp(message_handler):
    """Test handling message post with missing timestamp."""
    request = AsyncMock()
    request.json = AsyncMock(return_value={
        'content': 'Test message',
        'author': 'test_user'
    })

    response = await message_handler.handle_post_message(request)
    assert response['success'] is True
    assert 'data' in response
    stored_message = response['data']
    assert stored_message['content'] == 'Test message'
    assert stored_message['author'] == 'test_user'
    assert 'timestamp' in stored_message  # Should auto-generate timestamp


@pytest.mark.asyncio
async def test_handle_post_message_empty_content(message_handler):
    """Test handling message post with empty content."""
    request = AsyncMock()
    request.json = AsyncMock(return_value={
        'content': '',
        'author': 'test_user',
        'timestamp': '2025-01-17T14:51:18-05:00'
    })

    response = await message_handler.handle_post_message(request)
    assert response['success'] is False
    assert 'error' in response


@pytest.mark.asyncio
async def test_handle_post_message_whitespace_content(message_handler):
    """Test handling message post with whitespace-only content."""
    request = AsyncMock()
    request.json = AsyncMock(return_value={
        'content': '   \n\t  ',
        'author': 'test_user',
        'timestamp': '2025-01-17T14:51:18-05:00'
    })

    response = await message_handler.handle_post_message(request)
    assert response['success'] is False
    assert 'error' in response


@pytest.mark.asyncio
async def test_handle_post_message_invalid_json(message_handler):
    """Test handling message post with invalid JSON."""
    request = AsyncMock()
    request.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)

    response = await message_handler.handle_post_message(request)
    assert response['success'] is False
    assert 'error' in response


@pytest.mark.asyncio
async def test_create_message_with_current_time(message_handler):
    """Test creating a message with auto-generated current time."""
    message = await message_handler.create_message(
        content='Test message',
        author='test_user'
    )
    
    assert message['id'] == 1
    assert message['content'] == 'Test message'
    assert message['author'] == 'test_user'
    assert 'timestamp' in message
    # Verify timestamp format
    datetime.fromisoformat(message['timestamp'])  # Should not raise error
