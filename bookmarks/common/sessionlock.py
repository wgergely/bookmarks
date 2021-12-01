# -*- coding: utf-8 -*-
"""Module defines the classes and methods needed to set and edit session lock
files.

Bookmarks understand two session locks related to how active paths are read and
set. When `common.active_mode` is `common.SyncronisedActivePaths` bookmarks
will save active paths in the `user_settings`, as expected.

However, when multiple Bookmarks instances are running this poses a problem,
because instances will mutually overwrite each other's active path common.

Hence, when a second Bookmarks instance is launched `common.active_mode` is
automatically set to `common.PrivateActivePaths`. When this mode is active, the
initial active path values are read on startup `user_settings` will no longer
be modified. Instead, the paths will be saved into a private data container.

To toggle between  private active paths, and the ones stored in `user_settings`
see `actions.toggle_active_mode`.

`ToggleSessionModeButton` is a UI element used by the user to togge between
these modes.

"""
import os
import re
import psutil

from PySide2 import QtCore

from . import common


FORMAT = 'lock'
PREFIX = 'session_lock'
LOCK_PATH = '{root}/{product}/{prefix}_{pid}.{ext}'
LOCK_DIR = '{root}/{product}'


def get_lock_path():
    return LOCK_PATH.format(
        root=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        product=common.product,
        prefix=PREFIX,
        pid=os.getpid(),
        ext=FORMAT
    )


def prune_lock():
    """Removes stale lock files not associated with current PIDs.

    """
    path = LOCK_DIR.format(
        root=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        product=common.product,
    )

    r = r'{prefix}_([0-9]+)\.{ext}'.format(
        prefix=PREFIX,
        ext=FORMAT
    )
    pids = psutil.pids()
    for entry in os.scandir(path):
        if entry.is_dir():
            continue

        match = re.match(r, entry.name.lower())
        if not match:
            continue

        pid = int(match.group(1))
        path = entry.path.replace('\\', '/')
        if pid not in pids:
            if not QtCore.QFile(path).remove():
                raise RuntimeError('Failed to remove a lockfile.')


def init_lock():
    """Initialises the Bookmark's session lock.

    We'll check all lockfiles and to see if there's already a
    SyncronisedActivePaths session. As we want only one session controlling
    the active path settings we'll set all subsequent application sessions
    to be PrivateActivePaths (when PrivateActivePaths is on, all active path
    settings will be kept in memory, instead of writing them out to the
    disk).

    """
    path = LOCK_DIR.format(
        root=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        product=common.product,
    )
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
            # set to `SyncronisedActivePaths`, we'll set this session to be
            # in PrivateActivePaths as we don't want sessions to be able
            # to set their environent independently:
            if data == common.SyncronisedActivePaths:
                common.active_mode = common.PrivateActivePaths
                return write_current_mode_to_lock()

    # Otherwise, set the default value
    common.active_mode = common.SyncronisedActivePaths
    return write_current_mode_to_lock()


@QtCore.Slot()
@common.error
@common.debug
def write_current_mode_to_lock(*args, **kwargs):
    """Write the current mode this session's lock file.

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
