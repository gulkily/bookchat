"""Test message storage functionality."""

import os
import unittest
from pathlib import Path
from datetime import datetime

from server.message_handler import MessageHandler
from server.storage.file_storage import FileStorage
from server.config import DEFAULT_STORAGE_DIR

class TestMessageStorage(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """Set up test environment."""
        # Create a test storage directory
        self.test_storage_dir = os.path.join(DEFAULT_STORAGE_DIR, 'test_storage')
        self.storage = FileStorage(self.test_storage_dir)
        self.handler = MessageHandler(self.storage)
        
        # Ensure test directory exists
        Path(self.test_storage_dir).mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """Clean up test environment."""
        # Clean up test files after each test
        messages_dir = Path(self.test_storage_dir) / 'messages'
        if messages_dir.exists():
            for file in messages_dir.glob('*.txt'):
                file.unlink()
            messages_dir.rmdir()
        Path(self.test_storage_dir).rmdir()
    
    async def test_message_saved_to_filesystem(self):
        """Test that new messages are saved as files."""
        # Create a test message
        test_content = "Test message content"
        test_author = "test_user"
        
        # Create the message
        message = await self.handler.create_message(
            content=test_content,
            author=test_author
        )
        
        # Verify message was created with an ID
        self.assertIsNotNone(message['id'])
        
        # Check that the message file exists
        message_path = Path(self.test_storage_dir) / 'messages' / f"{message['id']}.txt"
        self.assertTrue(message_path.exists())
        
        # Verify file contents
        with open(message_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn(test_content, content)
            self.assertIn(test_author, content)
            self.assertIn(message['timestamp'], content)

if __name__ == '__main__':
    unittest.main()
