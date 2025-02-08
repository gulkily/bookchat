#!/usr/bin/env python3

"""
Chat Server Implementation
=========================

This is a robust HTTP server implementation for a real-time chat application with 
file storage capabilities and browser-based interface.

Key Features:
------------
- Asynchronous message handling using asyncio
- Cross-platform browser launching support (Windows/Linux/MacOS/WSL)
- CORS-enabled HTTP server with JSON API endpoints
- File-based message persistence
- Template rendering engine
- Static file serving
- Automatic port selection
- Comprehensive error handling and logging

Technical Details:
-----------------
The server is built on Python's HTTPServer and implements:
- GET/POST/OPTIONS request handling
- JSON response formatting
- CORS headers for cross-origin requests
- File content type detection
- Template variable substitution
- Conditional template rendering
- Graceful error handling for client disconnections

API Endpoints:
-------------
GET /messages - Retrieve all chat messages
GET /test_message - Test endpoint returning sample message format
GET / or /index.html - Serves main chat interface
GET /static/* - Serves static assets (CSS, JS, images etc)
POST /messages - Submit new chat messages

Configuration:
-------------
Environment Variables:
- DEBUG=true - Enable debug logging
- NO_BROWSER - Disable automatic browser launch
- SERVER_PORT - (Exported) Port number the server is running on

Dependencies:
------------
Standard Library:
- os, json, logging, asyncio, socket, webbrowser
- threading, platform, sys, subprocess
- http.server, urllib.parse
- datetime, pathlib

Custom Modules:
- server.storage.file_storage (FileStorage)
- server.message_handler (MessageHandler)

Usage:
------
Run directly: python3 server.py
The server will:
1. Find an available port (starting at 8001)
2. Export the port as SERVER_PORT
3. Start the HTTP server
4. Open the default browser (unless NO_BROWSER is set)
5. Begin handling requests

Error Handling:
--------------
- Comprehensive try/except blocks
- Graceful handling of client disconnections
- Detailed logging of errors with stack traces
- Proper HTTP error responses

Author: [Your Name]
Version: 1.0
License: [License Type]
"""

import os
import json
import logging
import asyncio
import socket
import webbrowser
import threading
import platform
import sys
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path

from server.storage.file_storage import FileStorage
from server.message_handler import MessageHandler

# Configure logging
log_level = logging.INFO if os.environ.get('DEBUG') == 'true' else logging.WARNING
logging.basicConfig(
    level=log_level,
    format='%(levelname)s %(name)s:%(filename)s:%(lineno)d %(message)s'
)
