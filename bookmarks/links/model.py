from PySide2 import QtCore

from .lib import Links


class Node:
    """
    A class representing a node in the tree model.
    """

    def __init__(self, data, parent=None):
        """
        Initialize the Node.

        Args:
            data: The data to store in this node.
            parent (Node): The parent node.
        """
        self._data = data
        self._parent = parent
        self._children = []

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

    def data(self):
        """
        Get the data stored in this node.

        Returns:
            The data.
        """
        return self._data

    def parent(self):
        """
        Get the parent node.

        Returns:
            Node: The parent node.
        """
        return self._parent

    def row(self):
        """
        Get the row number of this node in its parent's children list.

        Returns:
            int: The row index.
        """
        if self._parent:
            return self._parent._children.index(self)
        return 0  # Root node


class AssetLinksModel(QtCore.QAbstractItemModel):
    """
    A model representing the asset links as a tree.
    """

    def __init__(self, path, parent=None):
        """
        Initialize the model.

        Args:
            path (str): Path to a folder containing a .links file.
            parent: The parent object.
        """
        super().__init__(parent)
        self._links = Links(path)
        self._root_node = Node('Root')
        self.init_data()

    def init_data(self):
        """
        Set up the tree structure based on the links.
        """
        # Clear existing data
        self._root_node = Node('Root')

        # Create a node for the links file
        links_node = Node(self._links.links_file, self._root_node)
        self._root_node.append_child(links_node)

        # Get the relative links from the links instance
        links = self._links.get()

        # For each link, create a child node under links_node
        for link in links:
            child_node = Node(link, links_node)
            links_node.append_child(child_node)

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        Return the number of rows under the given parent.

        Args:
            parent (QtCore.QModelIndex): The parent index.

        Returns:
            int: The number of rows.
        """
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_node = self._root_node
        else:
            parent_node = parent.internalPointer()

        return parent_node.child_count()

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        Return the number of columns for the children of the given parent.

        Args:
            parent (QtCore.QModelIndex): The parent index.

        Returns:
            int: The number of columns.
        """
        return 1  # Only one column needed for link names

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        Return the data stored under the given role for the item referred to by the index.

        Args:
            index (QtCore.QModelIndex): The index of the item.
            role (int): The role.

        Returns:
            The data.
        """
        if not index.isValid():
            return None

        node = index.internalPointer()

        if role == QtCore.Qt.DisplayRole:
            if node.parent() == self._root_node:
                return node.data().replace('.links', '').strip('/')
            else:
                return node.data()



        if role == QtCore.Qt.UserRole:
            return node.data()

        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """
        Return the data for the given role and section in the header with the specified orientation.

        Args:
            section (int): The section number.
            orientation (QtCore.Qt.Orientation): The orientation.
            role (int): The role.

        Returns:
            The header data.
        """
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return "Links"
            else:
                return f"Row {section}"

        return None

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """
        Return the index of the item in the model specified by the given row, column, and parent index.

        Args:
            row (int): The row.
            column (int): The column.
            parent (QtCore.QModelIndex): The parent index.

        Returns:
            QtCore.QModelIndex: The index.
        """
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parent_node = self._root_node
        else:
            parent_node = parent.internalPointer()

        child_node = parent_node.child(row)
        if child_node:
            return self.createIndex(row, column, child_node)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        """
        Return the parent of the model item with the given index.

        Args:
            index (QtCore.QModelIndex): The index.

        Returns:
            QtCore.QModelIndex: The parent index.
        """
        if not index.isValid():
            return QtCore.QModelIndex()

        child_node = index.internalPointer()
        parent_node = child_node.parent()

        if parent_node == self._root_node or parent_node is None:
            return QtCore.QModelIndex()

        grandparent_node = parent_node.parent()
        if grandparent_node:
            row = grandparent_node.children().index(parent_node)
            return self.createIndex(row, 0, parent_node)
        else:
            return QtCore.QModelIndex()

    def links(self):
        """
        Get the links object.

        Returns:
            Links: The links object.
        """
        return self._links

    def add_link(self, link):
        """
        Add a link to the model and update the view.

        Args:
            link (str): The link to add.
        """
        # Use the links/lib.py API to add the link
        self.beginResetModel()
        self._links.add(link)
        self.init_data()
        self.endResetModel()

    def remove_link(self, link):
        """
        Remove a link from the model and update the view.

        Args:
            link (str): The link to remove.
        """
        # Use the links/lib.py API to remove the link
        self.beginResetModel()
        self._links.remove(link)
        self.init_data()
        self.endResetModel()

    def clear_links(self):
        """
        Clear all links from the model and update the view.
        """
        self.beginResetModel()
        self._links.clear()
        self.init_data()
        self.endResetModel()

    def prune_links(self):
        """
        Prune invalid links from the model and update the view.
        """
        self.beginResetModel()
        v = self._links.prune()
        self.init_data()
        self.endResetModel()

        return v
