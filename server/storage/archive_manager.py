import os
import zipfile
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional
import sqlite3

logger = logging.getLogger(__name__)

class MessageArchiver:
    def __init__(self, db_path: str, archive_dir: str, days_threshold: Optional[int] = None, git_manager=None):
        """Initialize the message archiver.
        
        Args:
            db_path: Path to SQLite database
            archive_dir: Directory to store archive files
            days_threshold: Number of days after which messages should be archived
            git_manager: Optional GitManager instance for syncing archives
        """
        self.db_path = Path(db_path)
        self.archive_dir = Path(archive_dir)
        self.days_threshold = days_threshold or int(os.environ.get('ARCHIVE_DAYS_THRESHOLD', '30'))
        self.max_size_mb = int(os.environ.get('ARCHIVE_MAX_SIZE_MB', '100'))
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.git_manager = git_manager
        
        # Metrics
        self.last_archive_time = None
        self.total_archives_created = 0
        self.total_messages_archived = 0
        self.total_bytes_archived = 0
        
        # Initialize database if it doesn't exist
        self._init_database()
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def _init_database(self):
        """Initialize the SQLite database with required tables."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    user TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    signature TEXT
                )
            """)
            conn.commit()
            
    def get_messages_to_archive(self, reference_time: datetime) -> List[Dict[str, Any]]:
        """Get messages older than the threshold date.
        
        Args:
            reference_time: Current time to calculate threshold from
            
        Returns:
            List of message dictionaries to archive
        """
        threshold_date = reference_time - timedelta(days=self.days_threshold)
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM messages WHERE datetime(timestamp) < datetime(?) ORDER BY timestamp",
                (threshold_date.isoformat(),)
            )
            return [dict(row) for row in cursor.fetchall()]
            
    def archive_messages(self, reference_time: datetime) -> Optional[str]:
        """Archive old messages and remove them from the database.
        
        Args:
            reference_time: Current time to calculate threshold from
            
        Returns:
            Optional[str]: Path to created archive if messages were archived, None otherwise
        """
        messages = self.get_messages_to_archive(reference_time)
        if not messages:
            logger.info("No messages to archive")
            return None
            
        # Create archive filename based on date range
        first_msg_date = datetime.fromisoformat(messages[0]['timestamp'])
        last_msg_date = datetime.fromisoformat(messages[-1]['timestamp'])
        archive_name = f"chat_{first_msg_date.strftime('%Y%m%d')}_{last_msg_date.strftime('%Y%m%d')}.zip"
        archive_path = self.archive_dir / archive_name
        
        # Create zip file with messages
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            messages_json = json.dumps(messages, indent=2)
            zf.writestr('messages.json', messages_json)
            
            # Add metadata file
            metadata = {
                'created_at': datetime.now().isoformat(),
                'message_count': len(messages),
                'date_range': {
                    'start': first_msg_date.isoformat(),
                    'end': last_msg_date.isoformat()
                }
            }
            zf.writestr('metadata.json', json.dumps(metadata, indent=2))
            
        # Update metrics
        self.last_archive_time = datetime.now()
        self.total_archives_created += 1
        self.total_messages_archived += len(messages)
        self.total_bytes_archived += archive_path.stat().st_size
        
        # Remove archived messages from database
        with self._get_connection() as conn:
            threshold_date = reference_time - timedelta(days=self.days_threshold)
            conn.execute(
                "DELETE FROM messages WHERE datetime(timestamp) < datetime(?)",
                (threshold_date.isoformat(),)
            )
            conn.commit()
            
        # Sync archive to GitHub if git manager is available
        if self.git_manager is not None:
            try:
                self.git_manager.sync_changes_to_github(
                    archive_path,
                    author="BookChat Archiver",
                )
                logger.info(f"Successfully synced archive {archive_name} to GitHub")
            except Exception as e:
                logger.error(f"Failed to sync archive to GitHub: {e}")
        
        return str(archive_path)
        
    def get_archive_list(self) -> List[Dict[str, Any]]:
        """Get list of available archives with metadata.
        
        Returns:
            List of archive information dictionaries
        """
        archives = []
        for archive_file in self.archive_dir.glob('chat_*.zip'):
            try:
                with zipfile.ZipFile(archive_file, 'r') as zf:
                    # Read metadata if available
                    try:
                        with zf.open('metadata.json') as f:
                            metadata = json.loads(f.read())
                            archives.append({
                                'filename': archive_file.name,
                                'path': str(archive_file),
                                **metadata
                            })
                            continue
                    except KeyError:
                        pass
                        
                    # Fallback to reading messages.json
                    with zf.open('messages.json') as f:
                        messages = json.loads(f.read())
                        archives.append({
                            'filename': archive_file.name,
                            'path': str(archive_file),
                            'message_count': len(messages),
                            'date_range': {
                                'start': messages[0]['timestamp'],
                                'end': messages[-1]['timestamp']
                            }
                        })
            except Exception as e:
                logger.error(f"Error reading archive {archive_file}: {e}")
                continue
                
        return sorted(archives, key=lambda x: x['date_range']['start'])
        
    def get_messages_from_archive(self, archive_path: str) -> List[Dict[str, Any]]:
        """Retrieve messages from a specific archive file.
        
        Args:
            archive_path: Path to the archive file
            
        Returns:
            List of message dictionaries from the archive
        """
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                with zf.open('messages.json') as f:
                    return json.loads(f.read())
        except Exception as e:
            logger.error(f"Error reading archive {archive_path}: {e}")
            return []
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get archiver metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            'last_archive_time': self.last_archive_time.isoformat() if self.last_archive_time else None,
            'total_archives_created': self.total_archives_created,
            'total_messages_archived': self.total_messages_archived,
            'total_bytes_archived': self.total_bytes_archived,
            'total_mb_archived': self.total_bytes_archived / 1024 / 1024,
            'archive_dir_size': sum(f.stat().st_size for f in self.archive_dir.glob('*.zip')),
            'archive_count': len(list(self.archive_dir.glob('*.zip')))
        }
