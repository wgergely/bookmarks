import functools
import os

from PySide2 import QtWidgets, QtCore

from .lib import ServerAPI
from .model import ServerModel, NodeType
from .. import contextmenu, common, shortcuts, ui, actions
from ..editor import base


class ServerContextMenu(contextmenu.BaseContextMenu):

    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
        self.add_server_menu()
        self.separator()
        self.remove_server_menu()
        self.separator()
        self.add_view_menu()

    def add_server_menu(self):
        """Add the server menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Add Server...',
            'icon': ui.get_icon('add', color=common.Color.Green()),
            'action': self.parent().add_server,
            'shortcut': shortcuts.get(
                shortcuts.ServerViewShortcuts,
                shortcuts.AddServer
            ).key(),
            'description': shortcuts.hint(
                shortcuts.ServerViewShortcuts,
                shortcuts.AddServer
            )
        }

    def remove_server_menu(self):
        """Remove server menu.

        """
        node = self.parent().get_node_from_selection()

        if node and node.type != NodeType.ServerNode:
            self.menu[contextmenu.key()] = {
                'text': 'Remove...',
                'icon': ui.get_icon('close', color=common.Color.Red()),
                'action': self.parent().remove_server,
                'shortcut': shortcuts.get(
                    shortcuts.ServerViewShortcuts,
                    shortcuts.RemoveServer
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.ServerViewShortcuts,
                    shortcuts.RemoveServer
                ),
            }
        if node and node.type == NodeType.RootNode:
            self.menu[contextmenu.key()] = {
                'text': 'Remove...',
                'icon': ui.get_icon('close', color=common.Color.Red()),
                'action': self.parent().remove_server,
                'shortcut': shortcuts.get(
                    shortcuts.ServerViewShortcuts,
                    shortcuts.RemoveServer
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.ServerViewShortcuts,
                    shortcuts.RemoveServer
                ),
            }

        # Remove all
        self.menu[contextmenu.key()] = {
            'text': 'Remove All Servers',
            'icon': ui.get_icon('close', color=common.Color.Red()),
            'action': self.parent().remove_all_servers,
            'shortcut': shortcuts.get(
                shortcuts.ServerViewShortcuts,
                shortcuts.RemoveAllServers
            ).key(),
            'description': shortcuts.hint(
                shortcuts.ServerViewShortcuts,
                shortcuts.RemoveAllServers
            ),
        }

    def add_view_menu(self):
        """Add view menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'icon': ui.get_icon('refresh'),
            'action': self.parent().init_data,
            'shortcut': shortcuts.get(
                shortcuts.ServerViewShortcuts,
                shortcuts.ReloadServers
            ).key(),
            'description': shortcuts.hint(
                shortcuts.ServerViewShortcuts,
                shortcuts.ReloadServers
            ),
        }
        self.menu[contextmenu.key()] = {
            'text': 'Expand All',
            'icon': ui.get_icon('expand'),
            'action': (self.parent().expandAll),
            'help': 'Expand all items.',
        }
        self.menu[contextmenu.key()] = {
            'text': 'Collapse All',
            'icon': ui.get_icon('collapse'),
            'action': (self.parent().collapseAll),
            'help': 'Collapse all items.',
        }


class AddServerDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Add Server')

        self.name_editor = None
        self.ok_button = None
        self.cancel_button = None

        self._init_ui()
        self._init_completer()
        self._connect_signals()

    def _init_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.Size.Indicator(6.0)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        row = ui.add_row(None, height=None, parent=self)
        self.name_editor = ui.LineEdit(row, parent=self)
        self.name_editor.setPlaceholderText('Enter a path to a server...')

        action = QtWidgets.QAction(self.name_editor)
        action.setIcon(ui.get_icon('preset', color=common.Color.Text()))
        self.name_editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

        action = QtWidgets.QAction(self.name_editor)
        action.setIcon(ui.get_icon('folder', color=common.Color.Text()))
        self.name_editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

        self.name_editor.setValidator(base.path_validator)

        row.layout().addWidget(self.name_editor)

        row = ui.add_row(None, height=None, parent=self)

        self.ok_button = ui.PaintedButton('Add', parent=self)
        row.layout().addWidget(self.ok_button, 1)

        self.cancel_button = ui.PaintedButton('Cancel', parent=self)
        row.layout().addWidget(self.cancel_button)

        self.setFocusProxy(self.name_editor)

    def _connect_signals(self):
        self.name_editor.actions()[-1].triggered.connect(self.pick_folder)
        self.name_editor.actions()[-2].triggered.connect(self.name_editor.completer().complete)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    @common.error
    @common.debug
    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            return super().done(r)

        v = self.name_editor.text()
        if not v:
            raise ValueError('Must enter a valid path.')
        if not os.path.exists(v):
            raise ValueError(f'Path "{v}" does not exist.')

        ServerAPI.add_server(v)
        super().done(r)

    @common.error
    @common.debug
    @QtCore.Slot()
    def pick_folder(self):
        """Pick a folder."""
        v = self.name_editor.text()
        if v and os.path.exists(v):
            p = v
        else:
            p = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DesktopLocation)

        path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select a server folder', p)
        if not path:
            return
        if not os.path.exists(path):
            raise ValueError(f'Path "{path}" does not exist.')

        self.name_editor.setText(path)

    def _init_completer(self):
        servers = []

        _saved_servers = ServerAPI.get_servers()
        _saved_servers = _saved_servers if _saved_servers else {}

        servers += list(_saved_servers.keys())

        drives = ServerAPI.get_mapped_drives()
        for k in drives:
            servers.append(k)
            servers.append(drives[k])

        servers = sorted({k.replace('\\', '/').rstrip('/'): k for k in servers}.values())

        completer = QtWidgets.QCompleter(servers, parent=self)
        completer.setCompletionMode(QtWidgets.QCompleter.UnfilteredPopupCompletion)
        self.name_editor.setCompleter(completer)
        common.set_stylesheet(completer.popup())

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight(0.1)
        )


