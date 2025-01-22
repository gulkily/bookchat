"""Test GitHub synchronization functionality."""

import os
import pytest
from pathlib import Path
from server.storage.file_storage import FileStorage
from server.message_handler import MessageHandler

@pytest.fixture
def message_handler():
    """Create a MessageHandler instance for testing."""
    # Set environment variables to enable GitHub sync
    os.environ['SYNC_TO_GITHUB'] = 'true'
    
    # Create FileStorage with the actual repository
    storage = FileStorage(data_dir=os.getcwd())
    return MessageHandler(storage=storage)
