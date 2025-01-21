"""Storage module for BookChat."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
import os

class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def init_storage(self) -> bool:
        """Initialize the storage."""
        pass
    
    @abstractmethod
    async def save_message(self, message: Dict[str, str]) -> Optional[str]:
        """Save a new message.
        
        Args:
            message: Dictionary containing message data (author, content, timestamp)
            
        Returns:
            Message ID if successful, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_messages(self) -> List[Dict[str, Any]]:
        """Retrieve messages."""
        pass
    
    @abstractmethod
    async def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific message by ID."""
        pass


"""Storage package initialization."""

from pathlib import Path
from typing import Union

from server.storage.file_storage import FileStorage
from server.storage.git_storage import GitStorage

def init_storage(data_dir: str, use_git: bool = False) -> Union[FileStorage, GitStorage]:
    """Initialize storage with the given data directory.
    
    Args:
        data_dir: Directory to store data in
        use_git: Whether to use git-based storage
        
    Returns:
        Storage instance
    """
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    if os.getenv('SYNC_TO_GITHUB', 'false').lower() == 'true':
        return GitStorage(data_dir)
    return FileStorage(data_dir)
