"""Used to store all file item data loaded by models across our app.

"""
import weakref
from . import common


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


def is_loaded(key, task, data_type):
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
