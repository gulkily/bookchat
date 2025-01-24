# BookChat Future Options and Enhancements

This document outlines potential future enhancements and features that could be added to BookChat. These features were part of earlier specifications but are not currently implemented.

## Message Storage Enhancements

### Git-Based Storage System
- Store messages in Git repository with commit history
- Automatic commit and push on message creation
- Message archiving with Git history preservation
- File naming convention: `YYYYMMDD_HHMMSS_username.txt`

### Advanced Message Types
1. **Regular Message** (`Type: message`)
   - Normal chat messages
   - Content is plain text
   - Signature verification

2. **Username Change** (`Type: username_change`)
   - Content in JSON format: `{"old_username": "old", "new_username": "new"}`
   - Signature verification with old username
   - Public key migration between usernames

3. **System Message** (`Type: system`)
   - System notifications and status updates
   - No signature requirement
   - Reserved "system" author

4. **Error Message** (`Type: error`)
   - Structured error reporting
   - Error categorization
   - Error tracking and analytics

### Message Format Extensions
```
Date: [ISO 8601 timestamp]
Author: [username]
Signature: [base64_encoded_signature]
Type: [message_type]
Parent-Message: [parent_message_id]  # For threading

[message content]
```

## Security Enhancements

### Cryptographic Message Verification
- RSA signature system
- Public key infrastructure
- Key management system
  ```
  identity/
  └── public_keys/
      └── username.pub  # RSA public keys
  keys/
  └── local.pem        # RSA private keys
  ```

### Message Integrity
- Signature verification for all messages
- Replay attack prevention
- Message tampering detection

## Advanced Features

### Message Threading
- Parent-child message relationships
- Thread visualization
- Thread collapsing/expanding
- Thread-based notifications

### Message Archiving System
```python
class ArchiveManager:
    def __init__(self):
        self.archive_interval = int(os.getenv('ARCHIVE_INTERVAL_SECONDS', 3600))
        self.days_threshold = int(os.getenv('ARCHIVE_DAYS_THRESHOLD', 30))
        self.max_size_mb = int(os.getenv('ARCHIVE_MAX_SIZE_MB', 100))
```

#### Archive Configuration
- `ARCHIVE_INTERVAL_SECONDS`: Frequency of archive checks
- `ARCHIVE_DAYS_THRESHOLD`: Age threshold for archiving
- `ARCHIVE_MAX_SIZE_MB`: Size threshold for forced archiving

### Enhanced Logging System
- Hierarchical logging levels
- Rotating log files
- Log categories:
  ```
  logs/
  ├── debug.log    # All messages
  ├── info.log     # INFO and above
  └── error.log    # ERROR and above
  ```

### GitHub Integration Extensions
- Automatic repository management
- Branch-based message organization
- Pull request-based message moderation
- GitHub Actions integration

## UI Enhancements

### Advanced Message Display
```css
.message .content.threaded
.message .content.archived
.message .signature-verified
.message .signature-invalid
```

### Rich Text Support
- Markdown formatting
- Code block syntax highlighting
- Image embedding
- Link previews

### User Interface Components
- Thread view
- Archive browser
- User profile pages
- Message search interface

## API Extensions

### Enhanced Endpoints
```
GET /status
- Server health information
- Active connections
- Message statistics

GET /public_key/{username}
- Public key retrieval
- Key verification status

GET /thread/{thread_id}
- Thread message retrieval
- Thread metadata
```

### WebSocket Support
- Real-time message delivery
- Typing indicators
- Online status
- Message read receipts

## Implementation Considerations

### Message Handling
- Atomic operations for message storage
- Transaction support for complex operations
- Message validation pipeline
- Content filtering system

### Performance Optimizations
- Message caching
- Lazy loading for archived content
- Optimized search indexing
- Rate limiting

### Scalability Features
- Distributed message storage
- Load balancing
- Message partitioning
- Replication support

## Security Considerations
1. Key rotation policies
2. Rate limiting strategies
3. Content validation rules
4. Access control mechanisms
5. Audit logging requirements

*Last updated: 2025-01-24*
