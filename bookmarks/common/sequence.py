# -*- coding: utf-8 -*-
"""Common methods used to work with sequentially numbered file items.

A sequence item is a file that has a number component that can be incremented. See
:func:`get_sequence`. E.g.:

.. code-block:: python

    s = 'C:/test/my_image_sequence_0001.png'
    seq = common.get_sequence(s)


A collapsed item is a single item that refers to a series of sequence items
and is marked by the :attr:`.SEQSTART`, sequence range and :attr:`.SEQEND` characters. See
:func:`is_collapsed`. E.g.:

.. code-block:: python

    s = 'C:/test/my_image_sequence_{1-200}.png'
    common.is_collapsed(s) # = True

"""
import functools
import re
import weakref

from PySide2 import QtCore

from .. import common

#: Start character used to encapsulate the sequence range of collapsed items.
SEQSTART = '{'

#: End character used to encapsulate the sequence range of collapsed items.
SEQEND = '}'

#: Placeholder sequence marker used to associate settings and database values
#: with sequence items.
SEQPROXY = f'{SEQSTART}0{SEQEND}'

#: Regular expression used to find sequence items
IsSequenceRegex = re.compile(
    rf'^(.+?)({SEQSTART}.*{SEQEND})(.*)$',
    flags=re.IGNORECASE
)

#: Regular expression used to get the first frame of a collapsed sequence
SequenceStartRegex = re.compile(
    rf'^(.*){SEQSTART}([0-9]+).*{SEQEND}(.*)$',
    flags=re.IGNORECASE
)

#: Regular expression used to get the last frame of a collapsed sequence
SequenceEndRegex = re.compile(
    rf'^(.*){SEQSTART}.*?([0-9]+){SEQEND}(.*)$',
    flags=re.IGNORECASE
)

#: Regular expression used to get the path components of a collapsed sequence
GetSequenceRegex = re.compile(
    r'^(.*?)([0-9]+)([0-9\\/]*|[^0-9\\/]*(?=.+?))\.([^\.]+)$',
    flags=re.IGNORECASE
)

@functools.lru_cache(maxsize=4194304)
def is_collapsed(s):
    """Checks the presence :attr:`SEQSTART` and :attr:`SEQEND` markers.

    When Bookmarks is displaying a sequence of files as a single item, the item is
    *collapsed*. Every collapsed item contains the :attr:`SEQEND`, sequence range and
    :attr:`SEQSTART` elements.

    Example:

        .. code-block:: python
            :lineno:

            filename = 'job_sh010_animation_{001-299}_gw.png'
            m = is_collapsed(filename)
            prefix = match.group(1) # = 'job_sh010_animation_'
            sequence_string = match.group(2) # = '{001-299}'
            suffix = match.group(3) # = '_gw.png'

    Args:
        s (str): A file path.

    Returns:
        SRE_Match:
            * group(1) - All the characters **before** the sequence marker.
            * group(2) - The sequence marker, e.g. ``{01-50}``.
            * group(3) - All characters **after** the sequence marker.

    """
    common.check_type(s, str)
    return IsSequenceRegex.search(s)


@functools.lru_cache(maxsize=4194304)
def get_sequence(s):
    """Checks if the given text contains a sequence element.

    Strictly speaking, a sequence is any file that has a valid number element.
    There can only be **one** incremental element - it will always be the
    number closest to the end.

    The regex will understand sequences with the `v` prefix, eg *v001*, *v002*,
    but works without the prefix as well. E.g. **001**, **002**. In the case of a
    filename like ``job_sh010_animation_v002.c4d`` **002** will be the
    prevailing sequence number, ignoring the number in the extension.

    Likewise, in ``job_sh010_animation_v002.0001.c4d`` the sequence number will
    be **0001**, and not 010 or 002.

    Args:
            s (str): A file path.

    Returns:
            group 1 (SRE_Match):    All the characters **before** the sequence number.
            group 2 (SRE_Match):    The sequence number, as a string.
            group 3 (SRE_Match):    All the characters **after** the sequence number up until the file extensions.
            group 4 (SRE_Match):    The file extension **without** the '.' dot.

    .. code-block:: python

       s = 'job_sh010_animation_v002_wgergely.c4d'
       m = get_sequence(s)
       if m:
               prefix = match.group(1)
               sequence_number = match.group(2)
               suffix = match.group(3)
               extension = match.group(4)

    Returns:
            ``SRE_Match``: ``None`` if the text doesn't contain a number or an ``SRE_Match`` object.

    """
    common.check_type(s, str)
    if is_collapsed(s):
        raise RuntimeError(
            'Cannot extract sequence numbers from collapsed items.')
    return GetSequenceRegex.search(s)


def proxy_path(v):
    """Encompasses the logic used to associate preferences with items.

    Sequence items need a generic key to save values as the sequence notation
    might change as files are added/removed to image sequences. Any `FileItem`
    will use their file path as the key and SequenceItems will use `[0]` in place
    of their frame-range notation.

    Args:
            v (QModelIndex, weakref.ref, dict or str): Data dict, index or filepath string.

    Returns:
            str: The key used to store the item's information in the local
            preferences and the bookmark item database.

    """
    if isinstance(v, str):
        pass
    elif isinstance(v, weakref.ref):
        v = v()[common.PathRole]
    elif isinstance(v, dict):
        v = v[common.PathRole]
    elif isinstance(v, (QtCore.QModelIndex, QtCore.QPersistentModelIndex)):
        v = v.data(common.PathRole)
    else:
        raise TypeError(
            f'Invalid type, expected one of {weakref.ref}, {QtCore.QModelIndex}, {dict}, got {type(v)}')
    return _proxy_path(v)


@functools.lru_cache(maxsize=4194304)
def _proxy_path(v):
    collapsed = is_collapsed(v)
    if collapsed:
        return f'{collapsed.group(1)}{SEQPROXY}{collapsed.group(3)}'
    seq = get_sequence(v)
    if seq:
        return f'{seq.group(1)}{SEQPROXY}{seq.group(3)}.{seq.group(4)}'
    return v


@functools.lru_cache(maxsize=4194304)
def get_sequence_start_path(path):
    """Checks if given string is collapsed, and if so, returns the path of
    the first item of the sequence.

    Args:
        path (str): A collapsed sequence name.

    Returns:
        str: The path to the first file of the sequence.

    """
    common.check_type(path, str)

    if not is_collapsed(path):
        return path

    match = SequenceStartRegex.search(path)
    if match:
        path = SequenceStartRegex.sub(r'\1\2\3', path)
    return path


@functools.lru_cache(maxsize=4194304)
def get_sequence_end_path(path):
    """Checks if given string is collapsed, and if so, returns the path of
    the last item of the sequence.

    Args:
        path (str): A collapsed sequence name.

    Returns:
        str: The path to the last file of the sequence.

    """
    common.check_type(path, str)
    if not is_collapsed(path):
        return path

    match = SequenceEndRegex.search(path)
    if match:
        path = SequenceEndRegex.sub(r'\1\2\3', path)
    return path


def get_sequence_paths(index):
    """Return a list of file paths of the individual files that make up the
    sequence.

    Args:
        index (QtCore.QModelIndex): A list view index.

    Returns:
        list: A list of file paths.

    """
    path = index.data(common.PathRole)
    if not is_collapsed(path):
        return [path, ]

    v = []
    seq = index.data(common.SequenceRole)
    for frame in index.data(common.FramesRole):
        v.append(f'{seq.group(1)}{frame}{seq.group(3)}.{seq.group(4)}')
    return v
