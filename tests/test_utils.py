"""Tests for utility functions."""

import os
import socket
import tempfile
import unittest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from server.utils import (
    find_available_port,
    ensure_directories,
    parse_message,
    get_file_size,
    get_directory_size,
    bytes_to_mb,
    mb_to_bytes,
    format_size,
    get_content_type,
    send_json_response,
    ensure_directory_exists
)
from server.config import STATIC_DIR, TEMPLATES_DIR, STORAGE_DIR

class TestUtils(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))

    def test_find_available_port(self):
        """Test finding an available port."""
        # Test normal case
        port = find_available_port(start_port=8080)
        self.assertIsInstance(port, int)
        self.assertGreaterEqual(port, 8080)

        # Test when port is in use
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 9090))
            port = find_available_port(start_port=9090)
            self.assertNotEqual(port, 9090)
            self.assertGreater(port, 9090)

    def test_ensure_directories(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('server.utils.STATIC_DIR', os.path.join(temp_dir, 'static')), \
                 patch('server.utils.TEMPLATES_DIR', os.path.join(temp_dir, 'templates')), \
                 patch('server.utils.STORAGE_DIR', os.path.join(temp_dir, 'storage')):
                
                ensure_directories()
                
                # Check if directories were created
                self.assertTrue(os.path.exists(os.path.join(temp_dir, 'static')))
                self.assertTrue(os.path.exists(os.path.join(temp_dir, 'templates')))
                self.assertTrue(os.path.exists(os.path.join(temp_dir, 'storage')))

    def test_parse_message(self):
        """Test message parsing."""
        # Test valid message
        valid_message = {
            'content': 'Test message',
            'author': 'test_user',
            'timestamp': '2025-01-22T12:00:00Z'
        }
        parsed = parse_message(valid_message)
        self.assertEqual(parsed['content'], 'Test message')
        self.assertEqual(parsed['author'], 'test_user')
        self.assertEqual(parsed['timestamp'], '2025-01-22T12:00:00Z')

        # Test missing field
        invalid_message = {
            'content': 'Test message',
            'author': 'test_user'
        }
        with self.assertRaises(ValueError) as cm:
            parse_message(invalid_message)
        self.assertIn('Missing required field', str(cm.exception))

    def test_get_file_size(self):
        """Test getting file size."""
        # Create a temporary file with known content
        test_file = os.path.join(self.temp_dir, 'test.txt')
        content = 'Hello, World!'
        with open(test_file, 'w') as f:
            f.write(content)
        
        size = get_file_size(test_file)
        self.assertEqual(size, len(content))
        
        # Test non-existent file
        size = get_file_size('nonexistent.txt')
        self.assertEqual(size, 0)

    def test_get_directory_size(self):
        """Test getting directory size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some files with known sizes
            file1 = os.path.join(temp_dir, 'file1.txt')
            file2 = os.path.join(temp_dir, 'file2.txt')
            
            with open(file1, 'w') as f:
                f.write('Hello')  # 5 bytes
            with open(file2, 'w') as f:
                f.write('World')  # 5 bytes
                
            # Create a subdirectory with a file
            subdir = os.path.join(temp_dir, 'subdir')
            os.makedirs(subdir)
            file3 = os.path.join(subdir, 'file3.txt')
            with open(file3, 'w') as f:
                f.write('Test')  # 4 bytes
                
            total_size = get_directory_size(temp_dir)
            self.assertEqual(total_size, 14)  # 5 + 5 + 4 bytes

    def test_bytes_and_mb_conversion(self):
        """Test byte/MB conversion functions."""
        # Test bytes to MB
        self.assertEqual(bytes_to_mb(1048576), 1.0)  # 1 MB
        self.assertEqual(bytes_to_mb(2097152), 2.0)  # 2 MB
        
        # Test MB to bytes
        self.assertEqual(mb_to_bytes(1.0), 1048576)  # 1 MB
        self.assertEqual(mb_to_bytes(2.0), 2097152)  # 2 MB

    def test_format_size(self):
        """Test size formatting."""
        self.assertEqual(format_size(500), '500 B')
        self.assertEqual(format_size(1024), '1.0 KB')
        self.assertEqual(format_size(1048576), '1.0 MB')
        self.assertEqual(format_size(1073741824), '1.0 GB')

    def test_get_content_type(self):
        """Test content type detection."""
        self.assertEqual(get_content_type('test.html'), 'text/html')
        self.assertEqual(get_content_type('test.css'), 'text/css')
        self.assertEqual(get_content_type('test.js'), 'application/javascript')
        self.assertEqual(get_content_type('test.json'), 'application/json')
        self.assertEqual(get_content_type('test.png'), 'image/png')
        self.assertEqual(get_content_type('test.unknown'), 'application/octet-stream')

    def test_send_json_response(self):
        """Test sending JSON response."""
        mock_handler = MagicMock()
        test_data = {'message': 'test'}
        
        send_json_response(mock_handler, test_data, 200)
        
        # Verify response was sent correctly
        mock_handler.send_response.assert_called_once_with(200)
        mock_handler.send_header.assert_called_once_with('Content-Type', 'application/json')
        mock_handler.end_headers.assert_called_once()
        mock_handler.wfile.write.assert_called_once()
        
        # Test error handling
        mock_handler.wfile.write.side_effect = Exception('Test error')
        send_json_response(mock_handler, test_data, 200)
        mock_handler.send_error.assert_called_once()

    def test_ensure_directory_exists(self):
        """Test ensuring directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = os.path.join(temp_dir, 'test_dir')
            
            # Test creating new directory
            ensure_directory_exists(test_dir)
            self.assertTrue(os.path.exists(test_dir))
            self.assertTrue(os.path.isdir(test_dir))
            
            # Test with existing directory (should not raise error)
            ensure_directory_exists(test_dir)
            self.assertTrue(os.path.exists(test_dir))

if __name__ == '__main__':
    unittest.main()
