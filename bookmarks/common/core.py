"""Common attributes, methods and flag values.

This module provides shared constants, enumerations, and utility functions across the application.
It includes decorators for error handling and debugging, platform detection, file path helpers,
and various enumerations for UI scaling, fonts, and colors.

References:
    :class:`~bookmarks.common.setup.initialize`
"""

import enum
import functools
import inspect
import logging
import os
import re
import sys
import time
import traceback
import uuid

from PySide2 import QtCore, QtWidgets, QtGui

from .. import common

#: The app's official url
documentation_url = 'https://bookmarks-vfx.com'

#: The environment variable key used to check for the app's distribution root.
env_key = 'Bookmarks_ROOT'

#: The app's name
product = 'bookmarks'

#: The app's organization name
organization = 'bookmarks'

#: The app's organization domain
organization_domain = 'bookmarks-vfx.com'

link_file = '.links'
bookmark_item_data_dir = '.bookmark'
bookmark_item_database = 'bookmark.db'
favorite_file_ext = 'bfav'
user_settings = 'user_settings.ini'
stylesheet_file = 'stylesheet.qss'

#: Hardcoded maximum number of items to display in a list
max_list_items = 999999

#: Supported ui scale factors
ui_scale_factors = [
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    1.0,
    1.25,
    1.5,
    1.75,
    2.0,
    2.5,
    3.0
]

#: The default thumbnail format
thumbnail_format = 'png'


class Mode(enum.IntEnum):
    """Startup mode enums used by :class:`~bookmarks.common.setup.initialize`.

    Attributes:
        Core (int): Startup mode when bookmarks is called as a library.
        Embedded (int): Startup mode used when `Bookmarks` runs embedded in a host DCC.
        Standalone (int): Startup mode when `Bookmarks` is running as a standalone Qt app.
    """
    Core = 0
    Embedded = 1
    Standalone = 2


BookmarkTab = 0
AssetTab = 1
FileTab = 2
FavouriteTab = 3

PlatformWindows = 0
PlatformMacOS = 1
PlatformUnsupported = 2

WindowsPath = 0
MacOSPath = 1
UnixPath = 2

MarkedAsArchived = 0b1000000000
MarkedAsFavourite = 0b10000000000
MarkedAsActive = 0b100000000000

FileItem = 1100
SequenceItem = 1200


def idx_func():
    """A simple number generator similar to itertools.count().

    Returns:
        function: A closure that returns an incremented integer each time it's called.
    """
    _num = -1
    _start = -1

    def _idx_func(reset=False, start=None):
        """
        The index function. Increments and returns a counter.

        Args:
            reset (bool, optional): If True, reset the counter to the start value.
            start (int, optional): If provided, sets a new start value.

        Returns:
            int: The current counter value.
        """
        nonlocal _num
        nonlocal _start
        if start is not None:
            _start = start - 1
        if reset:
            _num = _start
        _num += 1
        return _num

    return _idx_func


#: The index function used to generate index values across the application.
idx = idx_func()

#: List item roles used across the UI
FlagsRole = QtCore.Qt.ItemDataRole(idx(reset=True, start=QtCore.Qt.UserRole + 4096))
PathRole = QtCore.Qt.ItemDataRole(idx())
ParentPathRole = QtCore.Qt.ItemDataRole(idx())
DescriptionRole = QtCore.Qt.ItemDataRole(idx())
FilterTextRole = QtCore.Qt.ItemDataRole(idx())
NoteCountRole = QtCore.Qt.ItemDataRole(idx())
AssetCountRole = QtCore.Qt.ItemDataRole(idx())
FileDetailsRole = QtCore.Qt.ItemDataRole(idx())
SequenceRole = QtCore.Qt.ItemDataRole(idx())
FramesRole = QtCore.Qt.ItemDataRole(idx())
FileInfoLoaded = QtCore.Qt.ItemDataRole(idx())
ThumbnailLoaded = QtCore.Qt.ItemDataRole(idx())
StartPathRole = QtCore.Qt.ItemDataRole(idx())
EndPathRole = QtCore.Qt.ItemDataRole(idx())
EntryRole = QtCore.Qt.ItemDataRole(idx())
IdRole = QtCore.Qt.ItemDataRole(idx())
QueueRole = QtCore.Qt.ItemDataRole(idx())
DataTypeRole = QtCore.Qt.ItemDataRole(idx())
DataDictRole = QtCore.Qt.ItemDataRole(idx())
ItemTabRole = QtCore.Qt.ItemDataRole(idx())
SortByNameRole = QtCore.Qt.ItemDataRole(idx())
SortByLastModifiedRole = QtCore.Qt.ItemDataRole(idx())
SortBySizeRole = QtCore.Qt.ItemDataRole(idx())
SortByTypeRole = QtCore.Qt.ItemDataRole(idx())
SGLinkedRole = QtCore.Qt.ItemDataRole(idx())
AssetProgressRole = QtCore.Qt.ItemDataRole(idx())
AssetLinkRole = QtCore.Qt.ItemDataRole(idx())

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


