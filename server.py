#!/usr/bin/env python3

import http.server
import socketserver
import json
import os
import pathlib
import logging
import traceback
import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse
from http import HTTPStatus
from dotenv import load_dotenv
from storage.factory import create_storage
from pathlib import Path
import threading
import time
import subprocess
from jinja2 import Environment, FileSystemLoader

# Configure logging with a more detailed format and multiple levels
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
console_format = '%(asctime)s - %(levelname)s - %(message)s'  # Simpler format for console

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Remove all existing handlers
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

# Configure file handlers for different log levels
debug_handler = logging.FileHandler('logs/debug.log')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter(log_format))

info_handler = logging.FileHandler('logs/info.log')
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter(log_format))

error_handler = logging.FileHandler('logs/error.log')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter(log_format))

# Configure console handler with simpler format and ERROR level only
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)  # Only show ERROR level messages in console
console_handler.setFormatter(logging.Formatter(console_format))

# Create git logger with special handling
git_logger = logging.getLogger('git')
git_logger.setLevel(logging.INFO)  # Set to INFO to ignore DEBUG messages
git_handler = logging.FileHandler('logs/git.log')
git_handler.setLevel(logging.INFO)
git_handler.setFormatter(logging.Formatter(log_format))
git_logger.addHandler(git_handler)
git_logger.propagate = False  # Don't propagate to root logger

# Add all handlers to root logger
root.addHandler(debug_handler)
root.addHandler(info_handler)
root.addHandler(error_handler)
root.addHandler(console_handler)

# Set root logger to lowest level (DEBUG) to catch all logs
root.setLevel(logging.DEBUG)

# Create a logger specific to this application
logger = logging.getLogger('bookchat')

# Log initial debug state
logger.info(f"Console logging level: {logging.getLevelName(console_handler.level)}")
if console_handler.level == logging.DEBUG:
    logger.info("Debug logging enabled via BOOKCHAT_DEBUG environment variable")

# Load environment variables
load_dotenv()

# Feature flags
MESSAGE_VERIFICATION_ENABLED = os.getenv('MESSAGE_VERIFICATION', 'false').lower() == 'true'

# Configuration
PORT = int(os.getenv('PORT', 8000))
REPO_PATH = os.getenv('REPO_PATH', os.path.abspath(os.path.dirname(__file__)))

# Initialize storage backend
logger.info(f"Initializing storage backend with repo path: {REPO_PATH}")
storage = None

class ChatRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for the chat application"""

    def __init__(self, *args, **kwargs):
        # Initialize storage
        global storage
        if storage is None:
            storage = create_storage(
                storage_type='sqlite',
                db_path=str(Path('database/messages.db'))
            )
        # Set up Jinja2 environment
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))
        # Set the directory for serving static files
        logger.debug("Initializing ChatRequestHandler")
        super().__init__(*args, directory="static", **kwargs)

    def handle_error(self, error):
        """Handle errors and return appropriate response"""
        error_msg = f"Error occurred: {str(error)}"
        logger.error(error_msg, exc_info=True)  # Include full stack trace
        
        # Don't try to send error response for broken pipe errors
        if isinstance(error, BrokenPipeError):
            logger.info("Client disconnected prematurely - suppressing broken pipe error")
            return
            
        try:
            error_response = {
                'error': str(error),
                'traceback': traceback.format_exc()
            }
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError) as e:
            logger.info(f"Failed to send error response due to connection issue: {e}")

    def do_GET(self):
        """Handle GET requests"""
        try:
            parsed_url = urlparse(self.path)
            
            # Route GET requests
            if parsed_url.path == '/':
                self.serve_file('templates/index.html', 'text/html')
            elif parsed_url.path == '/messages' or parsed_url.path == '/api/messages':
                self.serve_messages()
            elif parsed_url.path == '/api/messages/pinned':
                self.serve_messages()
            elif parsed_url.path.startswith('/static/'):
                self.serve_file(parsed_url.path[1:], self._get_content_type(parsed_url.path))
            elif parsed_url.path == '/status':
                self.serve_status_page()
            elif parsed_url.path.startswith('/public_key/'):
                key_name = parsed_url.path.split('/')[-1]
                key_path = Path('identity/public_keys') / key_name
                if key_path.exists() and key_path.suffix == '.pub':
                    self.serve_file(key_path, 'text/plain')
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
            elif parsed_url.path.startswith('/messages/'):
                # Serve individual message files
                filename = parsed_url.path.split('/')[-1]
                message_path = Path('messages') / filename
                if message_path.exists() and message_path.is_file():
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(message_path.read_bytes())
                else:
                    self.send_error(HTTPStatus.NOT_FOUND, "Message file not found")
            elif parsed_url.path.startswith('/identity/public_keys/'):
                # Serve public key files
                username = parsed_url.path.split('/')[-1].split('.')[0]
                public_key_path = os.path.join(REPO_PATH, 'identity/public_keys', f'{username}.pub')
                if os.path.exists(public_key_path):
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    with open(public_key_path, 'r') as f:
                        self.wfile.write(f.read().encode('utf-8'))
                else:
                    self.send_error(HTTPStatus.NOT_FOUND, "Public key not found")
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
                
        except Exception as e:
            self.handle_error(e)

    def do_POST(self):
        """Handle POST requests"""
        try:
            parsed_url = urlparse(self.path)
            
            # Route POST requests
            if parsed_url.path == '/api/messages':
                self.handle_message_post()
            elif parsed_url.path.startswith('/api/messages/') and parsed_url.path.endswith('/pin'):
                self.handle_pin_message(parsed_url.path)
            elif parsed_url.path == '/api/username':
                self.handle_username_post()
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
                
        except Exception as e:
            self.handle_error(e)

    def handle_pin_message(self, path):
        """Handle message pin/unpin requests"""
        try:
            # Extract message_id from path
            message_id = path.split('/')[3]  # /api/messages/{id}/pin
            
            # Get request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            # Get current username
            username = self.verify_username()
            if not username:
                self.send_error(HTTPStatus.UNAUTHORIZED)
                return

            # Check if pinning or unpinning
            is_pinning = data.get('action') == 'pin'
            
            # Perform pin/unpin operation
            success = (storage.pin_message(message_id, username) if is_pinning 
                      else storage.unpin_message(message_id, username))
            
            if success:
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {'success': True, 'action': 'pinned' if is_pinning else 'unpinned'}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
                
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST)
        except Exception as e:
            self.handle_error(e)

    def handle_message_post(self):
        """Handle message posting"""
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            logger.debug(f"Content length: {content_length}")
            
            # Read the body as plaintext
            content = self.rfile.read(content_length).decode('utf-8')
            logger.debug(f"Received message body: {content[:200]}...")  # Log first 200 chars to avoid huge logs
            
            # Get username from cookie if available
            cookies = {}
            if 'Cookie' in self.headers:
                for cookie in self.headers['Cookie'].split(';'):
                    name, value = cookie.strip().split('=', 1)
                    cookies[name] = value
            
            # Get author from cookie
            author = cookies.get('username', 'anonymous')
            logger.info(f"Processing message from {author}: {content}")
            
            # Check if user has a key pair
            has_key = storage.key_manager.has_key_pair(author)
            logger.debug(f"Author {author} has key pair: {has_key}")
            
            # Save the message
            logger.debug("Attempting to save message...")
            try:
                success = storage.save_message(
                    author, 
                    content, 
                    datetime.now(),
                    sign=has_key  # Only sign if user has a key pair
                )
                logger.info(f"Message save {'successful' if success else 'failed'} with signing={has_key}")

                # Start git operations in a background thread if save was successful
                if success:
                    def git_ops():
                        try:
                            # Get the latest message file (the one we just saved)
                            latest_message = max(storage.messages_dir.glob('*.txt'), key=os.path.getctime)
                            try:
                                storage.git_manager.add_and_commit_file(
                                    str(latest_message),
                                    f"Add message from {author}"
                                )
                                storage.git_manager.push()
                                logger.debug(f"Git operations completed successfully for {latest_message}")
                            except Exception as e:
                                logger.debug(f"Git operations completed with non-critical error: {e}")
                        except Exception as e:
                            logger.error(f"Failed to process git operations: {e}")
                    
                    threading.Thread(target=git_ops, daemon=True).start()
                    
            except Exception as e:
                logger.error(f"Exception while saving message: {e}\n{traceback.format_exc()}")
                success = False
        
            if success:
                # Get the latest messages to return the new message
                messages = storage.get_messages(limit=1)
                new_message = messages[0] if messages else None
                logger.info(f"Retrieved new message: {new_message}")
                
                # Return response
                try:
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(new_message).encode('utf-8'))
                except BrokenPipeError:
                    # Client disconnected, log it but don't treat as error
                    logger.info("Client disconnected before response could be sent")
                    return
            else:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to save message")
        except Exception as e:
            logger.error(f"Error in message post handler", exc_info=True)
            self.handle_error(e)

    def handle_username_post(self):
        """Handle username change request"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            logger.debug(f"Username change request: {body}")
            
            # Parse form data
            form_data = parse_qs(body)
            new_username = form_data.get('new_username', [''])[0]
            
            if new_username:
                # Create username change message
                content = json.dumps({
                    'old_username': 'anonymous',
                    'new_username': new_username,
                    'type': 'username_change'
                })
                storage.save_message('system', content, datetime.now())
            
            # Redirect back to home page
            self.send_response(HTTPStatus.FOUND)
            self.send_header('Location', '/')
            self.end_headers()
        except Exception as e:
            logger.error(f"Error in username change request", exc_info=True)
            self.handle_error(e)

    def handle_username_change(self):
        """Handle username change request"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            old_username = data.get('old_username')
            new_username = data.get('new_username')
            
            if not old_username or not new_username:
                self.send_error(HTTPStatus.BAD_REQUEST, "Missing username data")
                return
            
            # Generate new keypair and handle username change
            success, message = storage.git_manager.handle_username_change(old_username, new_username)
            
            if success:
                # Set username cookie
                cookie = f'username={new_username}; Path=/; HttpOnly; SameSite=Strict'
                
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Set-Cookie', cookie)
                self.end_headers()
                self.wfile.write(message.encode('utf-8'))
            else:
                self.send_error(HTTPStatus.BAD_REQUEST, message)
        except Exception as e:
            logger.error(f"Error in username change request", exc_info=True)
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def _get_content_type(self, path):
        """Determine the MIME type based on file extension"""
        ext = os.path.splitext(path)[1].lower()
        content_types = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon'
        }
        return content_types.get(ext, 'application/octet-stream')

    def serve_file(self, filepath, content_type):
        """Helper method to serve a file with specified content type"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as e:
            logger.error(f"Error serving file {filepath}: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)

    def serve_messages(self):
        """Helper method to serve messages as JSON"""
        try:
            # Parse query parameters
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)
            
            # Check if requesting pinned messages only
            pinned_only = parsed_url.path == '/api/messages/pinned'
            
            # Get messages
            if pinned_only:
                messages = storage.get_pinned_messages()
            else:
                limit = int(params.get('limit', [50])[0])
                messages = storage.get_messages(limit=limit)

            # Get current username from cookie
            cookies = {}
            if 'Cookie' in self.headers:
                for cookie in self.headers['Cookie'].split(';'):
                    name, value = cookie.strip().split('=', 1)
                    cookies[name] = value

            # Prepare response
            response = {
                'messages': messages,
                'currentUsername': cookies.get('username', 'anonymous'),
                'messageVerificationEnabled': False  # We'll keep this false for now
            }
            
            # Send response
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Error serving messages: {e}")
            self.handle_error(e)

    def get_system_status(self):
        """Get current system status information."""
        try:
            # Check git status
            subprocess.run(['git', 'status'], check=True, capture_output=True)
            git_status = True
        except subprocess.CalledProcessError:
            git_status = False

        signature_status = False
        if MESSAGE_VERIFICATION_ENABLED:
            try:
                # Check if we can create and verify a test signature
                test_message = b"test"
                signature = storage.key_manager.sign_message(test_message.decode())
                signature_status = True
            except Exception:
                signature_status = False

        try:
            # Get latest commit
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                 check=True, capture_output=True, text=True)
            latest_commit = result.stdout.strip()
        except subprocess.CalledProcessError:
            latest_commit = "Unknown"

        # Get list of public keys
        public_keys_dir = Path('identity/public_keys')
        public_keys = [f.name for f in public_keys_dir.glob('*.pub')] if public_keys_dir.exists() else []

        # Get message counts
        current_messages = storage.get_messages()
        current_message_count = len(current_messages)
        
        # Get archive metrics
        archive_metrics = storage.archiver.get_metrics()
        archived_message_count = archive_metrics['total_messages_archived']

        return {
            'git_status': git_status,
            'signature_status': signature_status,
            'message_verification_enabled': MESSAGE_VERIFICATION_ENABLED,
            'latest_commit': latest_commit,
            'public_keys': public_keys,
            'current_time': '2025-01-13T11:24:24-05:00',  # Using provided timestamp
            'repo_name': os.environ.get('GITHUB_REPO', ''),
            'current_message_count': current_message_count,
            'archived_message_count': archived_message_count
        }

    def serve_status_page(self):
        """Serve the system status page."""
        try:
            template = self.jinja_env.get_template('status.html')
            status_data = self.get_system_status()
            content = template.render(**status_data)
            
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode())
        except Exception as e:
            logger.error(f"Error serving status page: {str(e)}")
            self.handle_error(e)

