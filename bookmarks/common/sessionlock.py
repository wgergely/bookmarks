# -*- coding: utf-8 -*-
"""Module defines the classes and methods needed to set and edit session lock
files.

Bookmarks has two session modes. When `common.active_mode` is
`common.SynchronisedActivePaths`, Bookmarks will save active paths in the user settings
file. However, when multiple Bookmarks instances are running this poses a problem,
because instances will mutually overwrite each other's active paths.

Hence, when a second Bookmarks instance is launched `common.active_mode` is
automatically set to `common.PrivateActivePaths`. When this mode is active, the initial
active path values are read from the user settings, but active paths changes won't be
saved to the user settings. Instead, the paths will be stored in a private data
container.

To toggle between the two modes see :func:`bookmarks.actions.toggle_active_mode` and
:class:`bookmarks.statusbar.ToggleSessionModeButton`.

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
    """Returns the path to the current session's lock file."""
    return LOCK_PATH.format(
        root=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        product=common.product,
        prefix=PREFIX,
        pid=os.getpid(),
        ext=FORMAT
    )


def prune_lock():
    """Removes stale lock files not associated with running PIDs.

    """
    path = LOCK_DIR.format(
        root=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        product=common.product,
    )

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


def init_lock():
    """Initialises the Bookmark's session lock.

    We'll check all lock-files and to see if there's already a
    ``SynchronisedActivePaths`` session. As we want only one session controlling
    the active path settings we'll set all subsequent application sessions
    to be ``PrivateActivePaths`` (when ``PrivateActivePaths`` is on, all active path
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
