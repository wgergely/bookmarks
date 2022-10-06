"""Editor widget used by
:class:`~bookmarks.bookmarker.main.BookmarkerWidget`
to select and save a new server item.

"""
import functools

from PySide2 import QtCore, QtGui, QtWidgets

from .. import actions
from .. import common
from .. import contextmenu
from .. import images
from .. import shortcuts
from .. import ui


class AddServerEditor(QtWidgets.QDialog):
    """Dialog used to add a new server to user settings file.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ok_button = None
        self.pick_button = None
        self.editor = None

        self.setWindowTitle('Add New Server')

        self._create_ui()
        self._connect_signals()
        self._add_completer()

    def _create_ui(self):
        """Create ui."""
        if not self.parent():
            common.set_stylesheet(self)

        QtWidgets.QVBoxLayout(self)

        o = common.size(common.size_margin)
        self.layout().setSpacing(o)
        self.layout().setContentsMargins(o, o, o, o)

        self.ok_button = ui.PaintedButton('Done', parent=self)
        self.ok_button.setFixedHeight(common.size(common.size_row_height))
        self.pick_button = ui.PaintedButton('Pick', parent=self)

        self.editor = ui.LineEdit(parent=self)
        self.editor.setPlaceholderText(
            'Enter the path to a server, e.g. \'//my_server/jobs\''
        )
        self.setFocusProxy(self.editor)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)

        row = ui.add_row(None, parent=self)
        row.layout().addWidget(self.editor, 1)
        row.layout().addWidget(self.pick_button, 0)

        row = ui.add_row(None, parent=self)
        row.layout().addWidget(self.ok_button, 1)

    def _add_completer(self):
        """Add and populate a QCompleter with mounted drive names.

        """
        items = []
        for info in QtCore.QStorageInfo.mountedVolumes():
            if info.isValid():
                items.append(info.rootPath())
        items += common.servers.values()

        completer = QtWidgets.QCompleter(items, parent=self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_stylesheet(completer.popup())
        self.editor.setCompleter(completer)

    def _connect_signals(self):
        """Connect signals."""
        self.ok_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted)
        )
        self.pick_button.clicked.connect(self.pick)
        self.editor.textChanged.connect(
            lambda: self.editor.setStyleSheet(
                'color: {};'.format(common.rgb(common.color(common.color_green)))
            )
        )

    @QtCore.Slot()
    def pick(self):
        """Get an existing directory to use as a server.

        """
        _dir = QtWidgets.QFileDialog.getExistingDirectory(parent=self)
        if not _dir:
            return

        file_info = QtCore.QFileInfo(_dir)
        if file_info.exists():
            self.editor.setText(file_info.absoluteFilePath())

    @common.error
    @common.debug
    def done(self, result):
        """Finalize action.

        """
        if result == QtWidgets.QDialog.Rejected:
            super().done(result)
            return

        if not self.text():
            return

        v = self.text()
        file_info = QtCore.QFileInfo(v)

        if not file_info.exists() or not file_info.isReadable() or v in \
                common.servers:
            # Indicate the selected item is invalid and keep the editor open
            self.editor.setStyleSheet(
                'color: {0}; border-color: {0}'.format(
                    common.rgb(common.color(common.color_red))
                )
            )
            self.editor.blockSignals(True)
            self.editor.setText(v)
            self.editor.blockSignals(False)
            return

        actions.add_server(v)
        super().done(QtWidgets.QDialog.Accepted)

    def text(self):
        """Sanitize text.

        Returns:
            str: The sanitized text.

        """
        v = self.editor.text()
        return common.strip(v) if v else ''

    def showEvent(self, event):
        """Show event handler.

        """
        self.editor.setFocus()
        common.center_window(self)

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width),
            common.size(common.size_row_height) * 2
        )


class ServerContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with :class:`ServerItemEditor`.

    """

    def setup(self):
        """Creates the context menu.

        """
        self.add_menu()
        self.separator()
        if isinstance(
                self.index, QtWidgets.QListWidgetItem
        ) and self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.reveal_menu()
            self.remove_menu()
        elif isinstance(
                self.index,
                QtWidgets.QListWidgetItem
        ) and not self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.remove_menu()
        self.separator()
        self.refresh_menu()

    def add_menu(self):
        """Add server action.

        """
        self.menu['Add New Server...'] = {
            'action': self.parent().add,
            'icon': ui.get_icon('add', color=common.color(common.color_green))
        }

    def reveal_menu(self):
        """Reveal server item action.

        """
        self.menu['Reveal...'] = {
            'action': lambda: actions.reveal(f'{self.index.text()}/.'),
            'icon': ui.get_icon('folder'),
        }

    def remove_menu(self):
        """Remove server item action.

        """
        self.menu['Remove'] = {
            'action': self.parent().remove,
            'icon': ui.get_icon('close', color=common.color(common.color_red))
        }

    def refresh_menu(self):
        """Refresh server list action.

        """
        self.menu['Refresh'] = {
            'action': self.parent().init_data,
            'icon': ui.get_icon('refresh')
        }


