"""Methods for handling chat requests."""

import json
import logging
import os
from datetime import datetime

from aiohttp import web

from server.config import (
    STATIC_DIR,
    MESSAGE_VERIFICATION
)
from server.message_handler import MessageHandler

logger = logging.getLogger(__name__)

async def serve_messages(request):
    """Serve messages from storage."""
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

async def serve_status_page(request):
    """Serve status page."""
    try:
        return web.json_response({
            'status': 'ok',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f'Error serving status page: {e}')
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def handle_message_post(request):
    """Handle message post request."""
    try:
        data = await request.json()
        content = data.get('content', '').strip()
        # Accept either username or author in request
        username = data.get('username', '') or data.get('author', '').strip()

        if not content or not username:
            return web.json_response({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Create message
        message_handler = MessageHandler(request.app['storage'])
        response = await message_handler.handle_post_message({
            'content': content,
            'username': username
        })

        if isinstance(response, dict) and not response.get('success', True):
            return web.json_response(response, status=400)

        return web.json_response(response['data'], status=200)

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
