# -*- coding: utf-8 -*-
"""Sub-editor widget used by
:class:`bookmarks.bookmark_editor.bookmark_editor_widget.BookmarkEditorWidget`
to add/remove bookmarks items to and from the user settings.

"""
import functools
import json
import os

from PySide2 import QtCore, QtWidgets

from .. import actions
from .. import common
from .. import contextmenu
from .. import log
from .. import shortcuts
from .. import ui


class BookmarkContextMenu(contextmenu.BaseContextMenu):
    def setup(self):
        self.add_menu()
        self.separator()
        if isinstance(
                self.index, QtWidgets.QListWidgetItem
        ) and self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.bookmark_properties_menu()
            self.reveal_menu()
            self.copy_json_menu()
        self.separator()
        self.refresh_menu()

    def add_menu(self):
        self.menu[contextmenu.key()] = {
            'text': 'Pick a new bookmark item...',
            'action': self.parent().add,
            'icon': ui.get_icon('add', color=common.color(common.GreenColor))
        }

    def reveal_menu(self):
        self.menu[contextmenu.key()] = {
            'text': 'Reveal',
            'action': functools.partial(
                actions.reveal, self.index.data(QtCore.Qt.UserRole) + '/.'
            ),
            'icon': ui.get_icon('folder')
        }

    def refresh_menu(self):
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'action': self.parent().init_data,
            'icon': ui.get_icon('refresh')
        }

    def bookmark_properties_menu(self):
        server = self.parent().window().server()
        job = self.parent().window().job()
        root = self.index.data(QtCore.Qt.DisplayRole)

        self.menu[contextmenu.key()] = {
            'text': 'Edit Properties...',
            'action': functools.partial(actions.edit_bookmark, server, job, root),
            'icon': ui.get_icon('settings')
        }

    def copy_json_menu(self):
        server = self.parent().window().server()
        job = self.parent().window().job()
        root = self.index.data(QtCore.Qt.DisplayRole)

        d = {
            f'{server}/{job}/{root}': {
                common.ServerKey: server,
                common.JobKey: job,
                common.RootKey: root
            }
        }
        s = json.dumps(d)

        self.menu[contextmenu.key()] = {
            'text': 'Copy as JSON',
            'action': functools.partial(
                QtWidgets.QApplication.clipboard().setText, s),
            'icon': ui.get_icon('copy')
        }


class BookmarkListWidget(ui.ListWidget):
    """Simple list widget used to add and remove servers to/from the local
    common.

    """
    loaded = QtCore.Signal()

    def __init__(self, parent=None):
        super(BookmarkListWidget, self).__init__(
            default_message='No items found.',
            parent=parent
        )

        self._interrupt_requested = False

        self.setWindowTitle('Bookmark Item Editor')
        self.setObjectName('BookmarkEditor')

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.setMinimumWidth(common.size(common.DefaultWidth) * 0.2)

        self._connect_signals()
        self.init_shortcuts()

    def init_shortcuts(self):
        shortcuts.add_shortcuts(self, shortcuts.BookmarkEditorShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.BookmarkEditorShortcuts
        )
        connect(shortcuts.AddItem, self.add)

    def _connect_signals(self):
        super()._connect_signals()

        self.itemActivated.connect(self.toggle_item_state)
        self.itemChanged.connect(
            lambda item: self.add_remove_bookmark(
                item.checkState(),
                item.data(QtCore.Qt.DisplayRole)
            )
        )

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def add_remove_bookmark(self, state, v):
        if state == QtCore.Qt.Checked:
            try:
                actions.add_bookmark(
                    self.window().server(),
                    self.window().job(),
                    v
                )
            except:
                log.error('Could not add bookmark')
        elif state == QtCore.Qt.Unchecked:
            try:
                actions.remove_bookmark(
                    self.window().server(),
                    self.window().job(),
                    v
                )
            except:
                log.error('Could not remove bookmark')
        else:
            raise ValueError('Invalid check state.')

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def toggle_item_state(self, item):
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
        elif item.checkState() == QtCore.Qt.Unchecked:
            item.setCheckState(QtCore.Qt.Checked)
        self.add_remove_bookmark(
            item.checkState(),
            item.data(QtCore.Qt.DisplayRole)
        )

    @common.debug
    @common.error
    @QtCore.Slot()
    def add(self, *args, **kwargs):
        if not self.window().server() or not self.window().job():
            return

        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            'Pick a new bookmark folder',
            self.window().job_path(),
            QtWidgets.QFileDialog.ShowDirsOnly |
            QtWidgets.QFileDialog.DontResolveSymlinks
        )

        if not path:
            return

        if self.window().job_path() not in path:
            raise RuntimeError('Bookmark item must be inside the current job folder.')

        if not QtCore.QDir(path).mkdir(common.bookmark_cache_dir):
            raise RuntimeError('Could not create bookmark')

        name = path[len(self.window().job_path()) + 1:]

        for n in range(self.count()):
            item = self.item(n)
            if item.data(QtCore.Qt.DisplayRole) == name:
                ui.MessageBox(
                    f'"{name}" is already a bookmark.'
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
            common.size(common.WidthMargin) * 2
        )
        item.setSizeHint(size)
        self.update_state(item)
        self.insertItem(self.count(), item)
        self.setCurrentItem(item)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = BookmarkContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    @QtCore.Slot()
    def init_data(self):
        """Loads a list of bookmarks found in the current job.

        """
        self.clear()

        if not self.window().job():
            return

        max_recursion = common.settings.value(
            common.SettingsSection,
            common.RecurseDepth
        )
        try:
            max_recursion = int(max_recursion)
        except:
            max_recursion = 3
        finally:
            max_recursion = 1 if max_recursion < 1 else max_recursion

        for name, path in self.item_generator(
                self.window().job_path(),
                max_recursion=max_recursion
        ):
            item = QtWidgets.QListWidgetItem()
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsUserCheckable
            )
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(QtCore.Qt.UserRole, path)
            item.setSizeHint(QtCore.QSize(0, common.size(common.WidthMargin) * 2))

            self.update_state(item)
            self.insertItem(self.count(), item)

        self.progressUpdate.emit('')

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def update_state(self, item):
        """Checks if the item is part of the current bookmark set and set the
        `checkState` and icon accordingly.

        Args:
            item(QtWidgets.QListWidgetItem):    The item to check.

        """
        self.blockSignals(True)
        if item.data(QtCore.Qt.UserRole) in list(common.bookmarks):
            item.setCheckState(QtCore.Qt.Checked)
        else:
            item.setCheckState(QtCore.Qt.Unchecked)
        self.blockSignals(False)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self._interrupt_requested = True

    def item_generator(self, path, recursion=0, max_recursion=3):
        """Recursive scanning function for finding bookmark folders
        inside the given path.

        """
        if self._interrupt_requested:
            return

        recursion += 1
        if recursion > max_recursion:
            return

        # We'll let unreadable paths fail silently
        try:
            it = os.scandir(path)
        except:
            return

        for entry in it:
            if not entry.is_dir():
                continue

            # yield the match
            path = entry.path.replace('\\', '/')
            self.progressUpdate.emit(f'Scanning {path}. Please wait...')

            if entry.name == common.bookmark_cache_dir:
                _path = '/'.join(path.split('/')[:-1])
                _name = _path[len(self.window().job_path()) + 1:]
                yield _name, _path

            for _name, _path in self.item_generator(
                    path,
                    recursion=recursion,
                    max_recursion=max_recursion
            ):
                yield _name, _path
