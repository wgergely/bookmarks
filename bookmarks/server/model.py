import enum
import os

from PySide2 import QtCore

from .lib import ServerAPI, JobStyle
from .. import common, ui


class NodeType(enum.IntEnum):
    RootNode = -1
    ServerNode = 0
    JobNode = 1
    BookmarkNode = 2


class Node:

    def __init__(self, server, job=None, root=None, parent=None):
        self._server = server
        self._job = job
        self._root = root

        self._parent = parent
        self._children = []

        self._job_candidate = False

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

    def has_children(self):
        return bool(self._children)

    def parent(self):
        """
        Get the parent node.

        Returns:
            Node: The parent node.
        """
        return self._parent

    @property
    def server(self):
        return self._server

    @property
    def job(self):
        return self._job

    @property
    def root(self):
        return self._root

    @property
    def type(self):
        if all([self._server, self._job, self._root]):
            return NodeType.BookmarkNode
        elif all([self._server, self._job]):
            return NodeType.JobNode
        elif self._server:
            return NodeType.ServerNode
        else:
            return NodeType.BookmarkNode

    @property
    def job_candidate(self):
        return self._job_candidate

    @job_candidate.setter
    def job_candidate(self, value):
        self._job_candidate = value

    def path(self):
        if all([self._server, self._job, self._root]):
            return f'{self._server}/{self._job}/{self._root}'
        elif all([self._server, self._job]):
            return f'{self._server}/{self._job}'
        elif self._server:
            return self._server
        else:
            return None

    @staticmethod
    def api():
        return ServerAPI


class ServerModel(QtCore.QAbstractItemModel):
    row_size = QtCore.QSize(1, common.Size.RowHeight())

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_node = None
        self._job_style = None

        self._connect_signals()
        self._init_job_style()

    def _init_job_style(self):
        v = common.settings.value(ServerAPI.job_style_settings_key)
        if isinstance(v, int):
            self._job_style = JobStyle(v)
        self._job_style = JobStyle.NoSubdirectories

    def _connect_signals(self):
        common.signals.serversChanged.connect(self.init_data)
        common.signals.bookmarksChanged.connect(self.init_data)

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

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return 'Servers'
            else:
                return f'Row {section}'

        return None

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        node = index.internalPointer()
        if not node:
            return None

        if role == QtCore.Qt.DisplayRole:
            if node.type == NodeType.ServerNode:
                return node.server
            elif node.type == NodeType.JobNode:
                return node.job
            elif node.type == NodeType.BookmarkNode:
                return node.root
        if role == QtCore.Qt.UserRole:
            if node.type == NodeType.ServerNode:
                return node.server
            elif node.type == NodeType.JobNode:
                return f'{node.server}/{node.job}'
            elif node.type == NodeType.BookmarkNode:
                return f'{node.server}/{node.job}/{node.root}'
        if role == QtCore.Qt.DecorationRole:
            if node.type == NodeType.ServerNode:
                return ui.get_icon('server')
            elif node.type == NodeType.JobNode:
                return None
            elif node.type == NodeType.BookmarkNode:
                return ui.get_icon('bookmark')
        if role == QtCore.Qt.SizeHintRole:
            if node.type == NodeType.ServerNode:
                return self.row_size
            elif node.type == NodeType.JobNode:
                return self.row_size
            elif node.type == NodeType.BookmarkNode:
                return QtCore.QSize(1, common.Size.RowHeight(0.66))

    def canFetchMore(self, parent):
        """The model fetches data on demand when a given node has subfolders."""
        node = parent.internalPointer()
        if not node:
            return False

        if node.type == NodeType.RootNode:
            return node.has_children()

        if node.type == NodeType.ServerNode or node.type == NodeType.JobNode:
            for entry in os.scandir(node.path()):
                if entry.is_dir():
                    return True

        return False

    def fetchMore(self, parent):
        node = parent.internalPointer()
        if not node:
            return

        if node.type == NodeType.RootNode:
            return  # data should have been fetched already

        if node.type == NodeType.ServerNode:  # fetch jobs
            pass

    def set_job_style(self, v):
        """Set the job style.

        The job style is used to determine how deep to traverse into folders in a server when fetching jobs.
        Depending on how job folders are stored on the server, they _usually_ follow a pattern, for example,
        - `server/job`
        - `server/department/job`
        - `server/client/job
        - `server/department/client/job`
        - etc.

        Args:
            v (int): The job style enum.

        """
        if v not in JobStyle:
            raise ValueError(f'Invalid job style: {v}. Expected one of {JobStyle}.')
        self._job_style = v

    @QtCore.Slot()
    def init_data(self, *args, **kwargs):
        self.beginResetModel()

        self._root_node = Node(None)

        servers = ServerAPI.get_servers()
        for server in servers:
            node = Node(server=server, parent=self._root_node)
            self._root_node.append_child(node)

        self.endResetModel()
