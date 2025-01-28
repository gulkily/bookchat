# User Branch Design

## Overview
This design outlines a system where each user's messages are stored in their own Git branch, while maintaining a unified local view of all messages.

## Branch Structure

### Remote Structure
- `main` branch: Contains core application code and system messages
- `user/<username>` branches: Contains messages from individual users
  - Example: `user/alice`, `user/bob`, `user/charlie`
  - Each branch has a `messages` directory with that user's messages only

### Local Structure
- Local working directory maintains a unified view
- All messages from all branches are merged into a single `messages` directory
- Message filenames are prefixed with username to prevent collisions
  - Format: `messages/<username>_<message_id>.txt`

## Implementation Details

### GitManager Updates

1. Branch Management:
```python
def ensure_user_branch(username: str) -> bool:
    """Ensure user branch exists and is properly configured."""
    branch_name = f'user/{username}'
    if branch_not_exists(branch_name):
        create_user_branch(username)
    return True

def save_message(message: Dict[str, str]) -> str:
    """Save message to appropriate user branch."""
    username = message['author']
    message_id = generate_id()
    
    # Switch to user's branch
    checkout_branch(f'user/{username}')
    
    # Save message
    save_to_current_branch(message)
    
    # Push changes
    push_branch(f'user/{username}')
    
    # Switch back to main
    checkout_branch('main')
    
    return message_id
```

2. Message Syncing:
```python
def sync_messages():
    """Sync messages from all user branches into local messages directory."""
    # Get list of user branches
    user_branches = list_user_branches()
    
    for branch in user_branches:
        username = branch.split('/')[-1]
        
        # Fetch latest changes
        fetch_branch(branch)
        
        # Copy messages to local directory with username prefix
        copy_messages_to_local(branch, username)
```

3. Efficient Fetching:
```python
def fetch_user_messages(username: str):
    """Fetch messages for a specific user."""
    branch = f'user/{username}'
    
    # Fetch only the specified user branch
    fetch_branch(branch)
    
    # Update local messages directory
    copy_messages_to_local(branch, username)
```

### Message Storage

1. Message Format:
```python
{
    'id': 'msg123',
    'content': 'Hello world',
    'author': 'alice',
    'timestamp': '2025-01-28T18:40:54-05:00',
    'filename': 'alice_msg123.txt'  # Username prefixed
}
```

2. Directory Structure:
```
/messages/
    alice_msg123.txt
    bob_msg456.txt
    charlie_msg789.txt
```

### Synchronization Flow

1. When Saving Messages:
```python
def handle_message_post(message):
    # 1. Save to user's branch
    save_to_user_branch(message)
    
    # 2. Copy to local messages directory
    copy_to_local_messages(message)
    
    # 3. Push user's branch
    push_user_branch(message['author'])
```

2. When Fetching Messages:
```python
def fetch_latest_messages():
    # 1. Get list of active users
    users = get_active_users()
    
    # 2. Fetch each user's branch
    for user in users:
        fetch_user_branch(user)
    
    # 3. Update local message pool
    sync_local_messages()
```

## Benefits

1. Efficient Downloads:
   - Users can fetch only the branches they're interested in
   - New users don't need to download entire message history
   - Branches can be fetched on-demand

2. Simple Local View:
   - All messages appear in one directory locally
   - No need to switch branches to view different messages
   - Easy to implement search and filtering

3. Natural User Organization:
   - Messages naturally organized by author
   - Easy to track user contributions
   - Simple to implement user-specific features

## Implementation Strategy

1. Phase 1: Basic Structure
   - Implement user branch creation
   - Set up local message pooling
   - Add basic sync functionality

2. Phase 2: Optimization
   - Add selective branch fetching
   - Implement efficient message merging
   - Add caching for frequently accessed content

3. Phase 3: Advanced Features
   - Add user activity tracking
   - Implement selective sync preferences
   - Add branch cleanup for inactive users

## Migration Plan

1. For Existing Messages:
   - Create user branches for existing authors
   - Move messages to appropriate branches
   - Update local message pool

2. For New Messages:
   - Save directly to user branches
   - Automatically sync to local pool
   - Maintain backward compatibility

## Considerations

1. Conflict Resolution:
   - Handle username collisions
   - Manage concurrent message updates
   - Resolve sync conflicts

2. Performance:
   - Optimize branch fetching
   - Efficient local message pooling
   - Smart caching strategies

3. Storage:
   - Manage local storage efficiently
   - Handle branch cleanup
   - Implement message archiving
