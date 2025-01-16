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
    
    def sign_message(self, message):
        # Sign message with private key
        signature = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(self.private_key_path)], input=message.encode(), capture_output=True, check=True).stdout
        return signature.hex()
    
    def verify_signature(self, message, signature_hex, public_key_pem):
        # Write signature to temp file
        sig_path = self.private_keys_dir / 'temp.sig'
        try:
            # Convert hex signature back to bytes and write to file
            signature_bytes = bytes.fromhex(signature_hex)
            sig_path.write_bytes(signature_bytes)

            #todo the pub key should be stored in a way that
            # it can be used again next time, and can also be
            # downloaded by the web browser

            # Write public key to temp file
            pub_path = self.private_keys_dir / 'temp.pub'
            pub_path.write_text(public_key_pem)
            
            # Verify signature
            result = subprocess.run(
                ['openssl', 'dgst', '-sha256', '-verify', str(pub_path), '-signature', str(sig_path)],
                input=message.encode(),
                capture_output=True
            )
            return result.returncode == 0
        except (ValueError, subprocess.CalledProcessError) as e:
            logger.error(f"Signature verification failed: {e}")
            return False
        finally:
            # Clean up temp files
            if sig_path.exists():
                sig_path.unlink()
            if pub_path.exists():
                pub_path.unlink()
    
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
    def __init__(self, repo_path):
        """Initialize GitManager with repository path and GitHub credentials."""
        self.repo_path = Path(repo_path)
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.repo_name = os.environ.get('GITHUB_REPO')
        self.should_sync_to_github = os.environ.get('SYNC_TO_GITHUB', '').lower() == 'true'
        self.enable_fork_sync = os.environ.get('ENABLE_FORK_SYNC', 'false').lower() == 'true'
        
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
            
            # Initialize git repository if needed
            if not (self.repo_path / '.git').exists():
                self.init_git_repo()
        else:
            logger.info("GitHub synchronization disabled")
        
        # Set up messages directory path
        self.messages_dir = self.repo_path / 'messages'
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        
        # Export public key for anonymous users
        public_keys_dir = self.repo_path / 'identity/public_keys'
        public_keys_dir.mkdir(parents=True, exist_ok=True)
        self.key_manager.export_public_key(public_keys_dir / 'anonymous.pub')
        
        # Sync public key if GitHub is enabled
        if self.use_github:
            self.sync_changes_to_github(public_keys_dir / 'anonymous.pub', "System")

    def _run_git_command(self, command, cwd=None):
        """Run a git command with suppressed output unless there's an error."""
        try:
            env = os.environ.copy()
            # Suppress git terminal prompts
            env['GIT_TERMINAL_PROMPT'] = '0'
            
            logger.debug(f"Running git command: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd or str(self.repo_path),
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Log output for debugging
            if result.stdout:
                logger.debug(f"Git command stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"Git command stderr: {result.stderr}")
                
            # Only log push messages at debug level
            if result.stderr and result.stderr.startswith('To '):
                logger.debug(f"Git push result: {result.stderr}")
            # Log other stderr messages that aren't common informational messages
            elif result.stderr and not any(msg in result.stderr for msg in [
                'nothing to commit',
                'branch is up to date',
                'Already up to date',
                'working tree clean'
            ]):
                logger.debug(f"Git command stderr (non-standard): {result.stderr}")
            
            return result
        except subprocess.CalledProcessError as e:
            # Only log real errors, not just informational messages
            if e.stderr and not any(msg in e.stderr for msg in [
                'nothing to commit',
                'branch is up to date',
                'Already up to date',
                'working tree clean'
            ]):
                logger.error(f"Git command failed: {' '.join(command)}")
                logger.debug(f"Command stderr: {e.stderr}")
            raise

    def init_git_repo(self):
        """Initialize git repository and set up remote."""
        if not (self.repo_path / '.git').exists():
            self._run_git_command(['git', 'init'])
            self._run_git_command(['git', 'remote', 'add', 'origin', f'https://github.com/{self.repo_name}.git'])
        self._run_git_command(['git', 'fetch', 'origin'])
        self._run_git_command(['git', 'checkout', '-B', 'main', 'origin/main'])

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
                text=False,  # Get bytes output
                check=True
            )

            # Check for modified or untracked files
            status_output = status.stdout.decode('utf-8').strip()
            if not status_output or not any(line.startswith(('M', 'A', '??')) for line in status_output.split('\n')):
                logger.debug(f"No changes to commit for {relative_path}")
                return

            # Commit changes
            commit_message = f"Update by {author}"
            self._run_git_command(['git', 'commit', '-m', commit_message])

            # Push to GitHub if enabled
            if self.use_github:
                self._run_git_command(['git', 'push', 'origin', 'main'])
                logger.info(f"Successfully pushed changes to GitHub for {relative_path}")

                # Sync with forks if enabled
                if self.enable_fork_sync:
                    self.sync_forks()

        except Exception as e:
            logger.error(f"Error syncing to GitHub: {e}")
            raise

    def sync_forks(self):
        """Sync with all forks listed in forks_list.txt."""
        if not self.use_github:
            return False
            
        try:
            # Get list of forks from GitHub
            forks = self.repo.get_forks()
            
            # Create cloned_repos directory if it doesn't exist
            self.cloned_repos_dir.mkdir(parents=True, exist_ok=True)
            
            # Process each fork
            for fork in forks:
                fork_dir = self.cloned_repos_dir / fork.full_name.replace('/', '_')
                
                try:
                    if not fork_dir.exists():
                        # Clone the fork
                        subprocess.run(['git', 'clone', fork.clone_url, str(fork_dir)], check=True)
                    else:
                        # Pull latest changes
                        subprocess.run(['git', 'pull'], cwd=str(fork_dir), check=True)
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error syncing fork {fork.full_name}: {e}")
                    continue
                    
            return True
        except Exception as e:
            logger.error(f"Error syncing forks: {e}")
            return False

    def sync_with_forks(self):
        """Alias for sync_forks for backward compatibility."""
        return self.sync_forks()

    def pull_from_github(self):
        """Pull latest changes from GitHub and sync forks."""
        if not self.use_github:
            return False

        # Check if enough time has passed since last pull
        current_time = time.time()
        if current_time - self.last_pull_time < self.pull_cooldown:
            return False

        try:
            # Only sync with forks if the feature is enabled
            if self.enable_fork_sync:
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

    def format_message(self, message_content, author, date_str, parent_id=None, signature=None, message_type=None):
        """Format a message with metadata footers."""
        footers = [
            f"Author: {author}",
            f"Date: {date_str}",
            f"Public-Key: identity/public_keys/{author}.pub"
        ]
        
        if parent_id:
            footers.append(f"Parent-Message: {parent_id}")
        
        if signature:
            footers.append(f"Signature: {signature}")
            
        if message_type:
            footers.append(f"Type: {message_type}")
        
        # Combine message and footers with standard email separator
        return f"{message_content.rstrip()}\n\n-- \n{chr(10).join(footers)}"

    def parse_message(self, content):
        """Parse a message into metadata and content."""
        # Split on standard email signature separator
        parts = content.split('\n-- \n', 1)
        if len(parts) != 2:
            # If no metadata footers, treat entire content as message
            return {
                'Author': 'anonymous',
                'Date': None,
                'Public-Key': None,
                'Content': parts[0].strip()
            }, parts[0].strip()
            
        message = parts[0].strip()
        metadata = {}
        
        # Parse metadata footers
        for line in parts[1].strip().split('\n'):
            if ': ' in line:
                key, value = line.split(': ', 1)
                metadata[key] = value
        
        # Add the actual message content to metadata
        metadata['Content'] = message
                
        return metadata, message

    def read_message(self, filename, skip_pull=False):
        """Read a message from a file, checking both main repo and forks."""
        if not skip_pull:
            self.pull_from_github()
            
        # Convert filename to Path object if it's a string
        filename = Path(filename)
        
        def process_message(content):
            """Helper function to process message content into the expected format"""
            if not content:
                return None
                
            # Skip .gitkeep and non-text files
            if filename.name == '.gitkeep' or not content.strip():
                return None
                
            # First try to parse as JSON for backward compatibility
            try:
                json_data = json.loads(content)
                if isinstance(json_data, dict):
                    # Convert old JSON format to new format
                    return {
                        'id': str(filename),
                        'content': json_data.get('content', ''),
                        'author': json_data.get('author', 'anonymous'),
                        'createdAt': json_data.get('timestamp'),
                        'parent_id': json_data.get('parent_id'),
                        'signed': 'signature' in json_data,
                        'verified': str(json_data.get('verified', False)).lower(),
                        'type': json_data.get('type', 'message')
                    }
            except json.JSONDecodeError:
                # Not JSON, parse as plaintext with footers
                metadata, message = self.parse_message(content)
                
                # Get the actual message content from metadata
                message = metadata.get('Content', message)
                
                # Try to get date in this order:
                # 1. From metadata Date header
                # 2. From filename (YYYYMMDD_HHMMSS)
                # 3. From git commit timestamp
                # 4. Mark as "No timestamp"
                date = metadata.get('Date')
                if date:
                    try:
                        # Try to parse as ISO format first
                        parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                        # Format as RFC 3339 with proper timezone offset
                        date_str = parsed_date.astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')
                        date = date_str[:-2] + ':' + date_str[-2:]  # Insert colon in timezone offset
                    except ValueError:
                        date = None
                
                if not date:
                    try:
                        # Try to parse from filename (YYYYMMDD_HHMMSS)
                        fname = filename.stem  # Get filename without extension
                        parts = fname.split('_')
                        if len(parts) >= 2:
                            date_part = parts[0]
                            time_part = parts[1]
                            date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}T{time_part[:2]}:{time_part[2:4]}:{time_part[4:]}Z"
                    except:
                        date = None
                
                if not date:
                    try:
                        # Try to get commit timestamp
                        rel_path = filename.relative_to(self.repo_path)
                        date = self.get_commit_timestamp(str(rel_path))
                    except ValueError:
                        # If relative_to fails, the file might be in a different path
                        date = None
                
                if not date:
                    date = "No timestamp"
                
                # Try to get author from metadata or filename
                author = metadata.get('Author', 'anonymous')
                if author == 'anonymous' and '_' in str(filename):
                    try:
                        # Try to get author from filename (YYYYMMDD_HHMMSS_author.txt)
                        author = filename.stem.split('_')[2]
                    except:
                        pass
                
                # Verify signature if present
                verified = self.verify_message(message, metadata)
                metadata['verified'] = str(verified if verified is not None else False).lower()
                
                # Get commit hash if GitHub is enabled
                commit_hash = ""
                if self.use_github:
                    try:
                        rel_path = filename.relative_to(self.repo_path)
                        commit_hash = self.get_commit_hash(str(rel_path))
                    except ValueError:
                        pass

                return {
                    'id': str(filename),
                    'content': message,  # Use the actual message content
                    'author': author,
                    'createdAt': date,
                    'parent_id': metadata.get('Parent-Message'),
                    'signed': 'Signature' in metadata,
                    'verified': metadata['verified'],
                    'type': metadata.get('Type', 'message'),
                    'commit_hash': commit_hash,
                    'repo_name': self.repo_name if self.use_github else ''
                }
        
        # First try to read from main repo
        main_file = self.messages_dir / filename.name
        if main_file.exists():
            try:
                with open(main_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    result = process_message(content)
                    if result:
                        return result
            except Exception as e:
                logger.debug(f"Error reading message from main repo: {e}")
        
        # Then check cloned repos
        if self.cloned_repos_dir.exists():
            for repo_dir in self.cloned_repos_dir.iterdir():
                if repo_dir.is_dir():
                    fork_file = repo_dir / 'messages' / filename.name
                    if fork_file.exists():
                        try:
                            with open(fork_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                result = process_message(content)
                                if result:
                                    return result
                        except Exception as e:
                            logger.debug(f"Error reading message from fork {repo_dir.name}: {e}")
        
        return None

    def verify_message(self, content, metadata):
        """Verify message signature if present."""
        signature = metadata.get('Signature')
        if not signature:
            return None  # Message is not signed
            
        # Try to find author's public key
        author = metadata.get('Author', 'anonymous')
        
        try:
            public_key = self.key_manager.get_public_key(author)
            if not public_key:
                return False  # Can't verify - no public key
                
            return self.key_manager.verify_signature(content, signature, public_key)
        except ValueError:
            return False  # Invalid signature format

    def handle_username_change(self, old_username, new_username, message_id=None):
        """Handle username change request after verification"""
        try:
            # Validate new username format
            USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,20}$')
            if not USERNAME_REGEX.match(new_username):
                return False, "Username must be 3-20 characters long and contain only letters, numbers, and underscores"
            
            try:
                # Ensure the public_keys directory exists
                public_keys_dir = self.repo_path / 'identity/public_keys'
                public_keys_dir.mkdir(exist_ok=True)
                
                # Generate new keypair for the user
                self.key_manager.generate_keypair(new_username)
                
                # If there was an old username, clean up its keys
                old_key_path = self.repo_path / 'identity/public_keys' / f'{old_username}.pub'
                if old_key_path.exists():
                    old_key_path.unlink()
                    old_private_key = self.key_manager.get_private_key_path(old_username)
                    if old_private_key.exists():
                        old_private_key.unlink()
                
                # Sync to GitHub if enabled
                if self.use_github:
                    new_key_path = self.repo_path / 'identity/public_keys' / f'{new_username}.pub'
                    self.sync_changes_to_github(new_key_path, new_username)
                
                return True, "Username changed successfully"
            except OSError as e:
                # If operation fails, return error
                return False, f"Failed to update username: {str(e)}"
                
        except Exception as e:
            return False, f"Username change failed: {str(e)}"

    def save_message(self, message_content, author="anonymous", parent_id=None, date_str=None, sign=True, message_type=None):
        """Save a message to a file and optionally sync to GitHub."""
        # Ensure messages directory exists
        self.ensure_repo_exists()
        
        # Validate parent_id if provided
        if parent_id:
            parent_file = self.messages_dir / parent_id
            if not parent_file.exists():
                raise ValueError(f"Parent message not found: {parent_id}")
        
        # Use current time if no date provided
        if date_str is None:
            date_str = datetime.now().isoformat()
        
        # Sign message if requested
        signature = None
        if sign:
            signature = self.key_manager.sign_message(message_content)
        
        # Create a timestamped filename
        timestamp = datetime.fromisoformat(date_str).strftime('%Y%m%d_%H%M%S')
        filename = f'{timestamp}_{author}.txt'
        filepath = self.messages_dir / filename
        
        # Format message with metadata
        formatted_message = self.format_message(
            message_content, 
            author, 
            date_str, 
            parent_id=parent_id,
            signature=signature,
            message_type=message_type
        )
        
        # Write message to file
        filepath.write_text(formatted_message)
        
        # Handle username change if this is a username change message
        if message_type == 'username_change':
            try:
                new_username = json.loads(message_content)['new_username']
                success, msg = self.handle_username_change(author, new_username, filename)
                if not success:
                    # If username change failed, add error message
                    error_msg = self.save_message(
                        f"Username change failed: {msg}",
                        "system",
                        parent_id=filename,
                        message_type="error"
                    )
            except (json.JSONDecodeError, KeyError) as e:
                # If message format is invalid, add error message
                error_msg = self.save_message(
                    f"Invalid username change message format: {e}",
                    "system",
                    parent_id=filename,
                    message_type="error"
                )
        
        # Sync to GitHub if enabled
        if self.use_github:
            self.sync_changes_to_github(filepath, author)
            
        # Return message info
        return {
            'id': filename,
            'content': message_content,
            'author': author,
            'date': date_str,
            'parent_id': parent_id,
            'signature': signature,
            'message_type': message_type
        }

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
        filename = manager.save_message("Test message", "test_user")
        
        # Print results
        logger.info("Message saved successfully!")
        logger.info(f"Filename: {filename}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