def find_available_port(start_port=8000, max_attempts=100):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socketserver.TCPServer(("", port), None) as s:
                s.server_close()
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

def open_browser(port):
    """Open the browser to the application URL"""
    try:
        import platform
        url = f'http://localhost:{port}'
        
        if platform.system() == 'Linux':
            # Check if running in WSL
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    # In WSL, use powershell.exe to start browser
                    os.system(f'powershell.exe -c "Start-Process \'{url}\'"')
                else:
                    # Pure Linux
                    os.system(f'xdg-open {url}')
        elif platform.system() == 'Windows':
            os.system(f'start {url}')
        elif platform.system() == 'Darwin':
            os.system(f'open {url}')
    except Exception as e:
        logger.error(f"Failed to open browser: {e}")

def main():
    """Start the server."""
    try:
        # Initialize storage
        global storage
        storage = create_storage(
            storage_type='sqlite',
            db_path=str(Path('database/messages.db'))
        )

        # Find available port
        port = find_available_port()
        if not port:
            print("No available ports found")
            return

        # Create and configure server
        server = socketserver.TCPServer(
            ("", port),
            ChatRequestHandler
        )
        print(f"Server started on port {port}")

        # Open browser in a separate thread
        threading.Thread(
            target=open_browser,
            args=(port,),
            daemon=True
        ).start()

        # Start server
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nShutting down server...")
        if 'server' in locals():
            server.server_close()
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    main()
