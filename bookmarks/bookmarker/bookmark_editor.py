"""Editor widget used by :class:`~bookmarks.bookmarker.main.BookmarkerWidget` to save
bookmark items to the user settings file.

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


class BookmarkEditorContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with :class:`BookmarkItemEditor`.

    """

    def setup(self):
        """Creates the context menu.

        """
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
        """Add bookmark item action."""
        self.menu[contextmenu.key()] = {
            'text': 'Pick a new bookmark item...',
            'action': self.parent().add,
            'icon': ui.get_icon('add', color=common.color(common.color_green))
        }

    def reveal_menu(self):
        """Reveal bookmark item action."""
        self.menu[contextmenu.key()] = {
            'text': 'Reveal',
            'action': functools.partial(
                actions.reveal, f'{self.index.data(QtCore.Qt.UserRole)}/.'
            ),
            'icon': ui.get_icon('folder')
        }

    def refresh_menu(self):
        """Refresh bookmark item list action."""
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'action': self.parent().init_data,
            'icon': ui.get_icon('refresh')
        }

    def bookmark_properties_menu(self):
        """Show the bookmark item property editor."""
        server = self.parent().window().server()
        job = self.parent().window().job()
        root = self.index.data(QtCore.Qt.DisplayRole)

        self.menu[contextmenu.key()] = {
            'text': 'Edit Properties...',
            'action': functools.partial(actions.edit_bookmark, server, job, root),
            'icon': ui.get_icon('settings')
        }

    def copy_json_menu(self):
        """Copy bookmark item as JSON action."""
        server = self.parent().window().server()
        job = self.parent().window().job()
        root = self.index.data(QtCore.Qt.DisplayRole)

        d = {
            f'{server}/{job}/{root}': {
                'server': server,
                'job': job,
                'root': root
            }
        }
        s = json.dumps(d)

        self.menu[contextmenu.key()] = {
            'text': 'Copy as JSON',
            'action': functools.partial(
                QtWidgets.QApplication.clipboard().setText, s),
            'icon': ui.get_icon('copy')
        }


class BookmarkItemEditor(ui.ListWidget):
    """List widget containing a job's available bookmark items.

    """
    loaded = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(
            default_icon='folder',
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
        self.setMinimumWidth(common.size(common.size_width) * 0.2)

        self._connect_signals()
        self._init_shortcuts()

    def _init_shortcuts(self):
        """Initialize shortcuts."""
        shortcuts.add_shortcuts(self, shortcuts.BookmarkEditorShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.BookmarkEditorShortcuts
        )
        connect(shortcuts.AddItem, self.add)

    def _connect_signals(self):
        """Connect signals."""
        super()._connect_signals()

        self.itemActivated.connect(self.toggle_item_state)
        self.itemChanged.connect(
            lambda item: self.add_remove_bookmark(
                item.checkState(),
                item.data(QtCore.Qt.DisplayRole)
            )
        )

        common.signals.serversChanged.connect(self.init_data)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def add_remove_bookmark(self, state, v):
        """Slot used to add or remove a bookmark item.

        Args:
            state (QtCore.Qt.CheckState): A check state.
            v (QtWidgets.QListWidgetItem): The item that was just toggled.

        """
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
        """Slot used to toggle the check state of an item."""
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
        """Pick and add a folder as a new bookmark item."""
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
            common.size(common.size_margin) * 2
        )
        item.setSizeHint(size)
        self.update_state(item)
        self.insertItem(self.count(), item)
        self.setCurrentItem(item)

    def contextMenuEvent(self, event):
        """Context menu event."""
        item = self.itemAt(event.pos())
        menu = BookmarkEditorContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    @QtCore.Slot()
    def init_data(self):
        """Initializes data.

        """
        self.clear()

        if not self.window().job():
            return

        max_recursion = common.settings.value('settings/job_scan_depth')
        max_recursion = 3 if not max_recursion else max_recursion

        it = self.item_generator(self.window().job_path(), max_recursion=max_recursion)
        items = sorted(set({f for f in it}))

        for name, path in items:
            self.progressUpdate.emit(f'Parsing {path}...')

            item = QtWidgets.QListWidgetItem()
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsUserCheckable
            )
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(QtCore.Qt.UserRole, path)
            item.setData(QtCore.Qt.StatusTipRole, path)
            item.setData(QtCore.Qt.WhatsThisRole, path)
            item.setData(QtCore.Qt.ToolTipRole, path)
            item.setSizeHint(QtCore.QSize(0, common.size(common.size_margin) * 2))

            self.update_state(item)
            self.insertItem(self.count(), item)

        self.progressUpdate.emit('')

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def update_state(self, item):
        """Checks if the item is part of the current bookmark set and sets the item's
        check state and icon accordingly.

        Args:
            item(QtWidgets.QListWidgetItem): The item to verify.

        """
        self.blockSignals(True)
        if item.data(QtCore.Qt.UserRole) in list(common.bookmarks):
            item.setCheckState(QtCore.Qt.Checked)
        else:
            item.setCheckState(QtCore.Qt.Unchecked)
        self.blockSignals(False)

    def item_generator(self, path, recursion=0, max_recursion=3):
        """Recursive scanning function for finding bookmark folders
        inside the given path.

        """
        if self._interrupt_requested:
            return

        # Return items stored in the link file
        if recursion == 0:
            for v in common.get_links(path, section='links/root'):
                if self._interrupt_requested:
                    return
                yield v, f'{path}/{v}'

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
                if self._interrupt_requested:
                    return
                yield _name, _path

    def keyPressEvent(self, event):
        """Key press event handler.

        """
        if event.key() == QtCore.Qt.Key_Escape:
            self._interrupt_requested = True
