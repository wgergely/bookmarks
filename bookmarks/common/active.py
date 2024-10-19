import collections
import enum
import os
import re

import psutil
from PySide2 import QtCore

from .. import common

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
    Synchronized = 0
    Private = 1
    Overridden = 2


def init_active(clear_all=True, load_settings=True, load_private=True, load_overrides=True):
    if clear_all:
        # Initialize the active_paths object
        common.active_paths = {
            ActiveMode.Synchronized: collections.OrderedDict(),
            ActiveMode.Private: collections.OrderedDict(),
        }

        # Init none values
        for k in (ActiveMode.Synchronized, ActiveMode.Private):
            for f in ActivePathSegmentTypes:
                common.active_paths[k][f] = None

    if load_settings:
        # Load values from the user settings file
        if not common.settings:
            raise ValueError('User settings not initialized')

        common.settings.sync()
        for k in ActivePathSegmentTypes:
            v = common.settings.value(f'active/{k}')
            v = v if isinstance(v, str) and v else None
            common.active_paths[common.ActiveMode.Synchronized][k] = v
        verify_path(common.ActiveMode.Synchronized)

    if load_private:
        # Copy values from the synchronized paths to the private paths
        for k in ActivePathSegmentTypes:
            common.active_paths[ActiveMode.Private][k] = common.active_paths[ActiveMode.Synchronized][k]
        verify_path(ActiveMode.Private)

    if load_overrides:
        # Load any active path overrides
        for k in ActivePathSegmentTypes:
            v = getattr(common, f'active_{k}_override', None)
            if v:
                common.active_paths[ActiveMode.Synchronized][k] = v
                common.active_paths[ActiveMode.Private][k] = v
        verify_path(ActiveMode.Synchronized)
        verify_path(ActiveMode.Private)


def verify_path(active_mode):
    """Verify the active path values and unset any item, that refers to an invalid path.

    Args:
        active_mode (int): One of ``SynchronisedActivePaths`` or ``Pr.

    """
    p = str()
    for k in ActivePathSegmentTypes:
        if common.active_paths[active_mode][k]:
            p += common.active_paths[active_mode][k]
        if not os.path.exists(p):
            common.active_paths[active_mode][k] = None
            if active_mode == ActiveMode.Synchronized:
                common.settings.setValue(f'active/{k}', None)
        p += '/'


@common.debug
def active(k, path=False, args=False, mode=None):
    """
    Get an active path segment for the given key.

    It can return the full path or the individual components that make up the path. The function also considers any
    override values that may be set.

    Active values are fetched either from the user settings if no overrides are present, or the current
    `active_{k}_override` value if it exists. These are set automatically when the app is initialized either by
    passing explicit values to the `initialize` function or by setting the `Bookmarks_ACTIVE_{KEY}` environment
    variables.

    Args:
        k (str): One of the following segment names: 'server', 'job', 'root', 'asset', 'task', 'file'.
        path (bool, optional): If True, returns the full path to the active item.
        args (bool, optional): If True, returns all components that make up the active path.
        mode (int, optional): One of ActiveMode.Synchronized, ActiveMode.Private.

    Returns:
        str: If path is True, returns the full path to the active item or None if the path can't be constructed.
        tuple: If args is True, returns all components that make up the active path or None if the args can't be
            constructed.
        str: If neither path nor args is True, returns the active value for the given key.

    Raises:
        KeyError: If the provided key is not valid.

    """
    if k not in _ActivePathSegmentTypes:
        raise KeyError(f'Invalid active key "{k}", must be one of "{ActivePathSegmentTypes}"')

    overrides = {}
    for _k in ActivePathSegmentTypes:
        overrides[_k] = getattr(common, f'active_{_k}_override', None)

    # Use the override value if it exists
    if path or args:
        _path = None
        _args = None
        idx = ActivePathSegmentTypes.index(k)

        if overrides[k] is not None:
            v = tuple(
                overrides[k]
                for k in ActivePathSegmentTypes[:idx + 1]
            )
        else:
            v = tuple(
                common.active_paths[common.active_mode][k]
                for k in ActivePathSegmentTypes[:idx + 1]
            )

        if path:
            _path = '/'.join(v) if all(v) else None
            if args:
                return _path, _args
            return _path

        if args:
            _args = v if all(v) else None
            if path:
                return _path, _args
            return _args

    # If there's a valid override for the given key, return that instead
    if overrides[k] is not None:
        return overrides[k]

    if mode is None:
        mode = common.active_mode
    return common.active_paths[mode][k]


