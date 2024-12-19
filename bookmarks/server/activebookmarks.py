import functools
import json
import os

from PySide2 import QtWidgets, QtCore, QtGui

from . import activebookmarks_presets
from .lib import ServerAPI
from .. import contextmenu, common, ui


class Node:
    def __init__(self, key='', parent=None):
        self.parent = parent
        self.children = []
        self.data = ['', '']  # [Key, Value]
        if key:
            self.data[0] = key
        if parent:
            parent.add_child(self)

    def add_child(self, child):
        self.children.append(child)
        child.parent = self
        self.sort_children()

    def sort_children(self):
        self.children.sort(key=lambda node: node.data[0].lower())

    def child(self, row):
        return self.children[row]

    def child_count(self):
        return len(self.children)

    def row(self):
        if self.parent:
            return self.parent.children.index(self, )
        return 0

    def set_data(self, column, value):
        if 0 <= column < len(self.data):
            self.data[column] = value
            return True
        return False

    def get_data(self, column):
        if 0 <= column < len(self.data):
            return self.data[column]
        return None


class SavePresetDialog(QtWidgets.QDialog):
    """Custom dialog for saving presets with a validated name."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle('Save Preset')

        self._editor = None
        self.save_button = None
        self.cancel_button = None

        self._create_ui()
        self._connect_signals()

    @property
    def editor(self):
        return self._editor

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)

        o = common.Size.Margin()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        row = ui.add_row('Name', parent=self)

        # Line edit with validator
        self._editor = ui.LineEdit(required=True, parent=row)
        self._editor.setPlaceholderText('Enter a name for the preset...')

        values = activebookmarks_presets.get_api().get_presets().keys()
        completer = QtWidgets.QCompleter(sorted(values), parent=self._editor)
        completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setFilterMode(QtCore.Qt.MatchContains)
        common.set_stylesheet(completer.popup())
        self._editor.setCompleter(completer)

        action = QtWidgets.QAction(self._editor)
        action.setIcon(ui.get_icon('preset', color=common.Color.Text()))
        action.triggered.connect(completer.complete)
        self._editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

        validator = QtGui.QRegExpValidator(QtCore.QRegExp(r'[^\$\s\\/:*?"<>|]*'))
        self._editor.setValidator(validator)

        row.layout().addWidget(self._editor)

        # Exclude special characters the filename cannot contain

        row = ui.add_row(None, parent=self)

        self.save_button = ui.PaintedButton('Save', parent=row)
        self.cancel_button = ui.PaintedButton('Cancel', parent=row)
        row.layout().addWidget(self.save_button, 1)
        row.layout().addWidget(self.cancel_button, 0)

    def _connect_signals(self):
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.RowHeight()
        )

    def get_preset_name(self):
        """Return the text entered in the line edit."""
        return self.line_edit.text()


class ActiveBookmarksContextMenu(contextmenu.BaseContextMenu):
    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """

        self.add_menu()
        self.separator()
        self.remove_menu()
        self.separator()
        self.refresh_menu()
        self.expand_all_menu()
        self.collapse_all_menu()

    def add_menu(self):
        """Creates the Add menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Add Bookmark...',
            'icon': ui.get_icon('add', color=common.Color.Green()),
            'action': self.parent().add_item,
        }

    def remove_menu(self):
        """Creates the Remove menu.

        """
        if self.index.isValid():
            self.menu[contextmenu.key()] = {
                'text': 'Remove Bookmark',
                'icon': ui.get_icon('bookmark', color=common.Color.Red()),
                'action': self.parent().remove_item,
            }

            self.separator()

        self.menu[contextmenu.key()] = {
            'text': 'Remove All Bookmarks',
            'icon': ui.get_icon('close'),
            'action': self.parent().remove_all_items,
        }

    def expand_all_menu(self):
        """Creates the Expand All menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Expand All',
            'icon': ui.get_icon('expand'),
            'action': self.parent().view().expandAll,
        }

    def collapse_all_menu(self):
        """Creates the Collapse All menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Collapse All',
            'icon': ui.get_icon('collapse'),
            'action': self.parent().view().collapseAll,
        }

    def refresh_menu(self):
        """Creates the Refresh menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'icon': ui.get_icon('refresh'),
            'action': self.parent().init_data,
        }


