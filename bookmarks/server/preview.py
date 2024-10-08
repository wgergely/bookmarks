import json
import os

from PySide2 import QtWidgets, QtCore

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
            return self.parent.children.index(self)
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


class DictionaryPreviewContextMenu(contextmenu.BaseContextMenu):
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
            'text': 'Add new bookmark item...',
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
            'icon': ui.get_icon('bookmark', color=common.Color.Red()),
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


class DictionaryModel(QtCore.QAbstractItemModel):
    #: Custom signal to emit data changes
    dataChangedSignal = QtCore.Signal(dict)

    def __init__(self, data_dict, parent=None):
        super().__init__(parent)
        self.root_node = Node()
        self.data_dict = data_dict
        self.init_data()

        common.signals.bookmarkAdded.connect(self.add_item)

    @QtCore.Slot(str, str, str)
    def on_bookmark_added(self, server, job, root):
        print(f'Bookmark added: {server}/{job}/{root}')

        print(common.bookmarks)

    def init_data(self):
        self.beginResetModel()
        self.root_node = Node()
        for key in sorted(self.data_dict.keys(), key=lambda x: x.lower()):
            key_node = Node(key, self.root_node)
            values = self.data_dict[key]
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

            if not os.path.exists(node.data[0]):
                font, metrics = common.Font.LightFont(common.Size.MediumText())
                font.setStrikeOut(True)
                font.setItalic(True)
                return font
            font, metrics = common.Font.LightFont(common.Size.MediumText())
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
        headers = ['Key', 'Value']
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

            self.data_dict.pop(key, None)
            self.data_dict[new_key] = components

            key_node.set_data(0, new_key)
            key_node.data[1] = ''

            self.root_node.sort_children()

            idx = self.createIndex(key_node.row(), 0, key_node)
            self.dataChanged.emit(idx, idx)
            self.dataChangedSignal.emit(self.data_dict.copy())
        elif node.parent == self.root_node:
            # Do not allow editing of the key column
            pass

    @common.error
    @common.debug
    @QtCore.Slot(str, str, str)
    def add_item(self, server, job, root):
        if not all([server, job, root]):
            return False  # Do not add if any component is empty
        new_key = f"{server}/{job}/{root}"
        if new_key in self.data_dict:
            return False  # Do not add duplicates
        components = {'server': server, 'job': job, 'root': root}

        self.beginInsertRows(
            QtCore.QModelIndex(),
            self.root_node.child_count(),
            self.root_node.child_count()
        )

        self.data_dict[new_key] = components
        key_node = Node(new_key, self.root_node)
        for component in ['server', 'job', 'root']:
            value = components[component]
            child_node = Node(component, key_node)
            child_node.data[1] = value
        self.root_node.sort_children()
        self.endInsertRows()

        self.dataChangedSignal.emit(self.data_dict.copy())
        return True

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        parent_node = self.get_node(parent)
        if parent_node != self.root_node:
            return False  # Only allow removal of top-level items
        self.beginRemoveRows(parent, row, row + count - 1)
        for i in range(count):
            child_node = parent_node.children.pop(row)
            # Remove from dictionary
            self.data_dict.pop(child_node.data[0], None)
        self.endRemoveRows()

        # Emit the custom signal
        self.dataChangedSignal.emit(self.data_dict.copy())
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


class DictionaryPreview(QtWidgets.QWidget):
    selectionChanged = QtCore.Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.data_dict = common.bookmarks.copy()

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        # Set up the layout
        self._create_ui()
        self._connect_signals()
        self.init_data()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.layout().setContentsMargins(0, 0, 0, 0)

        # Create QTreeView
        self.tree_view = QtWidgets.QTreeView(self)
        self.tree_view.setObjectName('dictionary_preview')

        self.tree_view.setAcceptDrops(True)
        self.tree_view.viewport().setAcceptDrops(True)
        self.tree_view.dragEnterEvent = self.dragEnterEvent
        self.tree_view.dragMoveEvent = self.dragMoveEvent

        self.tree_view.setModel(DictionaryModel(self.data_dict, parent=self.tree_view))
        self.tree_view.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        self.layout().addWidget(self.tree_view, 1)

    def _connect_signals(self):
        common.signals.bookmarksChanged.connect(self.init_data)

        self.model().dataChangedSignal.connect(self.on_data_changed)

        self.model().modelReset.connect(self.set_spanned)
        self.model().rowsInserted.connect(self.set_spanned)
        self.model().rowsRemoved.connect(self.set_spanned)

        self.view().selectionModel().selectionChanged.connect(self.emit_selection_changed)
        self.view().selectionModel().currentChanged.connect(self.emit_selection_changed)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def contextMenuEvent(self, event):
        """Context menu event.

        """
        index = next(iter(self.tree_view.selectedIndexes()), QtCore.QModelIndex())
        persistent_index = QtCore.QPersistentModelIndex(index)

        menu = DictionaryPreviewContextMenu(persistent_index, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def view(self):
        return self.tree_view

    def model(self):
        return self.tree_view.model()

    @QtCore.Slot()
    def emit_selection_changed(self):
        if not self.view().selectionModel().hasSelection():
            return

        index = next(iter(self.view().selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return

        node = self.model().get_node(index)
        if node.parent == self.model().root_node:
            v = common.bookmarks[node.data[0]]
            self.selectionChanged.emit(v['server'], v['job'], v['root'])

    @QtCore.Slot(str)
    def bookmark_node_changed(self, path):
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
        server, ok1 = QtWidgets.QInputDialog.getText(self, 'Add Item', 'Server:')
        if not ok1 or not server.strip():
            return
        job, ok2 = QtWidgets.QInputDialog.getText(self, 'Add Item', 'Job:')
        if not ok2 or not job.strip():
            return
        root, ok3 = QtWidgets.QInputDialog.getText(self, 'Add Item', 'Root:')
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

    def init_data(self):
        self.model().init_data()
        self.set_spanned()

    def set_spanned(self):
        for i in range(self.model().rowCount(self.model().root_index())):
            self.tree_view.setFirstColumnSpanned(i, self.model().root_index(), True)

    @QtCore.Slot(dict)
    def on_data_changed(self, data):
        ServerAPI.save_bookmarks(data)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(0.33),
            common.Size.DefaultHeight()
        )
