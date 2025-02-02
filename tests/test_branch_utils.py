import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.branch_utils import (GitError, ensure_branch, get_current_branch,
                            switch_branch)


class TestBranchUtils(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test git repository
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir)
        
        # Initialize git repository
        os.system(f'cd {self.temp_dir} && git init')
        os.system(f'cd {self.temp_dir} && git config user.email "test@example.com"')
        os.system(f'cd {self.temp_dir} && git config user.name "Test User"')
        
        # Create and commit an initial file
        with open(os.path.join(self.temp_dir, 'README.md'), 'w') as f:
            f.write('# Test Repository')
        os.system(f'cd {self.temp_dir} && git add README.md')
        os.system(f'cd {self.temp_dir} && git commit -m "Initial commit"')

    def tearDown(self):
        # Clean up temporary directory
        os.system(f'rm -rf {self.temp_dir}')

    def test_get_current_branch(self):
        """Test getting current branch name."""
        branch = get_current_branch(self.repo_path)
        self.assertEqual(branch, 'main')  # or 'master' depending on git version

    def test_switch_branch_new(self):
        """Test switching to a new branch."""
        switch_branch('test-branch', create=True, repo_path=self.repo_path)
        branch = get_current_branch(self.repo_path)
        self.assertEqual(branch, 'test-branch')

    def test_switch_branch_existing(self):
        """Test switching to an existing branch."""
        # Create a branch first
        switch_branch('test-branch', create=True, repo_path=self.repo_path)
        # Switch back to main
        switch_branch('main', repo_path=self.repo_path)
        # Switch to existing branch
        switch_branch('test-branch', repo_path=self.repo_path)
        branch = get_current_branch(self.repo_path)
        self.assertEqual(branch, 'test-branch')

    def test_switch_branch_nonexistent(self):
        """Test switching to a non-existent branch without create flag."""
        with self.assertRaises(GitError):
            switch_branch('nonexistent-branch', create=False, repo_path=self.repo_path)

    def test_ensure_branch_new(self):
        """Test ensuring a new user branch exists."""
        ensure_branch('testuser', repo_path=self.repo_path)
        branch = get_current_branch(self.repo_path)
        self.assertEqual(branch, 'user/testuser')

    def test_ensure_branch_existing(self):
        """Test ensuring an existing user branch."""
        # Create branch first
        ensure_branch('testuser', repo_path=self.repo_path)
        # Switch back to main
        switch_branch('main', repo_path=self.repo_path)
        # Ensure branch again
        ensure_branch('testuser', repo_path=self.repo_path)
        branch = get_current_branch(self.repo_path)
        self.assertEqual(branch, 'user/testuser')

    def test_ensure_branch_invalid_username(self):
        """Test ensuring branch with invalid username."""
        with self.assertRaises(ValueError):
            ensure_branch('invalid/username', repo_path=self.repo_path)
        with self.assertRaises(ValueError):
            ensure_branch('', repo_path=self.repo_path)

    @patch('subprocess.Popen')
    def test_git_command_failure(self, mock_popen):
        """Test handling of git command failures."""
        # Mock a failed git command
        mock_popen.return_value.communicate.return_value = ('', 'Command failed')
        mock_popen.return_value.returncode = 1

        with self.assertRaises(GitError):
            get_current_branch(self.repo_path)

if __name__ == '__main__':
    unittest.main()
