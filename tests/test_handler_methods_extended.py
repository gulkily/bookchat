"""Extended tests for handler_methods.py."""

import json
import pytest
from aiohttp import web
from unittest.mock import MagicMock, patch, AsyncMock
from server.handler_methods import (
    serve_messages,
    handle_message_post,
    handle_username_change,
    verify_username
)

@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = MagicMock()
    request.app = {'storage': MagicMock()}
    request.json = AsyncMock()
    return request

@pytest.fixture
def mock_message_handler():
    """Create a mock message handler."""
    with patch('server.handler_methods.MessageHandler') as mock:
        mock.return_value.handle_get_messages = AsyncMock()
        mock.return_value.handle_post_message = AsyncMock()
        yield mock

@pytest.fixture
def mock_json_response():
    """Create a mock for web.json_response."""
    with patch('server.handler_methods.web.json_response') as mock:
        def side_effect(data, status=200):
            response = MagicMock()
            response.status = status
            response._body = json.dumps(data).encode('utf-8')
            async def text():
                return response._body.decode('utf-8')
            response.text = text
            response.set_cookie = MagicMock()
            return response
        mock.side_effect = side_effect
        yield mock

@pytest.fixture
def mock_response():
    """Create a mock for web.Response."""
    with patch('server.handler_methods.web.Response') as mock:
        def side_effect(text='', status=200):
            response = MagicMock()
            response.status = status
            response._text = text
            async def text_func():
                return response._text
            response.text = text_func
            return response
        mock.side_effect = side_effect
        yield mock

@pytest.mark.asyncio
async def test_serve_messages_success(mock_request, mock_message_handler, mock_json_response):
    """Test successful message serving."""
    mock_handler = mock_message_handler.return_value
    mock_handler.handle_get_messages.return_value = {'messages': []}
    
    response = await serve_messages(mock_request)
    
    assert isinstance(response, MagicMock)
    assert response.status == 200
    assert json.loads(await response.text()) == {'messages': []}

@pytest.mark.asyncio
async def test_serve_messages_error(mock_request, mock_message_handler, mock_json_response):
    """Test error handling in serve_messages."""
    mock_handler = mock_message_handler.return_value
    mock_handler.handle_get_messages.side_effect = Exception('Test error')
    
    response = await serve_messages(mock_request)
    
    assert isinstance(response, MagicMock)
    assert response.status == 500
    assert json.loads(await response.text()) == {
        'success': False,
        'error': 'Test error'
    }

@pytest.mark.asyncio
async def test_handle_message_post_success(mock_request, mock_message_handler, mock_json_response):
    """Test successful message posting."""
    mock_request.json.return_value = {'content': 'test message', 'author': 'test_user'}
    mock_handler = mock_message_handler.return_value
    mock_handler.handle_post_message.return_value = {
        'success': True,
        'data': {'id': '123', 'content': 'test message'}
    }
    
    response = await handle_message_post(mock_request)
    
    assert isinstance(response, MagicMock)
    assert response.status == 200
    assert json.loads(await response.text()) == {'id': '123', 'content': 'test message'}

@pytest.mark.asyncio
async def test_handle_message_post_missing_fields(mock_request, mock_json_response):
    """Test message posting with missing fields."""
    test_cases = [
        ({'content': '', 'author': 'test_user'}, 'Missing required fields'),
        ({'content': 'test', 'author': ''}, 'Missing required fields'),
        ({'content': 'test'}, 'Missing required fields'),
        ({'author': 'test'}, 'Missing required fields'),
    ]
    
    for data, expected_error in test_cases:
        mock_request.json.return_value = data
        response = await handle_message_post(mock_request)
        
        assert response.status == 400
        response_data = json.loads(await response.text())
        assert response_data['success'] is False
        assert response_data['error'] == expected_error

@pytest.mark.asyncio
async def test_handle_message_post_invalid_json(mock_request, mock_json_response):
    """Test message posting with invalid JSON."""
    mock_request.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
    
    response = await handle_message_post(mock_request)
    
    assert response.status == 400
    response_data = json.loads(await response.text())
    assert response_data['success'] is False
    assert response_data['error'] == 'Invalid JSON data'

@pytest.mark.asyncio
async def test_handle_username_change_success(mock_request, mock_json_response):
    """Test successful username change."""
    mock_request.json.return_value = {
        'old_username': 'old_user',
        'new_username': 'new_user'
    }
    
    response = await handle_username_change(mock_request)
    
    assert isinstance(response, MagicMock)
    assert response.status == 200
    response_data = json.loads(await response.text())
    assert response_data['success'] is True
    assert response_data['username'] == 'new_user'
    
    # Verify cookie
    assert hasattr(response, 'set_cookie')
    response.set_cookie.assert_called_with(
        'username', 'new_user',
        max_age=31536000,
        httponly=True
    )

@pytest.mark.asyncio
async def test_handle_username_change_validation(mock_request, mock_response):
    """Test username change validation."""
    test_cases = [
        ('', 'New username cannot be empty'),
        ('ab', 'Username must be between 3 and 20 characters'),
        ('a' * 21, 'Username must be between 3 and 20 characters'),
        ('user@name', 'Username can only contain letters, numbers, and underscores'),
        ('user name', 'Username can only contain letters, numbers, and underscores'),
    ]
    
    for username, expected_error in test_cases:
        mock_request.json.return_value = {
            'old_username': 'old_user',
            'new_username': username
        }
        
        response = await handle_username_change(mock_request)
        
        assert response.status == 400
        assert await response.text() == expected_error

@pytest.mark.asyncio
async def test_verify_username(mock_request, mock_json_response):
    """Test username verification."""
    mock_request.cookies = {'username': 'test_user'}
    
    response = await verify_username(mock_request)
    
    assert isinstance(response, MagicMock)
    assert response.status == 200
    response_data = json.loads(await response.text())
    assert response_data['status'] == 'verified'
    assert response_data['username'] == 'test_user'
