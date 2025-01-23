"""Tests for the request handler module."""

import json
import unittest
from unittest.mock import MagicMock, patch
from aiohttp import web
import asyncio

from server.handler import ChatRequestHandler

class TestChatRequestHandler(unittest.IsolatedAsyncioTestCase):
    """Test cases for ChatRequestHandler."""

    def setUp(self):
        """Set up test environment."""
        self.app = MagicMock()
        self.handler = ChatRequestHandler(self.app)

    async def asyncTearDown(self):
        """Clean up test environment."""
        await super().asyncTearDown()
        # Ensure all pending tasks are complete
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def test_handle_get_messages(self):
        """Test GET /messages endpoint."""
        request = MagicMock()
        request.method = 'GET'
        request.path = '/messages'
        
        with patch('server.handler.serve_messages') as mock_serve:
            mock_serve.return_value = web.Response(text='test response')
            response = await self.handler.handle_request(request)
            
            mock_serve.assert_called_once_with(request)
            self.assertEqual(response.text, 'test response')

    async def test_handle_post_message(self):
        """Test POST /messages endpoint."""
        request = MagicMock()
        request.method = 'POST'
        request.path = '/messages'
        
        with patch('server.handler.handle_message_post') as mock_post:
            mock_post.return_value = web.Response(
                text=json.dumps({'status': 'success'}),
                content_type='application/json'
            )
            response = await self.handler.handle_request(request)
            
            mock_post.assert_called_once_with(request)
            self.assertEqual(
                json.loads(response.text),
                {'status': 'success'}
            )

    async def test_handle_username_change(self):
        """Test POST /change_username endpoint."""
        request = MagicMock()
        request.method = 'POST'
        request.path = '/change_username'
        
        with patch('server.handler.handle_username_change') as mock_change:
            mock_change.return_value = web.Response(
                text=json.dumps({'status': 'username changed'}),
                content_type='application/json'
            )
            response = await self.handler.handle_request(request)
            
            mock_change.assert_called_once_with(request)
            self.assertEqual(
                json.loads(response.text),
                {'status': 'username changed'}
            )
