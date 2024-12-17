import os
import shutil
import tempfile
import threading
import time
import unittest

from .active import *
from . import common


def clear_env():
    """Clear environment variables that set explicit overrides."""
    for seg in ActivePathSegmentTypes:
        env_key = f'Bookmarks_ACTIVE_{seg.upper()}'
        if env_key in os.environ:
            del os.environ[env_key]


class BaseIntegrationTest(unittest.TestCase):
    def setUp(self):
        common.shutdown()
        clear_env()

        self.temp_dir = tempfile.mkdtemp().replace('\\', '/')
        common.initialize(mode=common.Mode.Core, run_app=False)
        common.active_mode = None
        common.active_paths = None

    def tearDown(self):
        common.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestActiveIntegrationWithoutOverrides(BaseIntegrationTest):
    """Integration tests without explicit overrides."""

    def setUp(self):
        super().setUp()
        self.server = os.path.join(self.temp_dir, 'test_server')
        self.job = 'test_job'
        self.root = 'test_root'
        self.asset = 'test_asset'

        os.makedirs(os.path.join(self.server, self.job, self.root, self.asset), exist_ok=True)
        common.shutdown()
        common.initialize(mode=common.Mode.Core, run_app=False)

    def test_initial_state(self):
        for seg in ActivePathSegmentTypes:
            self.assertIsNone(active(seg), f"Expected no value for {seg} initially")

    def test_set_and_get_segments(self):
        set_active('server', self.server)
        set_active('job', self.job)
        root_path = os.path.join(self.server, self.job, self.root)
        asset_path = os.path.join(root_path, self.asset)
        os.makedirs(root_path, exist_ok=True)
        os.makedirs(asset_path, exist_ok=True)
        set_active('root', self.root)
        set_active('asset', self.asset)

        self.assertEqual(active('server'), self.server)
        self.assertEqual(active('job'), self.job)
        self.assertEqual(active('root'), self.root)
        self.assertEqual(active('asset'), self.asset)

        full_path = active('asset', path=True)
        expected = os.path.normpath(f"{self.server}/{self.job}/{self.root}/{self.asset}")
        self.assertEqual(os.path.normpath(full_path), expected)

    def test_unicode_segments(self):
        # Must set server and job first
        set_active('server', self.server)
        os.makedirs(os.path.join(self.server, self.job), exist_ok=True)
        set_active('job', self.job)
        unicode_name = 'tëst_ünicode'
        unicode_path = os.path.join(self.server, self.job, unicode_name)
        os.makedirs(unicode_path, exist_ok=True)

        set_active('root', unicode_name)
        val = active('root')
        self.assertEqual(val, unicode_name)

        full_path = active('root', path=True)
        expected = os.path.normpath(f"{self.server}/{self.job}/{unicode_name}")
        self.assertEqual(os.path.normpath(full_path), expected)

    def test_concurrency(self):
        def writer(seg, val):
            # Create a chain ensuring directories exist
            chain = [self.server]
            seg_index = {'server': 0, 'job': 1, 'root': 2, 'asset': 3, 'task': 4, 'file': 5}
            idx = seg_index[seg]

            # Predefined chain: server, value_1, value_2, value_3, value_4, value_5 for each level
            if idx >= 1:
                chain.append('value_1' if seg != 'job' else val)
            if idx >= 2:
                chain.append('value_2' if seg != 'root' else val)
            if idx >= 3:
                chain.append('value_3' if seg != 'asset' else val)
            if idx >= 4:
                chain.append('value_4' if seg != 'task' else val)
            if idx >= 5:
                chain.append('value_5' if seg != 'file' else val)

            os.makedirs(os.path.join(*chain), exist_ok=True)

            # Set each segment leading up to current
            set_active('server', self.server)
            if idx >= 1:
                set_active('job', 'value_1' if seg != 'job' else val)
            if idx >= 2:
                set_active('root', 'value_2' if seg != 'root' else val)
            if idx >= 3:
                set_active('asset', 'value_3' if seg != 'asset' else val)
            if idx >= 4:
                set_active('task', 'value_4' if seg != 'task' else val)
            if idx >= 5:
                set_active('file', 'value_5' if seg != 'file' else val)

            time.sleep(0.05)
            read_val = active(seg)
            self.assertEqual(read_val, val, f"Expected {val} got {read_val} for segment {seg}")

        threads = []
        for i, seg in enumerate(ActivePathSegmentTypes):
            val = f"value_{i}" if seg != 'server' else self.server
            t = threading.Thread(target=writer, args=(seg, val))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()


