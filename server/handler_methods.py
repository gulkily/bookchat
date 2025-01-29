"""Methods for handling chat requests."""

import json
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

async def serve_messages(request):
    """Serve messages."""
    try:
        message_store = request.app['message_store']
        messages = message_store.get_messages()
        return web.json_response({
            'success': True,
            'data': messages
        })
    except Exception as e:
        logger.error(f'Error serving messages: {e}')
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_message_post(request):
    """Handle message post request."""
    try:
        data = await request.json()
        content = data.get('content', '').strip()
        author = data.get('author', '') or data.get('username', '').strip()

        if not content or not author:
            return web.json_response({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Save message directly using UserBranchManager
        message_store = request.app['message_store']
        message_id = message_store.save_message({
            'content': content,
            'author': author,
            'timestamp': None  # Let UserBranchManager set the timestamp
        })

        if message_id:
            # Get the saved message
            messages = message_store.get_messages()
            message = next((m for m in messages if m['id'] == message_id), None)
            if message:
                return web.json_response(message, status=200)

        return web.json_response({
            'success': False,
            'error': 'Failed to save message'
        }, status=500)

    except json.JSONDecodeError:
        return web.json_response({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f'Error handling message post: {e}')
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)
