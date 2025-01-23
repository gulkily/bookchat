# BookChat Development Guide

This guide provides information for developers who want to contribute to or extend BookChat.

## Development Environment Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/yourusername/bookchat.git
   cd bookchat
   ```

2. Set up development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

3. Configure pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Project Structure

```
bookchat/
├── server/
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── file_storage.py
│   │   ├── git_storage.py
│   │   └── git_manager.py
│   ├── __init__.py
│   ├── config.py
│   ├── handler.py
│   ├── handler_methods.py
│   ├── logger.py
│   ├── main.py
│   ├── message_handler.py
│   └── utils.py
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_file_storage.py
    ├── test_git_storage.py
    ├── test_handler_methods.py
    └── test_message_handler.py
└── static/           # Frontend assets
│   ├── css/
│   └── js/
└── templates/        # HTML templates
```

## Core Components

### 1. Storage System

The storage system is built around a pluggable backend architecture:

```python
class BaseStorage:
    def init_storage(self):
        """Initialize storage backend"""
        pass

    def save_message(self, content, author, type='message'):
        """Save a message"""
        pass

    def get_messages(self):
        """Retrieve all messages"""
        pass
```

To implement a new storage backend:
1. Create a new class in `server/storage/`
2. Inherit from `BaseStorage`
3. Register in `server/storage/factory.py`

### 2. Message Handling

Messages follow a standardized format:
```python
{
    'date': ISO-8601 timestamp,
    'author': username,
    'type': message_type,
    'content': message_content,
    'signature': hex_encoded_signature  # Optional
}
```

Message types:
- `message`: Regular chat message
- `username_change`: Username change request
- `system`: System notification
- `error`: Error message

### 3. Key Management

The `KeyManager` class handles all cryptographic operations:
```python
class KeyManager:
    def __init__(self, private_keys_dir, public_keys_dir)
    def sign_message(self, message)
    def verify_signature(self, message, signature_hex, public_key_pem)
    def generate_keypair(self, username)
```

### 4. GitHub Integration

GitHub synchronization is handled by the `GitManager` class:
```python
class GitManager:
    def __init__(self, repo_path)
    def init_git_repo(self)
    def sync_changes_to_github(self, filepath, author)
```

## Testing

1. Run unit tests:
   ```bash
   python -m pytest tests/
   ```

2. Run with coverage:
   ```bash
   coverage run -m pytest tests/
   coverage report
   ```

3. Test specific components:
   ```bash
   python -m pytest tests/test_storage.py
   python -m pytest tests/test_git_manager.py
   ```

## Testing Requirements

### Core Testing Principles
1. Use actual GitHub API - no mocking
2. Write real messages to `messages/` directory
3. All messages must be committed and pushed immediately
4. Messages must follow format: `YYYYMMDD_HHMMSS_username.txt`
5. Public keys must be in `identity/public_keys/{username}.pub`

### Required Environment Variables
```bash
GITHUB_TOKEN=your_token      # Required: valid GitHub token
GITHUB_REPO=owner/repo       # Required: repository to use
SYNC_TO_GITHUB=true         # Must be true for tests
```

### Message Storage Rules
- All messages stored in project repo under `messages/`
- Messages must be Git-tracked (not gitignored)
- Old messages moved to `archive/` but still tracked
- Immediate commit and push on message creation

## Debugging

1. Enable debug logging:
   ```bash
   export BOOKCHAT_DEBUG=true
   python server.py
   ```

2. Log locations:
   - `logs/debug.log`: All messages
   - `logs/info.log`: INFO and above
   - `logs/error.log`: ERROR and above

## Code Style

1. Follow PEP 8 guidelines
2. Use type hints for function arguments and returns
3. Document all public functions and classes
4. Keep functions focused and small
5. Write meaningful commit messages

## Pull Request Process

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes:
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation

3. Submit PR:
   - Describe changes in detail
   - Reference any related issues
   - Include test results
   - Update relevant documentation

## Feature Implementation Guide

### Adding a New Message Type

1. Update message type constants in `server.py`
2. Implement message handler in `ChatRequestHandler`
3. Add frontend support in `static/js/main.js`
4. Update documentation
5. Add tests

### Adding a New Storage Backend

1. Create new class in `server/storage/`
2. Implement required interface methods
3. Add to factory in `server/storage/factory.py`
4. Add configuration options
5. Write tests
6. Update documentation

## Performance Considerations

1. Message Storage:
   - Use efficient file naming
   - Implement message archiving
   - Consider pagination

2. GitHub Sync:
   - Use cooldown period between pulls
   - Batch commits when possible
   - Handle network issues gracefully

3. Key Management:
   - Cache public keys
   - Implement key rotation
   - Handle key verification efficiently

## Security Best Practices

1. Key Management:
   - Secure key storage
   - Regular key rotation
   - Proper permission settings

2. Message Verification:
   - Sign all messages
   - Verify signatures
   - Handle invalid signatures

3. Input Validation:
   - Sanitize all user input
   - Validate message format
   - Check file permissions

*Last updated: 2025-01-13*
