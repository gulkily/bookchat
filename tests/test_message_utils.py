import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.message_utils import (MessageError, create_message, load_message,
                             save_message)


class TestMessageUtils(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test messages
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = Path(self.temp_dir)

    def test_create_message(self):
        """Test creating a new message."""
        message = create_message('testuser', 'Test message content')
        
        self.assertIsInstance(message, dict)
        self.assertIn('id', message)
        self.assertEqual(message['author'], 'testuser')
        self.assertEqual(message['content'], 'Test message content')
        self.assertIsNone(message['reply_to'])
        
        # Verify timestamp format
        datetime.fromisoformat(message['timestamp'])

    def test_create_message_with_reply(self):
        """Test creating a message with reply reference."""
        message = create_message('testuser', 'Test reply', reply_to='original-id')
        
        self.assertEqual(message['reply_to'], 'original-id')

    def test_create_message_invalid_author(self):
        """Test creating message with invalid author."""
        with self.assertRaises(ValueError):
            create_message('invalid/author', 'Test content')
        
        with self.assertRaises(ValueError):
            create_message('', 'Test content')

    def test_create_message_invalid_content(self):
        """Test creating message with invalid content."""
        with self.assertRaises(ValueError):
            create_message('testuser', '')
        
        with self.assertRaises(ValueError):
            create_message('testuser', '   ')

    def test_save_message(self):
        """Test saving a message to file."""
        message = create_message('testuser', 'Test message')
        file_path = save_message(message, self.base_path)
        
        self.assertTrue(file_path.exists())
        self.assertTrue(file_path.is_file())
        
        # Verify file structure
        self.assertIn('messages', str(file_path))
        
        # Load and verify content
        with open(file_path) as f:
            saved_message = json.load(f)
        self.assertEqual(saved_message, message)

    def test_save_message_invalid(self):
        """Test saving invalid message data."""
        with self.assertRaises(MessageError):
            save_message({'invalid': 'message'}, self.base_path)
        
        with self.assertRaises(MessageError):
            save_message('not a dict', self.base_path)

    def test_load_message(self):
        """Test loading a message from file."""
        # Create and save a message
        original_message = create_message('testuser', 'Test message')
        file_path = save_message(original_message, self.base_path)
        
        # Load the message
        loaded_message = load_message(file_path)
        
        self.assertEqual(loaded_message, original_message)

    def test_load_message_invalid_file(self):
        """Test loading from invalid message file."""
        # Create an invalid message file
        invalid_file = self.base_path / 'invalid.json'
        with open(invalid_file, 'w') as f:
            f.write('invalid json')
        
        with self.assertRaises(MessageError):
            load_message(invalid_file)

    def test_load_message_missing_file(self):
        """Test loading from non-existent file."""
        with self.assertRaises(MessageError):
            load_message(self.base_path / 'nonexistent.json')

    def test_message_directory_structure(self):
        """Test that messages are saved in the correct directory structure."""
        message = create_message('testuser', 'Test message')
        file_path = save_message(message, self.base_path)
        
        # Parse the timestamp
        timestamp = datetime.fromisoformat(message['timestamp'])
        
        # Verify directory structure
        expected_parts = [
            'messages',
            str(timestamp.year),
            f"{timestamp.month:02d}",
            f"{timestamp.day:02d}"
        ]
        
        current_path = self.base_path
        for part in expected_parts:
            current_path = current_path / part
            self.assertTrue(current_path.exists())
            self.assertTrue(current_path.is_dir())

if __name__ == '__main__':
    unittest.main()
