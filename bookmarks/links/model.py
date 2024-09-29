import os

from PySide2 import QtCore

from .lib import LinksAPI
from .. import common
from .. import ui


class Node:
    """
    A class representing a node in the tree model.
    """

    def __init__(self, path, parent=None):
        """
        Initialize the Node.

        Args:
            path: The data to store in this node.
            parent (Node): The parent node.
        """
        self._api = None
        self._path = path
        self._parent = parent
        self._exists = None
        self._children = []

    def exists(self, force=False):
        """
        Check if the path exists.

        Returns:
            bool: True if the path exists.
        """
        if self._exists is None:
            if self.is_leaf():
                path = self.api().to_absolute(self._path)
            else:
                path = self._path

        if not force and self._exists is not None:
            return self._exists

        self._exists = os.path.exists(path)
        return self._exists

    def append_child(self, child):
        """
        Add a child node.

        Args:
            child (Node): The child node to add.
        """
        self._children.append(child)

    def children(self):
        """
        Get the children of this node.

        Returns:
            list: The list of child nodes.
        """
        return self._children

    def child(self, row):
        """
        Get the child at the specified row.

        Args:
            row (int): The row index.

        Returns:
            Node: The child node.
        """
        if 0 <= row < len(self._children):
            return self._children[row]
        return None

    def child_count(self):
        """
        Get the number of children.

        Returns:
            int: The number of child nodes.
        """
        return len(self._children)

    def path(self):
        """
        Get the data stored in this node.

        Returns:
            The data.
        """
        return self._path

    def parent(self):
        """
        Get the parent node.

        Returns:
            Node: The parent node.
        """
        return self._parent

    def is_leaf(self):
        """
        Check if this node is a leaf node.

        Returns:
            bool: True if this node is a leaf node.
        """
        return len(self._children) == 0 and self._parent and self._parent._path != 'Root'

    def row(self):
        """
        Get the row number of this node in its parent's children list.

        Returns:
            int: The row index.
        """
        if self._parent:
            return self._parent._children.index(self)
        return 0  # Root node

    def api(self):
        """
        Get the links api instance.

        Returns:
            LinksAPI: The links api instance.
        """
        if self.is_leaf():
            if self._parent._api is None:
                api = LinksAPI(self._parent._path)
                self._parent._api = api
            return self._parent._api
        if self._api is None:
            self._api = LinksAPI(self._path)
        return self._api


