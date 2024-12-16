"""Interface to interact with the item data cache.

All data loaded by the item models are stored in :attr:`~bookmarks.common.item_data`.
The module provides methods for the models to access, load and reset the cached data.

"""
import weakref

from PySide2 import QtCore

from . import common


# module level QReadWriteLock
lock = QtCore.QReadWriteLock()


class DataDict(dict):
    """Custom dictionary class used to store model item data.

    This class adds compatibility for :class:`weakref.ref` referencing
    and custom attributes for storing data states.

    """

    def __str__(self):
        return (
            f'<DataDict ({len(self)} items); '
            f'(loaded={self.loaded}, '
            f'refresh_needed={self.refresh_needed}, '
            f'data_type={self.data_type})>'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._loaded = False
        self._refresh_needed = False
        self._data_type = None

    @property
    def loaded(self):
        """Special attribute used by the item models and associated thread workers.

        When set to `True`, the helper threads have finished populating data and the item
        and its children are fully loaded.

        """
        return self._loaded

    @loaded.setter
    def loaded(self, v):
        self._loaded = v

    @property
    def refresh_needed(self):
        """The data is out of date and needs refetching.

        """
        return self._refresh_needed

    @refresh_needed.setter
    def refresh_needed(self, v):
        self._refresh_needed = v

    @property
    def data_type(self):
        """Returns the associated model item type.

        """
        return self._data_type

    @data_type.setter
    def data_type(self, v):
        self._data_type = v

    @property
    def servers(self):
        """Get a list of servers stored in the data dictionary."""
        role = common.ParentPathRole
        return [v[role][0] for v in self.values() if v[role] and len(v[role]) > 1]

    @property
    def jobs(self):
        """Get a list of jobs stored in the data dictionary."""
        role = common.ParentPathRole
        return [v[role][1] for v in self.values() if v[role] and len(v[role]) > 2]

    @property
    def roots(self):
        """Get a list of file types stored in the data dictionary."""
        role = common.ParentPathRole
        return [v[role][2] for v in self.values() if v[role] and len(v[role]) > 3]

    @property
    def assets(self):
        """Get a list of assets stored in the data dictionary."""
        role = common.ParentPathRole
        return [v[role][3] for v in self.values() if v[role] and len(v[role]) > 4]

    @property
    def tasks_folders(self):
        """Get a list of tasks folders stored in the data dictionary."""
        role = common.ParentPathRole
        return [v[role][4] for v in self.values() if v[role] and len(v[role]) > 5]

    @property
    def relative_folders(self):
        """Get a list of relative folders stored in the data dictionary."""

        def func(v):
            pp = v[common.ParentPathRole]
            if not pp:
                return []
            _path = '/'.join(pp)
            if not v[common.PathRole]:
                return []
            path = v[common.PathRole]
            rel_path = path.replace(_path, '').rstrip('/')
            return rel_path.split('/')

        return list(set([f for v in self.values() for f in func(v)]))

    @property
    def file_types(self):
        """Get a list of file types stored in the data dictionary."""

        def func(v):
            if not v[common.PathRole]:
                return ''
            path = v[common.PathRole]
            if '.' not in path.split('/')[-1]:
                return ''
            return path.split('.')[-1].lstrip('.')

        return list(set([f for v in self.values() for f in func(v)]))


def sort_data(ref, sort_by, sort_order):
    """Sort the given data using `sort_by` and `sort_order`.

    Args:
        ref (weakref.ref): Pointer to a :class:`~bookmarks.common.data.DataDict` instance.
        sort_by (int): The role to use to sort the data.
        sort_order (bool): The sort order.

    Returns:
        common.DataDict: A sorted copy of the source data.

    """
    def sort_key(_idx):
        """Returns the sort key of the given item.

        """
        v = ref().__getitem__(_idx)
        return v[sort_by]

    sorted_idxs = sorted(
        ref().keys(),
        key=sort_key,
        reverse=sort_order
    )

    d = common.DataDict()

    # Copy over the property values from the source data
    d.loaded = ref().loaded
    d.data_type = ref().data_type
    d.refresh_needed = ref().refresh_needed

    for n, idx in enumerate(sorted_idxs):
        if not ref():
            raise RuntimeError('Model mutated during sorting.')
        d[n] = ref()[idx]
        d[n][common.IdRole] = n

    return d


def get_data(key, task, data_type):
    """Get a cached data dict from :attr:`~bookmarks.common.item_data`.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.
        data_type (int): One of :attr:`~bookmarks.common.FileItem` or :attr:`~bookmarks.common.SequenceItem`.

    Returns:
        common.DataDict: The cached data.

    """
    if key not in common.item_data:
        reset_data(key, task)
    elif task not in common.item_data[key]:
        reset_data(key, task)
    elif data_type not in common.item_data[key][task]:
        reset_data(key, task)
    return common.item_data[key][task][data_type]


def get_data_from_value(value, data_type, role=common.PathRole, get_container=True):
    """Get the internal data dictionary associated with a path.

    Args:
        value (object): A value to match.
        data_type (int): One of :attr:`~bookmarks.common.FileItem` or :attr:`~bookmarks.common.SequenceItem`.
        role (int): The role to match.
        get_container (bool): Return the container weakref if True, otherwise the data item that was found.

    Returns:
        common.DataDict: The cached data or None if not found.

    """
    for key in common.item_data:
        for task in common.item_data[key]:
            if data_type not in common.item_data[key][task]:
                return None
            data = common.item_data[key][task][data_type]
            for idx in data:
                if value == data[idx][role]:
                    if get_container:
                        return data
                    else:
                        return data[idx]
                elif value in data[idx][role]:
                    if get_container:
                        return data
                    else:
                        return data[idx]
    return None


def get_task_data(key, task):
    """Get cached data from :attr:`~bookmarks.common.item_data`.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.

    Returns:
        common.DataDict: The cached data.

    """
    if key not in common.item_data:
        reset_data(key, task)
    elif task not in common.item_data[key]:
        reset_data(key, task)
    return common.item_data[key][task]


def data_count(key, task, data_type):
    """Number of items in the data dictionary.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.
        data_type (int): One of :attr:`~bookmarks.common.FileItem` or :attr:`~bookmarks.common.SequenceItem`.

    Returns:
        int: The number of items in the data dictionary.

    """
    d = get_data(key, task, data_type)
    return len(d)


def is_data_loaded(key, task, data_type):
    """Checks if the cached is completely loaded.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.
        data_type (int): One of :attr:`~bookmarks.common.FileItem` or :attr:`~bookmarks.common.SequenceItem`.

    Returns:
        bool:   True if loaded, false otherwise.

    """
    d = get_data(key, task, data_type)
    if d and d.loaded:
        return True
    return False


def get_data_ref(key, task, data_type):
    """Get a data pointer from :attr:`bookmarks.common.item_data` cache.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.
        data_type (int):
            One of :attr:`bookmarks.common.FileItem` or
            :attr:`bookmarks.common.SequenceItem`.

    Returns:
        weakref.ref: Pointer to the requested data set.

    """
    if not key or not task:
        return None

    return weakref.ref(
        get_data(key, task, data_type)
    )


def get_ref_from_source_index(index):
    """Get a weakref pointer from source item model index.

    """
    if not index.isValid():
        return
    if not hasattr(index.model(), 'mapFromSource'):
        return None

    model = index.model()
    data = model.sourceModel().model_data()
    idx = model.mapToSource(index).row()
    return weakref.ref(data[idx])


def reset_data(key, task):
    """Delete the requested data from the cache.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.

    """
    if key not in common.item_data:
        common.item_data[key] = common.DataDict()
    common.item_data[key][task] = common.DataDict()
    for t in (common.FileItem, common.SequenceItem):
        common.item_data[key][task][t] = common.DataDict()
        common.item_data[key][task][t].data_type = t


def set_data(key, task, data_type, data):
    """Set data to :attr:`bookmarks.common.item_data`.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.
        data_type (int): One of :attr:`bookmarks.common.FileItem` or :attr:`bookmarks.common.SequenceItem`.
        data (common.DataDict): The data to set in the cache.

    Returns:
        common.DataDict: The cached data.

    """
    if key not in common.item_data:
        reset_data(key, task)
    elif task not in common.item_data[key]:
        reset_data(key, task)
    common.item_data[key][task][data_type] = data

    return common.item_data[key][task][data_type]
