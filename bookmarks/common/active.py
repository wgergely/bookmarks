"""
The active module manages currently active path segments.

An item is considered active when, the item path segments are set in the active module. The active module
provides functions to get and set active path segments. To get active path segments, use :func:`active`:

.. code-block:: python

    from bookmarks import common

    # Gets the active asset path segment, for example, 'SEQ010/SH010'
    asset = common.active('asset')

    # Gets the full path up to the asset segment, for example, '/MyServer/MyJob/Shots/SEQ010/SH010'
    asset_path = common.active('asset', path=True)

    # Gets all path segments leading up to the asset segment, for example,
    # ('MyServer', 'MyJob', 'Shots', 'SEQ010/SH010')
    asset_segments = common.active('asset', args=True)


To set active path segments, use :func:`set_active`:

.. code-block:: python

    from bookmarks import common

    # Sets the active asset path segment to 'SEQ010/SH010'
    common.set_active('asset', 'SEQ010/SH020')

    # Unsets the active asset path segment
    common.set_active('asset', None)


"""

import collections
import enum
import os
import re
import threading

import psutil
from PySide2 import QtCore

from .. import common, log

__all__ = [
    'ActiveMode',
    'ActivePathSegmentTypes',
    'get_active_overrides_from_env',
    'init_active',
    'verify_path',
    'active',
    'set_active',
    'init_active_mode',
    'get_lock_path',
    'get_lock_dir',
    'prune_lock',
    'remove_lock',
    'write_current_mode_to_lock',
]

EXT = 'lock'
BASENAME = 'session_lock'
LOCK_DIR = f'{QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.GenericDataLocation)}/{common.product}/'
LOCK_PATH = f'{LOCK_DIR}/{BASENAME}_{{pid}}.{EXT}'
LOCK_REGEX = re.compile(rf'{BASENAME}_(\d+)\.{EXT}', re.IGNORECASE)

ActivePathSegmentTypes = (
    'server',
    'job',
    'root',
    'asset',
    'task',
    'file',
)
_ActivePathSegmentTypes = {f for f in ActivePathSegmentTypes}


class ActiveMode(enum.IntEnum):
    """
    Represents the mode determining how active paths are read and written.

    Attributes:
        Synchronized (int): Active paths synchronized with user settings.
        Private (int): Active paths are private to this session, not saved to user settings.
        Explicit (int): Active paths overridden by environment variables.
    """
    Synchronized = 1
    Private = 2
    Explicit = 3


# Use an RLock to allow nested acquisitions in the same thread without deadlocks.
_lock = threading.RLock()


def get_lock_path(pid=None):
    """
    Get the lock file path for the given PID.

    Args:
        pid (int, optional): The process ID to use. If not provided, the current PID is used.

    Returns:
        str: The lock file path.
    """
    pid = pid or os.getpid()
    return LOCK_PATH.format(pid=pid)


def get_lock_dir():
    """
    Get the directory path where lock files are stored.

    Returns:
        str: The lock directory path.
    """
    return LOCK_DIR


def get_active_overrides_from_env():
    """
    Get explicit active path overrides from environment variables.

    The environment variables are of the form:
    ``Bookmarks_ACTIVE_<SEGMENT_NAME_UPPER>``.

    Returns:
        dict: A dictionary keyed by segment name (e.g., 'server', 'job'), with values from environment overrides or None.
    """
    _v = collections.OrderedDict()
    for k in ActivePathSegmentTypes:
        v = os.environ.get(f'Bookmarks_ACTIVE_{k.upper()}', None)
        _v[k] = v
    return _v


def init_active(clear_all=True, load_settings=True, load_private=True, load_overrides=True):
    """
    Initialize the active paths, applying user settings and explicit overrides as necessary.

    This function sets up the global :data:`common.active_paths` dictionary for each :class:`ActiveMode`.
    If requested, it loads user settings, private paths, and explicit overrides from environment variables.
    After loading and applying overrides, it calls :func:`verify_path` to ensure validity.

    Args:
        clear_all (bool, optional): If True, reset all active paths before initialization.
        load_settings (bool, optional): If True, load synchronized paths from user settings.
        load_private (bool, optional): If True, copy synchronized paths into private mode.
        load_overrides (bool, optional): If True, apply explicit overrides from environment variables.

    Raises:
        ValueError: If user settings are requested but not initialized.
    """
    with _lock:
        if clear_all or common.active_paths is None:
            common.active_paths = {}
            for mode in ActiveMode:
                common.active_paths[mode] = collections.OrderedDict()
            for mode in ActiveMode:
                for k in ActivePathSegmentTypes:
                    common.active_paths[mode][k] = None

        if load_overrides:
            env_overrides = get_active_overrides_from_env()
            for k, v in env_overrides.items():
                common.active_paths[ActiveMode.Explicit][k] = v
            verify_path(ActiveMode.Explicit)

        if load_settings:
            if not common.settings:
                raise ValueError('User settings not initialized')
            common.settings.sync()
            for k in ActivePathSegmentTypes:
                v = common.settings.value(f'active/{k}')
                v = v if isinstance(v, str) and v else None
                common.active_paths[ActiveMode.Synchronized][k] = v
            verify_path(ActiveMode.Synchronized)

        if load_private:
            for k in ActivePathSegmentTypes:
                common.active_paths[ActiveMode.Private][k] = common.active_paths[ActiveMode.Synchronized][k]
            verify_path(ActiveMode.Private)

        # Apply explicit overrides
        for k in ActivePathSegmentTypes:
            if common.active_paths[ActiveMode.Explicit][k]:
                common.active_paths[ActiveMode.Synchronized][k] = common.active_paths[ActiveMode.Explicit][k]
                common.active_paths[ActiveMode.Private][k] = common.active_paths[ActiveMode.Explicit][k]
        verify_path(ActiveMode.Synchronized)
        verify_path(ActiveMode.Private)


