import enum
import os

from PySide2 import QtCore, QtGui

from .lib import ServerAPI, JobStyle
from .. import common, ui, log, images
from ..links.lib import LinksAPI


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

        self._job_candidate = False

        self._parent = parent
        self._children = []
        self._children_fetched = False

        self._exists = None

    def insert_child(self, row, child):
        """
        Insert a child node at the specified row.

        Args:
            row (int): The row index.
            child (Node): The child node to insert.

        """
        self._children.insert(row, child)

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

    def exists(self):
        if self._exists is None:
            self._exists = os.path.exists(self.path())
        return self._exists

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
    def children_fetched(self):
        return self._children_fetched

    @property
    def job_candidate(self):
        return self._job_candidate

    @job_candidate.setter
    def job_candidate(self, value):
        self._job_candidate = value

    @children_fetched.setter
    def children_fetched(self, value):
        self._children_fetched = value

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
    row_size = QtCore.QSize(1, common.Size.RowHeight(0.8))

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_node = None
        self._job_style = None

        self._connect_signals()
        self._init_job_style()

    def _init_job_style(self):
        v = common.settings.value(ServerAPI.job_style_settings_key)
        if isinstance(v, int):
            e = JobStyle(v)
        else:
            e = JobStyle.NoSubdirectories
        self._job_style = int(e)

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
                return ' | '.join(node.job.split('/'))
            elif node.type == NodeType.BookmarkNode:
                return node.root
        if role == QtCore.Qt.UserRole:
            if node.type == NodeType.ServerNode:
                return node.server
            elif node.type == NodeType.JobNode:
                return f'{node.server}/{node.job}'
            elif node.type == NodeType.BookmarkNode:
                return f'{node.server}/{node.job}/{node.root}'
        if role == QtCore.Qt.ToolTipRole:
            return node.path()
        if role == QtCore.Qt.StatusTipRole:
            return node.path()
        if role == QtCore.Qt.WhatsThisRole:
            return node.path()
        if role == QtCore.Qt.FontRole:
            if node.type == NodeType.ServerNode and node.server in {v['server'] for v in common.bookmarks.values()}:
                font, _ = common.Font.BlackFont(common.Size.MediumText())
                # set underline
                font.setUnderline(True)

                return font
            if node.type == NodeType.JobNode and node.job in {v['job'] for v in common.bookmarks.values()}:
                font, _ = common.Font.BlackFont(common.Size.MediumText())
                font.setUnderline(True)
                return font
            if node.type == NodeType.RootNode and node.root in {v['root'] for v in common.bookmarks.values()}:
                font, _ = common.Font.BlackFont(common.Size.MediumText())
                font.setUnderline(True)
                return font
            font, _ = common.Font.LightFont(common.Size.MediumText())
            return font
        if role == QtCore.Qt.DecorationRole:
            if node.type == NodeType.ServerNode:
                if node.server in {v['server'] for v in common.bookmarks.values()}:
                    return ui.get_icon('bookmark', color=common.Color.Green())
                return ui.get_icon('server')
            elif node.type == NodeType.JobNode:
                thumb_path = f'{node.server}/{node.job}/thumbnail.{common.thumbnail_format}'
                pixmap = images.ImageCache.get_pixmap(thumb_path, self.row_size.height())
                if pixmap and not pixmap.isNull():
                    icon = QtGui.QIcon()
                    icon.addPixmap(pixmap)
                    return icon
                if node.job in {v['job'] for v in common.bookmarks.values()}:
                    return ui.get_icon('bookmark', color=common.Color.Green())
            elif node.type == NodeType.BookmarkNode:
                if node.root in {v['root'] for v in common.bookmarks.values()}:
                    return ui.get_icon('bookmark', color=common.Color.Green())
                if not node.exists():
                    return ui.get_icon('alert', color=common.Color.Red())
                return ui.get_icon('bookmark')
        if role == QtCore.Qt.SizeHintRole:
            if node.type == NodeType.JobNode:
                return QtCore.QSize(self.row_size.width(), common.Size.RowHeight(1))
            return self.row_size

    def canFetchMore(self, parent):
        """The model fetches data on demand when a given node has subfolders."""
        if not parent.isValid():
            return True

        node = parent.internalPointer()
        if not node:
            return False

        if node.type == NodeType.RootNode:
            return node.has_children()

        if node.type == NodeType.ServerNode:
            for entry in os.scandir(node.path()):
                if entry.is_dir():
                    return True
        if node.type == NodeType.JobNode:
            # Check if the job has a .links file
            api = LinksAPI(node.path())
            if api.has_links():
                return True
            node.job_candidate = False

        if node.type == NodeType.BookmarkNode:
            return False

        return False

    def fetchMore(self, parent):
        node = parent.internalPointer()
        if not node:
            return
        if node.children_fetched:
            return

        if not self.canFetchMore(parent):
            return

        if node.type == NodeType.RootNode:
            return  # data should have been fetched already

        if node.type == NodeType.ServerNode:  # fetch jobs
            root_path = node.path()

            # recursively iterate through all folders up until the job style level
            def _it(path, depth):
                depth += 1

                if depth > self._job_style:
                    return

                for entry in os.scandir(path):
                    if not entry.is_dir():
                        continue
                    if entry.name.startswith('.'):
                        continue
                    if not os.access(entry.path, os.R_OK | os.W_OK):
                        log.error(f'No access to {entry.path}')
                        continue
                    p = entry.path.replace('\\', '/')
                    rel_path = p[len(root_path) + 1:].strip('/')

                    if depth == self._job_style:
                        yield rel_path
                    abs_path = entry.path.replace('\\', '/')
                    images.ImageCache.flush(abs_path)
                    yield from _it(entry.path, depth)

            current_job_names = [child.job for child in node.children()]
            new_job_names = sorted([job_path for job_path in _it(root_path, -1)], key=str.lower)
            missing_job_names = set(new_job_names) - set(current_job_names)

            for job_path in missing_job_names:
                current_job_names.append(job_path)
                current_job_names = sorted(current_job_names, key=str.lower)
                idx = current_job_names.index(job_path)

                self.beginInsertRows(parent, idx, idx)
                job_node = Node(server=node.server, job=job_path, parent=node)
                node.insert_child(idx, job_node)

                if os.path.exists(f'{node.server}/{job_path}/.links'):
                    job_node.job_candidate = True

                self.endInsertRows()

        if node.type == NodeType.JobNode:  # fetch links
            if node.job_candidate:
                api = LinksAPI(node.path())
                links = api.get(force=True)

                self.beginInsertRows(parent, 0, len(links) - 1)
                for link in links:
                    link_node = Node(server=node.server, job=node.job, root=link, parent=node)
                    link_node.exists()
                    node.append_child(link_node)
                self.endInsertRows()

        node.children_fetched = True

    def hasChildren(self, parent):
        if not parent.isValid():
            return True
        return self.canFetchMore(parent)

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

        common.settings.setValue(ServerAPI.job_style_settings_key, v.value)
        self._job_style = v.value

        # Reset the model
        self.init_data()

    @QtCore.Slot()
    def init_data(self, *args, **kwargs):

        self.beginResetModel()

        self._root_node = Node(None)
        servers = ServerAPI.get_servers()
        for server in servers:
            node = Node(server=server, parent=self._root_node)
            self._root_node.append_child(node)

        self.endResetModel()