@common.debug
def set_active(k, v):
    """Sets the given path as the active path segment for the given key.

    Args:
        k (str): An active key, for example, `'server'`.
        v (str or None): A path segment, for example, '//myserver/jobs'.

    """
    common.check_type(k, str)
    common.check_type(k, (str, None))

    # Bail if there's a valid override for the given key
    if getattr(common, f'active_{k}_override', None):
        return

    if k not in common.SECTIONS['active']:
        keys = '", "'.join(common.SECTIONS['active'])
        raise ValueError(
            f'Invalid active key. Key must be the one of "{keys}"'
        )

    common.active_paths[common.active_mode][k] = v
    common.signals.activeChanged.emit()
    if common.active_mode == common.ActiveMode.Synchronized:
        common.settings.setValue(f'active/{k}', v)


def prune_lock():
    """Removes stale lock files not associated with running PIDs."""
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
                    from . import log
                    log.error(f'Failed to remove lockfile: {path}')
                    raise RuntimeError(f'Failed to remove lockfile: {path}')


def init_active_mode():
    """Initialises the Bookmark's active path reading mode.

    Two modes exist: ``ActiveMode.Synchronized`` when Bookmarks is in sync with the user settings and
    ``ActiveMode.Private`` when the Bookmarks sessions set the active paths values internally without changing the user
    settings.
    """
    if common.active_mode is not None:
        raise RuntimeError(f'Already initialized as "{common.active_mode}"!')

    # Remove stale lock files
    prune_lock()

    # Check if any of the environment variables are set
    overrides = {k: getattr(common, f'active_{k.lower()}_override', None) or None
                 for k in common.ActivePathSegmentTypes}

    if any(overrides.values()):
        common.active_mode = common.ActiveMode.Overridden
        return write_current_mode_to_lock()

    # Iterate over all lock files and check their contents
    with os.scandir(LOCK_DIR) as it:
        for entry in it:
            if entry.is_dir():
                continue

            if not entry.name.endswith('.lock'):
                continue

            # Read the contents
            with open(entry.path, 'r', encoding='utf8') as f:
                data = f.read().strip()

            try:
                data = int(data)
            except ValueError:
                data = common.ActiveMode.Private

            # If we encounter any session locks set to ActiveMode.Synchronized
            if data == common.ActiveMode.Synchronized:
                common.active_mode = common.ActiveMode.Private
                return write_current_mode_to_lock()

    # Otherwise, set the default value
    common.active_mode = common.ActiveMode.Synchronized
    return write_current_mode_to_lock()


def remove_lock():
    """Removes the session lock file."""
    path = LOCK_PATH.format(pid=os.getpid())
    f = QtCore.QFile(path)
    if f.exists():
        if not f.remove():
            from . import log
            log.error('Failed to remove lock file')


@QtCore.Slot()
@common.error
@common.debug
def write_current_mode_to_lock(*args, **kwargs):
    """Write this session's current mode to the lock file."""
    path = LOCK_PATH.format(pid=os.getpid())

    # Create all folders
    basedir = os.path.dirname(path)
    try:
        if not os.path.exists(basedir):
            os.makedirs(basedir)
    except OSError as e:
        from . import log
        log.error(f"Failed to create directories for lockfile: {basedir}\nError: {e}")
        return

    # Write current mode to the lockfile
    try:
        with open(path, 'w+', encoding='utf8') as f:
            f.write(f'{common.active_mode}')
    except IOError as e:
        from . import log
        log.error(f"Failed to write lockfile: {path}\nError: {e}")
        return

    return path
