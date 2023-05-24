"""Common attributes, methods and flag values.

"""

import functools
import hashlib
import os
import re
import sys
import time
import uuid

from PySide2 import QtCore, QtWidgets

from .. import common

#: The config file name
CONFIG = 'config.json'

#: Startup mode when `Bookmarks` is running as a standalone Qt application
StandaloneMode = 'standalone'
#: Startup mode used when `Bookmarks` runs embedded in a host DCC.
EmbeddedMode = 'embedded'

BookmarkTab = 0
AssetTab = 1
FileTab = 2
FavouriteTab = 3
TaskTab = 4

InfoThread = 0
ThumbnailThread = 1

PlatformWindows = 0
PlatformMacOS = 1
PlatformUnsupported = 2

WindowsPath = 0
MacOSPath = 1
UnixPath = 2
SlackPath = 3

MarkedAsArchived = 0b1000000000
MarkedAsFavourite = 0b10000000000
MarkedAsActive = 0b100000000000
MarkedAsDefault = 0b1000000000000

FileItem = 1100
SequenceItem = 1200

n = (f for f in range(999, QtCore.Qt.UserRole + 4096))

FlagsRole = QtCore.Qt.ItemDataRole(next(n))
PathRole = QtCore.Qt.ItemDataRole(next(n))
ParentPathRole = QtCore.Qt.ItemDataRole(next(n))
DescriptionRole = QtCore.Qt.ItemDataRole(next(n))
TodoCountRole = QtCore.Qt.ItemDataRole(next(n))
AssetCountRole = QtCore.Qt.ItemDataRole(next(n))
FileDetailsRole = QtCore.Qt.ItemDataRole(next(n))
SequenceRole = QtCore.Qt.ItemDataRole(next(n))
FramesRole = QtCore.Qt.ItemDataRole(next(n))
FileInfoLoaded = QtCore.Qt.ItemDataRole(next(n))
ThumbnailLoaded = QtCore.Qt.ItemDataRole(next(n))
StartPathRole = QtCore.Qt.ItemDataRole(next(n))
EndPathRole = QtCore.Qt.ItemDataRole(next(n))
TypeRole = QtCore.Qt.ItemDataRole(next(n))
EntryRole = QtCore.Qt.ItemDataRole(next(n))
IdRole = QtCore.Qt.ItemDataRole(next(n))
QueueRole = QtCore.Qt.ItemDataRole(next(n))
DataTypeRole = QtCore.Qt.ItemDataRole(next(n))
ItemTabRole = QtCore.Qt.ItemDataRole(next(n))
SortByNameRole = QtCore.Qt.ItemDataRole(next(n))
SortByLastModifiedRole = QtCore.Qt.ItemDataRole(next(n))
SortBySizeRole = QtCore.Qt.ItemDataRole(next(n))
SortByTypeRole = QtCore.Qt.ItemDataRole(next(n))
ShotgunLinkedRole = QtCore.Qt.ItemDataRole(next(n))
SlackLinkedRole = QtCore.Qt.ItemDataRole(next(n))
AssetProgressRole = QtCore.Qt.ItemDataRole(next(n))

DEFAULT_SORT_VALUES = {
    SortByNameRole: 'Name',
    SortBySizeRole: 'Size',
    SortByLastModifiedRole: 'Last modified',
    SortByTypeRole: 'Type',
}

GuiResource = 'gui'
ThumbnailResource = 'thumbnails'
FormatResource = 'formats'
TemplateResource = 'templates'

hashes_mutex = QtCore.QMutex()

def rsc(rel_path):
    """Returns a resource item from the `rsc` directory.

    """
    v = os.path.normpath('/'.join((__file__, os.pardir, os.pardir, 'rsc', rel_path)))
    f = QtCore.QFileInfo(v)
    if not f.exists():
        raise RuntimeError(f'{f.filePath()} does not exist.')
    return f.filePath()


