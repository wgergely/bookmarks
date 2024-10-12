"""Common attributes, methods and flag values.

"""
import enum
import functools
import os
import re
import sys
import time
import uuid

from PySide2 import QtCore, QtWidgets, QtGui

from .. import common

documentation_url = 'https://bookmarks-vfx.com'
env_key = 'Bookmarks_ROOT'
product = 'bookmarks'
organization = 'bookmarks'
organization_domain = 'bookmarks-vfx.com'
link_file = '.links'
bookmark_item_data_dir = '.bookmark'
bookmark_item_database = 'bookmark.db'
favorite_file_ext = 'bfav'
user_settings = 'user_settings.ini'
stylesheet_file = 'stylesheet.qss'
max_list_items = 999999

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

thumbnail_format = 'png'

#: Startup mode when bookmarks is called as a library
CoreMode = 'CoreMode'
#: Startup mode used when `Bookmarks` runs embedded in a host DCC.
EmbeddedMode = 'EmbeddedMode'
#: Startup mode when `Bookmarks` is running as a standalone Qt app
StandaloneMode = 'StandaloneMode'

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
    """
    Constructs and returns the index function.
    
    """
    _num = -1
    _start = -1

    def _idx_func(reset=False, start=None):
        """
        The index function. Increments and returns a counter.

        Args:
            reset (bool, optional): If True, reset the counter to the start value.
                                    Defaults to False.
            start (int, optional): If provided, set a new start value.
                                       Defaults to None.

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

#: List item role used to store favourite, archived, etc. flags.
FlagsRole = QtCore.Qt.ItemDataRole(idx(reset=True, start=QtCore.Qt.UserRole + 4096))
#: List item role used to store the item's file path.
PathRole = QtCore.Qt.ItemDataRole(idx())
#: List item role used to store the item's parent path.
ParentPathRole = QtCore.Qt.ItemDataRole(idx())
#: List item role used to store the item's description.
DescriptionRole = QtCore.Qt.ItemDataRole(idx())
#: List item role used to filter against
FilterTextRole = QtCore.Qt.ItemDataRole(idx())
#: List item role for the number of notes attached to the item.
NoteCountRole = QtCore.Qt.ItemDataRole(idx())
#: List item role for the number of assets attached to the item.
AssetCountRole = QtCore.Qt.ItemDataRole(idx())

#: List item role for storing file information.
FileDetailsRole = QtCore.Qt.ItemDataRole(idx())

#: List item role for getting the get_sequence() regex match results.
SequenceRole = QtCore.Qt.ItemDataRole(idx())
#: List item role for getting an item's number of frames.
FramesRole = QtCore.Qt.ItemDataRole(idx())
#: List item role to indicate if the item has been fully loaded.
FileInfoLoaded = QtCore.Qt.ItemDataRole(idx())
#: List item role to indicate if the item's thumbnail has been loaded.
ThumbnailLoaded = QtCore.Qt.ItemDataRole(idx())
#: A file item role to indicate a sequence item's first path
StartPathRole = QtCore.Qt.ItemDataRole(idx())
#: A file item role to indicate a sequence item's last path
EndPathRole = QtCore.Qt.ItemDataRole(idx())
#: A list item role to access the DirEntry instances associated with the item
EntryRole = QtCore.Qt.ItemDataRole(idx())
#: List item role for getting the item's persistent id.
IdRole = QtCore.Qt.ItemDataRole(idx())
#: List item role for getting the item's thread queue
QueueRole = QtCore.Qt.ItemDataRole(idx())
#: List item role for getting the item's data type (sequence or file)
DataTypeRole = QtCore.Qt.ItemDataRole(idx())
#: List item role for getting the container data dictionary
DataDictRole = QtCore.Qt.ItemDataRole(idx())
#: The view tab associated with the item
ItemTabRole = QtCore.Qt.ItemDataRole(idx())
#: Data used to sort the items by name
SortByNameRole = QtCore.Qt.ItemDataRole(idx())
#: Data used to sort the items by date
SortByLastModifiedRole = QtCore.Qt.ItemDataRole(idx())
#: Data used to sort the items by size
SortBySizeRole = QtCore.Qt.ItemDataRole(idx())
#: Data used to sort the items by type
SortByTypeRole = QtCore.Qt.ItemDataRole(idx())
#: Item linkage status
SGLinkedRole = QtCore.Qt.ItemDataRole(idx())
#: The progress tracking data linked with the item
AssetProgressRole = QtCore.Qt.ItemDataRole(idx())
#: The asset link file path
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
    BlackFont = 'Inter Black'
    BoldFont = 'Inter SemiBold'
    MediumFont = 'Inter'
    LightFont = 'Inter Medium'
    ThinFont = 'Inter Light'

    def __call__(self, size):
        from .. import common
        return common.font_db.get(size, self)


class Size(enum.Enum):
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
        if apply_scale:
            return round(self.value * float(multiplier))
        return round(self._value_ * float(multiplier))

    @property
    def value(self):
        return self.size(self._value_)

    @classmethod
    def size(cls, value):
        from ..common import ui_scale_factor, dpi
        return round(float(value) * (float(dpi) / 72.0)) * float(ui_scale_factor)


class Color(enum.Enum):
    Opaque = (0, 0, 0, 30)
    Transparent = (0, 0, 0, 0)
    #
    VeryDarkBackground = (40, 40, 40)
    DarkBackground = (65, 65, 65)
    Background = (85, 85, 85)
    LightBackground = (120, 120, 120)
    #
    DisabledText = (145, 145, 145)
    SecondaryText = (185, 185, 185)
    Text = (225, 225, 225)
    SelectedText = (255, 255, 255)
    #
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
        v = QtGui.QColor(*self._value_)
        if not qss:
            return v
        return self.rgb(v)

    @staticmethod
    def rgb(color):
        rgb = [str(f) for f in color.getRgb()]
        return f'rgba({",".join(rgb)})'


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
                    common.show_message(
                        'Error',
                        body=exc_value.__str__(),
                        message_type='error'
                    )
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


def temp_path():
    """Path to the folder to store temporary files.

    Returns:
            str: Path to a directory.

    """
    a = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.GenericDataLocation)
    b = common.product
    return f'{a}/{b}/temp'


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


@functools.lru_cache(maxsize=1048576)
def normalize_path(path):
    """Normalize the path and replace backslashes with forward slashes."""
    return os.path.abspath(os.path.normpath(path)).replace('\\', '/')


def get_entry_from_path(path, is_dir=True, force_exists=False):
    """Returns a scandir entry of the given file path.

    Args:
        path (str): Path to directory.
        is_dir (bool): Is the path a directory or a file.
        force_exists (bool): Force skip checking the existence of the path if we know path exist.

    Returns:
         scandir.DirEntry: A scandir entry, or None if not found.

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
    """Converts a numeric byte value to a human-readable string.

    Args:
        num (int): the number of bytes.
        suffix (str): a custom suffix.

    Returns:
        str: Human readable byte value.

    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return '%3.1f%s%s' % (num, unit, suffix)
        num /= 1024.0
    return '%.1f%s%s' % (num, 'Yi', suffix)


def get_py_obj_size(obj):
    """Sum byte size of an object and its members.

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


