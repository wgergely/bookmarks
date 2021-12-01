"""Used to store all file item data loaded by models across our app.

"""
import weakref
from PySide2 import QtCore

from . import common



def sort_data(ref, sortrole, sortorder):
    common.check_type(ref, weakref.ref)
    common.check_type(sortrole, QtCore.Qt.ItemDataRole)
    common.check_type(sortorder, bool)

    def sort_key(idx):
        # If sort_by_basename is `True` we'll use the base file name for sorting
        v = ref().__getitem__(idx)
        if common.sort_by_basename and sortrole == common.SortByNameRole and isinstance(v[sortrole], list):
            return v[sortrole][-1]
        return v[sortrole]

    sorted_idxs = sorted(
        ref().keys(),
        key=sort_key,
        reverse=sortorder
    )

    d = common.DataDict()
    d.loaded = ref().loaded
    d.data_type = ref().data_type

    for n, idx in enumerate(sorted_idxs):
        if not ref():
            raise RuntimeError('Model mutated during sorting.')
        ref()[idx][common.IdRole] = n
        d[n] = ref()[idx]
    return d


def get_data(key, task, data_type):
    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    if key not in common.itemdata:
        reset_data(key, task)
    elif task not in common.itemdata[key]:
        reset_data(key, task)
    elif data_type not in common.itemdata[key][task]:
        reset_data(key, task)
    return common.itemdata[key][task][data_type]


def get_task_data(key, task):
    common.check_type(key, tuple)
    common.check_type(task, str)

    if key not in common.itemdata:
        reset_data(key, task)
    elif task not in common.itemdata[key]:
        reset_data(key, task)
    return common.itemdata[key][task]


def data_count(key, task, data_type):
    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    d = get_data(key, task, data_type)
    return len(d)


def is_data_loaded(key, task, data_type):
    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    d = get_data(key, task, data_type)
    if d and d.loaded:
        return True
    return False


def get_data_ref(key, task, data_type):
    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    return weakref.ref(
        get_data(key, task, data_type)
    )


def reset_data(key, task):
    common.check_type(key, tuple)
    common.check_type(task, str)

    if key not in common.itemdata:
        common.itemdata[key] = common.DataDict()
    common.itemdata[key][task] = common.DataDict()
    for t in (common.FileItem, common.SequenceItem):
        common.itemdata[key][task][t] = common.DataDict()
        common.itemdata[key][task][t].data_type = t


def set_data(key, task, data_type, data):
    common.check_type(key, tuple)
    common.check_type(task, str)
    common.check_type(data_type, int)

    if key not in common.itemdata:
        reset_data(key, task)
    elif task not in common.itemdata[key]:
        reset_data(key, task)
    common.itemdata[key][task][data_type] = data