def check_type(value, _type):
    """Verify the type of object.

    Args:
        value (object): An object of invalid type.
        _type (type or tuple or types): The valid type.

    Raises:
        TypeError: When ``value`` is not of ``_type``.

    """
    if not common.typecheck_on:
        return

    if isinstance(_type, tuple):
        _type = [type(f) if f is None else f for f in _type]
        _types = [isinstance(value, type(f) if f is None else f) for f in _type]
        if not any(_types):
            _types = '" or "'.join([f.__name__ for f in _type])
            raise TypeError(
                f'Invalid type. Expected "{_types}", got "{type(value).__name__}" >>\n{value}'
            )
    else:
        _type = type(_type) if _type is None else _type
        if not isinstance(value, _type):
            raise TypeError(
                f'Invalid type. Expected "{_type.__name__}", got "'
                f'{type(value).__name__}"'
            )


@functools.lru_cache(maxsize=4194304)
def get_hash(key):
    """Calculates the md5 hash of a string.

    In practice, we use this function to generate hashes for file paths. These
    hashes are used by the `ImageCache`, `user_settings` and `BookmarkDB` to
    associate data with the file items. Generated hashes are server agnostic,
    meaning, if the passed string contains a known server's name, we'll remove it
    before hashing.

    Args:
        key (str): A key string to calculate a md5 hash for.

    Returns:
        str: MD5 hexadecimal digest of the key.

    """
    # Path must not contain backslashes
    if '\\' in key:
        key = key.replace('\\', '/')

    for s in common.servers:
        if s not in key:
            continue

        l = len(s)
        if key[:l] == s:
            key = key[l:]
            key = key.lstrip('/')
            break

    # Otherwise, we calculate, save and return the digest
    return hashlib.md5(key.encode('utf8')).hexdigest()


def error(func):
    """Decorator function used to handle exceptions and report them to the user.

    """

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        """

        Args:
            *args:
            **kwargs:

        Returns:

        """
        try:
            return func(*args, **kwargs)
        except:
            # Remove decorator(s) from the traceback stack
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if exc_traceback:
                while 'wrapper' in exc_traceback.tb_frame.f_code.co_name:
                    tb = exc_traceback.tb_next
                    if not tb:
                        break
                    exc_traceback = exc_traceback.tb_next

            from .. import log
            log.error(
                exc_value.__str__(), exc_info=(
                    exc_type, exc_value, exc_traceback)
            )

            # Making sure the ui popup is ignored in non-gui threads
            app = QtWidgets.QApplication.instance()
            if app and QtCore.QThread.currentThread() == app.thread():
                if QtWidgets.QApplication.instance():
                    from .. import ui
                    ui.ErrorBox(exc_value.__str__(), limit=1).open()
                common.signals.showStatusTipMessage.emit(
                    f'Error: {exc_value.__str__()}'
                )

            raise

    return func_wrapper


def debug(func):
    """Function decorator used to log a debug message.
    No message will be logged, unless :attr:`~bookmarks.common.debug_on` is set to
    True.

    """
    debug_message = '{trace}(): Executed in {time} secs.'
    debug_separator = ' --> '

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        """Function wrapper.

        """
        # If global debugging is turned off, do nothing
        if not common.debug_on:
            return func(*args, **kwargs)

        # Otherwise, get the callee, and the executing time and info
        t = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            if args and hasattr(args[0], '__class__'):
                name = f'{args[0].__class__}.{func.__name__}'
            else:
                name = func.__name__

            trace = [name, ]
            from .. import log
            log.debug(
                debug_message.format(
                    trace=debug_separator.join(trace),
                    time=time.time() - t
                )
            )

    return func_wrapper


def get_platform():
    """Returns the enum of the current platform.

    One of the following values: PlatFormWindows, PlatFormMacOS or PlatFormUnsupported.

    Returns:
        int: The current platform or PlatFormUnsupported.

    """
    ptype = QtCore.QSysInfo().productType()
    if ptype.lower() in ('osx', 'macos'):
        return PlatformMacOS
    if 'win' in ptype.lower():
        return PlatformWindows
    return PlatformUnsupported


def get_username():
    """Returns the name of the currently logged-in user.

    """
    v = ''
    if get_platform() == PlatformWindows:
        if 'username' in os.environ:
            v = os.environ['username']
        elif 'USERNAME' in os.environ:
            v = os.environ['USERNAME']
    if get_platform() == PlatformMacOS:
        if 'user' in os.environ:
            v = os.environ['user']
        elif 'USER' in os.environ:
            v = os.environ['USER']
    v = v.replace('.', '')
    return v


