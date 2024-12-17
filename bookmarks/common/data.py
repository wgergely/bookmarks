"""Interface to interact with the item data cache.

All data loaded by the item models are stored in :attr:`~bookmarks.common.item_data`.
The module provides methods for the models to access, load and reset the cached data.
"""

import weakref
from typing import Tuple, Optional, Any, List, Union

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
    def data_type(self) -> Optional[int]:
        return self._data_type

    @data_type.setter
    def data_type(self, v: int):
        self._data_type = v

    @property
    def servers(self) -> List[str]:
        role = common.ParentPathRole
        return [v[role][0] for v in self.values() if v.get(role) and len(v[role]) > 1]

    @property
    def jobs(self) -> List[str]:
        role = common.ParentPathRole
        return [v[role][1] for v in self.values() if v.get(role) and len(v[role]) > 2]

    @property
    def roots(self) -> List[str]:
        role = common.ParentPathRole
        return [v[role][2] for v in self.values() if v.get(role) and len(v[role]) > 3]

    @property
    def assets(self) -> List[str]:
        role = common.ParentPathRole
        return [v[role][3] for v in self.values() if v.get(role) and len(v[role]) > 4]

    @property
    def tasks_folders(self) -> List[str]:
        role = common.ParentPathRole
        return [v[role][4] for v in self.values() if v.get(role) and len(v[role]) > 5]

    @property
    def relative_folders(self) -> List[str]:
        role = common.ParentPathRole

        def func(val: dict) -> List[str]:
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
    def file_types(self) -> List[str]:
        def func(val: dict) -> str:
            path = val.get(common.PathRole, '')
            if '.' not in path.split('/')[-1]:
                return ''
            return path.split('.')[-1].lstrip('.')

        unique_types = {f for v in self.values() for f in [func(v)] if f}
        return list(unique_types)


# ---------------------- Internal Helper Functions (No Locking) ----------------------

def _reset_data_no_lock(key: Tuple[str, ...], task: str) -> None:
    """Internal helper: resets data without acquiring any lock."""
    if key not in common.item_data:
        common.item_data[key] = DataDict()
    common.item_data[key][task] = DataDict()
    for t in (common.FileItem, common.SequenceItem):
        common.item_data[key][task][t] = DataDict()
        common.item_data[key][task][t].data_type = t


def _ensure_data_exists_no_lock(key: Tuple[str, ...], task: str, data_type: int) -> None:
    """Ensure the requested data structure exists in common.item_data without locking."""
    if key not in common.item_data:
        _reset_data_no_lock(key, task)
    elif task not in common.item_data[key]:
        _reset_data_no_lock(key, task)
    elif data_type not in common.item_data[key][task]:
        _reset_data_no_lock(key, task)


def _get_data_no_lock(key: Tuple[str, ...], task: str, data_type: int) -> DataDict:
    _ensure_data_exists_no_lock(key, task, data_type)
    return common.item_data[key][task][data_type]


def _get_task_data_no_lock(key: Tuple[str, ...], task: str) -> DataDict:
    if key not in common.item_data:
        _reset_data_no_lock(key, task)
    elif task not in common.item_data[key]:
        _reset_data_no_lock(key, task)
    return common.item_data[key][task]


def _get_data_from_value_no_lock(value: Any, data_type: int, role: int, get_container: bool) -> Optional[
    Union[DataDict, dict]]:
    for key, tasks_dict in common.item_data.items():
        for task, types_dict in tasks_dict.items():
            data = types_dict.get(data_type)
            if data is None:
                continue
            for idx, item in data.items():
                r = item.get(role)
                if r == value or (isinstance(r, list) and value in r):
                    if get_container:
                        return data
                    else:
                        return item
    return None


def _set_data_no_lock(key: Tuple[str, ...], task: str, data_type: int, data: DataDict) -> DataDict:
    _ensure_data_exists_no_lock(key, task, data_type)
    common.item_data[key][task][data_type] = data
    return common.item_data[key][task][data_type]


# ---------------------- Public API Functions (With Locking) ----------------------

def sort_data(ref: weakref.ref, sort_by: int, sort_order: bool) -> DataDict:
    """Sort the given data using `sort_by` and `sort_order`."""
    lock.lockForRead()
    try:
        data = ref()
        if data is None:
            raise RuntimeError('Data reference is no longer valid.')

        def sort_key(_idx: Any) -> Any:
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


def get_data(key: Tuple[str, ...], task: str, data_type: int) -> DataDict:
    lock.lockForWrite()
    try:
        return _get_data_no_lock(key, task, data_type)
    finally:
        lock.unlock()


def get_data_from_value(value: Any, data_type: int, role: int = common.PathRole, get_container: bool = True) -> \
        Optional[Union[DataDict, dict]]:
    lock.lockForRead()
    try:
        return _get_data_from_value_no_lock(value, data_type, role, get_container)
    finally:
        lock.unlock()


def get_task_data(key: Tuple[str, ...], task: str) -> DataDict:
    lock.lockForWrite()
    try:
        return _get_task_data_no_lock(key, task)
    finally:
        lock.unlock()


def data_count(key: Tuple[str, ...], task: str, data_type: int) -> int:
    lock.lockForWrite()
    try:
        d = _get_data_no_lock(key, task, data_type)
        return len(d)
    finally:
        lock.unlock()


def is_data_loaded(key: Tuple[str, ...], task: str, data_type: int) -> bool:
    lock.lockForWrite()
    try:
        d = _get_data_no_lock(key, task, data_type)
        return bool(d and d.loaded)
    finally:
        lock.unlock()


def get_data_ref(key: Tuple[str, ...], task: str, data_type: int) -> Optional[weakref.ref]:
    lock.lockForWrite()
    try:
        if not key or not task:
            return None
        d = _get_data_no_lock(key, task, data_type)
        return weakref.ref(d)
    finally:
        lock.unlock()


def get_ref_from_source_index(index) -> Optional[weakref.ref]:
    # This function does not read or write from item_data; no lock needed.
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


def reset_data(key: Tuple[str, ...], task: str) -> None:
    lock.lockForWrite()
    try:
        _reset_data_no_lock(key, task)
    finally:
        lock.unlock()


def set_data(key: Tuple[str, ...], task: str, data_type: int, data: DataDict) -> DataDict:
    lock.lockForWrite()
    try:
        return _set_data_no_lock(key, task, data_type, data)
    finally:
        lock.unlock()