class Font(enum.Enum):
    """Enumeration of font names."""

    BlackFont = 'Inter Black'
    BoldFont = 'Inter SemiBold'
    MediumFont = 'Inter'
    LightFont = 'Inter Medium'
    ThinFont = 'Inter Light'

    def __call__(self, size):
        """
        Returns a QFont object for the given size and this font enum.

        Args:
            size (float|int): The desired font size.

        Returns:
            QFont: The font object.
        """
        from .. import common
        return common.font_db.get(size, self)


class Size(enum.Enum):
    """Enumeration of size values used for UI scaling."""
    SmallText = 11.0
    MediumText = 12.0
    LargeText = 16.0
    Indicator = 4.0
    Separator = 1.0
    Margin = 18.0
    Section = 86.0
    RowHeight = 34.0
    Thumbnail = 512.0
    DefaultWidth = 640.0
    DefaultHeight = 480.0

    def __new__(cls, value):
        obj = object.__new__(cls)
        obj._value_ = float(value)
        return obj

    def __eq__(self, other):
        if isinstance(other, (float, int)):
            return self._value_ == float(other)
        return super().__eq__(other)

    def __call__(self, multiplier=1.0, apply_scale=True):
        """
        Returns the scaled size value.

        Args:
            multiplier (float): A multiplier to apply to the size.
            apply_scale (bool): If True, applies UI scaling factors.

        Returns:
            int: The scaled size.
        """
        if apply_scale:
            return round(self.value * float(multiplier))
        return round(self._value_ * float(multiplier))

    @property
    def value(self):
        """float: The scaled size value."""
        return self.size(self._value_)

    @classmethod
    def size(cls, value):
        """Scale a value by DPI and UI scale factor."""
        from ..common import ui_scale_factor, dpi
        return round(float(value) * (float(dpi) / 72.0)) * float(ui_scale_factor)


class Color(enum.Enum):
    """Enumeration of colors used across the UI."""

    Opaque = (0, 0, 0, 30)
    Transparent = (0, 0, 0, 0)
    VeryDarkBackground = (40, 40, 40)
    DarkBackground = (65, 65, 65)
    Background = (85, 85, 85)
    LightBackground = (120, 120, 120)
    DisabledText = (145, 145, 145)
    SecondaryText = (185, 185, 185)
    Text = (225, 225, 225)
    SelectedText = (255, 255, 255)
    Blue = (88, 138, 180)
    LightBlue = (50, 50, 195, 180)
    MediumBlue = (66, 118, 160, 180)
    DarkBlue = (31, 39, 46)
    Red = (219, 114, 114)
    LightRed = (240, 100, 100, 180)
    MediumRed = (210, 75, 75, 180)
    DarkRed = (65, 35, 35, 180)
    Green = (90, 200, 155)
    LightGreen = (80, 150, 100, 180)
    MediumGreen = (65, 110, 75, 180)
    DarkGreen = (35, 65, 45)
    Yellow = (253, 166, 1, 200)
    LightYellow = (255, 220, 100, 180)
    MediumYellow = (255, 200, 50, 180)
    DarkYellow = (155, 125, 25)

    def __new__(cls, r, g, b, a=255):
        obj = object.__new__(cls)
        obj._value_ = (r, g, b, a)
        return obj

    def __call__(self, qss=False):
        """
        Returns a QColor or CSS rgba string.

        Args:
            qss (bool): If True, returns a CSS rgba string suitable for QSS.

        Returns:
            QColor or str: A QColor instance if qss=False, otherwise a CSS rgba string.
        """
        v = QtGui.QColor(*self._value_)
        if not qss:
            return v
        return self.rgb(v)

    @staticmethod
    def rgb(color):
        """Returns the CSS rgba string for a QColor."""
        rgb = [str(f) for f in color.getRgb()]
        return f'rgba({",".join(rgb)})'


