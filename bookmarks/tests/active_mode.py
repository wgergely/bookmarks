import os
import tempfile
import unittest

from .. import common
from ..common import active_mode
from ..common import init_active_mode, write_current_mode_to_lock, prune_lock, remove_lock


class TestActiveMode(unittest.TestCase):

    def setUp(self):
        # Create temporary directories for server, job, root, and asset
        self.temp_dir = tempfile.mkdtemp().replace('\\', '/')
        self.server = os.path.join(self.temp_dir, 'test_server')
        self.job = 'test_job'
        self.root = 'test_root'
        self.asset = 'test_asset'

        os.makedirs(f'{self.server}/{self.job}/{self.root}/{self.asset}', exist_ok=True)

        # Monkeypatch LOCK_DIR and LOCK_PATH in active_mode to use the temporary folder
        active_mode.LOCK_DIR = self.temp_dir
        active_mode.LOCK_PATH = f'{active_mode.LOCK_DIR}/session_lock_{{pid}}.lock'

        # Initialize the app with active overrides
        common.initialize(
            mode=common.Mode.Core,
            run_app=False,
            server=self.server,
            job=self.job,
            root=self.root,
            asset=self.asset
        )

        # Ensure that the lock directory exists
        if not os.path.exists(active_mode.LOCK_DIR):
            os.makedirs(active_mode.LOCK_DIR)

    def tearDown(self):
        # Shutdown the application environment
        common.shutdown()

        # Cleanup the temporary directory
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_init_active_mode_private_paths(self):
        """Test initializing active mode with ActiveMode.Private due to environment overrides."""
        os.environ['Bookmarks_ACTIVE_SERVER'] = 'mock_server'
        init_active_mode()
        self.assertEqual(common.active_mode, common.ActiveMode.Private)

        # Check if the lock file was created and contains the correct mode
        lock_file = active_mode.LOCK_PATH.format(pid=os.getpid())
        self.assertTrue(os.path.exists(lock_file))
        with open(lock_file, 'r', encoding='utf8') as f:
            data = f.read().strip()
        self.assertEqual(int(data), common.ActiveMode.Private)

        # Clean up the environment variable
        del os.environ['Bookmarks_ACTIVE_SERVER']

    def test_init_active_mode_synchronized_paths(self):
        """Test initializing active mode with ActiveMode.Synchronized by default."""
        init_active_mode()
        self.assertEqual(common.active_mode, common.ActiveMode.Synchronized)

        # Check if the lock file was created and contains the correct mode
        lock_file = active_mode.LOCK_PATH.format(pid=os.getpid())
        self.assertTrue(os.path.exists(lock_file))
        with open(lock_file, 'r', encoding='utf8') as f:
            data = f.read().strip()
        self.assertEqual(int(data), common.ActiveMode.Synchronized)

    def test_prune_lock_removes_stale_lock(self):
        """Test that prune_lock correctly removes stale lock files."""
        # Create a fake lock file for a non-existing PID
        fake_pid = 99999
        fake_lock_path = f'{active_mode.LOCK_DIR}/session_lock_{fake_pid}.lock'
        with open(fake_lock_path, 'w', encoding='utf8') as f:
            f.write(f'{common.ActiveMode.Synchronized}')

        # Run prune_lock and verify that the fake lock file is removed
        prune_lock()
        self.assertFalse(os.path.exists(fake_lock_path))

    def test_remove_lock(self):
        """Test that remove_lock removes the current session lock file."""
        # Initialize the lock file
        init_active_mode()

        lock_file = active_mode.LOCK_PATH.format(pid=os.getpid())
        self.assertTrue(os.path.exists(lock_file))

        # Remove the lock file
        remove_lock()
        self.assertFalse(os.path.exists(lock_file))

    def test_write_current_mode_to_lock(self):
        """Test writing the current mode to the lock file."""
        common.active_mode = common.ActiveMode.Synchronized
        write_current_mode_to_lock()

        # Verify that the correct mode is written to the lock file
        lock_file = active_mode.LOCK_PATH.format(pid=os.getpid())
        self.assertTrue(os.path.exists(lock_file))
        with open(lock_file, 'r', encoding='utf8') as f:
            data = f.read().strip()
        self.assertEqual(int(data), common.ActiveMode.Synchronized)


if __name__ == '__main__':
    unittest.main()
