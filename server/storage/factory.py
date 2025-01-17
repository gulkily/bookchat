"""Factory for creating storage backends."""

import logging
import os
from pathlib import Path
from typing import Any, Dict

from .file_storage import FileStorage

logger = logging.getLogger(__name__)

def create_storage(**kwargs: Dict[str, Any]) -> FileStorage:
    """Create and return a storage backend instance.
    
    Args:
        **kwargs: Additional arguments to pass to the storage backend.
            - repo_path: Path to the repository
        
    Returns:
        A FileStorage instance.
    """
    try:
        repo_path = kwargs.get('repo_path', os.environ.get('REPO_PATH', '.'))
        return FileStorage(repo_path)
    except Exception as e:
        logger.error(f"Error creating storage backend", exc_info=True)
        raise
