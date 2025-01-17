"""Main server module."""

import logging
from aiohttp import web
from server.config import get_config
from server.handler_methods import handle_message_post, serve_messages
from server.storage import init_storage

logger = logging.getLogger(__name__)

async def init_app() -> web.Application:
    """Initialize the application."""
    app = web.Application()
    
    # Load config
    config = get_config()
    
    # Initialize storage with git if configured
    app['storage'] = init_storage(
        config.data_dir,
        use_git=config.get('USE_GIT_STORAGE', False)
    )
    
    # Setup routes
    app.router.add_post('/api/messages', handle_message_post)
    app.router.add_get('/api/messages', serve_messages)
    
    return app

def main():
    """Run the server."""
    app = asyncio.run(init_app())
    web.run_app(app)

if __name__ == '__main__':
    main()