def sanitize_hashtags(s):
    """Sanitize hashtags in a string.

    Args:
        s (str): String to sanitize.


    Returns:
        str: Sanitized string.

    """
    s = s if s else ''

    # Remove trailing spaces
    s = s.strip()

    # Split the string into tokens, remove any empty tokens
    tokens = s.split(' ')

    # Remove instances of ## or # not followed by characters
    tokens = [re.sub(r'##+', '#', token) for token in tokens]
    tokens = [re.sub(r'#\s', '', token) for token in tokens]

    # Filter out the tokens from the non-token text
    hash_tokens = sorted(set([re.sub(r'(?<=\w)#', '_', token) for token in tokens if token.startswith('#')]))
    non_hash_tokens = [token for token in tokens if not token.startswith('#')]

    # Rejoin the tokens and non-token text into a single string
    s = ' '.join(non_hash_tokens + hash_tokens)

    return s


def split_text_and_hashtags(s):
    """Split a string into regular text and hashtags.

    Args:
        s (str): String to split.

    Returns:
        str, str: Regular text and hashtags.

    """
    s = s if s else ''

    # Split the string into tokens
    tokens = s.split(' ')

    # Filter out the tokens from the non-token text
    hash_tokens = [token for token in tokens if token.startswith('#')]
    non_hash_tokens = [token for token in tokens if not token.startswith('#')]

    # Join the tokens and non-token text into separate strings
    regular_text = ' '.join(non_hash_tokens)
    tokens_text = ' '.join(hash_tokens)

    return regular_text, tokens_text


class Timer(QtCore.QTimer):
    """A custom QTimer class used across the app.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common.timers[repr(self)] = self
        self.setObjectName(self.__class__.__name__)

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
