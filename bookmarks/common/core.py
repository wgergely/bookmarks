import os
import re
import time
import functools
import sys
import json
import uuid
import hashlib
import collections
import traceback
import inspect

import _scandir
from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import log


CONFIG = 'config.json'


# static_bookmarks_PATH = get_template_file_path(static_bookmarks)
# DEFAULT_ASSET_SOURCE = get_template_file_path(DEFAULT_JOB_TEMPLATE)
# DEFAULT_JOB_SOURCE = get_template_file_path(DEFAULT_ASSET_TEMPLATE)

StandaloneMode = 'standalone'
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
MarkedAsPersistent = 0b1000000000000

FileItem = 1100
SequenceItem = 1200

FlagsRole = QtCore.Qt.ItemDataRole(QtCore.Qt.UserRole + 4096)
ParentPathRole = QtCore.Qt.ItemDataRole(FlagsRole + 1)
DescriptionRole = QtCore.Qt.ItemDataRole(ParentPathRole + 1)
TodoCountRole = QtCore.Qt.ItemDataRole(DescriptionRole + 1)
AssetCountRole = QtCore.Qt.ItemDataRole(TodoCountRole + 1)
FileDetailsRole = QtCore.Qt.ItemDataRole(AssetCountRole + 1)
SequenceRole = QtCore.Qt.ItemDataRole(FileDetailsRole + 1)
FramesRole = QtCore.Qt.ItemDataRole(SequenceRole + 1)
FileInfoLoaded = QtCore.Qt.ItemDataRole(FramesRole + 1)
ThumbnailLoaded = QtCore.Qt.ItemDataRole(FileInfoLoaded + 1)
StartpathRole = QtCore.Qt.ItemDataRole(ThumbnailLoaded + 1)
EndpathRole = QtCore.Qt.ItemDataRole(StartpathRole + 1)
TypeRole = QtCore.Qt.ItemDataRole(EndpathRole + 1)
EntryRole = QtCore.Qt.ItemDataRole(TypeRole + 1)
IdRole = QtCore.Qt.ItemDataRole(EntryRole + 1)
QueueRole = QtCore.Qt.ItemDataRole(IdRole + 1)
DataTypeRole = QtCore.Qt.ItemDataRole(QueueRole + 1)
SortByNameRole = QtCore.Qt.ItemDataRole(DataTypeRole + 1)
SortByLastModifiedRole = QtCore.Qt.ItemDataRole(SortByNameRole + 1)
SortBySizeRole = QtCore.Qt.ItemDataRole(SortByLastModifiedRole + 1)
SortByTypeRole = QtCore.Qt.ItemDataRole(SortBySizeRole + 1)
ShotgunLinkedRole = QtCore.Qt.ItemDataRole(SortByTypeRole + 1)

DEFAULT_SORT_VALUES = {
    SortByNameRole: 'Name',
    SortBySizeRole: 'Date Modified',
    SortByLastModifiedRole: 'Size',
    SortByTypeRole: 'Type',
}


def _get_conf_path():
    return os.path.normpath(os.path.abspath(os.path.sep.join((
        __file__, os.pardir, os.pardir, 'rsc', CONFIG
    ))))


def _init_config():
    """Load the config values from CONFIG and set them in the `common` module as
    public properties.

    """
    p = _get_conf_path()
    if not os.path.isfile(p):
        raise RuntimeError(f'{p} not found.')

    with open(p, 'r', encoding='utf8') as f:
        config = json.loads(f.read())

    # Set config values in the common module
    for k, v in config.items():
        setattr(common, k, v)


def get_template_file_path(name):
    """Returns the path to the source template file.

    Args:
        name (str): The name of the template file.

    Returns:
        str: The path to the template file.

    """
    return os.path.normpath(os.path.abspath(os.path.sep.join((
        __file__, os.pardir, os.pardir, 'rsc', 'templates', name
    ))))


def initialize(mode):
    """Initializes the components of the application required to run in
    standalone mode.

    Args:
            mode (bool):    Bookmarks will run in *standalone* mode when `True`.

    """
    if common.init_mode is not None:
        raise RuntimeError(f'Already initialized as "{common.init_mode}"!')
    if mode not in (StandaloneMode, EmbeddedMode):
        raise ValueError(f'Invalid initalization mode. Got "{mode}", expected `StandaloneMode` or `EmbeddedMode`')

    common.init_mode = mode

    _init_config()

    common.itemdata = DataDict()

    if not os.path.isdir(temp_path()):
        os.makedirs(os.path.normpath(temp_path()))

    common.init_signals()
    common.prune_lock()
    common.init_lock() # Sets the current active mode
    common.init_settings()

    _init_ui_scale()
    _init_dpi()


    common.cursor = QtGui.QCursor()

    from .. import images
    images.init_imagecache()
    images.init_resources()

    print(f'# {common.product} initialized as "{common.init_mode}".')

    from .. import standalone
    if not QtWidgets.QApplication.instance() and mode == common.StandaloneMode:
        standalone.BookmarksApp([])
    elif not QtWidgets.QApplication.instance():
        raise RuntimeError('No QApplication instance found.')

    images.init_pixel_ratio()
    common.init_font()
    if mode == common.StandaloneMode:
        standalone.init()
    else:
        from .. import main
        main.init()

    common.init_monitor()


