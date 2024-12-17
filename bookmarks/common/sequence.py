"""Common methods to work with sequentially numbered file items.

A sequence item is a file that has a numerical component that can be incremented.
For example:

.. code-block:: python
    :linenos:

    s = 'C:/test/my_image_sequence_0001.png'
    seq = get_sequence(s)

A *collapsed item* is a single path that actually represents a series of
sequence items and is marked by :attr:`SEQSTART`, a sequence range, and
:attr:`SEQEND`. For example:

.. code-block:: python
    :linenos:

    s = 'C:/test/my_image_sequence_{1-200}.png'
    is_collapsed(s) # True

This module provides helper functions to determine if a path is a collapsed
sequence, extract its first or last file, generate a proxy path for caching and
preference storage, and retrieve all paths from a collapsed sequence.

All functions perform input validation and raise appropriate exceptions for
invalid inputs.

"""
import functools
import re
import weakref

from PySide2 import QtCore
from . import common

__all__ = [
    'SEQSTART',
    'SEQEND',
    'SEQPROXY',
    'is_collapsed',
    'get_sequence',
    'proxy_path',
    'get_sequence_start_path',
    'get_sequence_end_path',
    'get_sequence_paths'
]

#: Start character used to encapsulate the sequence range of collapsed items.
SEQSTART = '<<'

#: End character used to encapsulate the sequence range of collapsed items.
SEQEND = '>>'

#: Placeholder sequence marker used to associate settings and database values
#: with sequence items.
SEQPROXY = f'{SEQSTART}?{SEQEND}'

#: Regular expression used to find sequence items.
IsSequenceRegex = re.compile(
    rf'^(.+?){re.escape(SEQSTART)}(\d+\-\d+){re.escape(SEQEND)}(.*)$',
    flags=re.IGNORECASE
)

#: Regular expression used to get the first frame of a collapsed sequence.
SequenceStartRegex = re.compile(
    rf'^(.*){SEQSTART}(\d+).*{SEQEND}(.*)$',
    flags=re.IGNORECASE
)

#: Regular expression used to get the last frame of a collapsed sequence.
SequenceEndRegex = re.compile(
    rf'^(.*){SEQSTART}.*?(\d+){SEQEND}(.*)$',
    flags=re.IGNORECASE
)

#: Regular expression used to get the path components of a non-collapsed sequence.
GetSequenceRegex = re.compile(
    r'^(.*?)(\d+)([\d\\/]*|[^\d\\/]*(?=.+?))\.([A-Za-z][^\.]*)$',
    flags=re.IGNORECASE
)


@functools.lru_cache(maxsize=4194304)
def is_collapsed(s):
    """Check if the given path is a collapsed sequence.

    A collapsed item contains :attr:`SEQSTART` and :attr:`SEQEND` markers.
    For example, 'my_image_sequence_{001-200}.exr' is a collapsed sequence.

    Args:
        s (str): A file path.

    Raises:
        TypeError: If `s` is not a string.

    Returns:
        re.Match or None:
            If a match is found, returns the regex match object. Groups:
            * group(1) - Characters before the sequence marker.
            * group(2) - The sequence marker (e.g. '{001-200}').
            * group(3) - Characters after the sequence marker.
            Otherwise returns None.
    """
    if not isinstance(s, str):
        raise TypeError("is_collapsed expects a string path.")
    return IsSequenceRegex.search(s)


@functools.lru_cache(maxsize=4194304)
def get_sequence(s):
    """Check if the given path contains a sequence number component.

    A sequence is identified by a numerical component. Only one incremental
    element is considered the sequence number. For collapsed sequences, this
    function raises an error.

    Args:
        s (str): A file path.

    Raises:
        TypeError: If `s` is not a string.
        RuntimeError: If `s` is a collapsed sequence.

    Returns:
        re.Match or None:
            If a match is found, returns the regex match object. Groups:
            * group(1) - Characters before the sequence number.
            * group(2) - The sequence number (as a string).
            * group(3) - Characters after the sequence number, before extension.
            * group(4) - The file extension without '.'.
            Otherwise returns None.
    """
    if not isinstance(s, str):
        raise TypeError("get_sequence expects a string path.")
    if is_collapsed(s):
        raise RuntimeError('Cannot extract sequence numbers from collapsed items.')
    return GetSequenceRegex.search(s)