def get_template_file_path(name):
    """Returns the path to the source template file.

    Args:
        name (str): The name of the template file.

    Returns:
        str: The path to the template file.

    """
    return os.path.normpath(
        os.path.sep.join(
            (
                __file__, os.pardir, os.pardir, 'rsc', 'templates', name
            )
        )
    )


def pseudo_local_bookmark():
    """Return a location on the local system to store temporary files.
    This is used to store thumbnails for starred items and other temporary items.

    Returns:
            tuple: A tuple of path segments.

    """
    return (
        QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation
        ),
        common.product,
        'temp',
    )


def temp_path():
    """Path to the folder to store temporary files.

    Returns:
            str: Path to a directory.

    """
    return '/'.join(pseudo_local_bookmark())


def get_thread_key(*args):
    """Returns the key associated with args and the current thread.

    Args:
        *args: `server`, `job`, `root` path segments.

    Returns:
        str: The key value.

    """
    t = repr(QtCore.QThread.currentThread())
    return '/'.join(args) + t


@functools.lru_cache(maxsize=1048576)
def sort_words(s):
    """Sorts a comma separated list of words found in the given string.

    Returns:
        str: A comma-separated list of sorted words.

    """
    return ', '.join(sorted(re.findall(r"[\w']+", s)))


@functools.lru_cache(maxsize=1048576)
def is_dir(path):
    """Cache-back type query.

    """
    return QtCore.QFileInfo(path).isDir()


def get_sequence_and_shot(s):
    """Returns the sequence and shot name of the given path.

    E.g. if the path is `C:/SEQ050/SH010/my_file.ma` will return
    `('SEQ050', 'SH010')`. If neither the sequence or shot name is found,
    will try to match using digits only.

    Args:
        s (str): A file or folder path.

    Returns:
        tuple (str, str): Sequence and shot name, or `(None, None)`
                                    if not found.

    """
    common.check_type(s, str)

    # Get sequence name
    match = re.search(
        r'(SQ|SEQ|SEQUENCE)([0-9]+)',
        s,
        flags=re.IGNORECASE
    )
    seq = ''.join(match.groups()) if match and match.groups() else None

    # Get shot name
    match = re.search(
        r'(SH|SHOT)([0-9]+)',
        s,
        flags=re.IGNORECASE
    )
    shot = ''.join(match.groups()) if match and match.groups() else None

    # If we don't have a match for either, we could try to check for a numerical pattern
    if not seq and not shot:
        match = re.search(
            r'(?<=\D)(\d{2,4})_(\d{2,5})(?=\D)',
            s,
            flags=re.IGNORECASE
        )
        seq, shot = (match.group(1), match.group(2)) if match else (seq, shot)

    return seq, shot


def get_entry_from_path(path, is_dir=True):
    """Returns a scandir entry of the given file path.

    Args:
        path (str): Path to directory.
        is_dir (bool): Is the path a directory or a file.

    Returns:
         scandir.DirEntry: A scandir entry, or None if not found.

    """
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return None

    for entry in os.scandir(file_info.dir().path()):
        if is_dir and not entry.is_dir():
            continue
        if entry.name == file_info.fileName():
            return entry
    return None


def get_links(path, section='links/asset'):
    """Returns a list of file links defined in a ``.links`` file.

    .link files are simple QSettings ini files that define a list of paths relative to the
    .link file. These can be used to define nested assets or bookmark item locations
    inside job templates.

    If a .links file contains two relative paths,
    `subfolder1/nested_asset1` and `subfolder2/nested_asset2`...

    .. code-block:: text

        asset/
        ├─ .links
        ├─ subfolder1/
        │  ├─ nested_asset1/
        ├─ subfolder2/
        │  ├─ nested_asset2/

    ...two asset will be read, `nested_asset1` and `nested_asset2`
    (but not the original root `asset`).

    Args:
        path (str): Path to a folder where the link file resides. E.g. an asset root folder.
        section (str):
            The settings section to look for links in.
            Optional. Defaults to 'links/asset'.

    Returns:
        list: A list of relative file paths.

    """
    l = f'{path}/{common.link_file}'
    if not QtCore.QFileInfo(l).exists():
        return []

    s = QtCore.QSettings(l, QtCore.QSettings.IniFormat)
    v = s.value(section)
    if not v:
        return []
    if not isinstance(v, (list, tuple)):
        v = [v, ]

    try:
        # Check validity of the list before returning anything
        links = []
        for _v in v:
            file_info = QtCore.QFileInfo(f'{path}/{_v}')
            if file_info.exists():
                links.append(_v.replace('\\', '/'))
            else:
                from .. import log
                log.error(f'Link "{file_info.filePath()}" does not exist.')
        return sorted(links)
    except:
        return []


