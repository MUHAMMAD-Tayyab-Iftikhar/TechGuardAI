import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.cleaner import SystemCleaner

class TestCleanerPermissions(unittest.TestCase):
    def setUp(self):
        self.cleaner = SystemCleaner()
        # Use a dummy target for testing
        self.cleaner.scan_targets = {'TestTarget': 'C:\\Dummy\\Path'}

    @patch('core.cleaner.logger')
    @patch('os.remove')
    @patch('os.chmod')
    @patch('os.walk')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_permission_error_handled(self, mock_getsize, mock_exists, mock_walk, mock_chmod, mock_remove, mock_logger):
        """Test that PermissionError is handled and logs debug, not warning."""
        mock_exists.return_value = True
        mock_getsize.return_value = 100
        # Mock os.walk to return one file
        mock_walk.return_value = [('C:\\Dummy\\Path', [], ['test_file.txt'])]
        
        # Scenario 1: PermissionError raises, chmod raises Exception -> Should log DEBUG
        mock_remove.side_effect = PermissionError("Access denied")
        mock_chmod.side_effect = Exception("Chmod failed")
        
        self.cleaner.clean_junk(['TestTarget'])
        
        # assert chmod was called
        mock_chmod.assert_called()
        
        # check logger calls
        # We expect logger.debug to be called with "Failed to delete ... after chmod"
        debug_calls = [args[0] for args, _ in mock_logger.debug.call_args_list]
        warning_calls = [args[0] for args, _ in mock_logger.warning.call_args_list]
        
        self.assertTrue(any("Failed to delete" in str(call) for call in debug_calls), 
                        f"Expected debug log for chmod failure, got: {debug_calls}")
        self.assertEqual(len(warning_calls), 0, f"Expected 0 warnings, got: {warning_calls}")

    @patch('core.cleaner.logger')
    @patch('os.remove')
    @patch('os.walk')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_file_in_use_handled(self, mock_getsize, mock_exists, mock_walk, mock_remove, mock_logger):
        """Test that OSError 32 (File used by another process) is handled silently/debug."""
        mock_exists.return_value = True
        mock_getsize.return_value = 100
        mock_walk.return_value = [('C:\\Dummy\\Path', [], ['locked_file.txt'])]
        
        # Create an OSError with winerror 32
        error = OSError(32, "The process cannot access the file...")
        error.winerror = 32
        mock_remove.side_effect = error
        
        self.cleaner.clean_junk(['TestTarget'])
        
        # Check logs
        debug_calls = [args[0] for args, _ in mock_logger.debug.call_args_list]
        warning_calls = [args[0] for args, _ in mock_logger.warning.call_args_list]
        
        self.assertTrue(any("Skipped (in use)" in str(call) for call in debug_calls), 
                        f"Expected debug log for in-use file, got: {debug_calls}")
        self.assertEqual(len(warning_calls), 0, f"Expected 0 warnings, got: {warning_calls}")

    @patch('core.cleaner.logger')
    @patch('os.remove')
    @patch('os.walk')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_access_denied_ose_handled(self, mock_getsize, mock_exists, mock_walk, mock_remove, mock_logger):
        """Test that OSError 5 (Access Denied) is handled silently/debug."""
        mock_exists.return_value = True
        mock_getsize.return_value = 100
        mock_walk.return_value = [('C:\\Dummy\\Path', [], ['admin_file.txt'])]
        
        # Create an OSError with winerror 5
        error = OSError(5, "Access is denied")
        error.winerror = 5
        mock_remove.side_effect = error
        
        self.cleaner.clean_junk(['TestTarget'])
        
        # Check logs
        debug_calls = [args[0] for args, _ in mock_logger.debug.call_args_list]
        warning_calls = [args[0] for args, _ in mock_logger.warning.call_args_list]
        
        self.assertTrue(any("Skipped (access denied)" in str(call) for call in debug_calls), 
                        f"Expected debug log for access denied, got: {debug_calls}")
        self.assertEqual(len(warning_calls), 0, f"Expected 0 warnings, got: {warning_calls}")

if __name__ == '__main__':
    unittest.main()
