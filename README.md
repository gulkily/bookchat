# BookChat - Git-Backed Messaging Application

A lightweight, Git-backed web-based messaging application that allows users to communicate through a simple interface while maintaining message history in a Git repository.

## Features

- Simple and intuitive web interface
- Flexible storage backend using Git
- Git integration for message history
- Real-time message updates
- Basic user authentication
- Markdown support for messages
- Serverless-friendly when using Git storage
- Comprehensive logging system with multiple debug levels

## Tech Stack

- Backend: Python (No frameworks)
- Storage: Git-based and File-based JSON storage
- Frontend: HTML, CSS, JavaScript (Vanilla)
- Version Control: Git (via GitHub API)
- Authentication: GitHub OAuth
- Logging: Comprehensive debug and application logging
- Testing: pytest framework

## Project Structure

```
bookchat/
├── README.md
├── .env
├── server/                 # Server-related modules
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── templates/
│   ├── index.html
│   ├── chat.html
│   └── status.html
├── storage/
│   ├── __init__.py
│   ├── factory.py
│   ├── git_storage.py
│   ├── file_storage.py
│   └── archive_manager.py
├── messages/              # Message storage directory
├── identity/             # Identity management
├── server.py
├── git_manager.py        # Git operations handler
├── key_manager.py        # Key management utilities
├── requirements.txt
├── requirements-dev.txt  # Development dependencies
└── requirements-test.txt # Testing dependencies
```

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bookchat.git
   cd bookchat
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment in `.env`:
   ```bash
   # GitHub Configuration (optional)
   SYNC_TO_GITHUB=false          # Enable GitHub synchronization
   GITHUB_TOKEN=your_github_token
   GITHUB_REPO=username/repository

   # Server Configuration
   PORT=8000                     # Default: 8000

   # Key Management (optional)
   KEYS_DIR=/path/to/keys        # Default: repo/keys
   SIGN_MESSAGES=true           # Enable message signing

   # Feature Flags
   MESSAGE_VERIFICATION=true    # Enable message verification
   ENABLE_FORK_SYNC=false      # Enable GitHub fork syncing

   # Archive Settings
   ARCHIVE_INTERVAL_SECONDS=3600
   ARCHIVE_DAYS_THRESHOLD=30
   ARCHIVE_MAX_SIZE_MB=100

   # Logging
   BOOKCHAT_DEBUG=true         # Enable debug logging
   ```

5. Run the server:
   ```bash
   python server.py
   ```

## Deployment Options

BookChat supports multiple deployment configurations:

### 1. Standard Server Deployment
- Run as a standalone Python server
- Support for both Git and File-based storage backends
- Full feature set including message signing and verification
- Suitable for most deployments
- Configurable logging and debugging

### 2. GitHub-Integrated Deployment
- Enable GitHub synchronization for message persistence
- Automatic fork synchronization support
- Message archiving capabilities
- Perfect for distributed team setups
- Requires valid GitHub credentials

### 3. Local Development Setup
- Quick setup with file-based storage
- Debug logging for development
- Support for testing environment
- Includes development and testing dependencies
- Ideal for contributing to the project

Each deployment option can be configured through environment variables to enable/disable specific features as needed.

## Logging and Debugging

BookChat includes a comprehensive logging system with multiple debug levels:

### Log Files

All logs are stored in the `logs` directory:
- `logs/debug.log`: Contains all log messages (DEBUG and above)
- `logs/info.log`: Contains INFO level and above messages
- `logs/error.log`: Contains only ERROR and CRITICAL messages

### Console Output

By default, the console shows only WARNING and above messages to keep the output clean. To enable debug output in the console:

1. Set the environment variable:
   ```bash
   export BOOKCHAT_DEBUG=true
   ```

2. Or add to your `.env` file:
   ```bash
   BOOKCHAT_DEBUG=true
   ```

### Log Levels

The logging system uses standard Python logging levels (from lowest to highest priority):
- DEBUG: Detailed information for debugging
- INFO: General operational messages
- WARNING: Warning messages for potential issues
- ERROR: Error messages for actual problems
- CRITICAL: Critical issues that need immediate attention

### Debugging Tips

1. Check the appropriate log file based on the severity of the issue:
   - For detailed debugging: `logs/debug.log`
   - For general operation info: `logs/info.log`
   - For errors and critical issues: `logs/error.log`

2. Enable console debug output temporarily using the `BOOKCHAT_DEBUG` environment variable

3. Log files include detailed information such as:
   - Timestamp
   - Log level
   - Source file and line number
   - Detailed message

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
