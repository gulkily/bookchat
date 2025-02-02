#!/usr/bin/env python3

import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SyncError(Exception):
    """Custom exception for sync-related errors."""
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
        SyncError: If the command fails
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
            raise SyncError(f"Git command failed: {stderr.strip()}")
            
        return stdout.strip(), stderr.strip()
    except subprocess.SubprocessError as e:
        raise SyncError(f"Failed to execute git command: {e}")

def get_modified_files(repo_path: Optional[Path] = None) -> List[str]:
    """
    Get list of modified files in the repository.
    
    Args:
        repo_path: Optional path to the git repository
        
    Returns:
        List of modified file paths
        
    Raises:
        SyncError: If unable to get modified files
    """
    try:
        stdout, _ = _run_git_command(['git', 'status', '--porcelain'], repo_path)
        modified_files = []
        
        for line in stdout.split('\n'):
            if line:
                status = line[:2]
                file_path = line[3:]
                if status != '??':  # Exclude untracked files
                    modified_files.append(file_path)
                    
        return modified_files
    except SyncError as e:
        logger.error(f"Failed to get modified files: {e}")
        raise

def stage_changes(files: Optional[List[str]] = None, repo_path: Optional[Path] = None) -> None:
    """
    Stage changes for commit.
    
    Args:
        files: Optional list of files to stage (stages all if None)
        repo_path: Optional path to the git repository
        
    Raises:
        SyncError: If unable to stage changes
    """
    try:
        cmd = ['git', 'add']
        if files:
            cmd.extend(files)
        else:
            cmd.append('.')
            
        _run_git_command(cmd, repo_path)
        logger.info("Successfully staged changes")
    except SyncError as e:
        logger.error(f"Failed to stage changes: {e}")
        raise

def commit_changes(message: str, repo_path: Optional[Path] = None) -> None:
    """
    Commit staged changes.
    
    Args:
        message: Commit message
        repo_path: Optional path to the git repository
        
    Raises:
        SyncError: If unable to commit changes
    """
    try:
        if not message:
            raise ValueError("Commit message cannot be empty")
            
        _run_git_command(['git', 'commit', '-m', message], repo_path)
        logger.info(f"Successfully committed changes: {message}")
    except (SyncError, ValueError) as e:
        logger.error(f"Failed to commit changes: {e}")
        raise

def pull_changes(remote: str = 'origin', branch: Optional[str] = None, repo_path: Optional[Path] = None) -> None:
    """
    Pull changes from remote repository.
    
    Args:
        remote: Remote repository name
        branch: Optional branch name (uses current branch if None)
        repo_path: Optional path to the git repository
        
    Raises:
        SyncError: If unable to pull changes
    """
    try:
        cmd = ['git', 'pull', remote]
        if branch:
            cmd.append(branch)
            
        _run_git_command(cmd, repo_path)
        logger.info(f"Successfully pulled changes from {remote}")
    except SyncError as e:
        logger.error(f"Failed to pull changes: {e}")
        raise

def push_changes(remote: str = 'origin', branch: Optional[str] = None, repo_path: Optional[Path] = None) -> None:
    """
    Push changes to remote repository.
    
    Args:
        remote: Remote repository name
        branch: Optional branch name (uses current branch if None)
        repo_path: Optional path to the git repository
        
    Raises:
        SyncError: If unable to push changes
    """
    try:
        cmd = ['git', 'push', remote]
        if branch:
            cmd.append(branch)
            
        _run_git_command(cmd, repo_path)
        logger.info(f"Successfully pushed changes to {remote}")
    except SyncError as e:
        logger.error(f"Failed to push changes: {e}")
        raise

def sync_repository(commit_msg: Optional[str] = None, repo_path: Optional[Path] = None) -> None:
    """
    Perform a full synchronization cycle: stage, commit, pull, and push.
    
    Args:
        commit_msg: Optional commit message (uses default if None)
        repo_path: Optional path to the git repository
        
    Raises:
        SyncError: If synchronization fails
    """
    try:
        modified = get_modified_files(repo_path)
        if modified:
            stage_changes(repo_path=repo_path)
            commit_changes(
                commit_msg or "Auto-commit: Sync repository",
                repo_path=repo_path
            )
            
        pull_changes(repo_path=repo_path)
        push_changes(repo_path=repo_path)
        logger.info("Repository synchronization complete")
    except SyncError as e:
        logger.error(f"Repository synchronization failed: {e}")
        raise

def main():
    """Command line interface for git synchronization utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Git synchronization utilities")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Pull command
    pull_parser = subparsers.add_parser("pull", help="Pull changes from remote")
    pull_parser.add_argument("--remote", default="origin", help="Remote repository name")
    pull_parser.add_argument("--branch", help="Branch name")
    
    # Push command
    push_parser = subparsers.add_parser("push", help="Push changes to remote")
    push_parser.add_argument("--remote", default="origin", help="Remote repository name")
    push_parser.add_argument("--branch", help="Branch name")
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Perform full sync cycle")
    sync_parser.add_argument("--message", "-m", help="Commit message")
    
    # Parse arguments
    args = parser.parse_args()
    
    try:
        if args.command == "pull":
            pull_changes(args.remote, args.branch)
        elif args.command == "push":
            push_changes(args.remote, args.branch)
        elif args.command == "sync":
            sync_repository(args.message)
        else:
            parser.print_help()
    except SyncError as e:
        logger.error(str(e))
        exit(1)

if __name__ == "__main__":
    main()
