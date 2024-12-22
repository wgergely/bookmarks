"""Interface to interact with the item data cache.

All data loaded by the item models are stored in :attr:`~bookmarks.common.item_data`.
The module provides methods for the models to access, load and reset the cached data.
"""

import weakref

from PySide2 import QtCore

from . import common

lock = QtCore.QReadWriteLock()


class DataDict(dict):
    """Custom dictionary class used to store model item data.

    This class adds compatibility for :class:`weakref.ref` referencing
    and custom attributes for storing data states.
    """

    def __str__(self) -> str:
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
    def loaded(self) -> bool:
        return self._loaded

    @loaded.setter
    def loaded(self, v: bool):
        self._loaded = v

    @property
    def refresh_needed(self) -> bool:
        return self._refresh_needed

    @refresh_needed.setter
    def refresh_needed(self, v: bool):
        self._refresh_needed = v

    @property
    def data_type(self):
        return self._data_type

    @data_type.setter
    def data_type(self, v):
        self._data_type = v

    @property
    def servers(self):
        role = common.ParentPathRole
        return [v[role][0] for v in self.values() if v.get(role) and len(v[role]) > 1]

    @property
    def jobs(self):
        role = common.ParentPathRole
        return [v[role][1] for v in self.values() if v.get(role) and len(v[role]) > 2]

    @property
    def roots(self):
        role = common.ParentPathRole
        return [v[role][2] for v in self.values() if v.get(role) and len(v[role]) > 3]

    @property
    def assets(self):
        role = common.ParentPathRole
        return [v[role][3] for v in self.values() if v.get(role) and len(v[role]) > 4]

    @property
    def tasks_folders(self):
        role = common.ParentPathRole
        return [v[role][4] for v in self.values() if v.get(role) and len(v[role]) > 5]

    @property
    def relative_folders(self):
        role = common.ParentPathRole

        def func(val: dict):
            pp = val.get(role)
            if not pp:
                return []
            _path = '/'.join(pp)
            path = val.get(common.PathRole, '')
            if not path:
                return []
            rel_path = path.replace(_path, '').rstrip('/')
            return rel_path.split('/') if rel_path else []

        unique_folders = {f for v in self.values() for f in func(v) if f}
        return list(unique_folders)

    @property
    def file_types(self):
        def func(val: dict):
            path = val.get(common.PathRole, '')
            if '.' not in path.split('/')[-1]:
                return ''
            return path.split('.')[-1].lstrip('.')

        unique_types = {f for v in self.values() for f in [func(v)] if f}
        return list(unique_types)


def _reset_data_no_lock(key):
    """Reset data for the given key without acquiring any lock."""
    if key not in common.item_data:
        common.item_data[key] = DataDict()
    for t in (common.FileItem, common.SequenceItem):
        common.item_data[key][t] = DataDict()
        common.item_data[key][t].data_type = t


def _ensure_data_exists_no_lock(key, data_type):
    """Ensure the requested data structure exists in common.item_data without locking."""
    if key not in common.item_data:
        _reset_data_no_lock(key)
    elif data_type not in common.item_data[key]:
        _reset_data_no_lock(key)


def _get_data_no_lock(key, data_type):
    _ensure_data_exists_no_lock(key, data_type)
    return common.item_data[key][data_type]


def _get_data_from_value_no_lock(value, data_type, role, get_container):
    for _, type_dict in common.item_data.items():
        data = type_dict.get(data_type)
        if data is None:
            continue
        for _, item in data.items():
            r = item.get(role)
            if r == value or (isinstance(r, list) and value in r):
                return data if get_container else item
    return None


def _set_data_no_lock(key, data_type, data):
    _ensure_data_exists_no_lock(key, data_type)
    common.item_data[key][data_type] = data
    return common.item_data[key][data_type]


# ---------------------- Public API Functions (With Locking) ----------------------

def sort_data(ref, sort_by, sort_order):
    """Sort the given data using `sort_by` and `sort_order`."""
    lock.lockForRead()
    try:
        data = ref()
        if data is None:
            raise RuntimeError('Data reference is no longer valid.')

        def sort_key(_idx):
            item = data.get(_idx)
            if item is None:
                return None
            return item[sort_by]

        sorted_idxs = sorted(data.keys(), key=sort_key, reverse=sort_order)

        d = DataDict()
        d.loaded = data.loaded
        d.data_type = data.data_type
        d.refresh_needed = data.refresh_needed

        for n, idx in enumerate(sorted_idxs):
            current_data = ref()
            if current_data is None:
                raise RuntimeError('Data mutated or destroyed during sorting.')
            d[n] = current_data[idx]
            d[n][common.IdRole] = n

        return d
    finally:
        lock.unlock()


def get_data(key, data_type):
    lock.lockForWrite()
    try:
        return _get_data_no_lock(key, data_type)
    finally:
        lock.unlock()


def get_data_from_value(value, data_type, role=common.PathRole, get_container=True):
    lock.lockForRead()
    try:
        return _get_data_from_value_no_lock(value, data_type, role, get_container)
    finally:
        lock.unlock()


def data_count(key, data_type):
    lock.lockForWrite()
    try:
        d = _get_data_no_lock(key, data_type)
        return len(d)
    finally:
        lock.unlock()


def is_data_loaded(key, data_type):
    lock.lockForWrite()
    try:
        d = _get_data_no_lock(key, data_type)
        return bool(d and d.loaded)
    finally:
        lock.unlock()


def get_data_ref(key, data_type):
    lock.lockForWrite()
    try:
        if not key:
            return None
        d = _get_data_no_lock(key, data_type)
        return weakref.ref(d)
    finally:
        lock.unlock()


def get_ref_from_source_index(index):
    """Return a weakref to the data at the model index, if available."""
    if not index.isValid():
        return None
    if not hasattr(index.model(), 'mapFromSource'):
        return None

    model = index.model()
    source_model = model.sourceModel()
    if not hasattr(source_model, 'model_data'):
        return None

    data = source_model.model_data()
    idx = model.mapToSource(index).row()

    if 0 <= idx < len(data):
        return weakref.ref(data[idx])
    return None


def reset_data(key):
    lock.lockForWrite()
    try:
        _reset_data_no_lock(key)
    finally:
        lock.unlock()


def set_data(key, data_type, data):
    lock.lockForWrite()
    try:
        return _set_data_no_lock(key, data_type, data)
    finally:
        lock.unlock()
