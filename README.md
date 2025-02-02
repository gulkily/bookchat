# BookChat

A distributed chat system that uses git for message storage and synchronization.

## Features

- Message storage in git repositories
- User-specific branches for message isolation
- Command-line utilities for git operations
- HTTP server for web access
- Flexible architecture supporting multiple implementations

## Installation

1. Clone the repository:
```bash
git clone https://github.com/gulkily/bookchat.git
cd bookchat
```

2. Install dependencies:
```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies (optional)
pip install -r requirements-dev.txt
```

3. Make utilities executable:
```bash
chmod +x bin/*
```

## Usage

### Command-line Utilities

The system provides both Python and shell script implementations of core utilities:

#### Branch Management
- `bin/branch-current` or `bin/branch_utils.py current`: Get current branch
- `bin/branch-switch` or `bin/branch_utils.py switch <branch>`: Switch branches
- `bin/branch-ensure` or `bin/branch_utils.py ensure <username>`: Create user branch

#### Message Management
- `bin/message-create` or `bin/message_utils.py create <author>`: Create message
- `bin/message-save` or `bin/message_utils.py save <file>`: Save message

#### Git Sync
- `bin/git-sync-push` or `bin/git_sync.py push`: Push changes
- `bin/git-sync-pull` or `bin/git_sync.py pull`: Pull changes

### HTTP Server

Start the server:
```bash
python3 server/main.py
```

## Development

1. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Run tests:
```bash
pytest tests/
```

3. Format code:
```bash
black .
isort .
```

4. Lint code:
```bash
flake8
```

## License

See LICENSE file for details.
