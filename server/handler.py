"""Request handler module."""

from server.handler_methods import (
    serve_messages,
    handle_message_post,
    handle_username_change
)

class ChatRequestHandler:
    """Handler for chat requests."""

    def __init__(self, app):
        """Initialize the handler with app."""
        self.app = app

    async def handle_request(self, request):
        """Handle incoming request."""
        if request.method == 'GET':
            if request.path == '/messages':
                return await serve_messages(request)
        elif request.method == 'POST':
            if request.path == '/messages':
                return await handle_message_post(request)
            elif request.path == '/change_username':
                return await handle_username_change(request)
        
        # Return 404 for unknown paths
        return web.Response(status=404, text='Not found')
