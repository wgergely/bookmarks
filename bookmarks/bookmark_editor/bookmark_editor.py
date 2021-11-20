# -*- coding: utf-8 -*-
"""Sub-editor widget used by the Bookmark Editor to add and toggle bookmarks.

"""
import functools
from PySide2 import QtCore, QtGui, QtWidgets

import _scandir

from .. import common
from .. import log
from .. import images
from .. import contextmenu
from .. import ui
from .. import shortcuts
from .. import actions


class BookmarkContextMenu(contextmenu.BaseContextMenu):
    """Custom context menu used to control the list of saved servers.

    """

    def setup(self):
        self.add_menu()
        self.separator()
        if isinstance(self.index, QtWidgets.QListWidgetItem) and self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.bookmark_properties_menu()
            self.reveal_menu()
        self.separator()
        self.refresh_menu()

    def add_menu(self):
        self.menu['Add Bookmark...'] = {
            'action': self.parent().add,
            'icon': self.get_icon('add', color=common.GREEN)
        }

    def reveal_menu(self):
        self.menu[contextmenu.key()] = {
            'text': 'Reveal',
            'action': functools.partial(actions.reveal, self.index.data(QtCore.Qt.UserRole) + '/.'),
            'icon': self.get_icon('folder')
        }

    def refresh_menu(self):
        self.menu['Refresh'] = {
            'action': self.parent().init_data,
            'icon': self.get_icon('refresh')
        }

    def bookmark_properties_menu(self):
        server = self.parent().server
        job = self.parent().job
        root = self.index.data(QtCore.Qt.DisplayRole)

        self.menu['Properties'] = {
            'text': 'Edit Properties...',
            'action': functools.partial(actions.edit_bookmark, server, job, root),
            'icon': self.get_icon('settings')
        }


