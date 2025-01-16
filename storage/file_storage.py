"""File-based storage backend for BookChat."""

import json
import os
import logging
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import fcntl

logger = logging.getLogger(__name__)

class FileStorage:
    """Storage backend that uses text files for message storage."""
    
    def __init__(self, base_dir):
        """Initialize message storage with base directory."""
        self.base_dir = Path(base_dir)
        self.messages_dir = self.base_dir / 'messages'
        self.messages_dir.mkdir(parents=True, exist_ok=True)

    async def get_messages(self, limit=None):
        """Get all messages, optionally limited to a number."""
        messages = []
        try:
            # Log start of message retrieval
            logger.info(f"Starting message retrieval from {self.messages_dir}")
            
            # Check if messages directory exists and is readable
            if not os.path.exists(self.messages_dir):
                logger.error(f"Messages directory does not exist: {self.messages_dir}")
                return []
            
            if not os.access(self.messages_dir, os.R_OK):
                logger.error(f"Messages directory is not readable: {self.messages_dir}")
                return []
            
            # Get all .txt files and sort by modification time
            message_files = sorted(
                [f for f in os.listdir(self.messages_dir) if f.endswith('.txt')],
                key=lambda f: os.path.getmtime(self.messages_dir / f)
            )
            
            logger.info(f"Found {len(message_files)} message files")
            
            for filename in message_files:
                file_path = self.messages_dir / filename
                try:
                    with open(file_path, 'r') as f:
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                        try:
                            content = f.read()
                            parts = content.split('\n-- \n', 1)
                            message_content = parts[0].strip()
                            
                            # Parse metadata
                            metadata = {}
                            if len(parts) > 1:
                                for line in parts[1].strip().split('\n'):
                                    if ':' in line:
                                        key, value = line.split(':', 1)
                                        metadata[key.strip().lower()] = value.strip()
                            
                            # Parse timestamp to datetime for sorting
                            try:
                                timestamp_str = metadata.get('timestamp')
                                if not timestamp_str:
                                    timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))
                                else:
                                    timestamp = datetime.fromisoformat(timestamp_str)
                            except (ValueError, TypeError):
                                # If timestamp parsing fails, use file modification time
                                timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))
                                logger.warning(f"Invalid timestamp in message {file_path}, using file modification time")
                                
                            message = {
                                'id': file_path.stem,
                                'content': message_content,
                                'author': metadata.get('author', 'anonymous'),
                                'timestamp': timestamp.isoformat(),
                                'verified': metadata.get('verified', 'false')
                            }
                            messages.append(message)
                        finally:
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except Exception as e:
                    logger.error(f"Error reading message file {filename}: {e}", exc_info=True)
                    continue

            # Preserve original order of messages
            if limit is not None:
                messages = messages[-limit:]
            
            logger.info(f"Successfully retrieved {len(messages)} messages")
            return messages
            
        except Exception as e:
            logger.error(f"Comprehensive error getting messages: {e}", exc_info=True)
            return []

    async def save_message(self, author, content, timestamp, metadata=None):
        """Save a new message."""
        try:
            # Generate message ID
            message_id = str(uuid.uuid4())
            
            # Format timestamp
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()
                
            # Create metadata
            metadata = metadata or {}
            metadata.update({
                'author': author,
                'timestamp': timestamp,
                'verified': metadata.get('verified', 'false')
            })

            # Use message ID in filename
            file_path = self.messages_dir / f"{message_id}.txt"

            # Write message atomically
            temp_path = file_path.with_suffix('.tmp')
            try:
                with open(temp_path, 'w') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        # Write content
                        f.write(content)
                        f.write('\n-- \n')  # Metadata separator
                        
                        # Write metadata
                        for key, value in metadata.items():
                            f.write(f"{key.title()}: {value}\n")
                            
                        f.flush()
                        os.fsync(f.fileno())
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                        
                os.rename(temp_path, file_path)
                return message_id
                
            except Exception as e:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise e

        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    async def get_message(self, message_id):
        """Get a specific message by ID."""
        try:
            file_path = self.messages_dir / f"{message_id}.txt"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        content = f.read()
                        parts = content.split('\n-- \n', 1)
                        message_content = parts[0].strip()
                        
                        # Parse metadata
                        metadata = {}
                        if len(parts) > 1:
                            for line in parts[1].strip().split('\n'):
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    metadata[key.strip().lower()] = value.strip()
                        
                        return {
                            'id': message_id,
                            'content': message_content,
                            'author': metadata.get('author', 'anonymous'),
                            'timestamp': metadata.get('timestamp', datetime.now().isoformat()),
                            'verified': metadata.get('verified', 'false')
                        }
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return None

        except Exception as e:
            logger.error(f"Error getting message by ID: {e}")
            return None

    async def update_message(self, message_id, updates):
        """Update an existing message's metadata."""
        try:
            file_path = self.messages_dir / f"{message_id}.txt"
            if not file_path.exists():
                return False

            # Read existing message
            with open(file_path, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    content = f.read()
                    parts = content.split('\n-- \n', 1)
                    message_content = parts[0].strip()
                    
                    # Parse existing metadata
                    metadata = {}
                    if len(parts) > 1:
                        for line in parts[1].strip().split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                metadata[key.strip().lower()] = value.strip()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Update metadata
            metadata.update(updates)

            # Write updated message atomically
            temp_path = file_path.with_suffix('.tmp')
            try:
                with open(temp_path, 'w') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        # Write content
                        f.write(message_content)
                        f.write('\n-- \n')  # Metadata separator
                        
                        # Write metadata
                        for key, value in metadata.items():
                            f.write(f"{key.title()}: {value}\n")
                            
                        f.flush()
                        os.fsync(f.fileno())
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                        
                os.rename(temp_path, file_path)
                return True
                
            except Exception as e:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise e

        except Exception as e:
            logger.error(f"Error updating message: {e}")
            return False

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import fcntl
import os
import asyncio

logger = logging.getLogger('bookchat')

class MessageStorage:
    """Handles persistent storage of chat messages using files."""
    
    def __init__(self, messages_dir: Path):
        """Initialize the message storage.
        
        Args:
            messages_dir: Path to directory where messages will be stored
        """
        self.messages_dir = Path(messages_dir)
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        
    async def save_message(self, author: str, content: str, timestamp: datetime, metadata: Optional[Dict] = None) -> Optional[str]:
        """Save a new message to storage.
        
        Args:
            author: Username of message author
            content: Message content
            timestamp: Message timestamp
            metadata: Optional additional metadata
            
        Returns:
            Message ID if successful, None if failed
        """
        try:
            # Generate a stable message ID
            message_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{timestamp.isoformat()}_{author}"))
            
            # Format filename: YYYYMMDD_HHMMSS_username.txt
            filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{author}.txt"
            file_path = self.messages_dir / filename
            
            # Prepare message data
            message_data = {
                'content': content.strip(),
                'metadata': {
                    'author': author,
                    'date': timestamp.isoformat(),
                    'id': message_id,
                    **(metadata or {})
                }
            }
            
            # Write atomically using file locking
            async with open(file_path, mode='w') as f:
                # Get exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    # Write content first
                    f.write(message_data['content'])
                    f.write('\n-- \n')  # Metadata separator
                    
                    # Write metadata
                    for key, value in message_data['metadata'].items():
                        f.write(f"{key.title()}: {value}\n")
                        
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    # Release lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            logger.info(f"Saved message {message_id} to {file_path}")
            return message_id
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None
    
    async def get_messages(self, limit: Optional[int] = None, before: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get messages from storage with optional filtering.
        
        Args:
            limit: Maximum number of messages to return
            before: Only return messages before this timestamp
            
        Returns:
            List of message dictionaries
        """
        try:
            messages = []
            
            # Get all message files
            message_files = sorted(
                list(self.messages_dir.glob('*.txt')),
                key=lambda x: x.stat().st_mtime
            )
            
            # Apply timestamp filter
            if before:
                message_files = [f for f in message_files if datetime.fromtimestamp(f.stat().st_mtime) < before]
            
            # Apply limit
            if limit:
                message_files = message_files[-limit:]
            
            for file_path in message_files:
                try:
                    message = await self._parse_message_file(file_path)
                    if message:
                        messages.append(message)
                except Exception as e:
                    logger.error(f"Error reading message {file_path}: {e}")
                    continue
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []
    
    async def _parse_message_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a message file into a message dictionary.
        
        Args:
            file_path: Path to message file
            
        Returns:
            Message dictionary or None if parsing failed
        """
        try:
            with open(file_path, mode='r') as f:
                # Get shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    content = f.read()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Split content and metadata
            parts = content.split('\n-- \n', 1)
            message_content = parts[0].strip()
            
            # Parse metadata
            metadata = {}
            if len(parts) > 1:
                for line in parts[1].split('\n'):
                    if ': ' in line:
                        key, value = line.split(': ', 1)
                        metadata[key.lower()] = value.strip()
            
            # Extract or generate required fields
            try:
                timestamp = metadata.get('date')
                if not timestamp:
                    # Parse from filename
                    dt_str = file_path.stem.split('_')[0:2]
                    timestamp = datetime.strptime('_'.join(dt_str), '%Y%m%d_%H%M%S').isoformat()
            except Exception as e:
                logger.error(f"Error parsing timestamp for {file_path}: {e}")
                timestamp = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            
            # Get author from metadata or filename
            author = metadata.get('author', file_path.stem.split('_')[-1])
            
            # Generate stable message ID if not present
            message_id = metadata.get('id') or str(uuid.uuid5(uuid.NAMESPACE_DNS, str(file_path)))
            
            return {
                'content': message_content,
                'author': author,
                'timestamp': timestamp,
                'id': message_id,
                'verified': metadata.get('verified', 'true'),
                'type': 'message'
            }
            
        except Exception as e:
            logger.error(f"Error parsing message file {file_path}: {e}")
            return None
    
    async def update_message(self, message_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing message's metadata.
        
        Args:
            message_id: ID of message to update
            updates: Dictionary of metadata updates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find message file by ID
            for file_path in self.messages_dir.glob('*.txt'):
                try:
                    message = await self._parse_message_file(file_path)
                    if message and message['id'] == message_id:
                        # Update message file
                        with open(file_path, mode='r+') as f:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                            try:
                                # Read existing content
                                content = f.read()
                                parts = content.split('\n-- \n', 1)
                                message_content = parts[0].strip()
                                
                                # Parse existing metadata
                                metadata = {}
                                if len(parts) > 1:
                                    for line in parts[1].split('\n'):
                                        if ': ' in line:
                                            key, value = line.split(': ', 1)
                                            metadata[key.lower()] = value.strip()
                                
                                # Update metadata
                                metadata.update(updates)
                                
                                # Write back to file
                                f.seek(0)
                                f.truncate()
                                f.write(message_content)
                                f.write('\n-- \n')
                                for key, value in metadata.items():
                                    f.write(f"{key.title()}: {value}\n")
                                    
                                f.flush()
                                os.fsync(f.fileno())
                                return True
                            finally:
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except Exception as e:
                    logger.error(f"Error checking message {file_path}: {e}")
                    continue
                    
            logger.error(f"Message {message_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            return False