def verify_path(mode):
    """
    Verify the active path segments of the given mode, ensuring they form a valid path.

    For each segment in the specified mode, this function checks whether the partial path exists.
    If it does not, the invalid segment is cleared (set to None), ensuring that partial or incorrect paths
    do not persist.

    Args:
        mode (ActiveMode): The active mode to verify.

    See Also:
        - :func:`init_active`
        - :func:`set_active`
    """
    with _lock:
        p = ''
        for k in ActivePathSegmentTypes:
            if common.active_paths[mode][k]:
                p += common.active_paths[mode][k]
            if not os.path.exists(p):
                common.active_paths[mode][k] = None
                if mode == ActiveMode.Synchronized:
                    common.settings.setValue(f'active/{k}', None)
            p += '/'


@common.debug
def active(k, path=False, args=False, mode=None):
    """
    Retrieve an active path segment or constructed path.

    This function returns the currently active path segment for the given key. It can also return
    the full path up to that segment (if `path=True`) or all segments leading up to it (if `args=True`).

    When explicit overrides (environment variables) are set, they take precedence over synchronized or private values.

    Args:
        k (str): One of 'server', 'job', 'root', 'asset', 'task', 'file'.
        path (bool, optional): If True, returns the full path up to this segment.
        args (bool, optional): If True, returns all path segments leading up to this segment as a tuple.
        mode (ActiveMode, optional): The mode to read from. If None, the current :data:`common.active_mode` is used.

    Returns:
        str or tuple:
            - If `path=True`, returns a string representing the full path or None if incomplete.
            - If `args=True`, returns a tuple of segments or None if incomplete.
            - Otherwise, returns the active value for the given segment key or None.

    Raises:
        KeyError: If `k` is not a valid segment name.

    See Also:
        - :func:`set_active`
        - :func:`init_active`
    """
    if k not in _ActivePathSegmentTypes:
        raise KeyError(f'Invalid active key "{k}", must be one of "{ActivePathSegmentTypes}"')
    with _lock:
        mode = mode or common.active_mode

        if path or args:
            idx = ActivePathSegmentTypes.index(k)
            v = tuple(
                common.active_paths[ActiveMode.Explicit][seg] or common.active_paths[mode][seg]
                for seg in ActivePathSegmentTypes[:idx + 1]
            )
            if path:
                return '/'.join(v) if all(v) else None
            if args:
                return v if all(v) else None

        return common.active_paths[ActiveMode.Explicit][k] or common.active_paths[mode][k]


@common.debug
def set_active(seg, v, mode=None, force=False):
    """
    Set the specified path segment in the given mode (or current mode if not specified).

    By default, this respects the current active mode and any explicit overrides set via environment variables.
    If an explicit override is present and `force=False`, this call is ignored. If `force=True`, the override is bypassed.

    After updating, :func:`verify_path` is called to ensure validity. If the mode is :attr:`ActiveMode.Synchronized`,
    the new value is saved to user settings.

    Args:
        seg (str): The segment key to modify (e.g., 'server', 'job', 'root', 'asset', 'task', 'file').
        v (str or None): The new segment value. Use None to clear the segment.
        mode (ActiveMode, optional): The mode to update. If None, the current :data:`common.active_mode` is used.
        force (bool, optional): If True, overwrite segment even if an explicit override exists.

    Raises:
        KeyError: If `seg` isn't a valid segment key.

    See Also:
        - :func:`active`
        - :func:`init_active`
    """
    if seg not in _ActivePathSegmentTypes:
        raise KeyError(f'Invalid active key "{seg}", must be one of "{ActivePathSegmentTypes}"')

    with _lock:
        mode = mode or common.active_mode
        if mode == ActiveMode.Explicit and not force:
            log.warning(__name__, 'Cannot set __name__, active path segment in explicit mode')
            return

        if common.active_paths[ActiveMode.Explicit][seg] and not force:
            log.warning(__name__, f'Cannot set active path segment "{seg}" when an explicit override is set')
            return

        # Remove the explicit override
        if force and common.active_paths[ActiveMode.Explicit][seg]:
            common.active_paths[ActiveMode.Explicit][seg] = None

        common.active_paths[mode][seg] = v
        verify_path(mode)

    # Emit signals outside lock to avoid deadlocks
    common.signals.activeChanged.emit()

    # Save to settings if synchronized mode
    if mode == ActiveMode.Synchronized:
        with _lock:
            common.settings.setValue(f'active/{seg}', v)


