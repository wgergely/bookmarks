import unittest
import tempfile
import shutil
import threading
import time
import os

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import database

class TestBookmarkDB(unittest.TestCase):

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
        database.remove_all_connections()

    def tearDown(self):
        # Shutdown the application environment
        common.shutdown()

        # Remove temporary directories
        shutil.rmtree(self.temp_dir)

        # Ensure that the database connections are closed after each test
        database.remove_all_connections()

    def test_get_database_connection(self):
        # Test retrieving a database connection
        db = database.get(self.server, self.job, self.root)
        self.assertIsInstance(db, database.BookmarkDB)
        self.assertTrue(db.is_valid())

    def test_set_and_get_value(self):
        # Test setting and getting a value in the database
        db = database.get(self.server, self.job, self.root)
        source = os.path.join(self.server, self.job, self.root, 'test_source')
        test_value = 'Test Description'

        db.set_value(source, 'description', test_value, database.AssetTable)
        retrieved_value = db.value(source, 'description', database.AssetTable)
        self.assertEqual(retrieved_value, test_value)

    def test_data_type_consistency(self):
        # Test data type consistency for various types
        db = database.get(self.server, self.job, self.root)
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
            db.set_value(source, key, value, database.AssetTable)
            retrieved_value = db.value(source, key, database.AssetTable)
            self.assertEqual(retrieved_value, value)
            self.assertIsInstance(retrieved_value, type(value))

    def test_concurrent_access(self):
        # Test concurrent access to the database
        def worker(db, source, key, value, table):
            db.set_value(source, key, value, table)
            retrieved_value = db.value(source, key, table)
            self.assertEqual(retrieved_value, value)

        db = database.get(self.server, self.job, self.root)
        key = 'description'  # Use a valid column name
        table = database.AssetTable

        threads = []
        for i in range(500):
            source_i = os.path.join(self.server, self.job, self.root, f'test_source_{i}')
            value_i = f"Value_{i}"
            t = threading.Thread(target=worker, args=(db, source_i, key, value_i, table))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify that all values were set correctly
        for i in range(500):
            source_i = os.path.join(self.server, self.job, self.root, f'test_source_{i}')
            retrieved_value = db.value(source_i, key, table)
            self.assertEqual(retrieved_value, f"Value_{i}")

    def test_multithreading_safety(self):
        # Test that database connections are thread-specific and safe
        results = []

        def thread_func(server, job, root, source, key, value, table):
            db = database.get(server, job, root)
            db.set_value(source, key, value, table)
            retrieved_value = db.value(source, key, table)
            results.append((value, retrieved_value))

        threads = []
        for i in range(500):
            source = os.path.join(self.server, self.job, self.root, f'test_source_{i}')
            key = 'description'  # Use a valid column name
            value = f"Thread_Value_{i}"
            table = database.AssetTable
            t = threading.Thread(target=thread_func, args=(self.server, self.job, self.root, source, key, value, table))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for expected, actual in results:
            self.assertEqual(expected, actual)

    def test_invalid_key(self):
        # Test that setting a value with an invalid key raises ValueError
        db = database.get(self.server, self.job, self.root)
        source = os.path.join(self.server, self.job, self.root, 'test_source')
        with self.assertRaises(ValueError):
            db.set_value(source, 'invalid_key', 'some_value', database.AssetTable)

    def test_remove_db(self):
        # Test removing a database connection
        db = database.get(self.server, self.job, self.root)
        database.remove_db(self.server, self.job, self.root)
        self.assertNotIn(common.get_thread_key(self.server, self.job, self.root), common.db_connections)

    def test_remove_all_connections(self):
        # Test removing all database connections
        db1 = database.get(self.server, self.job, self.root)
        db2 = database.get(self.server, self.job, self.root + '_2')
        database.remove_all_connections()
        self.assertEqual(len(common.db_connections), 0)

    def test_in_memory_database_on_failure(self):
        # Simulate a failure to create the bookmark directory
        original_create_bookmark_dir = database.BookmarkDB._create_bookmark_dir
        database.BookmarkDB._create_bookmark_dir = lambda self: False

        db = database.get(self.server, self.job, self.root)
        self.assertFalse(db.is_valid())

        # Restore the original method
        database.BookmarkDB._create_bookmark_dir = original_create_bookmark_dir

    def test_load_json_invalid_data(self):
        # Test loading invalid JSON data
        with self.assertRaises(Exception):
            database.load_json('invalid_base64_string')

    def test_b64encode_decode(self):
        # Test base64 encoding and decoding
        test_string = 'Test String'
        encoded = database.b64encode(test_string)
        decoded = database.b64decode(encoded.encode('utf-8'))
        self.assertEqual(decoded, test_string)

    def test_set_flag(self):
        # Test setting and unsetting flags
        db = database.get(self.server, self.job, self.root)
        source = os.path.join(self.server, self.job, self.root, 'test_source')

        flag_value = 0b0010  # Example flag
        database.set_flag(self.server, self.job, self.root, source, True, flag_value)
        flags = db.value(source, 'flags', database.AssetTable)
        self.assertEqual(flags, flag_value)

        database.set_flag(self.server, self.job, self.root, source, False, flag_value)
        flags = db.value(source, 'flags', database.AssetTable)
        self.assertEqual(flags, 0)

    def test_delete_row(self):
        # Test deleting a row from the database
        db = database.get(self.server, self.job, self.root)
        source = os.path.join(self.server, self.job, self.root, 'test_source')

        db.set_value(source, 'description', 'To be deleted', database.AssetTable)
        db.delete_row(source, database.AssetTable)
        value = db.value(source, 'description', database.AssetTable)
        self.assertIsNone(value)

    def test_get_column(self):
        # Test retrieving all values from a column
        db = database.get(self.server, self.job, self.root)
        sources = [os.path.join(self.server, self.job, self.root, f'test_source_{i}') for i in range(3)]
        descriptions = [f'Description_{i}' for i in range(3)]

        for source, desc in zip(sources, descriptions):
            db.set_value(source, 'description', desc, database.AssetTable)

        retrieved_descriptions = list(db.get_column('description', database.AssetTable))
        self.assertCountEqual(retrieved_descriptions, descriptions)

    def test_get_rows(self):
        # Test retrieving all rows from the database
        db = database.get(self.server, self.job, self.root)
        sources = [os.path.join(self.server, self.job, self.root, f'test_source_{i}') for i in range(3)]
        data = [{'description': f'Description_{i}', 'flags': i} for i in range(3)]

        for source, entry in zip(sources, data):
            for key, value in entry.items():
                db.set_value(source, key, value, database.AssetTable)

        retrieved_rows = list(db.get_rows(database.AssetTable))

        # Adjust the assertion to compare relevant keys
        for entry in data:
            match_found = False
            for row in retrieved_rows:
                if all(row.get(k) == v for k, v in entry.items()):
                    match_found = True
                    break
            self.assertTrue(match_found, f"Entry {entry} not found in retrieved rows.")

    def test_context_manager(self):
        # Test using the database connection as a context manager
        db = database.get(self.server, self.job, self.root)
        source = os.path.join(self.server, self.job, self.root, 'test_source')
        with db.connection():
            db.set_value(source, 'description', 'Within context', database.AssetTable)
        value = db.value(source, 'description', database.AssetTable)
        self.assertEqual(value, 'Within context')

    def test_database_locking(self):
        # Test that database handles locking correctly
        db = database.get(self.server, self.job, self.root)
        source = os.path.join(self.server, self.job, self.root, 'test_source')

        def lock_database():
            # Begin an exclusive transaction to lock the database
            cursor = db.connection().cursor()
            cursor.execute('BEGIN EXCLUSIVE TRANSACTION')
            time.sleep(1)  # Hold the lock for 1 second
            cursor.execute('COMMIT')

        t = threading.Thread(target=lock_database)
        t.start()

        time.sleep(0.1)  # Ensure the lock is acquired

        # Attempt to access the database while it's locked
        start_time = time.time()
        db.set_value(source, 'description', 'After lock', database.AssetTable)
        end_time = time.time()

        t.join()

        # Ensure that the set_value call waited for the lock to be released
        self.assertGreater(end_time - start_time, 0.9)
        value = db.value(source, 'description', database.AssetTable)
        self.assertEqual(value, 'After lock')

if __name__ == '__main__':
    unittest.main()
