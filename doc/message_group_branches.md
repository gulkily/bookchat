# Message Group Branches Design

## Overview
This document outlines the design for storing message groups in separate Git branches to reduce the size of the main branch and improve download times.

## Current Implementation
- All messages are stored in a single `messages` directory in the main branch
- Each message is a text file with metadata headers
- Messages are synchronized with GitHub using the GitManager

## Proposed Changes

### 1. Branch Structure
- `main` branch: Contains core application code and minimal message history
- `group/<group-id>` branches: Each message group gets its own branch
  - Example: `group/general`, `group/support`, `group/announcements`
- Messages in each group branch will be stored in `messages/<group-id>/` directory

### 2. Storage System Changes

#### GitManager Updates
- Add methods for managing group branches:
  ```python
  create_message_group(group_id: str, description: str) -> bool
  delete_message_group(group_id: str) -> bool
  list_message_groups() -> List[Dict[str, str]]
  switch_to_group(group_id: str) -> bool
  ```

- Modify message storage to use group-specific directories:
  ```python
  save_message(message: Dict[str, str], group_id: str) -> str
  get_messages(group_id: str) -> List[Dict[str, Any]]
  get_message_by_id(message_id: str, group_id: str) -> Optional[Dict[str, Any]]
  ```

#### Storage Backend Updates
- Update StorageBackend interface to support group operations
- Modify GitStorage implementation to handle group branches
- Add group metadata storage (name, description, creation date)

### 3. API Changes

#### New Endpoints
- `POST /api/groups`: Create a new message group
- `GET /api/groups`: List available message groups
- `DELETE /api/groups/<group_id>`: Delete a message group
- `GET /api/groups/<group_id>/messages`: Get messages from a specific group
- `POST /api/groups/<group_id>/messages`: Post a message to a specific group

#### Message Format Updates
```json
{
  "id": "msg123",
  "content": "Hello world",
  "author": "user1",
  "timestamp": "2025-01-28T18:36:07-05:00",
  "group_id": "general"
}
```

### 4. Implementation Strategy

1. Create branch structure:
   - Keep main branch clean with minimal message history
   - Create group branches as needed
   - Implement branch switching in GitManager

2. Message storage:
   - Store messages in group-specific directories
   - Handle branch switching during read/write operations
   - Implement group metadata storage

3. Synchronization:
   - Pull/push specific group branches as needed
   - Handle conflicts between group branches
   - Optimize network usage by fetching only required groups

4. Migration:
   - Create migration script to move existing messages to groups
   - Default group for backward compatibility
   - Update documentation for new group features

### 5. Benefits

1. Reduced Download Size:
   - Users only need to fetch relevant message groups
   - Main branch stays lightweight
   - Faster initial clone and sync

2. Better Organization:
   - Messages organized by topic/purpose
   - Easier to manage access control
   - Improved message discovery

3. Performance:
   - Faster message retrieval within groups
   - Reduced memory usage
   - More efficient synchronization

### 6. Considerations

1. Backward Compatibility:
   - Maintain support for existing message format
   - Provide migration path for existing messages
   - Default group for backward compatibility

2. Error Handling:
   - Handle branch switching failures
   - Manage concurrent access to groups
   - Recover from synchronization issues

3. Performance:
   - Cache frequently accessed groups
   - Optimize branch switching
   - Implement lazy loading of group messages