class ServerView(QtWidgets.QTreeView):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Servers')

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        if not parent:
            common.set_stylesheet(self)

        self.setHeaderHidden(True)

        self._expanded_nodes = []
        self._selected_node = None

        self._init_model()
        self._init_shortcuts()
        self._connect_signals()

        QtCore.QTimer.singleShot(100, self.model().init_data)

    def _init_shortcuts(self):
        shortcuts.add_shortcuts(self, shortcuts.ServerViewShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.ServerViewShortcuts
        )
        connect(shortcuts.AddServer, self.add_server)
        connect(shortcuts.RemoveServer, self.remove_server)
        connect(shortcuts.RemoveAllServers, self.remove_all_servers)
        connect(shortcuts.AddBookmark, self.add_bookmark)
        connect(shortcuts.RevealServer, self.reveal)
        connect(shortcuts.ReloadServers, self.init_data)

    def _init_model(self):
        model = ServerModel(parent=self)
        self.setModel(model)

    def _connect_signals(self):
        self.selectionModel().selectionChanged.connect(self.save_selected_node)
        self.model().modelAboutToBeReset.connect(self.save_selected_node)

        self.model().modelReset.connect(self.restore_selected_node)
        self.expanded.connect(self.restore_selected_node)

    def contextMenuEvent(self, event):
        """Context menu event.

        """
        index = self.indexAt(event.pos())
        menu = ServerContextMenu(index, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight()
        )

    def get_node_from_selection(self):
        """
        Get the internal node from the current selection.

        """
        if not self.selectionModel().hasSelection():
            return None

        index = next(f for f in self.selectionModel().selectedIndexes())
        if not index.isValid():
            return None

        node = index.internalPointer()
        if not node:
            return None

        return node

    @QtCore.Slot()
    def save_expanded_nodes(self, *args, **kwargs):
        """
        Save the expanded nodes.

        """
        if not self.model():
            self._expanded_nodes = []

        # Iterate over all direct child indexes of the root node
        for i in range(self.model().rowCount(parent=self.rootIndex())):
            index = self.model().index(i, 0, self.rootIndex())
            if not index.isValid():
                continue

            if self.isExpanded(index):
                node = index.internalPointer()
                if not node:
                    continue
                self._expanded_nodes.append(node.path())

    @QtCore.Slot()
    def restore_expanded_nodes(self, *args, **kwargs):
        """
        Restore the expanded nodes.

        """
        if not self._expanded_nodes:
            return

        if not self.model():
            return

        for i in range(self.model().rowCount(parent=self.rootIndex())):
            index = self.model().index(i, 0, self.rootIndex())
            if not index.isValid():
                continue

            node = index.internalPointer()
            if not node:
                continue

            if node.path() in self._expanded_nodes:
                self.expand(index)

    @QtCore.Slot()
    def save_selected_node(self, *args, **kwargs):
        """
        Save the selected node.

        """
        node = self.get_node_from_selection()
        if not node:
            return
        print(node.path())
        self._selected_node = node.path()

    @QtCore.Slot()
    def restore_selected_node(self):
        """
        Restore the selected node.

        """

        def _it_children(parent_index):
            for i in range(self.model().rowCount(parent=parent_index)):
                index = self.model().index(i, 0, parent_index)
                if not index.isValid():
                    continue

                if index.model().hasChildren(parent=index):
                    for child_index in _it_children(index):
                        yield child_index

                yield index

        if not self._selected_node:
            return

        for index in _it_children(self.rootIndex()):
            node = index.internalPointer()
            if not node:
                continue

            if node.path() == self._selected_node:
                self.selectionModel().select(index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.setCurrentIndex(index)
                self.scrollTo(index)
                break

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_server(self):
        """Add a server.

        """
        dialog = AddServerDialog(parent=self)
        dialog.open()

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_server(self):
        """Remove a server.

        """
        node = self.get_node_from_selection()
        if not node:
            return

        if node.type != NodeType.ServerNode:
            return

        ServerAPI.remove_server(node.server)

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_all_servers(self):
        """Remove all servers.

        """
        if common.show_message(
                'Are you sure you want to remove all servers?',
                body='This action cannot be undone.',
                message_type='error',
                buttons=[common.YesButton, common.NoButton],
                modal=True,

        ) == QtWidgets.QDialog.Rejected:
            return
        ServerAPI.clear_servers()

    @common.error
    @common.debug
    @QtCore.Slot()
    def init_data(self):
        """Initialize the data.

        """
        self.model().init_data()

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_bookmark(self):
        """Add a bookmark.

        """
        pass

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_bookmark(self):
        """Remove a bookmark.

        """
        pass

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_all_bookmarks(self):
        """Remove all bookmarks.

        """

    @common.error
    @common.debug
    @QtCore.Slot()
    def reveal(self):
        """
        Reveal the link in the file explorer.
        """
        node = self.get_node_from_selection()
        if not node:
            return

        path = node.path()
        if not path:
            return
        actions.reveal(path)
