import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.git_sync import (SyncError, commit_changes, get_modified_files,
                         pull_changes, push_changes, stage_changes,
                         sync_repository)


class TestGitSync(unittest.TestCase):
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

    def create_modified_file(self, filename='test.txt', content='test content'):
        """Helper to create a modified file."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        return filename

    def test_get_modified_files_none(self):
        """Test getting modified files when none exist."""
        modified = get_modified_files(self.repo_path)
        self.assertEqual(modified, [])

    def test_get_modified_files_with_changes(self):
        """Test getting modified files with changes present."""
        filename = self.create_modified_file()
        os.system(f'cd {self.temp_dir} && git add {filename}')
        
        modified = get_modified_files(self.repo_path)
        self.assertIn(filename, modified)

    def test_stage_changes_all(self):
        """Test staging all changes."""
        filename = self.create_modified_file()
        stage_changes(repo_path=self.repo_path)
        
        # Verify file is staged
        output = os.popen(f'cd {self.temp_dir} && git status --porcelain').read()
        self.assertIn('A  ' + filename, output)

    def test_stage_changes_specific(self):
        """Test staging specific files."""
        file1 = self.create_modified_file('test1.txt')
        file2 = self.create_modified_file('test2.txt')
        
        stage_changes([file1], repo_path=self.repo_path)
        
        # Verify only file1 is staged
        output = os.popen(f'cd {self.temp_dir} && git status --porcelain').read()
        self.assertIn('A  ' + file1, output)
        self.assertIn('?? ' + file2, output)

    def test_commit_changes(self):
        """Test committing changes."""
        filename = self.create_modified_file()
        stage_changes(repo_path=self.repo_path)
        commit_changes("Test commit", repo_path=self.repo_path)
        
        # Verify commit
        output = os.popen(f'cd {self.temp_dir} && git log -1 --pretty=%B').read()
        self.assertIn("Test commit", output)

    def test_commit_changes_empty_message(self):
        """Test committing with empty message."""
        with self.assertRaises(ValueError):
            commit_changes("", repo_path=self.repo_path)

    @patch('subprocess.Popen')
    def test_pull_changes(self, mock_popen):
        """Test pulling changes."""
        mock_popen.return_value.communicate.return_value = ('', '')
        mock_popen.return_value.returncode = 0
        
        pull_changes(repo_path=self.repo_path)
        
        # Verify git pull was called
        mock_popen.assert_called_with(
            ['git', 'pull', 'origin'],
            stdout=-1,
            stderr=-1,
            text=True,
            cwd=self.repo_path
        )

    @patch('subprocess.Popen')
    def test_push_changes(self, mock_popen):
        """Test pushing changes."""
        mock_popen.return_value.communicate.return_value = ('', '')
        mock_popen.return_value.returncode = 0
        
        push_changes(repo_path=self.repo_path)
        
        # Verify git push was called
        mock_popen.assert_called_with(
            ['git', 'push', 'origin'],
            stdout=-1,
            stderr=-1,
            text=True,
            cwd=self.repo_path
        )

    @patch('src.git_sync.pull_changes')
    @patch('src.git_sync.push_changes')
    def test_sync_repository_no_changes(self, mock_push, mock_pull):
        """Test syncing repository with no changes."""
        sync_repository(repo_path=self.repo_path)
        
        mock_pull.assert_called_once()
        mock_push.assert_called_once()

    @patch('src.git_sync.pull_changes')
    @patch('src.git_sync.push_changes')
    def test_sync_repository_with_changes(self, mock_push, mock_pull):
        """Test syncing repository with changes."""
        self.create_modified_file()
        sync_repository("Test sync", repo_path=self.repo_path)
        
        # Verify changes were committed
        output = os.popen(f'cd {self.temp_dir} && git log -1 --pretty=%B').read()
        self.assertIn("Test sync", output)
        
        mock_pull.assert_called_once()
        mock_push.assert_called_once()

    @patch('subprocess.Popen')
    def test_command_failure(self, mock_popen):
        """Test handling of command failures."""
        mock_popen.return_value.communicate.return_value = ('', 'Command failed')
        mock_popen.return_value.returncode = 1
        
        with self.assertRaises(SyncError):
            pull_changes(repo_path=self.repo_path)

if __name__ == '__main__':
    unittest.main()
