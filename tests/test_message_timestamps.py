import unittest
import json
from datetime import datetime
from server.message_handler import MessageHandler

class MockStorage:
    async def get_messages(self):
        return [
            {
                'id': '123',
                'content': 'Test message 1',
                'author': 'test_user',
                'timestamp': '2025-01-17T17:25:23-05:00'
            },
            {
                'id': '124',
                'content': 'Test message 2',
                'author': 'test_user',
                'timestamp': '2025-01-17T17:28:24-05:00'
            }
        ]
    
    async def save_message(self, message):
        return '123'

class TestMessageTimestamps(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.storage = MockStorage()
        self.handler = MessageHandler(self.storage)

    def test_message_timestamp_format(self):
        """Test that message timestamps are correctly formatted in API response"""
        current_time = '2025-01-17T20:07:45-05:00'
        
        # Get a message from the handler
        message = self.handler._to_api_response({
            'id': '123',
            'content': 'Test message',
            'author': 'test_user',
            'timestamp': current_time
        })
        
        # Verify the timestamp is present in the response
        self.assertIn('timestamp', message)
        self.assertEqual(message['timestamp'], current_time)
        
        # Verify the timestamp can be parsed by JavaScript Date
        # We'll simulate this by trying to parse it with Python's datetime
        try:
            datetime.fromisoformat(message['timestamp'])
        except ValueError:
            self.fail("Timestamp is not in ISO format that JavaScript can parse")
    
    def test_different_messages_different_timestamps(self):
        """Test that different messages have different timestamps"""
        # Create two messages in succession
        message1 = self.handler._to_api_response({
            'id': '123',
            'content': 'Test message 1',
            'author': 'test_user',
            'timestamp': '2025-01-17T17:25:23-05:00'
        })
        
        message2 = self.handler._to_api_response({
            'id': '124',
            'content': 'Test message 2',
            'author': 'test_user',
            'timestamp': '2025-01-17T17:28:24-05:00'
        })
        
        # Verify the timestamps are different
        self.assertNotEqual(message1['timestamp'], message2['timestamp'])
        
        # Verify both timestamps are valid ISO format
        try:
            datetime.fromisoformat(message1['timestamp'])
            datetime.fromisoformat(message2['timestamp'])
        except ValueError:
            self.fail("Timestamps are not in ISO format that JavaScript can parse")
    
    async def test_new_message_gets_current_time(self):
        """Test that new messages get the current time as their timestamp"""
        # Create a new message without specifying a timestamp
        current_time = '2025-01-17T20:07:45-05:00'
        message = await self.handler.create_message(
            content='New message',
            author='test_user',
            current_time=current_time
        )
        
        # Verify the timestamp is the current time from metadata
        self.assertEqual(message['timestamp'], current_time)
        
        # Create another message with a different current time
        new_current_time = '2025-01-17T20:07:46-05:00'  # One second later
        message2 = await self.handler.create_message(
            content='Another message',
            author='test_user',
            current_time=new_current_time
        )
        
        # Verify timestamps are different
        self.assertNotEqual(message['timestamp'], message2['timestamp'])
        self.assertEqual(message2['timestamp'], new_current_time)
        
        # Verify timestamps can be parsed by JavaScript Date
        try:
            datetime.fromisoformat(message['timestamp'])
            datetime.fromisoformat(message2['timestamp'])
        except ValueError:
            self.fail("Timestamps are not in ISO format that JavaScript can parse")

if __name__ == '__main__':
    unittest.main()
