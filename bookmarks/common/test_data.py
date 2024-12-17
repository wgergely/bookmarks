import random
import threading
import time
import unittest
import weakref

from PySide2.QtCore import QAbstractListModel, QModelIndex, Qt, QIdentityProxyModel

from . import common
from .data import lock  # Import the global lock from the module we are testing


def create_test_data(items=5, data_type=common.FileItem, loaded=True, version=0):
    d = common.DataDict()
    d.loaded = loaded
    d.data_type = data_type
    d.refresh_needed = False
    # No 'version' or non-integer keys, as per requirements
    for i in range(items):
        item = common.DataDict()
        item[common.IdRole] = i
        # If needed, add version to the path, but ensure no extra keys in the dict
        item[common.PathRole] = f"/path/to/item_{i}.ext"
        item[common.ParentPathRole] = ["server", "job", "root", "asset", "task_folder"]
        d[i] = item
    return d


class TestModel(QAbstractListModel):
    """A QAbstractListModel that stores a DataDict of DataDicts."""

    def __init__(self, data_list: common.DataDict, parent=None):
        super().__init__(parent)
        self._data_list = data_list  # DataDict

    def rowCount(self, parent=QModelIndex()):
        return len(self._data_list)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self._data_list.get(index.row())
        return None

    def model_data(self):
        # Return the underlying DataDict.
        return self._data_list


