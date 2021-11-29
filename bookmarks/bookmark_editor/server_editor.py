# -*- coding: utf-8 -*-
"""Sub-editor widget used by the Bookmark Editor to add and select jobs on on a
server.

"""
import functools

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import ui
from .. import images
from .. import contextmenu
from .. import shortcuts
from .. import actions


class AddServerEditor(QtWidgets.QDialog):
    """Dialog used to add a new server to `local_settings`.

    """

    def __init__(self, parent=None):
        super(AddServerEditor, self).__init__(parent=parent)
        self.ok_button = None
        self.pick_button = None
        self.editor = None

        self.setWindowTitle('Add New Server')

        self._create_ui()
        self._connect_signals()
        self._add_completer()

    def _create_ui(self):
        if not self.parent():
            common.set_custom_stylesheet(self)

        QtWidgets.QVBoxLayout(self)

        o = common.size(common.WidthMargin)
        self.layout().setSpacing(o)
        self.layout().setContentsMargins(o, o, o, o)

        self.ok_button = ui.PaintedButton('Done', parent=self)
        self.ok_button.setFixedHeight(common.size(common.HeightRow))
        self.pick_button = ui.PaintedButton('Pick', parent=self)

        self.editor = ui.LineEdit(parent=self)
        self.editor.setPlaceholderText(
            'Enter the path to a server, eg. \'//my_server/jobs\'')
        self.setFocusProxy(self.editor)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)

        row = ui.add_row(None, parent=self)
        row.layout().addWidget(self.editor, 1)
        row.layout().addWidget(self.pick_button, 0)

        row = ui.add_row(None, parent=self)
        row.layout().addWidget(self.ok_button, 1)

    def _add_completer(self):
        items = []
        for info in QtCore.QStorageInfo.mountedVolumes():
            if info.isValid():
                items.append(info.rootPath())
        items += common.servers.values()

        completer = QtWidgets.QCompleter(items, parent=self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_custom_stylesheet(completer.popup())
        self.editor.setCompleter(completer)

    def _connect_signals(self):
        self.ok_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))
        self.pick_button.clicked.connect(self.pick)
        self.editor.textChanged.connect(lambda: self.editor.setStyleSheet(
            'color: {};'.format(common.rgb(common.color(common.GreenColor)))))

    @QtCore.Slot()
    def pick(self):
        _dir = QtWidgets.QFileDialog.getExistingDirectory(parent=self)
        if not _dir:
            return

        file_info = QtCore.QFileInfo(_dir)
        if file_info.exists():
            self.editor.setText(file_info.absoluteFilePath())

    @common.error
    @common.debug
    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            super(AddServerEditor, self).done(result)
            return

        if not self.text():
            return

        v = self.text()
        file_info = QtCore.QFileInfo(v)

        if not file_info.exists() or not file_info.isReadable() or v in common.servers:
            # Indicate the selected item is invalid and keep the editor open
            self.editor.setStyleSheet(
                'color: {0}; border-color: {0}'.format(common.rgb(common.color(common.RedColor))))
            self.editor.blockSignals(True)
            self.editor.setText(v)
            self.editor.blockSignals(False)
            return

        actions.add_server(v)
        super(AddServerEditor, self).done(QtWidgets.QDialog.Accepted)

    def text(self):
        v = self.editor.text()
        return common.strip(v) if v else ''

    def showEvent(self, event):
        self.editor.setFocus()
        common.center_window(self)

    def sizeHint(self):
        return QtCore.QSize(common.size(common.DefaultWidth), common.size(common.HeightRow) * 2)


class ServerContextMenu(contextmenu.BaseContextMenu):
    """Custom context menu used to control the list of saved servers.

    """

    def setup(self):
        self.add_menu()
        self.separator()
        if isinstance(self.index, QtWidgets.QListWidgetItem) and self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.reveal_menu()
            self.remove_menu()
        elif isinstance(self.index, QtWidgets.QListWidgetItem) and not self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.remove_menu()
        self.separator()
        self.refresh_menu()

    def add_menu(self):
        self.menu['Add server...'] = {
            'action': self.parent().add,
            'icon': self.get_icon('add', color=common.color(common.GreenColor))
        }

    def reveal_menu(self):
        self.menu['Reveal...'] = {
            'action': lambda: actions.reveal(self.index.text() + '/.'),
            'icon': self.get_icon('folder'),
        }

    def remove_menu(self):
        self.menu['Remove'] = {
            'action': self.parent().remove,
            'icon': self.get_icon('close', color=common.color(common.RedColor))
        }

    def refresh_menu(self):
        self.menu['Refresh'] = {
            'action': (self.parent().init_data, self.parent().restore_current),
            'icon': self.get_icon('refresh')
        }


