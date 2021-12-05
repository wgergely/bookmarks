"""Interface to interact with the item data cache.

All data loaded by the item models are stored in :attr:`bookmarks.common.item_data`.
The module provides methods for the models to access, load and reset the cached data.

"""
import weakref

from PySide2 import QtCore

from . import common


def sort_data(ref, sort_role, sort_order):
    """Sort the given data using `sort_role` and `sort_order`.

    Args:
        ref (weakref.ref): Pointer to a :class:`bookmarks.common.core.DataDict` instance.
        sort_role (int): The role to use to sort the data.
        sort_order (bool):  The sort order.

    Returns:
        common.DataDict: A sorted copy of the source data.

    """
    common.check_type(ref, weakref.ref)
    common.check_type(sort_role, (int, QtCore.Qt.ItemDataRole))
    common.check_type(sort_order, bool)

    def sort_key(_idx):
        # If sort_by_basename is `True` we'll use the base file name for sorting
        v = ref().__getitem__(_idx)
        if common.sort_by_basename and sort_role == common.SortByNameRole and isinstance(v[sort_role], list):
            return v[sort_role][-1]
        return v[sort_role]

    sorted_idxs = sorted(
        ref().keys(),
        key=sort_key,
        reverse=sort_order
    )

    d = common.DataDict()
    d.loaded = ref().loaded
    d.data_type = ref().data_type

    for n, idx in enumerate(sorted_idxs):
        if not ref():
            raise RuntimeError('Model mutated during sorting.')
        ref()[n][common.IdRole] = idx
        d[n] = ref()[idx]
    return d


def get_data(key, task, data_type):
    """Get a cached data dict from :attr:`bookmarks.common.item_data`.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.
        data_type (int): One of :attr:`bookmarks.common.FileItem` or :attr:`bookmarks.common.SequenceItem`.

    Returns:
        common.DataDict: The cached data.

    """
    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    if key not in common.item_data:
        reset_data(key, task)
    elif task not in common.item_data[key]:
        reset_data(key, task)
    elif data_type not in common.item_data[key][task]:
        reset_data(key, task)
    return common.item_data[key][task][data_type]


def get_task_data(key, task):
    """Get cached data from :attr:`bookmarks.common.item_data`.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.

    Returns:
        common.DataDict:    The cached data.

    """
    common.check_type(key, tuple)
    common.check_type(task, str)

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
        data_type (int): One of :attr:`bookmarks.common.FileItem` or :attr:`bookmarks.common.SequenceItem`.

    Returns:
        int: The number of items in the data dictionary.

    """
    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    d = get_data(key, task, data_type)
    return len(d)


def is_data_loaded(key, task, data_type):
    """Checks if the cached is completely loaded.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.
        data_type (int): One of :attr:`bookmarks.common.FileItem` or :attr:`bookmarks.common.SequenceItem`.

    Returns:
        bool:   True if loaded, false otherwise.

    """
    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    d = get_data(key, task, data_type)
    if d and d.loaded:
        return True
    return False


def get_data_ref(key, task, data_type):
    """Get a data pointer from :attr:`bookmarks.common.item_data`.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.
        data_type (int): One of :attr:`bookmarks.common.FileItem` or :attr:`bookmarks.common.SequenceItem`.

    Returns:
        weakref.ref: Pointer to the requested data set.

    """
    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    return weakref.ref(
        get_data(key, task, data_type)
    )


def reset_data(key, task):
    """Delete the requested data from the cache.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.

    """
    common.check_type(key, tuple)
    common.check_type(task, str)

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

    """
    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    if key not in common.item_data:
        reset_data(key, task)
    elif task not in common.item_data[key]:
        reset_data(key, task)
    common.item_data[key][task][data_type] = data
