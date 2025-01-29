"""Main server module."""

import asyncio
import logging
from aiohttp import web
from pathlib import Path
from server.config import get_config
from server.handler_methods import handle_message_post, serve_messages
from server.storage.git_manager import GitManager
from server.storage.user_branch_manager import UserBranchManager
from server.logger import setup_logging

logger = setup_logging()

async def init_app() -> web.Application:
    """Initialize the application."""
    app = web.Application()
    
    # Load config
    config = get_config()
    data_dir = Path(config['STORAGE_DIR'])
    
    # Initialize git manager and user branch manager
    git_manager = GitManager(data_dir)
    app['message_store'] = UserBranchManager(git_manager)
    logger.info("Initialized UserBranchManager for message storage")
    
    # Setup routes - only /messages endpoint needed
    app.router.add_get('/messages', serve_messages)
    app.router.add_post('/messages', handle_message_post)
    
    return app

def main():
    """Run the server."""
    app = asyncio.run(init_app())
    web.run_app(app)

if __name__ == '__main__':
    main()
