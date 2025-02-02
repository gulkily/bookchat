#!/usr/bin/env python3

import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitError(Exception):
    """Custom exception for git-related errors."""
    pass

def _run_git_command(cmd: list[str], cwd: Optional[Path] = None) -> Tuple[str, str]:
    """
    Run a git command and return its output.
    
    Args:
        cmd: List of command components
        cwd: Working directory for the command
        
    Returns:
        Tuple of (stdout, stderr)
        
    Raises:
        GitError: If the command fails
    """
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise GitError(f"Git command failed: {stderr.strip()}")
            
        return stdout.strip(), stderr.strip()
    except subprocess.SubprocessError as e:
        raise GitError(f"Failed to execute git command: {e}")

def get_current_branch(repo_path: Optional[Path] = None) -> str:
    """
    Get the name of the current git branch.
    
    Args:
        repo_path: Optional path to the git repository
        
    Returns:
        Name of the current branch
        
    Raises:
        GitError: If unable to get current branch
    """
    try:
        stdout, _ = _run_git_command(['git', 'branch', '--show-current'], repo_path)
        return stdout
    except GitError as e:
        logger.error(f"Failed to get current branch: {e}")
        raise

def switch_branch(branch_name: str, create: bool = False, repo_path: Optional[Path] = None) -> None:
    """
    Switch to a different git branch.
    
    Args:
        branch_name: Name of the branch to switch to
        create: If True, create the branch if it doesn't exist
        repo_path: Optional path to the git repository
        
    Raises:
        GitError: If unable to switch branches
    """
    try:
        cmd = ['git', 'checkout']
        if create:
            cmd.append('-b')
        cmd.append(branch_name)
        
        _run_git_command(cmd, repo_path)
        logger.info(f"Successfully switched to branch: {branch_name}")
    except GitError as e:
        logger.error(f"Failed to switch to branch {branch_name}: {e}")
        raise

def ensure_branch(username: str, repo_path: Optional[Path] = None) -> None:
    """
    Ensure a user branch exists and switch to it.
    
    Args:
        username: Username for the branch
        repo_path: Optional path to the git repository
        
    Raises:
        GitError: If unable to ensure branch exists
        ValueError: If username is invalid
    """
    if not username or not username.replace('_', '').isalnum():
        raise ValueError("Username must be alphanumeric (underscores allowed)")
        
    branch_name = f"user/{username}"
    
    try:
        # Check if branch exists
        stdout, _ = _run_git_command(['git', 'branch', '--list', branch_name], repo_path)
        
        if stdout:
            # Branch exists, switch to it
            switch_branch(branch_name, create=False, repo_path=repo_path)
        else:
            # Create and switch to new branch
            switch_branch(branch_name, create=True, repo_path=repo_path)
            
        logger.info(f"Successfully ensured branch for user: {username}")
    except GitError as e:
        logger.error(f"Failed to ensure branch for user {username}: {e}")
        raise

def main():
    """Command line interface for branch utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Git branch management utilities")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Current branch command
    subparsers.add_parser("current", help="Get current branch name")
    
    # Switch branch command
    switch_parser = subparsers.add_parser("switch", help="Switch to a branch")
    switch_parser.add_argument("branch", help="Branch name")
    switch_parser.add_argument("--create", "-b", action="store_true", help="Create branch if it doesn't exist")
    
    # Ensure branch command
    ensure_parser = subparsers.add_parser("ensure", help="Ensure user branch exists")
    ensure_parser.add_argument("username", help="Username")
    
    # Parse arguments
    args = parser.parse_args()
    
    try:
        if args.command == "current":
            print(get_current_branch())
        elif args.command == "switch":
            switch_branch(args.branch, args.create)
        elif args.command == "ensure":
            ensure_branch(args.username)
        else:
            parser.print_help()
    except (GitError, ValueError) as e:
        logger.error(str(e))
        exit(1)

if __name__ == "__main__":
    main()