def add_link(path, link, section='links/asset'):
    """Add a relative link to a link config file fount in the root of "path".

    Args:
        path (str): Path to a folder where the link file resides. E.g. an asset root folder.
        link (str): Relative path to the link file.
        section (str):
            The settings section to look for links in. Defaults to `links/asset`.

    """
    l = f'{path}/{common.link_file}'
    s = QtCore.QSettings(l, QtCore.QSettings.IniFormat)

    links = []
    if QtCore.QFileInfo(l).exists():
        links = s.value(section)
        if links and not isinstance(links, (list, tuple)):
            links = [links, ]
    links = links if links else []

    # Make sure the link points to a valid file
    file_info = QtCore.QFileInfo(f'{path}/{link}')
    if not file_info.exists():
        raise RuntimeError(f'{file_info.filePath()} does not exist')

    if link not in links:
        links.append(link)
        links = sorted(set(links))
    s.setValue(section, links)
    return True


def byte_to_pretty_string(num, suffix='B'):
    """Converts a numeric byte value to a human-readable string.

    Args:
        num (int): The number of bytes.
        suffix (str): A custom suffix.

    Returns:
        str:            Human readable byte value.

    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return u"%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return u"%.1f%s%s" % (num, 'Yi', suffix)


def get_py_obj_size(obj):
    """Sum size of object & members.

    """
    from gc import get_referents
    from types import ModuleType, FunctionType

    exclude = (type, ModuleType, FunctionType)
    seen_ids = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, exclude) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = get_referents(*need_referents)
    return size


def int_key(x):
    """Makes certain we convert int keys back to int values.

    """

    def _int(v):
        try:
            return int(v)
        except:
            return v

    if isinstance(x, dict):
        return {_int(k): v for k, v in x.items()}

    return x


class DataDict(dict):
    """Custom dictionary class used to store model item data.

    This class adds compatibility for :class:`weakref.ref` referencing
    and custom attributes for storing data state.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loaded = False
        self._refresh_needed = False
        self._data_type = None

    @property
    def loaded(self):
        """Special attribute used by the item models and associated thread workers.

        When set to `True`, the helper threads have finished populating data and the item
        is considered fully loaded.

        """
        return self._loaded

    @loaded.setter
    def loaded(self, v):
        self._loaded = v

    @property
    def refresh_needed(self):
        """Used to signal that the cached data is out of date and needs updating.

        """
        return self._refresh_needed

    @refresh_needed.setter
    def refresh_needed(self, v):
        self._refresh_needed = v

    @property
    def data_type(self):
        """Returns the associated model item type.

        """
        return self._data_type

    @data_type.setter
    def data_type(self, v):
        self._data_type = v


class Timer(QtCore.QTimer):
    """A custom QTimer class used across the app.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common.timers[repr(self)] = self

    def setObjectName(self, v):
        """Set the instance object name.

        Args:
            v (str): Object name.

        """
        v = f'{v}_{uuid.uuid1().hex}'
        super().setObjectName(v)

    @classmethod
    def delete_timers(cls):
        """Delete all cached timers instances.

        """
        for k in list(common.timers):
            try:
                common.timers[k].isActive()
            except:
                # The C++ object is probably already deleted
                del common.timers[k]
                continue

            # Check thread affinity
            if common.timers[k].thread() != QtCore.QThread.currentThread():
                continue
            common.timers[k].stop()
            common.timers[k].deleteLater()
            del common.timers[k]