def proxy_path(v):
    """Generate a proxy path to represent sequences or collapsed items consistently.

    For collapsed sequences, replaces the collapsed notation with :attr:`SEQPROXY`.
    For non-collapsed sequences, replaces the sequence number with :attr:`SEQPROXY`.
    Non-sequence items are returned as-is (only backslashes are replaced).

    Args:
        v (QModelIndex, weakref.ref, dict, str): Item representing a path.

    Raises:
        TypeError: If `v` is not an expected type or does not provide a valid path string.

    Returns:
        str: A proxy path string suitable for caching and preferences.
    """
    if isinstance(v, (QtCore.QModelIndex, QtCore.QPersistentModelIndex)):
        path_str = v.data(common.PathRole)
        if not isinstance(path_str, str):
            raise TypeError("Invalid path data from model index.")
        v = path_str
    elif isinstance(v, weakref.ref):
        ref_val = v()
        if not ref_val or common.PathRole not in ref_val:
            raise TypeError("Invalid weakref or missing PathRole in referenced object.")
        v = ref_val[common.PathRole]
    elif isinstance(v, dict):
        if common.PathRole not in v or not isinstance(v[common.PathRole], str):
            raise TypeError("Dictionary must contain a valid string PathRole.")
        v = v[common.PathRole]
    elif not isinstance(v, str):
        raise TypeError("proxy_path expects a string, dict, QModelIndex, or weakref.ref.")
    return _proxy_path(v)


@functools.lru_cache(maxsize=4194304)
def _proxy_path(v):
    """Internal helper for proxy_path."""
    collapsed = is_collapsed(v)
    if collapsed:
        return f"{collapsed.group(1)}{SEQPROXY}{collapsed.group(3)}".replace('\\', '/')

    seq = get_sequence(v)
    if seq:
        return f"{seq.group(1)}{SEQPROXY}{seq.group(3)}.{seq.group(4)}".replace('\\', '/')

    return v.replace('\\', '/')


@functools.lru_cache(maxsize=4194304)
def get_sequence_start_path(path):
    """Get the first file path in a collapsed sequence.

    If the given path is not collapsed, returns it unchanged.
    If it is collapsed, returns the path with the first frame.

    Args:
        path (str): A path string.

    Raises:
        TypeError: If `path` is not a string.

    Returns:
        str: The first file in the sequence.
    """
    if not isinstance(path, str):
        raise TypeError("get_sequence_start_path expects a string.")
    if not is_collapsed(path):
        return path
    match = SequenceStartRegex.search(path)
    if match:
        path = SequenceStartRegex.sub(r'\1\2\3', path)
    return path


@functools.lru_cache(maxsize=4194304)
def get_sequence_end_path(path):
    """Get the last file path in a collapsed sequence.

    If the given path is not collapsed, returns it unchanged.
    If it is collapsed, returns the path with the last frame.

    Args:
        path (str): A path string.

    Raises:
        TypeError: If `path` is not a string.

    Returns:
        str: The last file in the sequence.
    """
    if not isinstance(path, str):
        raise TypeError("get_sequence_end_path expects a string.")
    if not is_collapsed(path):
        return path
    match = SequenceEndRegex.search(path)
    if match:
        path = SequenceEndRegex.sub(r'\1\2\3', path)
    return path


def get_sequence_paths(index):
    """Return a list of file paths representing each file in a collapsed sequence.

    If the item is not collapsed, returns a single-element list.

    Args:
        index (QtCore.QModelIndex): Model index representing the item.

    Raises:
        TypeError: If `index` is not a `QtCore.QModelIndex` or `QtCore.QPersistentModelIndex`.
        ValueError: If sequence or frames data is missing or invalid.

    Returns:
        list: A list of file paths for each frame in the sequence.
    """
    if not isinstance(index, (QtCore.QModelIndex, QtCore.QPersistentModelIndex)):
        raise TypeError("get_sequence_paths expects a QModelIndex or QPersistentModelIndex.")

    path = index.data(common.PathRole)
    if not isinstance(path, str):
        raise ValueError("Invalid path data from index.")

    if not is_collapsed(path):
        return [path]

    seq = index.data(common.SequenceRole)
    frames = index.data(common.FramesRole)

    if not seq or not hasattr(seq, 'group') or not frames or not isinstance(frames, list):
        raise ValueError("Sequence or frames data is missing or invalid.")

    v = []
    for frame in frames:
        if not isinstance(frame, str):
            raise ValueError("Frame values must be strings.")
        v.append(f'{seq.group(1)}{frame}{seq.group(3)}.{seq.group(4)}')
    return v
