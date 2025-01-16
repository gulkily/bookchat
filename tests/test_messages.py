import unittest
from unittest.mock import MagicMock, patch
import json
import os
import tempfile
from datetime import datetime
import pytest

# Import your server modules
from server.handler_methods import MessageHandler
from server.utils import parse_message

@pytest.mark.asyncio
class TestMessageHandling:
    async def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        mock_server = MagicMock()
        self.handler = MessageHandler(mock_server)
        
    async def tearDown(self):
        # Clean up temp directory
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    async def test_message_persistence(self):
        """Test that messages are properly saved and can be retrieved after server restart"""
        test_message = {
            'content': 'Test message',
            'author': 'testuser',
            'timestamp': '2025-01-16T11:49:08-05:00'
        }
        
        # Save message
        await self.handler.server.storage.save_message(
            test_message['author'],
            test_message['content'],
            datetime.fromisoformat(test_message['timestamp'])
        )
        
        # Verify message was saved
        messages = await self.handler.server.storage.get_messages()
        assert len(messages) == 1
        saved_msg = messages[0]
        assert saved_msg['content'] == test_message['content']
        assert saved_msg['author'] == test_message['author']
        
    async def test_signature_handling(self):
        """Test that signatures are properly handled and not displayed in message content"""
        test_messages = [
            "Regular message without signature",
            "Message with signature\n-- \nSignature",
            "Message with multiple dashes\n--\nSignature\n--\nMore signature"
        ]
        
        for msg in test_messages:
            parsed = parse_message(msg)
            if '--' in msg:
                # Verify signature is separated
                assert '--' not in parsed['content']
                assert hasattr(parsed, 'signature')
            else:
                # Verify message without signature is unchanged
                assert parsed['content'] == msg
                assert not hasattr(parsed, 'signature')

@pytest.mark.asyncio
class TestUIBehavior:
    async def setUp(self):
        # Set up a mock DOM environment
        self.messages_container = MagicMock()
        self.messages_container.scrollHeight = 1000
        self.messages_container.clientHeight = 500
        
    async def test_auto_scroll(self):
        """Test that chat automatically scrolls to bottom on new messages"""
        # Mock the DOM elements
        with patch('document.getElementById') as mock_get_element:
            mock_get_element.return_value = self.messages_container
            
            # Simulate adding new message
            self.handler.add_message("New test message")
            
            # Verify scroll was set to bottom
            assert self.messages_container.scrollTop == self.messages_container.scrollHeight
            
    async def test_scroll_on_load(self):
        """Test that chat scrolls to bottom on initial load"""
        with patch('document.getElementById') as mock_get_element:
            mock_get_element.return_value = self.messages_container
            
            # Simulate loading messages
            self.handler.load_messages()
            
            # Verify scroll was set to bottom
            assert self.messages_container.scrollTop == self.messages_container.scrollHeight

if __name__ == '__main__':
    unittest.main()
