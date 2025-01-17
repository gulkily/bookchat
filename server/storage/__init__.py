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
