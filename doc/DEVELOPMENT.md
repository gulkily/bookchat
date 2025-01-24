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
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Install Node.js dependencies for frontend testing:
   ```bash
   npm install
   ```

## Project Structure

```
bookchat/
├── server/
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── file_storage.py
│   │   └── git_storage.py
│   ├── __init__.py
│   ├── message_handler.py
│   └── utils.py
├── static/           # Frontend assets
│   ├── css/
│   ├── js/
│   └── index.html
├── __tests__/        # Frontend tests
│   ├── e2e.test.js
│   └── test_messages.js
├── tests/            # Backend tests
│   ├── __init__.py
│   ├── test_server_integration.py
│   └── test_message_handler.py
├── server.py         # Main server implementation
└── requirements.txt  # Python dependencies
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

1. Run backend tests:
   ```bash
   pytest
   ```

2. Run frontend unit tests:
   ```bash
   npm run test:unit
   ```

3. Run end-to-end tests:
   ```bash
   npm run test:e2e
   ```

## Development Server

Start the development server:
```bash
python server.py
```

The server will automatically:
1. Find an available port (starting from 8001)
2. Open your default web browser
3. Support hot-reloading for development

## Adding New Features

When adding new features:
1. Add appropriate tests in `tests/` or `__tests__/`
2. Update the frontend in `static/js/main.js`
3. Update documentation
4. Run the full test suite before submitting PR

## Environment Variables

- `DEBUG`: Set to 'true' for detailed logging
- `PORT`: Override default port selection
- Other variables as specified in `.env.template`

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

*Last updated: 2025-01-23*