def error(func=None, *, show_error=True):
    """Function decorator used to handle errors.

    This decorator logs exceptions and optionally shows a UI error dialog.

    Usage:
        @error
        def foo():
            ...

        @error(show_error=False)
        def bar():
            ...
    """

    def decorator(func):
        from .. import log

        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:  # Changed to Exception for safer exception handling
                exc_type, exc_value, exc_traceback = sys.exc_info()

                # Trim frames introduced by wrappers
                if exc_traceback:
                    while exc_traceback and 'wrapper' in exc_traceback.tb_frame.f_code.co_name:
                        exc_traceback = exc_traceback.tb_next

                # Introspect caller
                try:
                    stack = inspect.stack()
                    caller_frame = stack[1].frame
                    try:
                        module = inspect.getmodule(caller_frame)
                    except:
                        module = None

                    if module is not None:
                        caller_module_name = module.__name__
                        if caller_module_name == '__main__':
                            caller_module_name = getattr(module, '__file__', 'unknown_module')
                    else:
                        caller_module_name = caller_frame.f_globals.get('__name__', None)
                        if caller_module_name is None or caller_module_name == '__main__':
                            caller_module_name = (inspect.getsourcefile(caller_frame) or
                                                  inspect.getfile(caller_frame) or
                                                  'unknown_module')

                    caller_locals = caller_frame.f_locals
                    if 'self' in caller_locals:
                        caller_class = caller_locals['self'].__class__.__name__
                    elif 'cls' in caller_locals:
                        caller_class = caller_locals['cls'].__name__
                    else:
                        caller_class = None

                    caller_method_name = stack[1].function
                except:
                    caller_module_name = 'unknown_module'
                    caller_class = None
                    caller_method_name = None

                caller_class = caller_class if caller_class else ''
                caller_method_name = caller_method_name if caller_method_name else ''
                trace = [caller_class, caller_method_name]
                trace = '.'.join([f for f in trace if f])
                trace = trace + '()' if trace else 'unknown()'

                tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                if not tb_str.strip():
                    tb_str = f'Error occurred at {caller_module_name}:{trace}'

                for line in tb_str.splitlines():
                    log.error(caller_module_name, line)

                if show_error:
                    app = QtWidgets.QApplication.instance()
                    if app and QtCore.QThread.currentThread() == app.thread():
                        common.show_message(
                            'Error',
                            body=tb_str,
                            message_type='error'
                        )
                        common.signals.showStatusTipMessage.emit(
                            f'Error: {str(exc_value)}'
                        )

                raise

        return func_wrapper

    if func is not None and callable(func):
        return decorator(func)
    else:
        return decorator


def debug(func):
    """Function decorator used to log debug messages and execution time."""
    from .. import log

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        if log.get_logging_level() > logging.DEBUG:
            return func(*args, **kwargs)

        try:
            stack = inspect.stack()
            caller_frame = stack[1].frame
            try:
                module = inspect.getmodule(caller_frame)
            except:
                module = None

            if module is not None:
                caller_module_name = module.__name__
                if caller_module_name == '__main__':
                    caller_module_name = getattr(module, '__file__', 'unknown_module')
            else:
                caller_module_name = caller_frame.f_globals.get('__name__', None)
                if caller_module_name is None or caller_module_name == '__main__':
                    caller_module_name = (inspect.getsourcefile(caller_frame) or
                                          inspect.getfile(caller_frame) or
                                          'unknown_module')
        except:
            caller_module_name = 'unknown_module'

        t = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            t = time.time() - t
            qualname = func.__qualname__
            trace = f'{qualname}()'
            msg = f'{trace}  --  {int(t * 1000)}ms'
            log.debug(caller_module_name, msg)

    return func_wrapper


def get_platform():
    """Returns the enum of the current platform.

    Returns:
        int: One of PlatformWindows, PlatformMacOS, or PlatformUnsupported.
    """
    ptype = QtCore.QSysInfo().productType()
    if ptype.lower() in ('osx', 'macos'):
        return PlatformMacOS
    if 'win' in ptype.lower():
        return PlatformWindows
    return PlatformUnsupported


def get_username():
    """Returns the name of the currently logged-in user.

    On Windows, it tries the 'username' or 'USERNAME' environment variable.
    On MacOS, it tries 'user' or 'USER'.

    Returns:
        str: The username (with '.' removed) or an empty string if not found.
    """
    v = ''
    if get_platform() == PlatformWindows:
        if 'username' in os.environ:
            v = os.environ['username']
        elif 'USERNAME' in os.environ:
            v = os.environ['USERNAME']
    elif get_platform() == PlatformMacOS:
        if 'user' in os.environ:
            v = os.environ['user']
        elif 'USER' in os.environ:
            v = os.environ['USER']
    return v.replace('.', '')


def temp_path():
    """Path to a folder to store temporary files.

    Returns:
        str: A directory path.
    """
    a = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.GenericDataLocation)
    b = common.product
    return f'{a}/{b}/temp'


def get_thread_key(*args):
    """Returns a unique key based on given args and the current thread.

    Args:
        *args: Segments such as `server`, `job`, `root`.

    Returns:
        str: The concatenated key.
    """
    t = repr(QtCore.QThread.currentThread())
    return '/'.join(args) + t


@functools.lru_cache(maxsize=1048576)
def sort_words(s):
    """Sorts words found in the string and returns them as a comma-separated list.

    Args:
        s (str): A string containing words.

    Returns:
        str: A comma-separated list of sorted words.
    """
    return ', '.join(sorted(re.findall(r"[\w']+", s)))


