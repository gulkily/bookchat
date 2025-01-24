# BookChat Application Specification

## Overview

BookChat is a lightweight chat application designed for simplicity and ease of use. It features message persistence using file storage, optional GitHub synchronization, and a modern web interface.

## Core Components

### 1. Message Storage
- Messages are stored in the `messages/` directory
- Each message is a separate `.txt` file
- Message filenames follow the format: `YYYYMMDD_HHMMSS_username.txt`
- Optional GitHub synchronization for message persistence

### 2. Message Format
Messages are stored in text files with the following structure:

```
[message content]

-- 
Author: [username]
Date: [ISO 8601 timestamp]
```

### 3. Server Implementation
- Built with Python's standard library `http.server`
- Asynchronous request handling
- Automatic port selection (starts from 8001)
- Cross-platform browser launching support
- WSL-aware implementation

### 4. Frontend Implementation
- Pure JavaScript implementation
- Real-time message updates
- Username management
- Clean, modern UI
- Mobile-responsive design

## API Endpoints

### 1. Messages
```
GET /messages
- Returns: List of messages
- Format: JSON array of message objects

POST /messages
- Payload: { "content": string, "type": string }
- Returns: Message confirmation
```

### 2. Username Management
```
GET /verify_username
- Returns: Current username status

POST /change_username
- Payload: { "username": string }
- Returns: Username update confirmation
```

### 3. Static Files
```
GET /static/*
- Serves static assets (CSS, JS, images)
```

## Security Features

### 1. Message Verification (Optional)
- Enable with MESSAGE_VERIFICATION environment variable
- Verifies message integrity
- Prevents unauthorized modifications

### 2. GitHub Integration (Optional)
- Secure token-based authentication
- Repository-based message backup
- Configurable through environment variables

## Testing

### 1. Backend Tests
- Unit tests for core functionality
- Integration tests for server components
- Run with pytest

### 2. Frontend Tests
- Unit tests with Jest
- End-to-end tests with Playwright
- Cross-browser compatibility testing

## Environment Variables

### Required
None - the application works with default settings

### Optional
- DEBUG: Enable detailed logging
- PORT: Override automatic port selection
- GITHUB_TOKEN: For GitHub integration
- GITHUB_REPO: Target repository for GitHub sync
- MESSAGE_VERIFICATION: Enable message verification

## File Structure
```
bookchat/
├── server/
│   ├── storage/
│   │   ├── file_storage.py
│   │   └── git_storage.py
│   ├── message_handler.py
│   └── utils.py
├── static/
│   ├── css/
│   ├── js/
│   └── index.html
├── __tests__/
├── tests/
├── server.py
└── requirements.txt
```

## Dependencies

### Python Packages
- requests: HTTP client
- PyGithub: GitHub API integration
- python-dotenv: Environment management
- cryptography: Message verification
- Jinja2: Template rendering

### Development Dependencies
- pytest: Testing framework
- pytest-cov: Coverage reporting
- Playwright: End-to-end testing
- Jest: JavaScript testing

## Browser Support
- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

*Last updated: 2025-01-23*