def _init_ui_scale():
    v = common.settings.value(
        common.SettingsSection,
        common.UIScaleKey
    )

    if v is None or not isinstance(v, str):
        common.ui_scale = 1.0
        return

    if '%' not in v:
        v = 1.0
    else:
        v = v.strip('%')
    try:
        v = float(v) * 0.01
    except:
        v = 1.0


    if not common.ui_scale_factors or v not in common.ui_scale_factors:
        v = 1.0

    common.ui_scale = v


def _init_dpi():
    if get_platform() == PlatformWindows:
        common.dpi = 72.0
    elif get_platform() == PlatformMacOS:
        common.dpi = 96.0
    elif get_platform() == PlatformUnsupported:
        common.dpi = 72.0


def init_environment(add_private=False):
    """Add the dependencies to the Python environment.

    The method requires that BOOKMARKS_ENV_KEY is set. The key is usually set
    by the Bookmark installer to point to the install root directory.
    The

    Raises:
            EnvironmentError: When the BOOKMARKS_ENV_KEY is not set.
            RuntimeError: When the BOOKMARKS_ENV_KEY is invalid or a directory missing.

    """
    if common.env_key not in os.environ:
        raise EnvironmentError(
            f'"{common.env_key}" environment variable is not set.')

    v = os.environ[common.env_key]

    if not os.path.isdir(v):
        raise RuntimeError(
            f'"{v}" is not a falid folder. Is "{common.env_key}" environment variable set?')

    # Add BOOKMARKS_ENV_KEY to the PATH
    v = os.path.normpath(os.path.abspath(v)).strip()
    if v.lower() not in os.environ['PATH'].lower():
        os.environ['PATH'] = v + ';' + os.environ['PATH'].strip(';')

    def _add_path_to_sys(p):
        _v = f'{v}{os.path.sep}{p}'
        if not os.path.isdir(_v):
            raise RuntimeError(f'{_v} does not exist.')

        if _v in sys.path:
            return
        sys.path.append(_v)

    _add_path_to_sys('shared')
    if add_private:
        _add_path_to_sys('private')
    sys.path.append(v)



def check_type(value, _type):
    """Verify the type of an object.

    Args:
            value (object): An object of invalid type.
            _type (type or tuple or types): The valid type.

    """
    if not common.typecheck_on:
        return

    it = None
    try:
        it = iter(_type)
    except:
        pass

    if it:
        if not any(isinstance(value, type(f) if f is None else f) for f in it):
            _types = ' or '.join([repr(type(f)) for f in _type])
            raise TypeError(f'Invalid type. Expected {_types}, got {type(value)}')
    else:
        if not isinstance(value, type(_type) if _type is None else _type):
            raise TypeError(f'Invalid type. Expected {_type}, got {type(value)}')


def get_hash(key):
    """Calculates the md5 hash of a string.

    In practice, we use this function to generate hashes for file paths. These
    hashes are used by the `ImageCache`, `user_settings` and `BookmarkDB` to
    associate data with the file items. Generated hashes are server agnostic,
    meaning, if the passed string contains a server's name, we'll remove it
    before hashing.

    Args:
        key (str): A key string to calculate an md5 hash for.

    Returns:
        str: MD5 hexadecimal digest of the key.

    """
    check_type(key, str)

    # Path must not contain backslashes
    if '\\' in key:
        key = key.replace('\\', '/')

    for s in common.servers:
        if s not in key:
            continue

        l = len(s)
        if key[:l] == s:
            key = key[l:]
            break

    key = key.encode('utf8')
    if key in common.hashes:
        return common.hashes[key]

    # Otherwise, we calculate, save and return the digest
    common.hashes[key] = hashlib.md5(key).hexdigest()
    return common.hashes[key]


def error(func):
    """Decorator to create a menu set."""
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            info = sys.exc_info()
            if all(info):
                e = ''.join(traceback.format_exception(*info))
            else:
                e = ''

            log.error('Error.')

            # So we can use the method in threads too
            app = QtWidgets.QApplication.instance()
            if app and QtCore.QThread.currentThread() == QtWidgets.QApplication.instance().thread():
                try:
                    if QtWidgets.QApplication.instance():
                        from .. import ui
                        ui.ErrorBox(info[1].__str__(), limit=1).open()
                    common.signals.showStatusBarMessage.emit(
                        'An error occured. See log for more details.')
                except:
                    pass
            raise
    return func_wrapper