class ServerItemEditor(ui.ListWidget):
    """List widget used to add and remove servers to and from the local
    user settings.

    """

    def __init__(self, parent=None):
        super().__init__(
            default_icon='server',
            parent=parent
        )

        self.setItemDelegate(ui.ListWidgetDelegate(parent=self))
        self.setWindowTitle('Server Editor')
        self.setObjectName('ServerEditor')

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
        """Initializes shortcuts.

        """
        shortcuts.add_shortcuts(self, shortcuts.BookmarkEditorShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.BookmarkEditorShortcuts
        )
        connect(shortcuts.AddItem, self.add)
        connect(shortcuts.RemoveItem, self.remove)

    def _connect_signals(self):
        """Connects signals.

        """
        super()._connect_signals()

        self.selectionModel().selectionChanged.connect(
            functools.partial(common.save_selection, self)
        )

        common.signals.serversChanged.connect(self.init_data)
        common.signals.serverAdded.connect(
            functools.partial(common.select_index, self)
        )

    @common.debug
    @common.error
    @QtCore.Slot()
    def remove(self, *args, **kwargs):
        """Remove a server item.

        """
        index = common.get_selected_index(self)
        if not index.isValid():
            return

        v = index.data(QtCore.Qt.DisplayRole)
        v = common.strip(v)
        actions.remove_server(v)

    @common.debug
    @common.error
    @QtCore.Slot()
    def add(self, *args, **kwargs):
        """Add a server item.

        """
        w = AddServerEditor(parent=self.window())
        pos = self.mapToGlobal(self.window().rect().topLeft())
        w.move(pos)
        if w.exec_() == QtWidgets.QDialog.Accepted:
            self.init_data()

    def contextMenuEvent(self, event):
        """Context menu event handler.

        """
        item = self.itemAt(event.pos())
        menu = ServerContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    @common.debug
    @common.error
    @QtCore.Slot()
    def init_data(self, *args, **kwargs):
        """Load data.

        """
        selected_index = common.get_selected_index(self)
        selected_name = selected_index.data(
            QtCore.Qt.DisplayRole
        ) if selected_index.isValid() else None

        self.selectionModel().blockSignals(True)
        self.clear()

        for path in common.servers:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, path)
            item.setData(QtCore.Qt.UserRole, path)
            item.setData(QtCore.Qt.UserRole + 1, path)
            item.setData(QtCore.Qt.StatusTipRole, path)
            item.setData(QtCore.Qt.WhatsThisRole, path)
            item.setData(QtCore.Qt.ToolTipRole, path)

            size = QtCore.QSize(
                0,
                common.size(common.size_margin) * 2
            )
            item.setSizeHint(size)
            self.validate_item(item)
            self.insertItem(self.count(), item)

        self.progressUpdate.emit('')

        if selected_name:
            for idx in range(self.model().rowCount()):
                index = self.model().index(idx, 0)
                if index.data(QtCore.Qt.DisplayRole) == selected_name:
                    self.selectionModel().select(
                        index, QtCore.QItemSelectionModel.ClearAndSelect
                    )

        self.selectionModel().blockSignals(False)
        common.restore_selection(self)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def validate_item(self, item):
        """Check if the given server item is valid.

        """
        selected_index = common.get_selected_index(self)

        self.blockSignals(True)

        pixmap = images.ImageCache.rsc_pixmap(
            'server', common.color(common.color_text),
            common.size(common.size_row_height) * 0.8
        )
        pixmap_selected = images.ImageCache.rsc_pixmap(
            'server', common.color(common.color_selected_text),
            common.size(common.size_row_height) * 0.8
        )
        pixmap_disabled = images.ImageCache.rsc_pixmap(
            'close', common.color(common.color_red),
            common.size(common.size_row_height) * 0.8
        )
        icon = QtGui.QIcon()

        file_info = QtCore.QFileInfo(item.text())
        if file_info.exists() and file_info.isReadable() and file_info.isWritable():
            icon.addPixmap(pixmap, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable
            )
            valid = True
        else:
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            valid = False

        item.setData(QtCore.Qt.DecorationRole, icon)
        self.blockSignals(False)

        index = self.indexFromItem(item)
        if not valid and selected_index == index:
            self.selectionModel().clearSelection()
