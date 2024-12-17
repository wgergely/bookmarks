import os
import sys
import unittest
import tempfile
import shutil

from .core import *


class TestCoreFunctions(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for file/directory-related tests
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_platform(self):
        p = get_platform()
        self.assertIn(p, (PlatformWindows, PlatformMacOS, PlatformUnsupported))

    def test_get_username(self):
        uname = get_username()
        self.assertIsInstance(uname, str)

    def test_temp_path(self):
        p = temp_path()
        self.assertIsInstance(p, str)
        self.assertTrue(len(p) > 0)

    def test_get_thread_key(self):
        key = get_thread_key('server', 'job', 'root')
        self.assertIsInstance(key, str)
        self.assertIn('server/job/root', key)

    def test_sort_words(self):
        result = sort_words('banana apple cherry')
        self.assertEqual(result, 'apple, banana, cherry')

    def test_is_dir(self):
        self.assertTrue(is_dir(self.temp_dir))
        self.assertFalse(is_dir(os.path.join(self.temp_dir, 'noexist')))

    def test_normalize_path(self):
        test_path = self.temp_dir.replace('\\', '/') + '/subfolder'
        normalized = normalize_path(test_path)
        self.assertTrue('\\' not in normalized)

    def test_get_entry_from_path(self):
        dir_path = os.path.join(self.temp_dir, 'folder')
        file_path = os.path.join(self.temp_dir, 'file.txt')
        os.mkdir(dir_path)
        with open(file_path, 'w') as f:
            f.write('test')

        dir_entry = get_entry_from_path(dir_path, is_dir=True, force_exists=True)
        self.assertIsNotNone(dir_entry)
        self.assertTrue(dir_entry.is_dir())

        file_entry = get_entry_from_path(file_path, is_dir=False, force_exists=True)
        self.assertIsNotNone(file_entry)
        self.assertTrue(file_entry.is_file())

    def test_byte_to_pretty_string(self):
        # Test boundary and various scales
        self.assertEqual(byte_to_pretty_string(0), '0.0B')
        self.assertIn('999.0B', byte_to_pretty_string(999))  # Just under 1KB
        self.assertIn('1.0K', byte_to_pretty_string(1024))  # Exactly 1KB
        self.assertIn('1.0M', byte_to_pretty_string(1024 ** 2))  # Exactly 1MB
        self.assertIn('1.0G', byte_to_pretty_string(1024 ** 3))  # Exactly 1GB
        self.assertIn('1.0T', byte_to_pretty_string(1024 ** 4))  # Exactly 1TB
        self.assertIn('1.0P', byte_to_pretty_string(1024 ** 5))  # Exactly 1PB
        self.assertIn('1.0E', byte_to_pretty_string(1024 ** 6))  # Exactly 1EB
        self.assertIn('1.0Z', byte_to_pretty_string(1024 ** 7))  # Exactly 1ZB
        # Testing a value between units
        self.assertIn('1.5K', byte_to_pretty_string(1536))  # 1.5KB

    def test_get_py_obj_size(self):
        size = get_py_obj_size({'a': 1, 'b': 2})
        self.assertTrue(size > 0)

    def test_int_key(self):
        d = {'1': 'a', '2': 'b'}
        d2 = int_key(d)
        self.assertIn(1, d2)
        self.assertIn(2, d2)
        self.assertEqual(int_key('abc'), 'abc')

    def test_sanitize_hashtags(self):
        self.assertEqual(sanitize_hashtags('  #test   ##test2 '), '#test #test2')

    def test_split_text_and_hashtags(self):
        text, tags = split_text_and_hashtags('hello world #tag1 #tag2')
        self.assertEqual(text, 'hello world')
        self.assertEqual(tags, '#tag1 #tag2')

    def test_timer(self):
        timer = Timer()
        self.assertTrue(timer.objectName().startswith('Timer_'))
        Timer.delete_timers()


if __name__ == '__main__':
    unittest.main()
