import pytest

def test_essential_imports():
    """Test that all essential modules can be imported correctly."""
    try:
        from server.storage.file_storage import FileStorage
        from server.message_handler import MessageHandler
        # Add other essential imports here
    except ImportError as e:
        pytest.fail(f"Failed to import essential module: {str(e)}")

    # Verify FileStorage can be instantiated
    import os
    storage = FileStorage(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert storage is not None