def debug(func):
    """Decorator to create a menu set."""
    DEBUG_MESSAGE = '{trace}(): Executed in {time} secs.'
    DEBUG_SEPARATOR = ' --> '

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        # If global debugging is turned off, do nothing
        if not common.debug_on:
            return func(*args, **kwargs)

        # Otherwise, get the callee, and the executing time and info
        try:
            if common.debug_on:
                t = time.time()
            return func(*args, **kwargs)
        finally:
            if args and hasattr(args[0], '__class__'):
                funcname = f'{args[0].__class__}.{func.func_name}'
            else:
                funcname = func.func_name

            if common.debug_on:
                trace = []
                for frame in reversed(inspect.stack()):
                    if frame[3] == '<module>':
                        continue
                    mod = inspect.getmodule(frame[0]).__name__
                    _funcname = f'{mod}.{frame[3]}'
                    trace.append(_funcname)
                trace.append(funcname)

                log.debug(
                    DEBUG_MESSAGE.format(
                        trace=DEBUG_SEPARATOR.join(trace),
                        time=time.time() - t
                    )
                )

    return func_wrapper


def sort_data(ref, sortrole, sortorder):
    check_type(sortrole, QtCore.Qt.ItemDataRole)
    check_type(sortorder, bool)

    def sort_key(idx):
        # If sort_by_basename is `True` we'll use the base file name for sorting
        v = ref().__getitem__(idx)
        if common.sort_by_basename and sortrole == SortByNameRole and isinstance(v[sortrole], list):
            return v[sortrole][-1]
        return v[sortrole]

    sorted_idxs = sorted(
        ref().keys(),
        key=sort_key,
        reverse=sortorder
    )

    d = DataDict()
    d.loaded = ref().loaded
    d.data_type = ref().data_type

    for n, idx in enumerate(sorted_idxs):
        if not ref():
            raise RuntimeError('Model mutated during sorting.')
        ref()[idx][IdRole] = n
        d[n] = ref()[idx]
    return d


def get_platform():
    """Returns the current platform."""
    ptype = QtCore.QSysInfo().productType()
    if ptype.lower() in ('osx', 'macos'):
        return PlatformMacOS
    if 'win' in ptype.lower():
        return PlatformWindows
    return PlatformUnsupported


def get_username():
    """Returns the name of the currently logged-in user.

    """
    n = QtCore.QFileInfo(os.path.expanduser('~')).fileName()
    n = re.sub(r'[^a-zA-Z0-9]*', '', n, flags=re.IGNORECASE | re.UNICODE)
    return n


def qlast_modified(n):
    return QtCore.QDateTime.fromMSecsSinceEpoch(n * 1000)


def get_path_to_executable(key):
    """Returns the path to an executable.

    Args:
        key (str):
            The setting key to look up (one of ``setings.FFMpegKey``, or
            ``common.RVKey``) or `None` if not found.

    Returns:
        str: The path to the executable.

    """
    # Only FFMpeg and RV are implemented at the moment
    if key == common.FFMpegKey:
        name = 'ffmpeg'
    elif key == common.RVKey:
        name = 'rv'
    else:
        raise ValueError('Unsupported key value.')

    # First let's check if we have set explictily a path to an executable
    v = common.settings.value(common.SettingsSection, key)
    if isinstance(v, str) and QtCore.QFileInfo(v).exists():
        return QtCore.QFileInfo(v).filePath()

    # Otheriwse, let's check the environment
    if get_platform() == PlatformWindows:
        paths = os.environ['PATH'].split(';')
        paths = {os.path.normpath(f).rstrip('\\')
                 for f in paths if os.path.isdir(f)}

        for path in paths:
            for entry in _scandir.scandir(path):
                if entry.name.lower().startswith(name):
                    return QtCore.QFileInfo(entry.path).filePath()

    # If the envinronment lookup fails too, we'll return nothing
    return None


def local_user_bookmark():
    """Return a location on the local system to store temporary files.
    This is used to store thumbnails for starred items and other temporary items.

    Returns:
            tuple: A tuple of path segments.

    """
    return (
        QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        common.product,
        'temp',
    )


def temp_path():
    """Path to the folder to store temporary files.

    Returns:
            str: Path to a directory.

    """
    return '/'.join(local_user_bookmark())


class DataDict(dict):
    """Subclassed dict type for weakref compatibility."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loaded = False
        self._refresh_needed = False
        self._data_type = None

    @property
    def loaded(self):
        return self._loaded

    @loaded.setter
    def loaded(self, v):
        self._loaded = v

    @property
    def refresh_needed(self):
        return self._refresh_needed

    @refresh_needed.setter
    def refresh_needed(self, v):
        self._refresh_needed = v

    @property
    def data_type(self):
        return self._data_type

    @data_type.setter
    def data_type(self, v):
        self._data_type = v


class Timer(QtCore.QTimer):
    """A custom QTimer.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common.timers[repr(self)] = self

    def setObjectName(self, v):
        v = '{}_{}'.format(v, uuid.uuid1().hex)
        super().setObjectName(v)

    @classmethod
    def delete_timers(cls):
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
