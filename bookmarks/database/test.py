import json
import os
import random
import shutil
import string
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from .lib import *
from .. import common


def random_unicode_string(length=50):
    """Generate a random unicode string for testing."""
    chars = string.ascii_letters + string.digits + "日本語한글русский"
    return ''.join(random.choice(chars) for _ in range(length))


class TestBookmarkDB(unittest.TestCase):
    """
    Comprehensive integration tests for BookmarkDB and associated database functions.
    Combines improved tests with tests from TestDatabaseIntegration.
    """

    def setUp(self):
        # Create temporary directories for server, job, root, and asset
        self.temp_dir = tempfile.mkdtemp().replace('\\', '/')
        self.server = os.path.join(self.temp_dir, 'test_server')
        self.job = 'test_job'
        self.root = 'test_root'
        self.asset = 'test_asset'

        os.makedirs(f'{self.server}/{self.job}/{self.root}/{self.asset}', exist_ok=True)

        # Initialize the app with active overrides
        common.initialize(
            mode=common.Mode.Core,
            run_app=False,
            server=self.server,
            job=self.job,
            root=self.root,
            asset=self.asset
        )

        # Ensure that the database connections are empty before each test
        remove_all_connections()

        # Get a database connection
        self.db = get(self.server, self.job, self.root)

    def tearDown(self):
        # Shutdown the application environment
        common.shutdown()
        # Remove temporary directories
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Ensure that the database connections are closed after each test
        remove_all_connections()

    def test_get_database_connection(self):
        db = get(self.server, self.job, self.root)
        self.assertIsInstance(db, BookmarkDB)
        self.assertTrue(db.is_valid())

    def test_set_and_get_value(self):
        source = os.path.join(self.server, self.job, self.root, 'test_source')
        test_value = 'Test Description'

        self.db.set_value(source, 'description', test_value, AssetTable)
        retrieved_value = self.db.value(source, 'description', AssetTable)
        self.assertEqual(retrieved_value, test_value)

    def test_data_type_consistency(self):
        source = os.path.join(self.server, self.job, self.root, 'test_source')

        test_values = {
            'description': 'Test Description',
            'notes': {'note1': 'This is a note', 'note2': 'This is another note'},
            'flags': 123,
            'sg_id': 456,
            'asset_framerate': 24.0,
            'asset_width': 1920,
            'asset_height': 1080
        }

        for key, value in test_values.items():
            self.db.set_value(source, key, value, AssetTable)
            retrieved_value = self.db.value(source, key, AssetTable)
            self.assertEqual(retrieved_value, value)
            self.assertIsInstance(retrieved_value, type(value))

    def test_concurrent_access(self):
        source_prefix = os.path.join(self.server, self.job, self.root, 'concurrent')
        keys = [f'item_{i}' for i in range(50)]

        def writer(i):
            src = f'{source_prefix}_{i}'
            self.db.set_value(src, 'description', f'desc_{i}', AssetTable)
            return i

        def reader(i):
            src = f'{source_prefix}_{i}'
            val = self.db.value(src, 'description', AssetTable)
            return (i, val)

        with ThreadPoolExecutor(max_workers=10) as executor:
            write_futures = [executor.submit(writer, i) for i in range(len(keys))]
            for f in write_futures:
                f.result()

        with ThreadPoolExecutor(max_workers=10) as executor:
            read_futures = [executor.submit(reader, i) for i in range(len(keys))]
            results = [f.result() for f in read_futures]

        for i, val in results:
            self.assertEqual(val, f'desc_{i}')

    def test_multithreading_safety(self):
        results = []

        def thread_func(server, job, root, source, key, value, table):
            db = get(server, job, root)
            db.set_value(source, key, value, table)
            retrieved_value = db.value(source, key, table)
            results.append((value, retrieved_value))

        key = 'description'
        table = AssetTable
        threads = []
        for i in range(500):
            source = os.path.join(self.server, self.job, self.root, f'test_source_{i}')
            value = f"Thread_Value_{i}"
            t = threading.Thread(target=thread_func, args=(self.server, self.job, self.root, source, key, value, table))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for expected, actual in results:
            self.assertEqual(expected, actual)

    def test_invalid_key(self):
        # Test that setting a value with an invalid key raises ValueError
        source = os.path.join(self.server, self.job, self.root, 'test_source')
        with self.assertRaises(ValueError):
            self.db.set_value(source, 'invalid_key', 'some_value', AssetTable)

    def test_remove_db(self):
        source = os.path.join(self.server, self.job, self.root, 'remove_db_test')
        self.db.set_value(source, 'description', 'will remove db', AssetTable)
        remove_db(self.server, self.job, self.root)
        self.assertNotIn(common.get_thread_key(self.server, self.job, self.root), common.db_connections)

    def test_remove_all_connections(self):
        db1 = get(self.server, self.job, self.root)
        db2 = get(self.server, self.job, self.root + '_2')
        remove_all_connections()
        self.assertEqual(len(common.db_connections), 0)

    def test_in_memory_database_on_failure(self):
        # Simulate a failure to create the bookmark directory
        original_create_bookmark_dir = BookmarkDB._create_bookmark_dir
        BookmarkDB._create_bookmark_dir = lambda self: False

        db = get(self.server, self.job, self.root)
        self.assertFalse(db.is_valid())

        # Restore the original method
        BookmarkDB._create_bookmark_dir = original_create_bookmark_dir

    def test_load_json_invalid_data(self):
        # Test loading invalid JSON data
        with self.assertRaises(Exception):
            load_json('invalid_base64_string')

    def test_b64encode_decode(self):
        # Integrated test for base64 encoding and decoding
        test_str = "Hello, World! 日本語 emojis: 😊🚀"
        encoded = b64encode(test_str)
        self.assertIsInstance(encoded, str)
        self.assertNotEqual(encoded, test_str)

        decoded = b64decode(encoded)
        self.assertEqual(decoded, test_str)

        # Test empty string
        empty_encoded = b64encode("")
        self.assertEqual(b64decode(empty_encoded), "")

    def test_set_flag(self):
        db = get(self.server, self.job, self.root)
        source = os.path.join(self.server, self.job, self.root, 'test_source')

        flag_value = 0b0010
        set_flag(self.server, self.job, self.root, source, True, flag_value)
        flags = db.value(source, 'flags', AssetTable)
        self.assertEqual(flags, flag_value)

        set_flag(self.server, self.job, self.root, source, False, flag_value)
        flags = db.value(source, 'flags', AssetTable)
        self.assertEqual(flags, 0)

    # Additional integration from TestDatabaseIntegration

    def test_unicode_handling(self):
        source = os.path.join(self.server, self.job, self.root, 'unicode_test')
        unicode_str = random_unicode_string()
        self.db.set_value(source, 'description', unicode_str, AssetTable)
        self.assertEqual(self.db.value(source, 'description', AssetTable), unicode_str)

    def test_type_validation(self):
        source = os.path.join(self.server, self.job, self.root, 'type_validation')
        with self.assertRaises(TypeError):
            self.db.set_value(source, 'description', 123, AssetTable)

        with self.assertRaises(TypeError):
            self.db.set_value(source, 'asset_width', 'not an int', AssetTable)

    def test_set_flag_utility(self):
        # Already tested set_flag, but we ensure compatibility
        source = os.path.join(self.server, self.job, self.root, 'flag_test')
        flag_bit = 0x1
        self.assertIsNone(self.db.value(source, 'flags', AssetTable))
        set_flag(self.server, self.job, self.root, source, True, flag_bit)
        self.assertEqual(self.db.value(source, 'flags', AssetTable), flag_bit)

        set_flag(self.server, self.job, self.root, source, False, flag_bit)
        self.assertEqual(self.db.value(source, 'flags', AssetTable), 0)

    def test_large_blob_in_template_table(self):
        source = os.path.join(self.server, self.job, self.root, 'blob_test')
        large_data = os.urandom(1024 * 1024 * 5)  # 5MB binary blob
        self.db.set_value(source, 'data', large_data, TemplateDataTable)
        retrieved = self.db.value(source, 'data', TemplateDataTable)
        self.assertEqual(retrieved, large_data)

    def test_very_large_blob_in_template_table(self):
        source = os.path.join(self.server, self.job, self.root, 'very_large_blob_test')
        large_data = os.urandom(1024 * 1024 * 10)  # 10MB
        self.db.set_value(source, 'data', large_data, TemplateDataTable)
        retrieved = self.db.value(source, 'data', TemplateDataTable)
        self.assertEqual(retrieved, large_data)

    def test_concurrent_read_and_write(self):
        source_prefix = os.path.join(self.server, self.job, self.root, 'concurrent_rw')
        total_items = 20

        def writer():
            for i in range(total_items):
                src = f'{source_prefix}_{i}'
                self.db.set_value(src, 'description', f'wdesc_{i}', AssetTable)
                time.sleep(0.001)

        def reader():
            for _ in range(total_items * 2):
                i = random.randint(0, total_items - 1)
                src = f'{source_prefix}_{i}'
                _ = self.db.value(src, 'description', AssetTable)
                time.sleep(0.0005)

        w_thread = threading.Thread(target=writer)
        r_thread = threading.Thread(target=reader)

        w_thread.start()
        r_thread.start()
        w_thread.join()
        r_thread.join()

        for i in range(total_items):
            val = self.db.value(f'{source_prefix}_{i}', 'description', AssetTable)
            self.assertEqual(val, f'wdesc_{i}')

    def test_delete_row(self):
        source = os.path.join(self.server, self.job, self.root, 'test_delete')
        self.db.set_value(source, 'description', 'To be deleted', AssetTable)
        self.db.delete_row(source, AssetTable)
        value = self.db.value(source, 'description', AssetTable)
        self.assertIsNone(value)

    def test_get_column(self):
        sources = [os.path.join(self.server, self.job, self.root, f'test_source_{i}') for i in range(3)]
        descriptions = [f'Description_{i}' for i in range(3)]

        for source, desc in zip(sources, descriptions):
            self.db.set_value(source, 'description', desc, AssetTable)

        retrieved_descriptions = list(self.db.get_column('description', AssetTable))
        self.assertCountEqual(retrieved_descriptions, descriptions)

    def test_get_rows(self):
        sources = [os.path.join(self.server, self.job, self.root, f'test_source_{i}') for i in range(3)]
        data = [{'description': f'Description_{i}', 'flags': i} for i in range(3)]

        for source, entry in zip(sources, data):
            for key, value in entry.items():
                self.db.set_value(source, key, value, AssetTable)

        retrieved_rows = list(self.db.get_rows(AssetTable))

        for entry in data:
            match_found = any(all(row.get(k) == v for k, v in entry.items()) for row in retrieved_rows)
            self.assertTrue(match_found, f"Entry {entry} not found in retrieved rows.")

    def test_context_manager(self):
        source = os.path.join(self.server, self.job, self.root, 'test_source')
        with self.db.connection():
            self.db.set_value(source, 'description', 'Within context', AssetTable)
        value = self.db.value(source, 'description', AssetTable)
        self.assertEqual(value, 'Within context')

    def test_database_locking(self):
        source = os.path.join(self.server, self.job, self.root, 'test_source')

        def lock_database():
            # Begin an exclusive transaction to lock the database
            cursor = self.db.connection().cursor()
            cursor.execute('BEGIN EXCLUSIVE TRANSACTION')
            time.sleep(1)  # Hold the lock for 1 second
            cursor.execute('COMMIT')

        t = threading.Thread(target=lock_database)
        t.start()

        time.sleep(0.1)  # Ensure the lock is acquired

        # Attempt to access the database while it's locked
        start_time = time.time()
        self.db.set_value(source, 'description', 'After lock', AssetTable)
        end_time = time.time()

        t.join()

        self.assertGreater(end_time - start_time, 0.9)
        value = self.db.value(source, 'description', AssetTable)
        self.assertEqual(value, 'After lock')

    def test_convert_return_values_str(self):
        original_value = "Some Description"
        encoded_value = b64encode(original_value)
        result = convert_return_values(AssetTable, 'description', encoded_value)
        self.assertEqual(result, original_value)

    def test_convert_return_values_int(self):
        result = convert_return_values(AssetTable, 'asset_width', '1920')
        self.assertEqual(result, 1920)

        # Invalid integer
        result = convert_return_values(AssetTable, 'asset_width', 'not_an_int')
        self.assertIsNone(result)

    def test_convert_return_values_float(self):
        result = convert_return_values(AssetTable, 'asset_framerate', '24.0')
        self.assertEqual(result, 24.0)

        result = convert_return_values(AssetTable, 'asset_framerate', 'not_a_float')
        self.assertIsNone(result)

    def test_convert_return_values_dict(self):
        original_dict = {'task1': True, 'task2': False}
        json_str = json.dumps(original_dict, ensure_ascii=False)
        encoded_value = b64encode(json_str)

        self.assertEqual(TABLES[BookmarkTable]['config_tasks']['type'], dict)
        result = convert_return_values(BookmarkTable, 'config_tasks', encoded_value)
        self.assertEqual(result, original_dict)

        invalid_encoded = b64encode("not_a_json_string")
        result = convert_return_values(BookmarkTable, 'config_tasks', invalid_encoded)
        self.assertIsNone(result)


