"""Methods for handling chat requests."""

import json
import logging
from aiohttp import web

from server.message_handler import MessageHandler

logger = logging.getLogger(__name__)

async def serve_messages(request):
    """Serve messages."""
    try:
        message_handler = MessageHandler(request.app['storage'])
        response = await message_handler.handle_get_messages()
        return web.json_response(response)
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

        # Create message
        message_handler = MessageHandler(request.app['storage'])
        response = await message_handler.handle_post_message({
            'content': content,
            'author': author
        })

        if isinstance(response, dict) and not response.get('success', True):
            return web.json_response(response, status=400)

        # Return message data directly from the response
        return web.json_response(response.get('data', {}), status=200)

    except json.JSONDecodeError:
        return web.json_response({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f'Error handling message post: {e}')
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_username_change(request):
    """Handle username change request."""
    try:
        data = await request.json()
        old_username = data.get('old_username', '').strip()
        new_username = data.get('new_username', '').strip()

        if not new_username:
            return web.Response(status=400, text='New username cannot be empty')

        if not (3 <= len(new_username) <= 20):
            return web.Response(status=400, text='Username must be between 3 and 20 characters')

        if not new_username.replace('_', '').isalnum():
            return web.Response(status=400, text='Username can only contain letters, numbers, and underscores')

        # Create response
        response = web.json_response({
            'success': True,
            'username': new_username
        })
        
        # Set username cookie that expires in 1 year
        response.set_cookie('username', new_username, max_age=31536000, httponly=True)
        
        return response
    except Exception as e:
        logger.error(f'Error changing username: {e}')
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def verify_username(request):
    """Handle username verification request."""
    try:
        # For now, just return success since we don't have server-side username persistence
        # In a real app, you would verify against a database or session
        return web.json_response({
            'status': 'verified',
            'username': request.cookies.get('username', 'anonymous')
        })
    except Exception as e:
        logger.error(f'Error verifying username: {e}')
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)
