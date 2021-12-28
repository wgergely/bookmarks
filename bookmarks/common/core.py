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

CONFIG = 'config.json'

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
StartPathRole = QtCore.Qt.ItemDataRole(ThumbnailLoaded + 1)
EndPathRole = QtCore.Qt.ItemDataRole(StartPathRole + 1)
TypeRole = QtCore.Qt.ItemDataRole(EndPathRole + 1)
EntryRole = QtCore.Qt.ItemDataRole(TypeRole + 1)
IdRole = QtCore.Qt.ItemDataRole(EntryRole + 1)
QueueRole = QtCore.Qt.ItemDataRole(IdRole + 1)
DataTypeRole = QtCore.Qt.ItemDataRole(QueueRole + 1)
SortByNameRole = QtCore.Qt.ItemDataRole(DataTypeRole + 1)
SortByLastModifiedRole = QtCore.Qt.ItemDataRole(SortByNameRole + 1)
SortBySizeRole = QtCore.Qt.ItemDataRole(SortByLastModifiedRole + 1)
SortByTypeRole = QtCore.Qt.ItemDataRole(SortBySizeRole + 1)
ShotgunLinkedRole = QtCore.Qt.ItemDataRole(SortByTypeRole + 1)
SlackLinkedRole = QtCore.Qt.ItemDataRole(ShotgunLinkedRole + 1)

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


def get_rsc(rel_path):
    """Return a resource item from the `rsc` directory.

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

    """
    if not common.typecheck_on:
        return

    if isinstance(_type, tuple):
        if not any([isinstance(value, type(f) if f is None else f) for f in _type]):
            _types = '" or "'.join([f.__name__ for f in _type])
            raise TypeError(
                f'Invalid type. Expected "{_types}", got "{type(value).__name__}"'
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
            key = key.lstrip('/')
            break

    if key in common.hashes:
        return common.hashes[key]

    # Otherwise, we calculate, save and return the digest
    common.hashes[key] = hashlib.md5(key.encode('utf8')).hexdigest()
    return common.hashes[key]


def error(func):
    """Function decorator used to handle exceptions and report them to the user.

    """

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            # Remove decorator(s) from the traceback stack
            exc_type, exc_value, exc_traceback = sys.exc_info()
            while 'wrapper' in exc_traceback.tb_frame.f_code.co_name:
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

    return func_wrapper


def debug(func):
    """Function decorator used to log a debug message.
    No message will be logged, unless :attr:`bookmarks.common.debug_on` is set to
    True.

    """
    DEBUG_MESSAGE = '{trace}(): Executed in {time} secs.'
    DEBUG_SEPARATOR = ' --> '

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
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
                DEBUG_MESSAGE.format(
                    trace=DEBUG_SEPARATOR.join(trace),
                    time=time.time() - t
                )
            )

    return func_wrapper


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
    if common.get_platform() == common.PlatformWindows:
        paths = os.environ['PATH'].split(';')
        paths = {os.path.normpath(f).rstrip('\\')
                 for f in paths if os.path.isdir(f)}

        for path in paths:
            for entry in os.scandir(path):
                if entry.name.lower().startswith(name):
                    return QtCore.QFileInfo(entry.path).filePath()

    return None


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
    t = repr(QtCore.QThread.currentThread())
    return '/'.join(args) + t


def sort_words(s):
    return ', '.join(sorted(re.findall(r"[\w']+", s)))


class DataDict(dict):
    """A weakref compatible dictionary used to store item data.

    """

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
    """
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
