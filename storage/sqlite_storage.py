"""SQLite storage backend for BookChat."""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import uuid
import logging

from storage import StorageBackend
from .archive_manager import MessageArchiver

logger = logging.getLogger(__name__)

class SQLiteStorage(StorageBackend):
    """Storage backend that uses SQLite for message storage."""
    
    def __init__(self, db_path: str):
        """Initialize SQLite storage with the given database path"""
        self.db_path = db_path
        self.init_storage()

    def _get_connection(self):
        """Get a database connection with proper configuration"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_storage(self):
        """Initialize the SQLite database with required schema"""
        from database.init_db import init_database
        init_database()

    def pin_message(self, message_id: str, pinned_by: str) -> bool:
        """Pin a message"""
        try:
            with self._get_connection() as conn:
                # Check if message exists
                message = conn.execute(
                    "SELECT id FROM messages WHERE id = ?",
                    (message_id,)
                ).fetchone()
                
                if not message:
                    return False

                # Add to pinned_messages and update messages table
                conn.execute(
                    """INSERT INTO pinned_messages (message_id, pinned_by)
                       VALUES (?, ?)""",
                    (message_id, pinned_by)
                )
                conn.execute(
                    "UPDATE messages SET is_pinned = 1 WHERE id = ?",
                    (message_id,)
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"Error pinning message: {e}")
            return False

    def unpin_message(self, message_id: str, unpinned_by: str) -> bool:
        """Unpin a message"""
        try:
            with self._get_connection() as conn:
                # Remove from pinned_messages and update messages table
                conn.execute(
                    "DELETE FROM pinned_messages WHERE message_id = ?",
                    (message_id,)
                )
                conn.execute(
                    "UPDATE messages SET is_pinned = 0 WHERE id = ?",
                    (message_id,)
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"Error unpinning message: {e}")
            return False

    def get_pinned_messages(self) -> List[Dict]:
        """Retrieve all pinned messages"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT m.*, pm.pinned_at, pm.pinned_by
                    FROM messages m
                    INNER JOIN pinned_messages pm ON m.id = pm.message_id
                    ORDER BY pm.pinned_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting pinned messages: {e}")
            return []

    def get_messages(self, limit: Optional[int] = None) -> List[Dict]:
        """Retrieve messages from the database"""
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT m.*, 
                           CASE WHEN pm.message_id IS NOT NULL THEN 1 ELSE 0 END as is_pinned,
                           pm.pinned_at,
                           pm.pinned_by
                    FROM messages m
                    LEFT JOIN pinned_messages pm ON m.id = pm.message_id
                    ORDER BY m.timestamp DESC
                """
                if limit:
                    query += f" LIMIT {limit}"
                    
                cursor = conn.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting messages: {e}")
            return []

    def save_message(self, user: str, content: str, timestamp: datetime) -> bool:
        """Save a new message"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO messages (user, content, timestamp)
                       VALUES (?, ?, ?)""",
                    (user, content, timestamp.isoformat())
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"Error saving message: {e}")
            return False

    def get_message_by_id(self, message_id: str) -> Optional[Dict]:
        """Get a specific message by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT m.*, 
                              CASE WHEN pm.message_id IS NOT NULL THEN 1 ELSE 0 END as is_pinned,
                              pm.pinned_at,
                              pm.pinned_by
                       FROM messages m
                       LEFT JOIN pinned_messages pm ON m.id = pm.message_id
                       WHERE m.id = ?""",
                    (message_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting message by ID: {e}")
            return None

    def archive_old_messages(self, reference_time: datetime) -> Optional[str]:
        """Archive messages older than the threshold.
        
        Args:
            reference_time: Current time to calculate threshold from
            
        Returns:
            Path to created archive if messages were archived, None otherwise
        """
        return None

    def get_messages(self, limit: Optional[int] = None, include_archives: bool = False) -> List[Dict[str, Any]]:
        """Retrieve messages from the SQLite database.
        
        Args:
            limit: Optional maximum number of messages to retrieve
            include_archives: Whether to include archived messages in the response
            
        Returns:
            List of message dictionaries
        """
        try:
            messages = []
            with self._get_connection() as conn:
                query = """
                    SELECT m.*, 
                           CASE WHEN pm.message_id IS NOT NULL THEN 1 ELSE 0 END as is_pinned,
                           pm.pinned_at,
                           pm.pinned_by
                    FROM messages m
                    LEFT JOIN pinned_messages pm ON m.id = pm.message_id
                    ORDER BY m.timestamp DESC
                """
                if limit:
                    query += f" LIMIT {limit}"
                    
                cursor = conn.execute(query)
                messages = [dict(row) for row in cursor.fetchall()]
                
            if include_archives:
                archives = []
                for archive in archives:
                    archived_messages = []
                    messages.extend(archived_messages)
                messages.sort(key=lambda x: x['timestamp'], reverse=True)
                if limit is not None:
                    messages = messages[:limit]
                    
            return messages
        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            return []
