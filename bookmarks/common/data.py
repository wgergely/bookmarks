"""Interface to interact with the item data cache.

All data loaded by the item models are stored in :attr:`~bookmarks.common.item_data`.
The module provides methods for the models to access, load and reset the cached data.

"""
import weakref

from PySide2 import QtCore

from . import common


def sort_data(ref, sort_by, sort_order):
    """Sort the given data using `sort_by` and `sort_order`.

    Args:
        ref (weakref.ref): Pointer to a :class:`~bookmarks.common.core.DataDict` instance.
        sort_by (int): The role to use to sort the data.
        sort_order (bool): The sort order.

    Returns:
        common.DataDict: A sorted copy of the source data.

    """
    common.check_type(ref, weakref.ref)
    common.check_type(sort_by, (int, QtCore.Qt.ItemDataRole))
    common.check_type(sort_order, bool)

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
    d.shotgun_names = ref().shotgun_names
    d.sg_task_names = ref().sg_task_names
    d.file_types = ref().file_types
    d.subdirectories = ref().subdirectories
    d.servers = ref().servers
    d.jobs = ref().jobs
    d.roots = ref().roots

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


def get_data_from_value(value, data_type, role=common.PathRole):
    """Get the internal data dictionary associated with a path.

    Args:
        value (object): A value to match.
        data_type (int): One of :attr:`~bookmarks.common.FileItem` or :attr:`~bookmarks.common.SequenceItem`.

    Returns:
        common.DataDict: The cached data or None if not found.

    """
    for key in common.item_data:
        for task in common.item_data[key]:
            if data_type not in common.item_data[key][task]:
                return None
            data = common.item_data[key][task][data_type]
            for idx in data:
                if value in data[idx][role]:
                    return data
    return None

def get_task_data(key, task):
    """Get cached data from :attr:`~bookmarks.common.item_data`.

    Args:
        key (tuple): A tuple of path segments.
        task (str): A task folder.

    Returns:
        common.DataDict: The cached data.

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
        data_type (int): One of :attr:`~bookmarks.common.FileItem` or :attr:`~bookmarks.common.SequenceItem`.

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
        data_type (int): One of :attr:`~bookmarks.common.FileItem` or :attr:`~bookmarks.common.SequenceItem`.

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

    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    return weakref.ref(
        get_data(key, task, data_type)
    )


def get_ref_from_source_index(index):
    """Get a weakref pointer from source item model index.

    """
    if not index.isValid():
        return
    if not hasattr(index.model(), 'sourceModel'):
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
    common.item_data[key][task][data_type] = data

    return common.item_data[key][task][data_type]
