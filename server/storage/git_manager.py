#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime
from pathlib import Path
from github import Github
import json
import re
import shutil
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import time
import logging
import uuid
from typing import Dict, List, Optional, Union
import tempfile
import base64

# Create a dedicated logger for git operations
logger = logging.getLogger('git')

class KeyManager:
    def __init__(self, private_keys_dir, public_keys_dir):
        self.private_keys_dir = Path(private_keys_dir)
        self.public_keys_dir = Path(public_keys_dir)
        self.private_keys_dir.mkdir(parents=True, exist_ok=True)
        self.public_keys_dir.mkdir(parents=True, exist_ok=True)
        self.private_key_path = self.private_keys_dir / 'local.pem'
        self.public_key_path = self.public_keys_dir / 'local.pub'
        
        # Generate key pair if it doesn't exist
        if not self.private_key_path.exists():
            subprocess.run(['openssl', 'genrsa', '-out', str(self.private_key_path), '2048'], check=True)
            subprocess.run(['openssl', 'rsa', '-pubout', '-in', str(self.private_key_path), '-out', str(self.public_key_path)], check=True)

    def sign_message(self, message: str) -> str:
        """Sign a message using a private key."""
        try:
            # Create temporary file for the message
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as msg_file:
                msg_file.write(message)
                msg_file_path = msg_file.name

            # Sign the message
            result = subprocess.run(
                [
                    'openssl', 'dgst',
                    '-sha256',
                    '-sign', str(self.private_key_path),
                    msg_file_path
                ],
                capture_output=True,
                check=True
            )

            # Base64 encode the signature
            signature = base64.b64encode(result.stdout).decode('utf-8')
            return signature

        except Exception as e:
            logger.error(f"Failed to sign message: {e}")
            return None
        finally:
            try:
                os.unlink(msg_file_path)
            except:
                pass

    def verify_signature(self, message: str, signature_b64: str, public_key_pem: str) -> bool:
        """Verify a message signature using a public key."""
        try:
            # Create temporary files for message, signature, and public key
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as msg_file:
                msg_file.write(message)
                msg_file_path = msg_file.name

            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as sig_file:
                sig_file.write(base64.b64decode(signature_b64))
                sig_file_path = sig_file.name

            with tempfile.NamedTemporaryFile(mode='w', delete=False) as key_file:
                key_file.write(public_key_pem)
                key_file_path = key_file.name

            # Verify the signature
            result = subprocess.run(
                [
                    'openssl', 'dgst',
                    '-sha256',
                    '-verify', key_file_path,
                    '-signature', sig_file_path,
                    msg_file_path
                ],
                capture_output=True,
                text=True,
                check=False
            )

            return result.returncode == 0 and "Verified OK" in result.stdout

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
        finally:
            try:
                os.unlink(msg_file_path)
                os.unlink(sig_file_path)
                os.unlink(key_file_path)
            except:
                pass

    def export_public_key(self, filepath):
        # Export public key to file
        subprocess.run(['cp', str(self.public_key_path), str(filepath)], check=True)

    def generate_keypair(self, username):
        """Generate key pair for the user"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()

        # Save private key
        private_key_path = self.private_keys_dir / f'{username}.pem'
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        private_key_path.write_bytes(private_pem)

        # Save public key
        public_key_path = self.public_keys_dir / f'{username}.pub'
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key_path.write_bytes(public_pem)

    def get_private_key_path(self, username):
        # Get private key path for the user
        return self.private_keys_dir / f'{username}.pem'

    def get_public_key(self, username):
        # Get public key for the user
        public_key_path = self.public_keys_dir / f'{username}.pub'
        if public_key_path.exists():
            return public_key_path.read_text()
        else:
            return None

class GitManager:
    """Manages git operations for message storage."""

    def __init__(self, repo_path: Union[str, Path], test_mode: bool = False):
        """Initialize GitManager.

        Args:
            repo_path: Path to the git repository
            test_mode: If True, operates in test mode without GitHub sync
        """
        self.repo_path = Path(repo_path)
        self.test_mode = test_mode
        self.repo_name = os.getenv('GITHUB_REPO') if not test_mode else None
        self.messages_dir = self.repo_path / 'messages'
        self.keys_dir = self.repo_path / 'keys'
        
        # Create necessary directories
        self.repo_path.mkdir(exist_ok=True)
        self.messages_dir.mkdir(exist_ok=True)
        self.keys_dir.mkdir(exist_ok=True)
        
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.should_sync_to_github = os.environ.get('SYNC_TO_GITHUB', '').lower() == 'true'
        
        # Initialize key manager with both private and public key directories
        private_keys_dir = os.environ.get('KEYS_DIR', str(self.repo_path / 'keys'))
        public_keys_dir = os.environ.get('PUBLIC_KEYS_DIR', str(self.repo_path / 'identity/public_keys'))
        self.key_manager = KeyManager(private_keys_dir, public_keys_dir)
        
        # Make GitHub optional
        self.use_github = bool(self.github_token and self.repo_name and self.should_sync_to_github)
        
        # Add last pull timestamp to prevent too frequent pulls
        self.last_pull_time = 0
        self.pull_cooldown = 5  # Minimum seconds between pulls
        
        # Initialize cloned repos directory
        self.cloned_repos_dir = self.repo_path / 'cloned_repos'
        self.cloned_repos_dir.mkdir(parents=True, exist_ok=True)
        
        if self.use_github:
            logger.info("GitHub synchronization enabled")
            # Initialize GitHub API client
            self.g = Github(self.github_token)
            self.repo = self.g.get_repo(self.repo_name)
        else:
            logger.info("GitHub synchronization disabled")
        
        # Set up messages directory path
        self.messages_dir = self.repo_path / 'messages'
        self.keys_dir = self.repo_path / 'identity/public_keys'
        self._ensure_directories()
        
        # Export public key for anonymous users
        public_keys_dir = self.repo_path / 'identity/public_keys'
        public_keys_dir.mkdir(parents=True, exist_ok=True)
        self.key_manager.export_public_key(public_keys_dir / 'anonymous.pub')
        
        # Sync public key if GitHub is enabled
        if self.use_github:
            self.sync_changes_to_github(public_keys_dir / 'anonymous.pub', "System")

    async def init(self):
        """Initialize the git repository."""
        try:
            # Create directories if they don't exist
            self.messages_dir.mkdir(parents=True, exist_ok=True)
            self.keys_dir.mkdir(parents=True, exist_ok=True)

            # Initialize git repo if not already initialized
            if not (self.repo_path / '.git').exists():
                await self._run_git_command('init')
                await self._run_git_command('config', 'user.email', 'bookchat@example.com')
                await self._run_git_command('config', 'user.name', 'BookChat Bot')

            # Create initial commit if no commits exist
            if not await self._has_commits():
                await self._run_git_command('add', '.')
                await self._run_git_command('commit', '-m', 'Initial commit')

            return True
        except Exception as e:
            logger.error(f"Error initializing git repo: {e}")
            return False

    async def _has_commits(self):
        """Check if the repository has any commits."""
        try:
            result = await self._run_git_command('rev-parse', '--verify', 'HEAD')
            return result.returncode == 0
        except Exception:
            return False

    async def init_git_repo(self):
        """Initialize git repository if it doesn't exist."""
        try:
            if not os.path.exists(os.path.join(str(self.repo_path), '.git')):
                logger.debug(f"Initializing git repository at {str(self.repo_path)}")
                
                # Initialize git repository
                self._run_git_command(['git', 'init'])
                
                # Configure git user for commits
                self._run_git_command(['git', 'config', '--local', 'user.email', 'bot@bookchat.local'])
                self._run_git_command(['git', 'config', '--local', 'user.name', 'BookChat Bot'])
                
                # In test mode, create an initial commit to establish the main branch
                if self.test_mode:
                    logger.debug("Setting up test repository structure")
                    
                    # Create necessary directories
                    os.makedirs(os.path.join(str(self.repo_path), 'messages'), exist_ok=True)
                    os.makedirs(os.path.join(str(self.repo_path), 'identity/public_keys'), exist_ok=True)
                    os.makedirs(os.path.join(str(self.repo_path), 'keys'), exist_ok=True)
                    
                    # Create initial README
                    readme_path = os.path.join(str(self.repo_path), 'README.md')
                    with open(readme_path, 'w') as f:
                        f.write('# Test Repository\nThis is a test repository for BookChat.')
                    
                    # Add and commit the initial structure
                    self._run_git_command(['git', 'add', '.'])
                    self._run_git_command(['git', 'commit', '-m', 'Initial commit'])
                    
                    # Create and checkout main branch
                    self._run_git_command(['git', 'branch', '-M', 'main'])
                else:
                    # For non-test mode, set up remote and sync with GitHub
                    if self.repo_name:
                        self._run_git_command(['git', 'remote', 'add', 'origin', f'https://github.com/{self.repo_name}.git'])
                        self._run_git_command(['git', 'fetch', 'origin'])
                        self._run_git_command(['git', 'checkout', '-B', 'main', 'origin/main'])
            return True
        except Exception as e:
            logger.error(f"Failed to initialize git repository: {str(e)}")
            raise

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)

    def _setup_git(self):
        """Initialize git repository if needed."""
        if not (self.repo_path / '.git').exists():
            self._run_git_command(['git', 'init'])
            self._run_git_command(['git', 'config', 'user.email', 'bot@bookchat.local'])
            self._run_git_command(['git', 'config', 'user.name', 'BookChat Bot'])
            
            # In test mode, create an initial commit to establish the main branch
            if self.test_mode:
                readme_path = self.repo_path / 'README.md'
                with open(readme_path, 'w') as f:
                    f.write('# Test Repository\nThis is a test repository for BookChat.')
                self._run_git_command(['git', 'add', 'README.md'])
                self._run_git_command(['git', 'commit', '-m', 'Initial commit'])
                self._run_git_command(['git', 'branch', '-M', 'main'])

    def _run_git_command(self, command, check=True):
        """Run a git command in the repository directory.

        Args:
            command: List of command parts
            check: If True, raise an exception on non-zero exit code

        Returns:
            CompletedProcess instance
        """
        try:
            logger.debug(f"Running git command: {' '.join(command)}")
            logger.debug(f"Working directory: {str(self.repo_path)}")

            result = subprocess.run(
                command,
                cwd=str(self.repo_path),  # Convert Path to string
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=check and not self.test_mode  # Don't raise errors in test mode
            )

            if result.stdout:
                logger.debug(f"Command stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"Command stderr: {result.stderr}")

            if result.returncode != 0:
                logger.error(f"Git command failed: {' '.join(command)}")
                logger.error(f"Return code: {result.returncode}")
                logger.error(f"Stderr: {result.stderr}")
                if not self.test_mode and check:
                    raise subprocess.CalledProcessError(
                        result.returncode, command, result.stdout, result.stderr
                    )
            return result
        except subprocess.CalledProcessError as e:
            if not self.test_mode and check:
                raise
            logger.error(f"Git command failed: {' '.join(command)}")
            logger.error(f"Exception: {str(e)}")
            return e

    def sync_changes_to_github(self, filepath, author="BookChat Bot"):
        """Sync changes to GitHub."""
        if not self.use_github:
            logger.debug("GitHub sync disabled, skipping")
            return
        
        try:
            # Ensure filepath is a Path object
            filepath = Path(filepath) if not isinstance(filepath, Path) else filepath
            
            # Check if the file exists before trying to sync
            if not filepath.exists():
                logger.warning(f"Warning: File {filepath} does not exist, skipping GitHub sync")
                return
            
            # Stage the file
            relative_path = filepath.relative_to(self.repo_path)
            self._run_git_command(['git', 'add', str(relative_path)])
            
            # Check if there are any changes to commit
            status = subprocess.run(
                ['git', 'status', '--porcelain', str(relative_path)],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True
            )
            
            if not status.stdout.strip():
                logger.debug(f"No changes to commit for {relative_path}")
                return
            
            # Commit the change
            commit_message = f'Update user key for {author}'
            self._run_git_command(['git', 'commit', '-m', commit_message])
            
            # Push to GitHub
            self._run_git_command(['git', 'push', 'origin', 'main'])
            logger.info(f"Successfully synced {relative_path} to GitHub")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error syncing to GitHub: {e}")
            # Continue without GitHub sync - don't raise the error

    def sync_forks(self):
        """Sync with all forks listed in forks_list.txt."""
        from sync_forks import clone_or_update_repo
        
        forks_file = self.repo_path / "forks_list.txt"
        if not forks_file.exists():
            logger.warning("forks_list.txt not found, skipping fork sync")
            return
        
        with open(forks_file, "r") as f:
            repos = [line.strip() for line in f if line.strip()]
    
        # Filter out current repo if it exists
        if self.repo_name:
            repos = [repo for repo in repos if self.repo_name not in repo]
    
        for repo in repos:
            try:
                clone_or_update_repo(repo, "messages")
            except Exception as e:
                logger.error(f"Error syncing fork {repo}: {e}")

    def pull_from_github(self):
        """Pull latest changes from GitHub and sync forks."""
        if not self.use_github:
            return False

        # Check if enough time has passed since last pull
        current_time = time.time()
        if current_time - self.last_pull_time < self.pull_cooldown:
            return False

        try:
            # First sync with all forks
            self.sync_forks()
            
            # Then pull from main repo
            self._run_git_command(['git', 'fetch', 'origin', 'main'])
            
            # Check if we're behind origin/main
            status = subprocess.run(
                ['git', 'rev-list', 'HEAD..origin/main', '--count'],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True
            )
            
            if status.stdout.strip() != '0':
                self._run_git_command(['git', 'pull', '--rebase', 'origin', 'main'])
                
                # Update last pull time
                self.last_pull_time = current_time
                return True
                
            return False
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Error pulling from GitHub: {e}")
            return False

    def ensure_repo_exists(self):
        """Ensure the repository exists locally, clone if it doesn't."""
        if self.use_github:
            self.pull_from_github()
            
        # Create messages directory if it doesn't exist
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        
        # Create .gitkeep to ensure directory is tracked
        gitkeep_path = self.messages_dir / '.gitkeep'
        if not gitkeep_path.exists():
            gitkeep_path.touch()

    async def save_message(self, message: dict) -> str:
        """Save a message to the repository.

        Args:
            message: Dictionary containing message data (username, content, timestamp)

        Returns:
            Message ID
        """
        try:
            # Create message file
            message_id = f"{message['timestamp']}-{message['username']}"
            message_file = self.messages_dir / f"{message_id}.txt"
            
            # Write message to file
            content = (
                f"ID: {message_id}\n"
                f"Content: {message['content']}\n"
                f"Username: {message['username']}\n"
                f"Timestamp: {message['timestamp']}\n"
            )
            with open(message_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # Add and commit the message
            if not self.test_mode:
                self.add_and_commit_file(
                    str(message_file),
                    f"Add message from {message['username']}",
                    message['username']
                )

            return message_id
        except Exception as e:
            logger.error(f"Failed to save message: {str(e)}")
            return None

    async def get_messages(self) -> List[Dict]:
        """Retrieve all messages."""
        messages = []
        try:
            # Get all message files
            message_files = sorted(self.messages_dir.glob('*.txt'))
            
            # Load each message
            for message_file in message_files:
                try:
                    with open(message_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        message_data = {}
                        for line in content.split('\n'):
                            if line.startswith('ID: '):
                                message_data['id'] = line[4:]
                            elif line.startswith('Content: '):
                                message_data['content'] = line[9:]
                            elif line.startswith('Username: '):
                                message_data['username'] = line[10:]
                            elif line.startswith('Timestamp: '):
                                message_data['timestamp'] = line[11:]
                        messages.append(message_data)
                except Exception as e:
                    logger.error(f"Error loading message {message_file}: {e}")
                    continue
            
            # Sort messages by timestamp
            messages.sort(key=lambda x: x.get('timestamp', ''))
            return messages
            
        except Exception as e:
            logger.error(f"Failed to retrieve messages: {e}")
            return []

    async def get_message_by_id(self, message_id: str) -> Optional[Dict]:
        """Get a message by its ID."""
        try:
            message_path = self.messages_dir / f"{message_id}.txt"
            if not message_path.exists():
                return None

            with open(message_path, 'r', encoding='utf-8') as f:
                content = f.read()
                message_data = {}
                for line in content.split('\n'):
                    if line.startswith('ID: '):
                        message_data['id'] = line[4:]
                    elif line.startswith('Content: '):
                        message_data['content'] = line[9:]
                    elif line.startswith('Username: '):
                        message_data['username'] = line[10:]
                    elif line.startswith('Timestamp: '):
                        message_data['timestamp'] = line[11:]
                return message_data

        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None

    def add_and_commit_file(self, filepath: str, commit_msg: str, author: str = "BookChat Bot"):
        """Add and commit a specific file."""
        self._run_git_command(['git', 'add', filepath])
        self._run_git_command(['git', 'commit', '-m', commit_msg, f'--author={author} <{author}@bookchat.local>'])
        return True

    def push(self):
        """Push changes to remote repository."""
        if not self.use_github:
            return False
            
        try:
            # Check if there are commits to push
            status = subprocess.run(
                ['git', 'status', '-sb'],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True,
                text=True
            )
            
            # If nothing to push, return early
            if 'ahead' not in status.stdout:
                return True
                
            self._run_git_command(['git', 'push', 'origin', 'main'])
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error pushing to remote: {e.stderr}")
            return False

    def get_commit_timestamp(self, filepath):
        """Get the timestamp of the last commit that modified this file."""
        try:
            # Get the timestamp of the last commit that modified this file
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%aI', filepath],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True
            )
            timestamp = result.stdout.strip()
            if timestamp:
                return timestamp
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get commit timestamp: {e}")
        return None

    def get_commit_hash(self, filepath: str) -> str:
        """Get the short commit hash of the last commit that modified this file.
        
        Args:
            filepath: Path to the file relative to repo root
            
        Returns:
            Short commit hash (7 characters) or empty string if not found
        """
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%h', '--', filepath],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

def main():
    """Main function for testing"""
    try:
        # Get repository path from environment
        repo_path = os.getenv('REPO_PATH')
        if not repo_path:
            raise ValueError("REPO_PATH environment variable is required")

        # Initialize GitManager
        manager = GitManager(repo_path)
        
        # Save a test message
        filename = manager.save_message({"username": "test_user", "content": "Test message", "timestamp": datetime.now().isoformat()})
        
        # Print results
        logger.info("Message saved successfully!")
        logger.info(f"Filename: {filename}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