@functools.lru_cache(maxsize=1048576)
def is_dir(path):
    """Check if the given path is a directory (cached).

    Args:
        path (str): The path to check.

    Returns:
        bool: True if directory, otherwise False.
    """
    return QtCore.QFileInfo(path).isDir()


@functools.lru_cache(maxsize=1048576)
def normalize_path(path):
    """Normalize and standardize the given path to forward slashes.

    Args:
        path (str): The file path.

    Returns:
        str: Normalized path.
    """
    return os.path.abspath(os.path.normpath(path)).replace('\\', '/')


def get_entry_from_path(path, is_dir=True, force_exists=False):
    """Returns a scandir entry for the given path if found.

    Args:
        path (str): The path to query.
        is_dir (bool): True if looking for a directory entry, otherwise False.
        force_exists (bool): If True, skip existence check (use if you know the path exists).

    Returns:
        scandir.DirEntry or None: The entry or None if not found.
    """
    file_info = QtCore.QFileInfo(path)

    if not force_exists and not file_info.exists():
        return None

    with os.scandir(file_info.dir().path()) as it:
        for entry in it:
            if is_dir and not entry.is_dir():
                continue
            if entry.name == file_info.fileName():
                return entry
    return None


def byte_to_pretty_string(num, suffix='B'):
    """Converts bytes to a human-readable format.

    Args:
        num (int): Number of bytes.
        suffix (str): Suffix to append. Default is 'B'.

    Returns:
        str: A human-readable byte string.
    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return '%3.1f%s%s' % (num, unit, suffix)
        num /= 1024.0
    return '%.1f%s%s' % (num, 'Yi', suffix)


def get_py_obj_size(obj):
    """Calculate approximate memory footprint of an object and all its contents.

    Args:
        obj (object): The Python object.

    Returns:
        int: The total size in bytes.
    """
    from gc import get_referents
    from types import ModuleType, FunctionType

    exclude = (type, ModuleType, FunctionType)
    seen_ids = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for o in objects:
            if not isinstance(o, exclude) and id(o) not in seen_ids:
                seen_ids.add(id(o))
                size += sys.getsizeof(o)
                need_referents.append(o)
        objects = get_referents(*need_referents)
    return size


def int_key(x):
    """Convert dictionary keys to int if possible.

    Args:
        x (dict or any): The input object.

    Returns:
        dict or any: The object with int keys if it was a dict.
    """

    def _int(v):
        try:
            return int(v)
        except:
            return v

    if isinstance(x, dict):
        return {_int(k): v for k, v in x.items()}
    return x


def sanitize_hashtags(s):
    """Normalize and sanitize hashtags in the given string.

    Removes extra spaces, duplicates, and normalizes hashtags.

    Args:
        s (str): The input string.

    Returns:
        str: Sanitized string.
    """
    s = s if s else ''
    s = s.strip()
    tokens = s.split(' ')
    tokens = [re.sub(r'##+', '#', token) for token in tokens]
    tokens = [re.sub(r'#\s', '', token) for token in tokens]

    hash_tokens = sorted(set([re.sub(r'(?<=\w)#', '_', token) for token in tokens if token.startswith('#')]))
    non_hash_tokens = [token for token in tokens if not token.startswith('#') and token]

    return ' '.join(non_hash_tokens + hash_tokens)


def split_text_and_hashtags(s):
    """Split a string into regular text and a separate string of hashtags.

    Args:
        s (str): The input string.

    Returns:
        tuple(str, str): (regular_text, hashtags)
    """
    s = s if s else ''
    tokens = s.split(' ')
    hash_tokens = [token for token in tokens if token.startswith('#')]
    non_hash_tokens = [token for token in tokens if not token.startswith('#')]
    return ' '.join(non_hash_tokens), ' '.join(hash_tokens)


class Timer(QtCore.QTimer):
    """A custom QTimer class used across the app to manage timed events."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common.timers[repr(self)] = self
        self.setObjectName(self.__class__.__name__)

    def setObjectName(self, v):
        """Set the instance object name, ensuring uniqueness.

        Args:
            v (str): Object name prefix.
        """
        v = f'{v}_{uuid.uuid1().hex}'
        super().setObjectName(v)

    @classmethod
    def delete_timers(cls):
        """Delete all cached timer instances associated with the current thread."""
        for k in list(common.timers):
            try:
                common.timers[k].isActive()
            except:
                # The C++ object is probably already deleted
                del common.timers[k]
                continue

            if common.timers[k].thread() != QtCore.QThread.currentThread():
                continue
            common.timers[k].stop()
            common.timers[k].deleteLater()
            del common.timers[k]