def prune_lock():
    """
    Remove stale lock files that belong to processes no longer running.

    This function scans the lock directory, identifies any lockfiles whose PIDs are not currently active,
    and removes them. If removal fails, a RuntimeError is raised.

    See Also:
        - :func:`remove_lock`
        - :func:`init_active_mode`
    """
    pids = psutil.pids()

    with os.scandir(LOCK_DIR) as it:
        for entry in it:
            if entry.is_dir():
                continue
            match = LOCK_REGEX.match(entry.name)
            if not match:
                continue
            pid = int(match.group(1))
            path = entry.path.replace('\\', '/')
            f = QtCore.QFile(path)
            if pid not in pids and f.exists():
                if not f.remove():
                    log.error(__name__, f'Failed to remove lockfile: {path}')
                    raise RuntimeError(f'Failed to remove lockfile: {path}')


def init_active_mode():
    """
    Initialize and determine the current active mode from available lockfiles.

    If a lockfile exists with a synchronized mode, we default to :attr:`ActiveMode.Private`.
    Otherwise, the mode defaults to :attr:`ActiveMode.Synchronized`.

    This function:
    - Calls :func:`prune_lock` to remove stale lockfiles.
    - Checks existing lockfiles to determine the mode.
    - Writes the determined mode to a lockfile with :func:`write_current_mode_to_lock`.

    Returns:
        str or None: The path to the written lockfile or None if an error occurred.

    Raises:
        RuntimeError: If the active mode is already initialized.

    See Also:
        - :func:`prune_lock`
        - :func:`write_current_mode_to_lock`
    """
    with _lock:
        if common.active_mode is not None:
            raise RuntimeError(f'Already initialized as "{common.active_mode}"!')

    prune_lock()

    with _lock:
        with os.scandir(LOCK_DIR) as it:
            for entry in it:
                if entry.is_dir():
                    continue
                if not entry.name.endswith('.lock'):
                    continue
                with open(entry.path, 'r', encoding='utf8') as f:
                    data = f.read().strip()
                try:
                    data = int(data)
                except ValueError:
                    data = common.ActiveMode.Private

                if data == common.ActiveMode.Synchronized:
                    common.active_mode = common.ActiveMode.Private
                    break
                elif data == common.ActiveMode.Private:
                    # If you want invalid lock contents to always force Private mode:
                    common.active_mode = common.ActiveMode.Private
                    break
            else:
                common.active_mode = common.ActiveMode.Synchronized

    return write_current_mode_to_lock()


def remove_lock():
    """
    Remove the current session's lock file if it exists.

    If the lockfile can't be removed, an error is logged.

    See Also:
        - :func:`prune_lock`
        - :func:`init_active_mode`
    """
    path = LOCK_PATH.format(pid=os.getpid())
    f = QtCore.QFile(path)
    if f.exists():
        if not f.remove():
            log.error(__name__, 'Failed to remove lock file')


@QtCore.Slot()
@common.error
@common.debug
def write_current_mode_to_lock(*args, **kwargs):
    """
    Write the current active mode to this session's lockfile.

    This function ensures the lockfile's directory exists, then writes the current :data:`common.active_mode`
    as an integer. This allows other processes or sessions to detect this session's mode.

    Returns:
        str or None: The path to the written lockfile, or None if there was an error.

    See Also:
        - :func:`init_active_mode`
        - :func:`remove_lock`
        - :func:`prune_lock`
    """
    with _lock:
        mode_value = common.active_mode

    path = LOCK_PATH.format(pid=os.getpid())

    basedir = os.path.dirname(path)
    try:
        if not os.path.exists(basedir):
            os.makedirs(basedir)
    except OSError as e:
        log.error(__name__, f"Failed to create directories for lockfile: {basedir}\nError: {e}")
        return

    try:
        with open(path, 'w+', encoding='utf8') as f:
            f.write(str(mode_value))
    except IOError as e:
        log.error(__name__, f"Failed to write lockfile: {path}\nError: {e}")
        return

    return path
