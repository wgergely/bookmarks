"""Used to store all file item data loaded by models accross our app.

"""
import weakref
from . import common


DATA = common.DataDict()


def get_data(parent_path, task, data_type):
    if parent_path not in DATA:
        reset_data(parent_path, task)
    elif task not in DATA[parent_path]:
        reset_data(parent_path, task)
    elif data_type not in DATA[parent_path][task]:
        reset_data(parent_path, task)
    return DATA[parent_path][task][data_type]


def get_task_data(parent_path, task):
    if parent_path not in DATA:
        reset_data(parent_path, task)
    elif task not in DATA[parent_path]:
        reset_data(parent_path, task)
    return DATA[parent_path][task]


def count(parent_path, task, data_type):
    d = get_data(parent_path, task, data_type)
    return len(d)


def is_loaded(parent_path, task, data_type):
    d = get_data(parent_path, task, data_type)
    if d and d.loaded:
        return True
    return False


def get_data_ref(parent_path, task, data_type):
    return weakref.ref(
        get_data(parent_path, task, data_type)
    )


def reset_data(parent_path, task):
    if parent_path not in DATA:
        DATA[parent_path] = common.DataDict()
    DATA[parent_path][task] = common.DataDict()
    for t in (common.FileItem, common.SequenceItem):
        DATA[parent_path][task][t] = common.DataDict()
        DATA[parent_path][task][t].data_type = t


def set_data(parent_path, task, data_type, data):
    if parent_path not in DATA:
        reset_data(parent_path, task)
    elif task not in DATA[parent_path]:
        reset_data(parent_path, task)
    DATA[parent_path][task][data_type] = data
