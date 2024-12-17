import os
import shutil
import tempfile
import unittest

from PySide2 import QtWidgets

from .env import *
from . import common


def _normalize_path(p):
    if p is None:
        return p
    return p.replace('\\', '/')


class TestEnv(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.server = os.path.join(self.temp_dir, 'test_server')
        self.job = 'test_job'
        self.root = 'test_root'
        self.asset = 'test_asset'
        os.makedirs(os.path.join(self.server, self.job, self.root, self.asset), exist_ok=True)

        # Initialize common in Core mode without running the app
        common.initialize(mode=common.Mode.Standalone, run_app=False)

        # Remove any environment variables that may affect tests
        os.environ.pop('Bookmarks_ROOT', None)
        # Remove system PATH to avoid finding binaries from system
        os.environ['PATH'] = ''

        for binary in external_binaries:
            os.environ.pop(f'BOOKMARKS_{binary.upper()}', None)

        # Clear user settings related to binaries
        for binary in external_binaries:
            common.settings.remove(f'settings/bin_{binary}')

    def tearDown(self):
        common.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_binary_no_setup(self):
        # With no environment, user settings, or dist bin,
        # and empty PATH, we should get None
        for binary in external_binaries:
            self.assertIsNone(get_binary(binary))

    def test_get_binary_user_setting(self):
        test_path = os.path.join(self.temp_dir, 'ffmpeg_fake.exe')
        with open(test_path, 'w') as f:
            f.write('fake ffmpeg')

        common.settings.setValue('settings/bin_ffmpeg', test_path)
        self.assertEqual(_normalize_path(get_binary('ffmpeg')), _normalize_path(test_path))
        self.assertEqual(_normalize_path(get_user_setting('ffmpeg')), _normalize_path(test_path))

    def test_get_binary_env_variable(self):
        test_path = os.path.join(self.temp_dir, 'rvpush_fake')
        with open(test_path, 'w') as f:
            f.write('fake rvpush')
        if hasattr(os, 'chmod'):
            os.chmod(test_path, 0o755)

        os.environ['BOOKMARKS_RVPUSH'] = test_path
        self.assertEqual(_normalize_path(get_binary('rvpush')), _normalize_path(test_path))

    def test_get_binary_distribution_bin(self):
        dist_root = os.path.join(self.temp_dir, 'dist')
        os.makedirs(os.path.join(dist_root, 'bin'), exist_ok=True)
        os.environ['Bookmarks_ROOT'] = dist_root

        test_path = os.path.join(dist_root, 'bin', 'rv_fake')
        with open(test_path, 'w') as f:
            f.write('fake rv')
        if hasattr(os, 'chmod'):
            os.chmod(test_path, 0o755)

        self.assertEqual(_normalize_path(get_binary('rv')), _normalize_path(test_path))

    def test_get_binary_with_unicode_name(self):
        dist_root = os.path.join(self.temp_dir, 'dist_unicode')
        os.makedirs(os.path.join(dist_root, 'bin'), exist_ok=True)
        os.environ['Bookmarks_ROOT'] = dist_root

        binary_display_name = ' oiiotoolç  '
        test_path = os.path.join(dist_root, 'bin', 'oiiotoolç')
        with open(test_path, 'w') as f:
            f.write('fake oiiotool with unicode')
        if hasattr(os, 'chmod'):
            os.chmod(test_path, 0o755)

        self.assertEqual(_normalize_path(get_binary(binary_display_name)), _normalize_path(test_path))

    def test_get_user_setting_invalid_path(self):
        common.settings.setValue('settings/bin_ffmpeg', '/invalid/path/ffmpeg')
        self.assertIsNone(get_user_setting('ffmpeg'))

    def test_env_path_editor_initialization(self):
        # Load a dummy stylesheet to prevent errors
        if hasattr(common, '_stylesheet'):
            common._stylesheet = ''

        dist_root = os.path.join(self.temp_dir, 'dist_init')
        os.makedirs(os.path.join(dist_root, 'bin'), exist_ok=True)
        os.environ['Bookmarks_ROOT'] = dist_root

        # Create dummy binaries
        for binary in external_binaries:
            test_path = os.path.join(dist_root, 'bin', binary)
            with open(test_path, 'w') as f:
                f.write(f'fake {binary}')
            if hasattr(os, 'chmod'):
                os.chmod(test_path, 0o755)

        editor_widget = EnvPathEditor()
        for binary in external_binaries:
            editor = getattr(editor_widget, f'{binary}_editor')
            self.assertTrue(editor.text().endswith(binary))

    def test_env_path_editor_pick_and_reveal_no_file(self):
        editor_widget = EnvPathEditor()
        for binary in external_binaries:
            editor_widget.pick(binary)
            editor_widget.reveal(binary)
            editor = getattr(editor_widget, f'{binary}_editor')
            self.assertEqual(editor.text(), '')

    def test_env_path_editor_set_user_settings(self):
        editor_widget = EnvPathEditor()

        test_path = os.path.join(self.temp_dir, 'custom_ffmpeg')
        with open(test_path, 'w') as f:
            f.write('fake ffmpeg')

        ffmpeg_editor = editor_widget.ffmpeg_editor
        ffmpeg_editor.setText(test_path)

        self.assertEqual(_normalize_path(common.settings.value('settings/bin_ffmpeg')),
                         _normalize_path(test_path))


if __name__ == '__main__':
    unittest.main()
