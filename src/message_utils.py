#!/usr/bin/env python3

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MessageError(Exception):
    """Custom exception for message-related errors."""
    pass

def create_message(author: str, content: str, reply_to: Optional[str] = None) -> Dict:
    """
    Create a new message with metadata.
    
    Args:
        author: Name of the message author
        content: Message content
        reply_to: Optional ID of message being replied to
        
    Returns:
        Dictionary containing message data
        
    Raises:
        ValueError: If required fields are invalid
    """
    if not author or not author.replace('_', '').isalnum():
        raise ValueError("Author must be alphanumeric (underscores allowed)")
    
    if not content or not content.strip():
        raise ValueError("Message content cannot be empty")
        
    message = {
        'id': str(uuid4()),
        'author': author,
        'content': content.strip(),
        'timestamp': datetime.utcnow().isoformat(),
        'reply_to': reply_to
    }
    
    logger.info(f"Created message {message['id']} from {author}")
    return message

def save_message(message: Dict, base_path: Optional[Path] = None) -> Path:
    """
    Save a message to the filesystem.
    
    Args:
        message: Message dictionary to save
        base_path: Optional base path for message storage
        
    Returns:
        Path where message was saved
        
    Raises:
        MessageError: If message cannot be saved
    """
    try:
        if not isinstance(message, dict) or 'id' not in message:
            raise ValueError("Invalid message format")
            
        # Use current directory if no base path provided
        base_path = Path(base_path or os.getcwd())
        
        # Create messages directory if it doesn't exist
        messages_dir = base_path / 'messages'
        messages_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamp-based directory structure
        timestamp = datetime.fromisoformat(message['timestamp'])
        year_dir = messages_dir / str(timestamp.year)
        month_dir = year_dir / f"{timestamp.month:02d}"
        day_dir = month_dir / f"{timestamp.day:02d}"
        
        # Create directory structure
        day_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp and message ID
        filename = f"{int(time.time())}_{message['id']}.json"
        file_path = day_dir / filename
        
        # Save message to file
        with open(file_path, 'w') as f:
            json.dump(message, f, indent=2)
            
        logger.info(f"Saved message {message['id']} to {file_path}")
        return file_path
        
    except (ValueError, OSError) as e:
        raise MessageError(f"Failed to save message: {e}")

def load_message(file_path: Path) -> Dict:
    """
    Load a message from a file.
    
    Args:
        file_path: Path to the message file
        
    Returns:
        Message dictionary
        
    Raises:
        MessageError: If message cannot be loaded
    """
    try:
        with open(file_path, 'r') as f:
            message = json.load(f)
            
        if not isinstance(message, dict) or 'id' not in message:
            raise ValueError("Invalid message format")
            
        return message
    except (json.JSONDecodeError, OSError, ValueError) as e:
        raise MessageError(f"Failed to load message: {e}")

def main():
    """Command line interface for message utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Message management utilities")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create message command
    create_parser = subparsers.add_parser("create", help="Create a new message")
    create_parser.add_argument("author", help="Message author")
    create_parser.add_argument("content", help="Message content")
    create_parser.add_argument("--reply-to", help="ID of message being replied to")
    
    # Save message command
    save_parser = subparsers.add_parser("save", help="Save a message from file")
    save_parser.add_argument("file", type=Path, help="JSON file containing message data")
    
    # Parse arguments
    args = parser.parse_args()
    
    try:
        if args.command == "create":
            message = create_message(args.author, args.content, args.reply_to)
            save_message(message)
        elif args.command == "save":
            message = load_message(args.file)
            save_message(message)
        else:
            parser.print_help()
    except (MessageError, ValueError) as e:
        logger.error(str(e))
        exit(1)

if __name__ == "__main__":
    main()
