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

    @abstractmethod
    def pin_message(self, message_id: int, pinned_by: str) -> bool:
        """Pin a message
        
        Args:
            message_id: ID of the message to pin
            pinned_by: Username of the user pinning the message
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def unpin_message(self, message_id: int, unpinned_by: str) -> bool:
        """Unpin a message
        
        Args:
            message_id: ID of the message to unpin
            unpinned_by: Username of the user unpinning the message
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_pinned_messages(self) -> List[Dict]:
        """Retrieve all pinned messages
        
        Returns:
            List of pinned message dictionaries
        """
        pass