class TestInvalidDatabaseHandling(unittest.TestCase):
    """
    Test class for scenarios where no valid server/job/root directory is set up.
    Tests fallback to in-memory databases or handling of invalid paths.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp().replace('\\', '/')

        common.initialize(
            mode=common.Mode.Core,
            run_app=False,
        )

        self.server = 'C:/invalid_server'
        self.job = 'invalid_job'
        self.root = 'invalid_root'

    def tearDown(self):
        remove_all_connections()
        common.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_in_memory_db(self):
        # Attempt to get a DB from an invalid server. This should fallback to in-memory mode.
        db_in_memory = get(self.server, self.job, self.root)
        self.assertFalse(db_in_memory.is_valid())  # in-memory should be considered not valid

        source = db_in_memory.source()
        # Attempting to set a value should have no effect because the DB is not valid.
        db_in_memory.set_value(source, 'description', 'in memory only', AssetTable)
        # Because the DB is invalid, we expect the value to NOT be stored and remain None.
        self.assertIsNone(db_in_memory.value(source, 'description', AssetTable))

        remove_all_connections()
        db_in_memory_reinit = get(self.server, self.job, self.root)
        # Even after reinit, it's still invalid and no persistence.
        self.assertIsNone(db_in_memory_reinit.value(source, 'description', AssetTable))


if __name__ == '__main__':
    unittest.main()