class TestActiveIntegrationWithOverrides(BaseIntegrationTest):
    """Integration tests with explicit overrides."""

    def setUp(self):
        super().setUp()
        self.server = os.path.join(self.temp_dir, 'test_server')
        self.job = 'test_job'
        self.root = 'test_root'
        self.asset = 'test_asset'
        os.makedirs(os.path.join(self.server, self.job, self.root, self.asset), exist_ok=True)

        common.shutdown()
        common.initialize(
            mode=common.Mode.Core,
            run_app=False,
            server=self.server,
            job=self.job,
            root=self.root,
            asset=self.asset
        )

    def test_explicit_overrides_applied(self):
        self.assertEqual(active('server'), self.server)
        self.assertEqual(active('job'), self.job)
        self.assertEqual(active('root'), self.root)
        self.assertEqual(active('asset'), self.asset)

        full_path = active('asset', path=True)
        expected = os.path.normpath(f"{self.server}/{self.job}/{self.root}/{self.asset}")
        self.assertEqual(os.path.normpath(full_path), expected)

    def test_explicit_override_block_set(self):
        original = active('asset')
        set_active('asset', 'ignored_value', force=False)
        self.assertEqual(active('asset'), original)

        new_val = 'forced_value'
        forced_asset_path = os.path.join(self.server, self.job, self.root, new_val)
        os.makedirs(forced_asset_path, exist_ok=True)
        set_active('asset', new_val, force=True)
        self.assertEqual(active('asset'), new_val)

    def test_unicode_explicit_overrides(self):
        unicode_val = 'ünïcødë'
        unicode_path = os.path.join(self.server, self.job, unicode_val)
        os.makedirs(unicode_path, exist_ok=True)

        set_active('root', unicode_val, force=True)
        self.assertEqual(active('root'), unicode_val)

        full_path = active('root', path=True)
        expected = os.path.normpath(f"{self.server}/{self.job}/{unicode_val}")
        self.assertEqual(os.path.normpath(full_path), expected)

    def test_concurrency_with_explicit(self):
        def accessor(seg):
            val = active(seg)
            if seg == 'server':
                self.assertEqual(val, self.server)

        threads = [threading.Thread(target=accessor, args=(seg,)) for seg in ActivePathSegmentTypes]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def test_prune_lock(self):
        prune_lock()
        fake_pid = 999999
        fake_lock_path = get_lock_path(fake_pid)
        basedir = os.path.dirname(fake_lock_path)
        os.makedirs(basedir, exist_ok=True)
        with open(fake_lock_path, 'w', encoding='utf8') as f:
            f.write(str(ActiveMode.Synchronized))

        prune_lock()
        self.assertFalse(os.path.exists(fake_lock_path))

    def test_remove_lock(self):
        written_path = write_current_mode_to_lock()
        self.assertTrue(os.path.exists(written_path))
        remove_lock()
        self.assertFalse(os.path.exists(written_path))


class TestActiveUnit(unittest.TestCase):
    """Unit tests for init_active and init_active_mode with env overrides."""

    def setUp(self):
        common.shutdown()
        clear_env()

        self.temp_dir = tempfile.mkdtemp().replace('\\', '/')
        common.initialize(mode=common.Mode.Core, run_app=False)
        common.active_mode = None
        common.active_paths = None

        lock_dir = get_lock_dir()
        if os.path.exists(lock_dir):
            for f in os.listdir(lock_dir):
                full_path = os.path.join(lock_dir, f)
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)

    def tearDown(self):
        common.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_active_no_overrides(self):
        init_active(clear_all=True, load_settings=False, load_private=False, load_overrides=False)
        self.assertIsNotNone(common.active_paths)
        for mode in ActiveMode:
            for seg in ActivePathSegmentTypes:
                self.assertIsNone(common.active_paths[mode][seg])

    def test_init_active_with_env_overrides(self):
        unicode_val = 'some_unicode_ä'
        os.environ['Bookmarks_ACTIVE_SERVER'] = unicode_val
        # Create directory for the unicode_val to prevent verify_path from clearing it
        os.makedirs(os.path.join(self.temp_dir, unicode_val), exist_ok=True)
        # Change current directory to temp_dir so that relative path checks succeed
        current_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            init_active(clear_all=True, load_settings=False, load_private=False, load_overrides=True)
            self.assertEqual(common.active_paths[ActiveMode.Explicit]['server'], unicode_val)
        finally:
            os.chdir(current_dir)

    def test_init_active_mode_no_locks(self):
        init_active(clear_all=True, load_settings=False, load_private=False, load_overrides=False)
        init_active_mode()
        self.assertEqual(common.active_mode, ActiveMode.Synchronized)

    def test_init_active_mode_with_sync_lock(self):
        lock_path = get_lock_path()
        with open(lock_path, 'w', encoding='utf8') as f:
            f.write(str(ActiveMode.Synchronized))

        init_active(clear_all=True, load_settings=False, load_private=False, load_overrides=False)
        init_active_mode()
        self.assertEqual(common.active_mode, ActiveMode.Private)

    def test_init_active_mode_invalid_lock_contents(self):
        lock_path = get_lock_path()
        with open(lock_path, 'w', encoding='utf8') as f:
            f.write("not_an_integer")

        init_active(clear_all=True, load_settings=False, load_private=False, load_overrides=False)
        init_active_mode()
        self.assertEqual(common.active_mode, ActiveMode.Private)


if __name__ == '__main__':
    unittest.main()
