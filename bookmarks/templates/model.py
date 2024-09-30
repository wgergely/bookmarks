from PySide2 import QtCore

from . import lib
from .. import common, log


class Node:
    """
    A class representing a node in the tree model.
    """

    def __init__(self, item, parent=None):
        """
        Initialize the Node.

        Args:
            item (TemplateItem): The item to represent.
            parent (Node): The parent node.
        """
        self._api = item
        self._parent = parent
        self._children = []

    @property
    def api(self):
        """
        The TemplateItem api instance.

        Returns:
            The data.
        """
        if not isinstance(self._api, lib.TemplateItem):
            return None
        return self._api

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
        return self.api is not None

    def row(self):
        """
        Get the row number of this node in its parent's children list.

        Returns:
            int: The row index.
        """
        if self._parent:
            return self._parent._children.index(self)
        return 0  # Root node

class TemplatesModel(QtCore.QAbstractItemModel):

    def __init__(self, parent=None):
        """
        Initialize the model.

        Args:
            path (str): Path to a folder containing a .links file.
            parent: The parent object.

        """
        super().__init__(parent)
        self._root_node = None

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
        return 4

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        node = index.internalPointer()
        if not node:
            return None

        # All columns
        if role == QtCore.Qt.SizeHintRole:
            o = common.Size.RowHeight()
            if node.is_leaf():
                return QtCore.QSize(o * 1.5, o * 1.5)
            return QtCore.QSize(o * 1.5, o)

        if index.column() == 0:
            return self._col0_data(index, node, role)

        if index.column() == 1:
            return self._col1_data(node, role)

        if index.column() == 2:
            return self._col2_data(node, role)

    def _col0_data(self, index, node, role):
        if not node.is_leaf():
            if role == QtCore.Qt.DisplayRole and index.row() == 0:
                return 'Project Templates'
            if role == QtCore.Qt.DisplayRole and index.row() == 1:
                return 'My Templates'
            return None

        if role == QtCore.Qt.DisplayRole:
            return 'Thumbnail'
        if role == QtCore.Qt.DecorationRole:
            return node.api.get_thumbnail()
        if role == QtCore.Qt.EditRole:
            return node.api.get_thumbnail()

    def _col1_data(self, node, role):
        if role == QtCore.Qt.DisplayRole:
            if node.is_leaf():
                d = node.api['description']
                d = f'{d}' if d else ''
                return f'{node.api["name"]}\n{d}'

        if role == QtCore.Qt.EditRole:
            if node.is_leaf():
                return node.api['name']

        if (
                role == QtCore.Qt.ToolTipRole or
                role == QtCore.Qt.StatusTipRole or
                role == QtCore.Qt.WhatsThisRole
        ):
            if node.is_leaf():
                return node.api['name']

    def _col2_data(self, node, role):
        if role == QtCore.Qt.DisplayRole:
            if node.is_leaf():
                author = node.api['author']
                author = f'Author: {author}' if author else '<no author>'
                date = node.api['date']
                date = f'Date: {date}' if date else '<no date>'
                size = common.byte_to_pretty_string(node.api.size)

                return f'{author}\n{date}\n{size}'

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if section == 0:
                    return 'Thumbnail'
                if section == 1:
                    return 'Name'
                if section == 2:
                    return 'Info'
                if section == 3:
                    return 'Template'
                return ''
            if orientation == QtCore.Qt.Vertical:
                return f'{section}'

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

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        node = index.internalPointer()
        if not node:
            return QtCore.Qt.NoItemFlags

        if index.column() == 0:
            if node.is_leaf():
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
        elif index.column() == 1:
            if node.is_leaf():
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
        elif index.column() == 2:
            if node.is_leaf():
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
        elif index.column() == 3:
            if node.is_leaf():
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def init_data(self):
        self.beginResetModel()

        self._root_node = Node(None)

        node1 = Node(None, parent=self._root_node)
        self._root_node.append_child(node1)

        try:
            templates = lib.TemplateItem.get_saved_templates(lib.TemplateType.DatabaseTemplate)
            templates = sorted(templates, key=lambda x: x['name'].lower())
            for template in templates:
                node = Node(template, parent=node1)
                node1.append_child(node)
        except Exception as e:
            log.error(f'Error loading database templates: {e}')

        node2 = Node(None, parent=self._root_node)
        self._root_node.append_child(node2)

        try:
            templates = lib.TemplateItem.get_saved_templates(lib.TemplateType.UserTemplate)
            templates = sorted(templates, key=lambda x: x['name'].lower())
            for template in templates:
                node = Node(template, parent=node2)
                node2.append_child(node)
        except Exception as e:
            log.error(f'Error loading user templates: {e}')

        self.endResetModel()