class ServerListWidget(ui.ListWidget):
    """Simple list widget used to add and remove servers to/from the local
    common.

    """
    serverChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(ServerListWidget, self).__init__(
            default_message='No servers found.',
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
        self.setMinimumWidth(common.size(common.DefaultWidth) * 0.2)

        self._connect_signals()
        self.init_shortcuts()

    def init_shortcuts(self):
        shortcuts.add_shortcuts(self, shortcuts.BookmarkEditorShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.BookmarkEditorShortcuts)
        connect(shortcuts.AddItem, self.add)
        connect(shortcuts.RemoveItem, self.remove)

    def _connect_signals(self):
        super(ServerListWidget, self)._connect_signals()

        self.selectionModel().selectionChanged.connect(self.save_current)
        self.selectionModel().selectionChanged.connect(self.emit_server_changed)

        common.signals.serversChanged.connect(self.init_data)
        common.signals.serversChanged.connect(self.restore_current)

    @common.debug
    @common.error
    @QtCore.Slot()
    def remove(self, *args, **kwargs):
        if not self.selectionModel().hasSelection():
            return
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        v = index.data(QtCore.Qt.DisplayRole)
        v = common.strip(v)
        actions.remove_server(v)

    @common.debug
    @common.error
    @QtCore.Slot()
    def add(self, *args, **kwargs):

        w = AddServerEditor(parent=self.window())
        pos = self.mapToGlobal(self.window().rect().topLeft())
        w.move(pos)
        if w.exec_() == QtWidgets.QDialog.Accepted:
            self.restore_current(current=w.text())
            self.save_current()

    @common.debug
    @common.error
    @QtCore.Slot()
    def emit_server_changed(self, *args, **kwargs):
        """Slot connected to the server editor's `serverChanged` signal.

        """
        if not self.selectionModel().hasSelection():
            self.serverChanged.emit(None)
            return
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            self.serverChanged.emit(None)
            return
        self.serverChanged.emit(index.data(QtCore.Qt.DisplayRole))

    @common.debug
    @common.error
    @QtCore.Slot()
    def save_current(self, *args, **kwargs):
        if not self.selectionModel().hasSelection():
            return

        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        v = index.data(QtCore.Qt.DisplayRole)
        common.settings.setValue(
            common.UIStateSection,
            common.BookmarkEditorServerKey,
            v
        )

    @common.debug
    @common.error
    @QtCore.Slot()
    def restore_current(self, current=None):
        if current is None:
            current = common.settings.value(
                common.UIStateSection,
                common.BookmarkEditorServerKey
            )
        if not current:
            self.serverChanged.emit(None)
            return

        for n in range(self.count()):
            if not current == self.item(n).text():
                continue
            index = self.indexFromItem(self.item(n))
            self.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )

            self.scrollToItem(
                self.item(n), QtWidgets.QAbstractItemView.EnsureVisible)
            self.selectionModel().emitSelectionChanged(
                QtCore.QItemSelection(index, index),
                QtCore.QItemSelection()
            )
            self.serverChanged.emit(self.item(n).data(QtCore.Qt.DisplayRole))
            return

    def contextMenuEvent(self, event):
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
        self.serverChanged.emit(None)

        self.blockSignals(True)
        self.selectionModel().blockSignals(True)

        self.clear()
        for server in common.servers:
            item = QtWidgets.QListWidgetItem(server)
            size = QtCore.QSize(
                0,
                common.size(common.WidthMargin) * 2
            )
            item.setSizeHint(size)
            self.validate_item(item)
            self.insertItem(self.count(), item)

        self.blockSignals(False)
        self.selectionModel().blockSignals(False)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def validate_item(self, item):
        self.blockSignals(True)

        pixmap = images.ImageCache.get_rsc_pixmap(
            'server', common.color(common.TextColor), common.size(common.HeightRow) * 0.8)
        pixmap_selected = images.ImageCache.get_rsc_pixmap(
            'server', common.color(common.TextSelectedColor), common.size(common.HeightRow) * 0.8)
        pixmap_disabled = images.ImageCache.get_rsc_pixmap(
            'close', common.color(common.RedColor), common.size(common.HeightRow) * 0.8)
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
            r = True
        else:
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            r = False

        item.setData(QtCore.Qt.DecorationRole, icon)
        self.blockSignals(False)

        if r:
            index = self.indexFromItem(item)
            self.selectionModel().emitSelectionChanged(
                QtCore.QItemSelection(index, index),
                QtCore.QItemSelection()
            )

        return r
