"""Defines active path reading mode.

The app has two session modes. When `common.active_mode` is
`common.SynchronisedActivePaths`, the app will save active paths in the user settings
file. However, when multiple app instances are running, this poses a problem,
because instances will mutually overwrite each other's active paths.

Hence, when a second app instance is launched `common.active_mode` is
automatically set to `common.PrivateActivePaths`. When this mode is active, the initial
active path values are read from the user settings, but active paths changes won't be
saved to the settings file.

The session mode will also be set to `common.PrivateActivePaths` if any of the
`BOOKMARKS_ACTIVE_SERVER`, `BOOKMARKS_ACTIVE_JOB`, `BOOKMARKS_ACTIVE_ROOT`,
`BOOKMARKS_ACTIVE_ASSET` and `BOOKMARKS_ACTIVE_TASK` environment variables are set
as these will take precedence over the user settings.

To toggle between the two modes use :func:`bookmarks.actions.toggle_active_mode`. Also see
:class:`bookmarks.statusbar.ToggleSessionModeButton`.

"""
import os
import re

import psutil

try:
    from PySide6 import QtWidgets, QtGui, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore

from . import common

FORMAT = 'lock'
PREFIX = 'session_lock'
LOCK_PATH = '{root}/{product}/{prefix}_{pid}.{ext}'
LOCK_DIR = '{root}/{product}'


def get_lock_path():
    """Returns the path to the current session's lock file."""
    return LOCK_PATH.format(
        root=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation
        ), product=common.product, prefix=PREFIX, pid=os.getpid(), ext=FORMAT
    )


def prune_lock():
    """Removes stale lock files not associated with running PIDs.

    """
    path = LOCK_DIR.format(
        root=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation
        ), product=common.product, )

    r = fr'{PREFIX}_([0-9]+)\.{FORMAT}'
    pids = psutil.pids()

    for entry in os.scandir(path):
        if entry.is_dir():
            continue

        match = re.match(r, entry.name)

        if not match:
            continue

        pid = int(match.group(1))
        path = entry.path.replace('\\', '/')
        if pid not in pids:
            if not QtCore.QFile(path).remove():
                raise RuntimeError('Failed to remove a lockfile.')


def init_active_mode():
    """Initialises the Bookmark's active path reading mode.

    We define two modes, ``SynchronisedActivePaths`` (when Bookmarks is in sync with the user settings) and
    ``PrivateActivePaths`` when the Bookmarks sessions set the active paths values internally without changing the user
    settings.

    The session mode will be initialised to a default value based on the following conditions:

        If any of the `BOOKMARKS_ACTIVE_SERVER`, `BOOKMARKS_ACTIVE_JOB`, `BOOKMARKS_ACTIVE_ROOT`,
        `BOOKMARKS_ACTIVE_ASSET` and `BOOKMARKS_ACTIVE_TASK` environment values have valid values, the session will
        automatically be marked ``PrivateActivePaths``.

        If the environment has not been set but there's already an active ``SynchronisedActivePaths`` session
        running, the current session will be set to ``PrivateActivePaths``.

        Any sessions that doesn't have environment values set and does not find synchronized session lock files will
        be marked ``SynchronisedActivePaths``.


    """
    # Remove stale lock files
    prune_lock()

    # Check if any of the environment variables are set
    _env_active_server = os.environ.get('BOOKMARKS_ACTIVE_SERVER', None)
    _env_active_job = os.environ.get('BOOKMARKS_ACTIVE_JOB', None)
    _env_active_root = os.environ.get('BOOKMARKS_ACTIVE_ROOT', None)
    _env_active_asset = os.environ.get('BOOKMARKS_ACTIVE_ASSET', None)
    _env_active_task = os.environ.get('BOOKMARKS_ACTIVE_TASK', None)

    if any((_env_active_server, _env_active_job, _env_active_root, _env_active_asset, _env_active_task)):
        common.active_mode = common.PrivateActivePaths
        return write_current_mode_to_lock()

    path = LOCK_DIR.format(
        root=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation
        ), product=common.product, )

    # Iterate over all lock files and check their contents
    for entry in os.scandir(path):
        if entry.is_dir():
            continue

        if not entry.name.endswith('.lock'):
            continue

        # Read the contents
        with open(entry.path, 'r', encoding='utf8') as f:
            data = f.read()

            try:
                data = int(data.strip())
            except:
                data = common.PrivateActivePaths

            # If we encounter any session locks that are currently
            # set to `SynchronisedActivePaths`, we'll set this session to be
            # in PrivateActivePaths as we don't want sessions to be able
            # to set their environment independently:
            if data == common.SynchronisedActivePaths:
                common.active_mode = common.PrivateActivePaths
                return write_current_mode_to_lock()

    # Otherwise, set the default value
    common.active_mode = common.SynchronisedActivePaths
    return write_current_mode_to_lock()


def remove_lock():
    """Removes the session lock file.

    """
    f = QtCore.QFile(get_lock_path())
    if f.exists():
        if not f.remove():
            print('Failed to remove lock file')


@QtCore.Slot()
@common.error
@common.debug
def write_current_mode_to_lock(*args, **kwargs):
    """Write this session's current mode to the lock file.

    """
    # Create our lockfile
    path = get_lock_path()

    # Create all folders
    basedir = os.path.dirname(path)
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    # Write current mode to the lockfile
    with open(path, 'w+', encoding='utf8') as f:
        f.write(f'{common.active_mode}')

    return path
