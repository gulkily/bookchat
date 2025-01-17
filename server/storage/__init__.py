"""Storage module for BookChat."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime

class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def init_storage(self) -> bool:
        """Initialize the storage."""
        pass
    
    @abstractmethod
    def save_message(self, user: str, content: str, timestamp: datetime) -> bool:
        """Save a new message."""
        pass
    
    @abstractmethod
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve messages, optionally limited to a certain number."""
        pass
    
    @abstractmethod
    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
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
    if use_git:
        return GitStorage(data_dir)
    return FileStorage(data_dir)