class BookmarkListWidget(ui.ListWidget):
    """Simple list widget used to add and remove servers to/from the local
    settings.

    """
    loaded = QtCore.Signal()

    def __init__(self, parent=None):
        super(BookmarkListWidget, self).__init__(
            default_message='No bookmarks found.',
            parent=parent
        )

        self._interrupt_requested = False

        self.setWindowTitle('Bookmark Editor')
        self.setObjectName('BookmarkEditor')

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.setMinimumWidth(common.WIDTH() * 0.33)

        self._connect_signals()
        self.init_shortcuts()

    def init_shortcuts(self):
        shortcuts.add_shortcuts(self, shortcuts.BookmarkEditorShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.BookmarkEditorShortcuts)
        connect(shortcuts.AddItem, self.add)

    def _connect_signals(self):
        super(BookmarkListWidget, self)._connect_signals()
        self.itemClicked.connect(self.toggle_item_state)
        self.itemActivated.connect(self.toggle_item_state)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def toggle_item_state(self, item):
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
            actions.remove_bookmark(
                self.server,
                self.job,
                item.data(QtCore.Qt.DisplayRole)
            )

        elif item.checkState() == QtCore.Qt.Unchecked:
            item.setCheckState(QtCore.Qt.Checked)
            actions.add_bookmark(
                self.server,
                self.job,
                item.data(QtCore.Qt.DisplayRole)
            )

    @common.debug
    @common.error
    @QtCore.Slot()
    def add(self, *args, **kwargs):
        if not self.server or not self.job:
            return

        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            'Pick a new bookmark folder',
            self.server + '/' + self.job,
            QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
        )
        if not path:
            return
        if not QtCore.QDir(path).mkdir(common.BOOKMARK_ROOT_DIR):
            log.error('Failed to create bookmark.')

        name = path.split(self.job)[-1].strip('/').strip('\\')

        for n in range(self.count()):
            item = self.item(n)
            if item.data(QtCore.Qt.DisplayRole) == name:
                ui.MessageBox(
                    '"{}" is already a bookmark.'.format(name),
                    'The selected folder is already a bookmark, skipping.'
                ).open()
                return

        item = QtWidgets.QListWidgetItem()
        item.setFlags(
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsUserCheckable
        )
        item.setCheckState(QtCore.Qt.Unchecked)
        item.setData(QtCore.Qt.DisplayRole, name)
        item.setData(QtCore.Qt.UserRole, path)
        size = QtCore.QSize(
            0,
            common.MARGIN() * 2
        )
        item.setSizeHint(size)
        self.insertItem(self.count(), item)
        self.set_item_state(item)
        self.setCurrentItem(item)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = BookmarkContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    @QtCore.Slot(str)
    def job_changed(self, server, job):
        """This slot responds to any job changes."""
        if server is None or job is None:
            self.clear()
            return

        if server == self.server and job == self.job:
            return

        self.server = server
        self.job = job
        self.init_data()

    @QtCore.Slot()
    def init_data(self):
        """Loads a list of bookmarks found in the current job.

        """
        self.clear()

        if not self.server or not self.job:
            self.loaded.emit()
            return

        path = self.server + '/' + self.job
        dirs = self.find_bookmark_dirs(path, -1, 4, [])
        self._interrupt_requested = False

        for d in dirs:
            item = QtWidgets.QListWidgetItem()
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                # QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsUserCheckable
            )
            item.setCheckState(QtCore.Qt.Unchecked)
            name = d.split(self.job)[-1].strip('/').strip('\\')
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(QtCore.Qt.UserRole, d)
            size = QtCore.QSize(
                0,
                common.MARGIN() * 2
            )
            item.setSizeHint(size)
            self.insertItem(self.count(), item)
            self.set_item_state(item)

        self.loaded.emit()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def set_item_state(self, item):
        """Checks if the item is part of the current bookmark set and set the
        `checkState` and icon accordingly.

        Args:
            item(QtWidgets.QListWidgetItem):    The item to check.

        """
        from . import job_editor
        pixmap = job_editor.get_job_thumbnail(self.server + '/' + self.job)

        if item.data(QtCore.Qt.UserRole) in [f for f in common.BOOKMARKS]:
            item.setCheckState(QtCore.Qt.Checked)

            if pixmap.isNull():
                pixmap = images.ImageCache.get_rsc_pixmap(
                    'check', common.GREEN, common.ROW_HEIGHT() * 0.8)

        else:
            item.setCheckState(QtCore.Qt.Unchecked)

            if pixmap.isNull():
                pixmap = images.ImageCache.get_rsc_pixmap(
                    'close', common.DARK_BG, common.ROW_HEIGHT() * 0.8)

        icon = QtGui.QIcon()

        icon.addPixmap(pixmap, QtGui.QIcon.Normal)
        icon.addPixmap(pixmap, QtGui.QIcon.Selected)
        icon.addPixmap(pixmap, QtGui.QIcon.Active)
        icon.addPixmap(pixmap, QtGui.QIcon.Disabled)
        item.setData(QtCore.Qt.DecorationRole, icon)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self._interrupt_requested = True

    def find_bookmark_dirs(self, path, count, limit, arr, emit_progress=True):
        """Recursive scanning function for finding bookmark folders
        inside the given path.

        """
        QtWidgets.QApplication.instance().processEvents()

        if self._interrupt_requested:
            return arr

        count += 1
        if count > limit:
            return arr

        # We'll let unreadable paths fail silently
        try:
            it = _scandir.scandir(path)
        except:
            return arr

        if emit_progress:
            self.progressUpdate.emit(
                'Scanning for bookmarks, please wait...\n{}'.format(path))

        for entry in it:
            if not entry.is_dir():
                continue
            path = entry.path.replace('\\', '/')
            if [f for f in arr if f in path]:
                continue

            if entry.name == common.BOOKMARK_ROOT_DIR:
                arr.append('/'.join(path.split('/')[:-1]))

            self.find_bookmark_dirs(path, count, limit, arr)

        if emit_progress:
            self.progressUpdate.emit('')

        return sorted(arr)