class AssetLinksModel(QtCore.QAbstractItemModel):
    """
    A model representing the asset links as a tree.
    """
    row_size = QtCore.QSize(1, common.Size.RowHeight())

    def __init__(self, parent=None):
        """
        Initialize the model.

        Args:
            path (str): Path to a folder containing a .links file.
            parent: The parent object.

        """
        super().__init__(parent)
        self._root_node = None

    def add_path(self, path):
        """
        Add a folder path to the model.

        Args:
            path (str): The path to a folder containing a .links file.

        """
        if not os.path.exists(path):
            raise ValueError(f'Path does not exist: {path}')

        if self.root_node() and self.root_node().children():
            for parent_node in self.root_node().children():
                if parent_node.path() == path:
                    raise ValueError(f'Path already added to the model: {path}')

        self.beginResetModel()

        if self.root_node() is None:
            self._root_node = Node('Root')

        parent_node = Node(path, parent=self.root_node())
        self.root_node().append_child(parent_node)

        # Get the relative links from the links api instance
        links = parent_node.api().get(force=True)

        # For each link, create a child node under links_node
        for link in links:
            child_node = Node(link, parent=parent_node)
            parent_node.append_child(child_node)

        self.endResetModel()

    def remove_path(self, path):
        """
        Remove a folder path from the model.

        Args:
            path (str): The path to a folder containing a .links file.

        """
        if self.root_node() is None:
            return

        for parent_node in self.root_node().children():
            if parent_node.path() != path:
                continue

            self.beginResetModel()
            self.root_node().children().remove(parent_node)
            self.endResetModel()
            break

    def reload_path(self, path):
        """
        Reload a path in the model.

        Args:
            path (str): The path to a folder containing a .links file.

        """
        if self.root_node() is None:
            return

        for parent_node in self.root_node().children():
            if parent_node.path() != path:
                continue

            self.beginResetModel()
            parent_node.children().clear()
            for link in parent_node.api().get(force=True):
                child_node = Node(link, parent=parent_node)
                parent_node.append_child(child_node)
            self.endResetModel()

    def clear(self):
        """
        Clear all children of the root node.

        """
        if not self.root_node():
            return

        self.beginResetModel()
        self.root_node().children().clear()
        self.endResetModel()

    def root_node(self):
        """
        Get the root node.

        Returns:
            Node: The root node.

        """
        return self._root_node

    def rowCount(self, parent=QtCore.QModelIndex()):
        if self.root_node() is None:
            return 0
        if not parent.isValid():
            parent_node = self.root_node()
            return parent_node.child_count()
        node = parent.internalPointer()
        if node is None:
            return 0
        return node.child_count()

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        node = index.internalPointer()
        if not node:
            return None

        if role == QtCore.Qt.DisplayRole:
            root_path = common.active('root', path=True)
            if node.is_leaf():
                name = node.path()
            else:

                name = node.path().replace('.links', '').replace('\\', '/').strip('/')
                if root_path in name:
                    name = name[len(root_path):].strip('/')

            if not node.exists():
                name = f'[Not yet created] {name}'

            return name

        elif role == QtCore.Qt.ToolTipRole or role == QtCore.Qt.StatusTipRole or role == QtCore.Qt.WhatsThisRole:
            if node.is_leaf():
                return node.api().to_absolute(node.path())
            return node.path()

        elif role == QtCore.Qt.DecorationRole:
            if not node.exists():
                return ui.get_icon('alert', color=common.Color.Red())

            if node.is_leaf():
                return ui.get_icon('link', color=common.Color.Blue())

            if node.child_count() > 0:
                icon = ui.get_icon('link', color=common.Color.SelectedText())
            else:
                icon = ui.get_icon('folder')

            return icon

        elif role == QtCore.Qt.SizeHintRole:
            if node.is_leaf():
                return QtCore.QSize(1, common.Size.RowHeight(0.66))
            return self.row_size

        elif role == QtCore.Qt.UserRole:
            return node.path()

        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return 'Links'
            else:
                return f'Row {section}'

        return None

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parent_node = self.root_node()
        else:
            parent_node = parent.internalPointer()

        child_node = parent_node.child(row)
        if child_node:
            return self.createIndex(row, column, child_node)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        node = index.internalPointer()
        parent_node = node.parent()

        if parent_node == self.root_node() or parent_node is None:
            return QtCore.QModelIndex()

        grandparent_node = parent_node.parent()
        if grandparent_node and parent_node in grandparent_node.children():
            row = grandparent_node.children().index(parent_node)
            return self.createIndex(row, 0, parent_node)
        else:
            return QtCore.QModelIndex()

    def clear_links(self, path):
        """
        Clear all links for the specified path.

        Args:
            path (str): The path to the folder containing the .links file.
        """
        if self.root_node() is None:
            return

        self.beginResetModel()
        for parent_node in self.root_node().children():
            if parent_node.path() != path:
                continue
            parent_node.api().clear()
            parent_node.children().clear()
            self.endResetModel()

            break

    def prune_links(self, path):
        """
        Prune links for the specified path.

        Args:
            path (str): The path to the folder containing the .links file.

        """
        if self.root_node() is None:
            return

        for parent_node in self.root_node().children():
            if parent_node.path() != path:
                continue

            removed_links = parent_node.api().prune()

            self.beginResetModel()
            parent_node.children().clear()
            for link in parent_node.api().get(force=True):
                child_node = Node(link, parent=parent_node)
                parent_node.append_child(child_node)
            self.endResetModel()

            return removed_links

    def remove_link(self, parent_path, path):
        """
        Remove a link from the model.

        Args:
            parent_path (str): The path to the parent folder containing the .links file.
            path (str): The link to remove.

        """
        if self.root_node() is None:
            return

        for parent_node in self.root_node().children():
            if parent_node.path() != parent_path:
                continue

            for child_node in parent_node.children():
                if child_node.path() == path:
                    parent_node.api().remove(path)

                    self.beginResetModel()
                    parent_node.children().remove(child_node)
                    self.endResetModel()
                    break

    def add_link(self, parent_path, path):
        """
        Add a link to the model.

        Args:
            parent_path (str): The path to the parent folder containing the .links file.
            path (str): The link to add.

        """
        if self.root_node() is None:
            return

        for parent_node in self.root_node().children():
            if parent_node.path() != parent_path:
                continue

            child_node = Node(path, parent=parent_node)
            child_node.api().add(path)

            self.beginResetModel()
            parent_node.append_child(child_node)
            parent_node.children().sort(key=lambda x: x.path())
            self.endResetModel()
            break

    def paste_links(self, path):
        """
        Paste links from the clipboard.

        Args:
            path (str): The path to the folder containing the .links file.

        Returns:
            list: A list of links that were skipped.

        """
        skipped = []
        for parent_node in self.root_node().children():
            if parent_node.path() != path:
                continue

            skipped = parent_node.api().paste_from_clipboard()

            self.beginResetModel()
            parent_node.children().clear()
            for link in parent_node.api().get(force=True):
                child_node = Node(link, parent=parent_node)
                parent_node.append_child(child_node)
            self.endResetModel()

        return skipped

    def apply_preset(self, preset, path=None):
        """
        Apply a preset to the model.

        Args:
            path (str, optional): The path to the folder containing the .links file.
                If None, all paths are affected.
            preset (str): The preset to apply.

        """
        for parent_node in self.root_node().children():
            if path is not None and parent_node.path() != path:
                continue

            parent_node.api().apply_preset(preset)

            self.beginResetModel()
            parent_node.children().clear()
            for link in parent_node.api().get(force=True):
                child_node = Node(link, parent=parent_node)
                parent_node.append_child(child_node)
            self.endResetModel()