class ActiveBookmarksModel(QtCore.QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_node = Node()
        self.bookmarks = {}
        self.init_data()

        common.signals.bookmarkAdded.connect(self.add_item)
        common.signals.bookmarkRemoved.connect(self.remove_item)

    def init_data(self):
        self.beginResetModel()
        self.bookmarks = ServerAPI.bookmarks(force=True)

        self.root_node = Node()
        for key in sorted(self.bookmarks.keys(), key=lambda x: x.lower()):
            key_node = Node(key, self.root_node)
            values = self.bookmarks[key]
            for component in ['server', 'job', 'root']:
                value = values.get(component, '')
                child_node = Node(component, key_node)
                child_node.data[1] = value
        self.endResetModel()

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0
        parent_node = self.get_node(parent)
        return parent_node.child_count()

    def columnCount(self, parent):
        return 2  # Key and Value

    def data(self, index, role):
        if not index.isValid():
            return None
        node = self.get_node(index)

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return node.get_data(index.column())

        if role == QtCore.Qt.DecorationRole:
            if not index.column() == 0:
                return None

            if not node.parent == self.root_node:
                return None

            if not os.path.exists(node.data[0]):
                return ui.get_icon('alert', color=common.Color.Red())
            return ui.get_icon('bookmark', color=common.Color.Green())

        if role == QtCore.Qt.FontRole:
            if not index.column() == 0:
                return None
            if not node.parent == self.root_node:
                return None

            font, metrics = common.Font.BoldFont(common.Size.MediumText())
            if not os.path.exists(node.data[0]):
                font, metrics = common.Font.ThinFont(common.Size.MediumText())
                return font

            return font

        if role == QtCore.Qt.SizeHintRole:
            if node.parent == self.root_node:
                height = common.Size.RowHeight()
            else:
                height = common.Size.RowHeight(0.66)
            font, metrics = common.Font.MediumFont(common.Size.MediumText())

            return QtCore.QSize(
                metrics.width(index.data(QtCore.Qt.DisplayRole)) + common.Size.Margin(),
                height,
            )
        return None

    def headerData(self, section, orientation, role):
        headers = ['Bookmarks', '']
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return headers[section]
        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        node = self.get_node(index)
        if index.column() == 1 and node.parent != self.root_node:
            return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |
                    QtCore.Qt.ItemIsEditable)
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def parent(self, index):
        node = self.get_node(index)
        parent_node = node.parent
        if parent_node == self.root_node or parent_node is None:
            return QtCore.QModelIndex()
        return self.createIndex(parent_node.row(), 0, parent_node)

    def index(self, row, column, parent):
        parent_node = self.get_node(parent)
        if row < 0 or row >= parent_node.child_count():
            return QtCore.QModelIndex()
        child_node = parent_node.child(row)
        return self.createIndex(row, column, child_node)

    def root_index(self):
        return self.createIndex(0, 0, self.root_node)

    def get_node(self, index):
        if index.isValid():
            return index.internalPointer()
        return self.root_node

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if index.isValid():
            value = value.strip()
            if not value:
                return False  # Reject empty strings
            node = self.get_node(index)
            if node.set_data(index.column(), value):
                # Update the dictionary if necessary
                self.update_data(node)
                self.dataChanged.emit(index, index)
                return True
        return False

    @QtCore.Slot(Node)
    def update_data(self, node):
        if node.parent and node.parent.parent == self.root_node:
            key_node = node.parent
            key = key_node.data[0]

            components = {child.data[0]: child.data[1] for child in key_node.children}
            new_key = f"{components.get('server', '')}/{components.get('job', '')}/{components.get('root', '')}"
            if '' in components.values():
                return

            self.bookmarks.pop(key, None)
            self.bookmarks[new_key] = components

            key_node.set_data(0, new_key)
            key_node.data[1] = ''

            self.root_node.sort_children()

            idx = self.createIndex(key_node.row(), 0, key_node)
            self.dataChanged.emit(idx, idx)
            ServerAPI.save_bookmarks(self.bookmarks)

        elif node.parent == self.root_node:
            # Do not allow editing of the key column
            pass

    @common.error
    @common.debug
    @QtCore.Slot(str, str, str)
    def add_item(self, server, job, root):
        if not all([server, job, root]):
            return False
        new_key = f"{server}/{job}/{root}"
        if new_key in self.bookmarks:
            return False  # Do not add duplicates
        components = {'server': server, 'job': job, 'root': root}

        self.beginInsertRows(
            QtCore.QModelIndex(),
            self.root_node.child_count(),
            self.root_node.child_count()
        )

        self.bookmarks[new_key] = components
        key_node = Node(new_key, self.root_node)
        for component in ['server', 'job', 'root']:
            value = components[component]
            child_node = Node(component, key_node)
            child_node.data[1] = value
        self.root_node.sort_children()
        self.endInsertRows()

        ServerAPI.save_bookmarks(self.bookmarks)
        return True

    @common.debug
    @QtCore.Slot(str)
    @QtCore.Slot(str)
    @QtCore.Slot(str)
    def remove_item(self, server, job, root):
        key = f"{server}/{job}/{root}"
        for i in range(self.rowCount(self.root_index())):
            index = self.index(i, 0, self.root_index())
            if not index.isValid():
                continue
            node = self.get_node(index)
            if node.data[0] == key:
                self.removeRows(i, 1)
                return

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        parent_node = self.get_node(parent)
        if parent_node != self.root_node:
            return False  # Only allow removal of top-level items
        self.beginRemoveRows(parent, row, row + count - 1)
        for i in range(count):
            child_node = parent_node.children.pop(row)
            # Remove from dictionary
            self.bookmarks.pop(child_node.data[0], None)
        self.endRemoveRows()

        ServerAPI.save_bookmarks(self.bookmarks)
        return True

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction

    def canDropMimeData(self, data, action, row, column, parent):
        if action != QtCore.Qt.CopyAction:
            return False
        if not data.hasFormat('text/plain'):
            return False
        return True

    def dropMimeData(self, data, action, row, column, parent):
        if not self.canDropMimeData(data, action, row, column, parent):
            return False
        if not data.hasText():
            return False
        text = data.text()

        try:
            data = json.loads(text)
            for value in data.values():
                if 'server' not in value or 'job' not in value or 'root' not in value:
                    return False
                if not self.add_item(value['server'], value['job'], value['root']):
                    return False
        except json.JSONDecodeError:
            return False

        return True


class ActiveBookmarksWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.toolbar = None
        self.tree_view = None
        self.apply_preset_action = None
        self.delete_preset_action = None

        self._create_ui()
        self._connect_signals()

        self.init_data()
        self.init_presets()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.layout().setContentsMargins(0, 0, 0, 0)

        # Toolbar
        self.toolbar = QtWidgets.QToolBar(self)
        self.toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolbar.setIconSize(QtCore.QSize(common.Size.Margin(), common.Size.Margin()))

        # Add item
        action = QtWidgets.QAction(ui.get_icon('add', color=common.Color.Green()), 'Add Bookmark', self)
        action.triggered.connect(self.add_item)
        self.toolbar.addAction(action)

        self.toolbar.addSeparator()

        # Add label "Presets"
        label = QtWidgets.QLabel('Presets', self)
        label.setStyleSheet(f'color: {common.Color.DisabledText(qss=True)};')
        self.toolbar.addWidget(label)

        # Save preset
        action = QtWidgets.QAction(ui.get_icon('add_preset', color=common.Color.DisabledText()), 'Save', self)
        action.triggered.connect(self.save_preset)
        self.toolbar.addAction(action)

        # Load preset
        action = QtWidgets.QAction(ui.get_icon('preset', color=common.Color.DisabledText()), 'Load', self)
        menu = QtWidgets.QMenu(self)
        menu.addAction('No presets...')
        menu.actions()[0].setEnabled(False)
        action.setMenu(menu)
        self.apply_preset_action = action
        action.triggered.connect(lambda: self.apply_preset_action.menu().exec_(QtGui.QCursor().pos()))
        self.toolbar.addAction(action)

        # Create QTreeView
        self.tree_view = QtWidgets.QTreeView(self)
        self.tree_view.setRootIsDecorated(False)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setObjectName('ActiveBookmarksView')

        self.tree_view.setAcceptDrops(True)
        self.tree_view.viewport().setAcceptDrops(True)
        self.tree_view.dragEnterEvent = self.dragEnterEvent
        self.tree_view.dragMoveEvent = self.dragMoveEvent

        self.tree_view.setModel(ActiveBookmarksModel(parent=self.tree_view))

        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.tree_view, 1)

    def _connect_signals(self):
        common.signals.bookmarksChanged.connect(self.init_data)
        common.signals.activeBookmarksPresetsChanged.connect(self.init_presets)

        self.model().modelReset.connect(self.set_spanned)
        self.model().rowsInserted.connect(self.set_spanned)
        self.model().rowsRemoved.connect(self.set_spanned)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def contextMenuEvent(self, event):
        """Context menu event.

        """
        index = next(iter(self.tree_view.selectedIndexes()), QtCore.QModelIndex())
        persistent_index = QtCore.QPersistentModelIndex(index)

        menu = ActiveBookmarksContextMenu(persistent_index, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def view(self):
        return self.tree_view

    def model(self):
        return self.tree_view.model()

    @QtCore.Slot(str)
    def selection_changed(self, path):
        # Select the item in the tree view
        model = self.model()

        for i in range(model.rowCount(QtCore.QModelIndex())):
            index = model.index(i, 0, QtCore.QModelIndex())
            if not index.isValid():
                continue
            if path == index.data(QtCore.Qt.DisplayRole):
                self.tree_view.selectionModel().select(index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.tree_view.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.Select)
                return

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_item(self):
        # Prompt user for server, job, and root
        server, ok1 = QtWidgets.QInputDialog.getText(self, 'Set Server', 'Server:')
        if not ok1 or not server.strip():
            return
        job, ok2 = QtWidgets.QInputDialog.getText(self, 'Set Job', 'Job:')
        if not ok2 or not job.strip():
            return
        root, ok3 = QtWidgets.QInputDialog.getText(self, 'Set Root', 'Root:')
        if not ok3 or not root.strip():
            return
        if not self.model().add_item(server.strip(), job.strip(), root.strip()):
            QtWidgets.QMessageBox.warning(self, 'Add Item', 'Item already exists or invalid input.')

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_item(self):
        index = self.tree_view.currentIndex()
        node = self.model().get_node(index)
        if node.parent != self.model().root_node:
            QtWidgets.QMessageBox.warning(self, 'Remove Item', 'Please select a top-level item to remove.')
            return
        row = index.row()
        self.model().removeRows(row, 1)
        self.model().dataChanged.emit(index, index)

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_all_items(self):
        self.model().removeRows(0, self.model().rowCount(self.model().root_index()))

    @common.error
    @common.debug
    @QtCore.Slot()
    def save_preset(self):
        """Save the current bookmarks as a preset.

        """
        if not common.bookmarks:
            raise ValueError('No bookmarks to save as a preset.')

        dialog = SavePresetDialog(parent=self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        preset_name = dialog.editor.text()
        if not preset_name:
            raise ValueError('Cannot save a preset with an empty name.')

        # Save the preset
        api = activebookmarks_presets.get_api()

        try:
            api.save_preset(preset_name)
        except FileExistsError:
            if common.show_message(
                    'A template with the same name already exists. Overwrite?',
                    body='This action not undoable.',
                    buttons=[common.YesButton, common.NoButton],
                    modal=True
            ) == QtWidgets.QDialog.Rejected:
                return

            api.save_preset(preset_name, force=True)

    @common.error
    @common.debug
    @QtCore.Slot(str)
    def activate_preset(self, preset, *args, **kwargs):
        if common.show_message(
                f'Are you sure you want to activate the preset "{preset}"?',
                body='This action will overwrite the current bookmark selection.',
                buttons=[common.YesButton, common.NoButton],
                modal=True
        ) == QtWidgets.QDialog.Rejected:
            return
        api = activebookmarks_presets.get_api()
        api.activate_preset(preset)

    @common.error
    @common.debug
    @QtCore.Slot(str)
    def delete_preset(self, preset_name, *args, **kwargs):
        """Removes the specified preset.

        """
        if not common.bookmarks:
            raise ValueError('No presets to remove.')

        if common.show_message(
                f'Are you sure you want to remove "{preset_name}"?',
                body='This action is not undoable.',
                buttons=[common.YesButton, common.NoButton],
                modal=True
        ) == QtWidgets.QDialog.Rejected:
            return

        api = activebookmarks_presets.get_api()
        api.delete_preset(preset_name)

        common.signals.activeBookmarksPresetsChanged.emit()

    @common.error
    @common.debug
    @QtCore.Slot()
    def init_data(self):
        self.model().init_data()
        self.set_spanned()

    @common.error
    @common.debug
    def init_presets(self):
        api = activebookmarks_presets.get_api()
        presets = api.get_presets(force=True)

        action = self.apply_preset_action
        menu = action.menu()
        menu.clear()
        if not presets:
            menu.addAction('No presets...').setEnabled(False)
            return

        for preset in sorted(presets.keys(), key=lambda x: x.lower()):
            _action = menu.addAction(preset)
            _action.triggered.connect(functools.partial(self.activate_preset, preset))
            menu.addAction(_action)

    def set_spanned(self):
        for i in range(self.model().rowCount(self.model().root_index())):
            self.tree_view.setFirstColumnSpanned(i, self.model().root_index(), True)
