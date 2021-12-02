import re
import weakref

from PySide2 import QtCore

from .. import common

SEQSTART = '{'
SEQEND = '}'
SEQPROXY = f'{SEQSTART}0{SEQEND}'

IsSequenceRegex = re.compile(
    rf'^(.+?)({SEQSTART}.*{SEQEND})(.*)$',
    flags=re.IGNORECASE | re.UNICODE
)
SequenceStartRegex = re.compile(
    rf'^(.*){SEQSTART}([0-9]+).*{SEQEND}(.*)$',
    flags=re.IGNORECASE | re.UNICODE
)
SequenceEndRegex = re.compile(
    rf'^(.*){SEQSTART}.*?([0-9]+){SEQEND}(.*)$',
    flags=re.IGNORECASE | re.UNICODE
)
GetSequenceRegex = re.compile(
    r'^(.*?)([0-9]+)([0-9\\/]*|[^0-9\\/]*(?=.+?))\.([^\.]+)$',
    flags=re.IGNORECASE | re.UNICODE)


def is_collapsed(s):
    """Check for the presence of the bracket-enclosed sequence markers.

    When Bookmarks is displaying a sequence of files as a single item,
    the item is *collapsed*. Every collapsed item contains a start and an end number
    enclosed in brackets. For instance: ``image_sequence_[001-233].png``

    Args:
            s (str): A file path.

    Returns:
            group 1 (SRE_Match):    All the characters **before** the sequence marker.
            group 2 (SRE_Match):    The sequence marker(e.g. ``{01-50}``), as a string.
            group 3 (SRE_Match):    All the characters **after** the sequence marker.

    .. code-block:: python

       filename = 'job_sh010_animation_[001-299]_wgergely.png'
       m = is_collapsed(filename)
       if m:
               prefix = match.group(1) # 'job_sh010_animation_'
               sequence_string = match.group(2) # '[001-299]'
               suffix = match.group(3) # '_wgergely.png'

    Returns:
            ``SRE_Match``: If the given name is indeed collpased it returns a ``SRE_Match`` object, otherwise ``None``.

    """
    common.check_type(s, str)
    return IsSequenceRegex.search(s)


def proxy_path(v):
    """Encompasses the logic used to associate preferences with items.

    Sequence items need a generic key to save values as the sequence notation
    might change as files are added/removed to image sequences. Any `FileItem`
    will use their file path as the key and SequenceItems will use `[0]` in place
    of their frame-range notation.

    Args:
            v (QModelIndex, dict or str): Data dict, index or filepath string.

    Returns:
            str: The key used to store the item's information in the local
            preferences and the bookmark item database.

    """
    if isinstance(v, weakref.ref):
        v = v()[QtCore.Qt.StatusTipRole]
    if isinstance(v, dict):
        v = v[QtCore.Qt.StatusTipRole]
    elif isinstance(v, QtCore.QModelIndex):
        v = v.data(QtCore.Qt.StatusTipRole)
    elif isinstance(v, str):
        pass
    else:
        raise TypeError(
            f'Invalid type, expected one of {weakref.ref}, {QtCore.QModelIndex}, {dict}, got {type(v)}')

    collapsed = is_collapsed(v)
    if collapsed:
        return collapsed.group(1) + SEQPROXY + collapsed.group(3)
    seq = get_sequence(v)
    if seq:
        return seq.group(1) + SEQPROXY + seq.group(3) + '.' + seq.group(4)
    return v


def get_sequence(s):
    """Check if the given text contains a sequence element.

    Strictly speaking, a sequence is any file that has a valid number element.
    There can only be **one** incrementable element - it will always be the
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


def get_sequence_startpath(path):
    """Checks the given string and if it denotes a sequence returns the path for
    the first file.

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


def get_sequence_endpath(path):
    """Checks the given string and if it denotes a sequence returns the path for
    the last file.

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
    """Given the index, returns a tuple of filenames referring to the
    individual sequence items.

    Args:
            index (QtCore.QModelIndex): A listview index.

    """
    path = index.data(QtCore.Qt.StatusTipRole)
    if not is_collapsed(path):
        return path

    sequence_paths = []
    for frame in index.data(common.FramesRole):
        seq = index.data(common.SequenceRole)
        seq = seq.group(1) + frame + seq.group(3) + '.' + seq.group(4)
        sequence_paths.append(seq)
    return sequence_paths
