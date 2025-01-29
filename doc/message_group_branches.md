# Message Group Branches Design

## Overview
This document outlines the design for storing messages in user-specific Git branches to improve organization and message management.

## Implementation
- Messages are stored in user-specific branches named `user/<username>`
- Each user's messages are stored in `messages/<username>/` directory
- Messages are stored in plaintext format with metadata
- User branches are created automatically when a user posts their first message

### Branch Structure
- `main` branch: Contains core application code
- `user/<username>` branches: Created automatically for each user
  - Example: `user/alice`, `user/bob`, `user/carol`
- Messages in each user branch stored in `messages/<username>/` directory

### Message Format
Messages are stored as plaintext files with the format:
```
[message content]
Author: [username]
Date: [timestamp]
```

### Storage System
The `UserBranchManager` class handles:
- Creating user branches automatically
- Storing messages in user-specific directories
- Reading messages from all user branches
- Managing Git operations through `GitManager`

### API Endpoints
- `GET /messages`: Get all messages from all users
- `POST /messages`: Post a new message (creates user branch if needed)
  ```json
  {
    "content": "message content",
    "author": "username"
  }
  ```

### Example
When a user named "alice" posts a message:
1. If `user/alice` branch doesn't exist:
   - Creates branch `user/alice`
   - Creates directory `messages/alice/`
2. Saves message to `messages/alice/[timestamp]_[random].txt`
3. Commits changes to user branch
4. Returns to main branch
