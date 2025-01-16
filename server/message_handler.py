import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self, storage):
        """Initialize the message handler with storage."""
        self.storage = storage

    async def handle_get_messages(self, request):
        """Handle GET request for messages."""
        try:
            messages = await self.storage.get_messages()
            return {
                'success': True,
                'messages': messages or [],  # Ensure messages is always a list
                'messageVerificationEnabled': True,
                'reactionsEnabled': True
            }
        except Exception as e:
            logger.error(f"Error getting messages: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'messages': []  # Return empty list to prevent frontend errors
            }

    async def handle_post_message(self, request):
        """Handle POST request for new message."""
        try:
            # Read request body
            content_length = int(request.headers.get('Content-Length', 0))
            if content_length > 0:
                body = request.rfile.read(content_length).decode('utf-8')
                data = json.loads(body)
            else:
                data = {}

            content = data.get('content', '').strip()
            username = data.get('username', 'anonymous')

            if not content:
                raise ValueError('Message content cannot be empty')

            # Create message
            now = datetime.now()
            timestamp = now.isoformat()
            
            message = {
                'content': content,
                'author': username,
                'timestamp': timestamp,
                'verified': 'true',  # Default to verified for now
                'reactions': {}
            }

            # Save message
            saved_message = await self.storage.save_message(
                author=username,
                content=content,
                timestamp=now,
                metadata={
                    'verified': 'true',
                    'reactions': {}
                }
            )

            if not saved_message:
                raise ValueError('Failed to save message')

            return {
                'success': True,
                'data': {
                    'id': saved_message,
                    'content': content,
                    'author': username,
                    'timestamp': message['timestamp'],
                    'verified': 'true',
                    'reactions': {}
                }
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {e}")
            return {
                'success': False,
                'error': 'Invalid JSON in request body'
            }
        except ValueError as e:
            logger.error(f"Invalid message data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Error handling POST message: {e}")
            return {
                'success': False,
                'error': f'Server error: {str(e)}'
            }

    async def handle_put_message(self, request):
        """Handle PUT request to update a message."""
        try:
            # Read request body
            content_length = int(request.headers.get('Content-Length', 0))
            if content_length > 0:
                body = request.rfile.read(content_length).decode('utf-8')
                data = json.loads(body)
            else:
                data = {}

            message_id = data.get('id')
            updates = data.get('updates', {})

            if not message_id:
                raise ValueError('Message ID is required')

            # Update message
            success = await self.storage.update_message(message_id, updates)
            if not success:
                raise ValueError('Failed to update message')

            # Get updated message
            message = await self.storage.get_message_by_id(message_id)
            if not message:
                raise ValueError('Message not found after update')

            return {
                'success': True,
                'data': message
            }
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def handle_reaction(self, request):
        """Handle POST request for message reactions."""
        try:
            # Read request body
            content_length = int(request.headers.get('Content-Length', 0))
            if content_length > 0:
                body = request.rfile.read(content_length).decode('utf-8')
                data = json.loads(body)
            else:
                data = {}

            message_id = data.get('messageId')
            reaction = data.get('reaction')
            action = data.get('action')
            username = data.get('username', 'anonymous')

            if not all([message_id, reaction, action]):
                raise ValueError('Missing required fields')

            if action not in ['add', 'remove']:
                raise ValueError('Invalid action')

            message = await self.storage.get_message(message_id)
            if not message:
                raise ValueError('Message not found')

            # Initialize reactions if not present
            if 'reactions' not in message:
                message['reactions'] = {}
            if reaction not in message['reactions']:
                message['reactions'][reaction] = []

            # Update reactions
            if action == 'add' and username not in message['reactions'][reaction]:
                message['reactions'][reaction].append(username)
            elif action == 'remove' and username in message['reactions'][reaction]:
                message['reactions'][reaction].remove(username)

            # Remove empty reaction lists
            if not message['reactions'][reaction]:
                del message['reactions'][reaction]

            updated_message = await self.storage.update_message(message_id, {'reactions': message['reactions']})

            return {
                'success': True,
                'data': updated_message
            }
        except Exception as e:
            logger.error(f"Error handling reaction: {e}")
            return {
                'success': False,
                'error': str(e)
            }