class TestDataModule(unittest.TestCase):
    def setUp(self):
        # Reset the global item_data before each test with a DataDict
        common.item_data = common.DataDict()

    def test_reset_data_creates_structure(self):
        key = ("a", "b")
        task = "mytask"
        common.reset_data(key, task)
        self.assertIn(key, common.item_data)
        self.assertIn(task, common.item_data[key])
        self.assertIn(common.FileItem, common.item_data[key][task])
        self.assertIn(common.SequenceItem, common.item_data[key][task])

    def test_set_and_get_data(self):
        key = ("server", "job")
        task = "mytask"
        d = create_test_data(items=3)
        common.set_data(key, task, common.FileItem, d)
        returned = common.get_data(key, task, common.FileItem)
        self.assertIs(returned, d)
        self.assertEqual(len(returned), 3)

    def test_data_count(self):
        key = ("server", "job")
        task = "count_task"
        d = create_test_data(items=10)
        common.set_data(key, task, common.FileItem, d)
        count = common.data_count(key, task, common.FileItem)
        self.assertEqual(count, 10)

    def test_is_data_loaded(self):
        key = ("path", "to")
        task = "loaded_task"
        d = create_test_data(items=2, loaded=True)
        common.set_data(key, task, common.FileItem, d)
        self.assertTrue(common.is_data_loaded(key, task, common.FileItem))

        d2 = create_test_data(items=2, loaded=False)
        common.set_data(key, task, common.SequenceItem, d2)
        self.assertFalse(common.is_data_loaded(key, task, common.SequenceItem))

    def test_get_data_from_value(self):
        key = ("some", "where")
        task = "search_task"
        d = create_test_data(items=5)
        common.set_data(key, task, common.FileItem, d)

        # Search by value that exists in PathRole
        found = common.get_data_from_value("/path/to/item_2.ext", common.FileItem,
                                           role=common.PathRole)
        self.assertIs(found, d)

        # Search for a non-existent value
        not_found = common.get_data_from_value("/non/existent", common.FileItem,
                                               role=common.PathRole)
        self.assertIsNone(not_found)

    def test_get_task_data(self):
        key = ("root",)
        task = "mytask"
        common.reset_data(key, task)
        result = common.get_task_data(key, task)
        self.assertIsInstance(result, common.DataDict)
        self.assertIn(common.FileItem, result)
        self.assertIn(common.SequenceItem, result)

    def test_sort_data(self):
        d = create_test_data(items=5)
        # Modify one path to ensure sorting is tested properly
        d[2][common.PathRole] = "/path/to/item_2.zzz"
        ref = weakref.ref(d)

        # Sort by PathRole alphabetically
        sorted_d = common.sort_data(ref, common.PathRole, sort_order=False)
        paths = [sorted_d[i][common.PathRole] for i in sorted_d]
        self.assertEqual(paths, sorted(paths))

    def test_get_data_ref(self):
        key = ("ref", "test")
        task = "ref_task"
        d = create_test_data(items=3)
        common.set_data(key, task, common.FileItem, d)
        ref = common.get_data_ref(key, task, common.FileItem)
        self.assertIsNotNone(ref)
        self.assertIs(ref(), d)

    def test_get_ref_from_source_index(self):
        test_data = common.DataDict()
        for i in range(5):
            item = common.DataDict()
            item["item"] = i
            test_data[i] = item

        source_model = TestModel(test_data)
        proxy_model = QIdentityProxyModel()
        proxy_model.setSourceModel(source_model)

        index = proxy_model.index(2, 0)
        ref = common.get_ref_from_source_index(index)
        self.assertIsNotNone(ref)
        self.assertEqual(ref().get("item"), 2)

    def test_invalid_index_for_ref(self):
        test_data = common.DataDict()
        for i in range(5):
            item = common.DataDict()
            item["item"] = i
            test_data[i] = item

        source_model = TestModel(test_data)
        proxy_model = QIdentityProxyModel()
        proxy_model.setSourceModel(source_model)

        invalid_index = QModelIndex()
        self.assertIsNone(common.get_ref_from_source_index(invalid_index))

    def test_handle_non_existent_data_type(self):
        key = ("non", "existent")
        task = "no_task"
        # get_data should reset and create empty structure
        d = common.get_data(key, task, common.FileItem)
        self.assertIsInstance(d, common.DataDict)
        self.assertIn(common.FileItem, common.item_data[key][task])

    def test_thread_safety_under_concurrent_access(self):
        key = ("concurrent", "test")
        task = "concurrent_task"

        def writer():
            for _ in range(50000):
                d = create_test_data(items=5)
                common.set_data(key, task, common.FileItem, d)
                if random.random() < 0.1:
                    time.sleep(0.001)

        def reader():
            for _ in range(50000):
                _ = common.get_data(key, task, common.FileItem)
                if random.random() < 0.1:
                    time.sleep(0.001)

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=reader)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def test_data_dict_attributes_concurrency(self):
        # Test concurrency of reading/writing DataDict attributes
        d = common.DataDict()
        d.loaded = True
        d.data_type = common.FileItem
        d.refresh_needed = False

        stop_event = threading.Event()
        stop_event.clear()

        def writer_thread():
            while not stop_event.is_set():
                # Acquire write lock before modifying attributes
                lock.lockForWrite()
                try:
                    d.loaded = random.choice([True, False])
                    d.data_type = random.choice([common.FileItem, common.SequenceItem])
                    d.refresh_needed = random.choice([True, False])
                finally:
                    lock.unlock()
                time.sleep(random.uniform(0.001, 0.01))

        def reader_thread():
            while not stop_event.is_set():
                # Acquire read lock before reading attributes
                lock.lockForRead()
                try:
                    l = d.loaded
                    dt = d.data_type
                    rn = d.refresh_needed
                    # Simple integrity check
                    self.assertIn(dt, [common.FileItem, common.SequenceItem])
                    self.assertIsInstance(l, bool)
                    self.assertIsInstance(rn, bool)
                finally:
                    lock.unlock()
                time.sleep(random.uniform(0.001, 0.01))

        # Start multiple writers and readers
        threads = []
        for _ in range(5):
            t = threading.Thread(target=writer_thread)
            t.start()
            threads.append(t)

        for _ in range(5):
            t = threading.Thread(target=reader_thread)
            t.start()
            threads.append(t)

        # Run for some time
        time.sleep(5)
        stop_event.set()

        for t in threads:
            t.join()

    # If you still need the integrity test with "version" keys, ensure versioning or remove it entirely
    # as it is not required by the module and can cause confusion.


if __name__ == '__main__':
    unittest.main()
