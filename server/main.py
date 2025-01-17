"""Main module for the chat server."""

import asyncio
import logging
import os
import webbrowser
from typing import Optional

from aiohttp import web

from server.config import (
    HOST,
    PORT,
    STATIC_DIR
)
from server.handler import ChatRequestHandler
from server.storage.factory import create_storage

logger = logging.getLogger(__name__)

def open_browser(url: str) -> None:
    """Open the browser to the specified URL."""
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.error(f'Error opening browser: {e}')

async def init_app() -> web.Application:
    """Initialize the application."""
    app = web.Application()
    
    # Create storage
    storage = create_storage()
    app['storage'] = storage

    # Setup routes
    app.router.add_get('/messages', lambda r: ChatRequestHandler(r).handle_request(r))
    app.router.add_post('/messages', lambda r: ChatRequestHandler(r).handle_request(r))
    app.router.add_get('/status', lambda r: ChatRequestHandler(r).handle_request(r))
    
    # Serve static files
    app.router.add_static('/', STATIC_DIR)

    return app

def main(port: Optional[int] = None) -> None:
    """Start the server."""
    try:
        # Create and configure app
        app = asyncio.run(init_app())
        
        # Use provided port or default
        server_port = port or PORT
        
        # Start server
        web.run_app(
            app,
            host=HOST,
            port=server_port,
            access_log=logger
        )
    except Exception as e:
        logger.error(f'Failed to start server: {e}')
        raise

if __name__ == '__main__':
    main()
