# -*- coding: utf-8 -*-
"""Module defines the classes and methods needed to set and edit session lock
files.

Bookmarks understand two session locks related to how active paths are read and
set. When `common.SESSION_MODE` is `common.SyncronisedActivePaths` bookmarks
will save active paths in the `local_settings`, as expected.

However, when multiple Bookmarks instances are running this poses a problem,
because instances will mutually overwrite each other's active path settings.

Hence, when a second Bookmarks instance is launched `common.SESSION_MODE` is
automatically set to `common.PrivateActivePaths`. When this mode is active, the
initial active path values are read on startup `local_settings` will no longer
be modified. Instead, the paths will be saved into a private data container.

To toggle between  private active paths, and the ones stored in `local_settings`
see `actions.toggle_session_mode`.

`ToggleSessionModeButton` is a UI element used by the user to togge between
these modes.

"""
import os
import re
import psutil
import _scandir

from PySide2 import QtCore, QtWidgets, QtGui

from . import common
from . import ui
from . import actions
from . import settings
from . import images


FORMAT = u'lock'
PREFIX = u'session_lock'
LOCK_PATH = u'{root}/{product}/{prefix}_{pid}.{ext}'
LOCK_DIR = u'{root}/{product}'


def prune():
    """Removes stale lock files not associated with current PIDs.

    """
    path = LOCK_DIR.format(
        root=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        product=common.PRODUCT,
    )

    r = ur'{prefix}_([0-9]+)\.{ext}'.format(
        prefix=PREFIX,
        ext=FORMAT
    )
    pids = psutil.pids()
    for entry in _scandir.scandir(path):
        if entry.is_dir():
            continue

        match = re.match(r, entry.name.lower())
        if not match:
            continue

        pid = int(match.group(1))
        path = entry.path.replace(u'\\', u'/')
        if pid not in pids:
            if not QtCore.QFile(path).remove():
                raise RuntimeError('Failed to remove a lockfile.')


def init(pid=None):
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
        product=common.PRODUCT,
    )

    # Set the pid
    if pid is None:
        pid = os.getpid()

    # Iterate over all lock files and check their contents
    for entry in _scandir.scandir(path):
        if entry.is_dir():
            continue

        if not entry.name.endswith(u'.lock'):
            continue

        # Read the contents
        with open(entry.path, 'r') as f:
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
                common.SESSION_MODE = common.PrivateActivePaths
                return write_current_mode_to_lock(pid)

    # Otherwise, set the default value
    common.SESSION_MODE = common.SyncronisedActivePaths
    return write_current_mode_to_lock(pid)


@common.error
@common.debug
def write_current_mode_to_lock(pid):
    """Write the current mode this session's lock file.

    """
    # Create our lockfile
    path = LOCK_PATH.format(
        root=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        product=common.PRODUCT,
        prefix=PREFIX,
        pid=pid,
        ext=FORMAT
    )

    # Create all folders
    basedir = os.path.dirname(path)
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    # Write current mode to the lockfile
    with open(path, 'w+') as f:
        f.write(u'{}'.format(common.SESSION_MODE))

    return path


class ToggleSessionModeButton(ui.ClickableIconButton):
    """Button used to toggle between Synronised and Private modes.

    """
    ContextMenu = None

    def __init__(self, parent=None):
        super(ToggleSessionModeButton, self).__init__(
            u'check',
            (common.GREEN, common.RED),
            common.MARGIN(),
            description=u'Click to toggle {}.'.format(
                common.PRODUCT),
            parent=parent
        )
        self.setMouseTracking(True)
        self.clicked.connect(actions.toggle_session_mode)
        common.signals.sessionModeChanged.connect(self.update)

    def pixmap(self):
        if common.SESSION_MODE == common.SyncronisedActivePaths:
            return images.ImageCache.get_rsc_pixmap('check', common.GREEN, self._size)
        if common.SESSION_MODE == common.PrivateActivePaths:
            return images.ImageCache.get_rsc_pixmap('crossed', common.RED, self._size)
        return images.ImageCache.get_rsc_pixmap('crossed', common.RED, self._size)

    def statusTip(self):
        if common.SESSION_MODE == common.SyncronisedActivePaths:
            return u'This session sets active paths. Click to toggle.'

        if common.SESSION_MODE == common.PrivateActivePaths:
            return u'This session does not modify active paths. Click to toggle.'

        return u'Invalid session lock.'

    def toolTip(self):
        return self.whatsThis()

    def whatsThis(self):
        return u'Private Active Paths:\n{}\n{}\n{}\n{}\n{}\n\n{}\n{}\n{}\n{}\n{}'.format(
            settings.instance(
            ).PRIVATE_SESSION_MODE_VALUES[settings.ServerKey],
            settings.instance().PRIVATE_SESSION_MODE_VALUES[settings.JobKey],
            settings.instance().PRIVATE_SESSION_MODE_VALUES[settings.RootKey],
            settings.instance().PRIVATE_SESSION_MODE_VALUES[settings.AssetKey],
            settings.instance().PRIVATE_SESSION_MODE_VALUES[settings.TaskKey],
            settings.active(settings.ServerKey),
            settings.active(settings.JobKey),
            settings.active(settings.RootKey),
            settings.active(settings.AssetKey),
            settings.active(settings.TaskKey),
        )
