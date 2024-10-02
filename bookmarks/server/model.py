import enum
import json
import os

from PySide2 import QtCore, QtGui

from .lib import ServerAPI, JobStyle
from .. import common, ui, log, images
from ..links.lib import LinksAPI
from ..templates import lib as templates_lib


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

    def remove_child(self, row):
        """
        Remove the child node at the specified row.

        Args:
            row (int): The row index.

        """
        if len(self._children) - 1 < row:
            return

        del self._children[row]

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

    def is_bookmarked(self):
        """
        Check if this node is bookmarked.

        Returns:
            bool: True if this node is bookmarked.

        """

        paths = common.bookmarks.keys()
        if not paths:
            return False

        if self.type == NodeType.BookmarkNode:
            if self.path() in paths:
                return True
        else:
            if self.path() in ''.join(paths):
                return True
        return False

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

    @children_fetched.setter
    def children_fetched(self, value):
        self._children_fetched = value

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


class ServerFilterProxyModel(QtCore.QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.text_filter = ''
        self.show_bookmarked = False
        self.hide_non_candidates = False

        self.setDynamicSortFilter(True)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

    def reset_filters(self, value):
        if not value:
            return
        self.show_bookmarked = False
        self.hide_non_candidates = False
        self.invalidateFilter()

    def set_text_filter(self, text):
        self.text_filter = text
        self.invalidateFilter()

    def set_show_bookmarked(self, value):
        self.show_bookmarked = value
        self.hide_non_candidates = False
        self.invalidateFilter()

    def set_hide_non_candidates(self, value):
        self.hide_non_candidates = value
        self.show_bookmarked = False
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        node = index.internalPointer()
        if not node:
            return False

        if self.show_bookmarked and not node.is_bookmarked():
            return False

        if node.type == NodeType.JobNode:
            if self.hide_non_candidates and not node.job_candidate:
                return False

        if not self.text_filter:
            return True

        if node.type == NodeType.JobNode:
            if self.text_filter.lower() not in node.job.lower():
                return False

        return True


class ServerModel(QtCore.QAbstractItemModel):
    row_size = QtCore.QSize(1, common.Size.RowHeight(1.0))

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
            e = JobStyle.DefaultJobFolders
        self._job_style = int(e)

    def _connect_signals(self):
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
                v = node.server
            elif node.type == NodeType.JobNode:
                v = ' | '.join(node.job.split('/'))
            elif node.type == NodeType.BookmarkNode:
                v = node.root

            if node.is_bookmarked():
                v = f'{v}  *'
            return v
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
            if node.is_bookmarked():
                font, _ = common.Font.BlackFont(common.Size.MediumText())
                return font
            else:
                font, _ = common.Font.LightFont(common.Size.MediumText())
                return font
        if role == QtCore.Qt.DecorationRole:
            if node.is_bookmarked():
                return ui.get_icon('bookmark', color=common.Color.Green())

            if node.type == NodeType.ServerNode:
                return ui.get_icon('server')
            elif node.type == NodeType.JobNode:
                thumb_path = f'{node.server}/{node.job}/thumbnail.{common.thumbnail_format}'
                pixmap = images.ImageCache.get_pixmap(thumb_path, self.row_size.height())
                if pixmap and not pixmap.isNull():
                    icon = QtGui.QIcon()
                    icon.addPixmap(pixmap)
                    return icon
            elif node.type == NodeType.BookmarkNode:
                if not node.exists():
                    return ui.get_icon('alert')
                return ui.get_icon('link', color=common.Color.Blue())

        if role == QtCore.Qt.SizeHintRole:
            if node.type == NodeType.JobNode:
                return QtCore.QSize(self.row_size.width(), common.Size.RowHeight(0.66))
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
            bookmarks = [v['root'] for v in common.bookmarks.values() if
                         v['server'] == node.server and v['job'] == node.job]
            if bookmarks:
                return True
            if LinksAPI(node.path()).has_links():
                return True
            node.job_candidate = False

        if node.type == NodeType.BookmarkNode:
            return False

        return False

    def fetchMore(self, parent):
        node = parent.internalPointer()
        if not node:
            return

        if node.type != NodeType.BookmarkNode and node.children_fetched:
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
                    if entry.name[0] in {'.', '$'}:
                        continue
                    if entry.name in templates_lib.template_blacklist:
                        continue
                    if not os.access(entry.path, os.R_OK | os.W_OK):
                        log.error(f'No access to {entry.path}')
                        continue
                    p = entry.path.replace('\\', '/')

                    rel_path = p.replace(root_path, '').strip('/')

                    if depth == self._job_style:
                        yield rel_path
                    abs_path = entry.path.replace('\\', '/')
                    images.ImageCache.flush(abs_path)
                    yield from _it(entry.path, depth)

            current_job_names = [child.job for child in node.children()]
            new_job_names = sorted([job_path for job_path in _it(root_path, -1)], key=lambda s: s.lower())
            missing_job_names = set(new_job_names) - set(current_job_names)

            for job_path in missing_job_names:
                if job_path in [f.job for f in node.children()]:
                    continue

                current_job_names.append(job_path)
                current_job_names = sorted(current_job_names, key=lambda s: s.lower())
                idx = current_job_names.index(job_path)

                self.beginInsertRows(parent, idx, idx)
                job_node = Node(server=node.server, job=job_path, parent=node)
                node.insert_child(idx, job_node)
                self.endInsertRows()

                if os.path.exists(f'{node.server}/{job_path}/.links'):
                    job_node.job_candidate = True

        if node.type == NodeType.JobNode:  # fetch links
            if node.job_candidate:
                api = LinksAPI(node.path())
                links = api.get(force=True)

                # Add bookmark items
                bookmarks = [v['root'] for v in common.bookmarks.values() if
                             v['server'] == node.server and v['job'] == node.job]
                links += bookmarks
                links = sorted(set(links), key=lambda s: s.lower())

                if node.children():
                    self.beginRemoveRows(parent, 0, len(node.children()) - 1)
                    node.children().clear()
                    self.endRemoveRows()

                self.beginInsertRows(parent, 0, len(links) - 1)
                for link in links:
                    if link in [f.root for f in node.children()]:
                        continue
                    link_node = Node(server=node.server, job=node.job, root=link, parent=node)
                    link_node.exists()
                    node.append_child(link_node)
                self.endInsertRows()

        node.children_fetched = True

    def hasChildren(self, parent):
        if not parent.isValid():
            return True
        return self.canFetchMore(parent)

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        node = index.internalPointer()
        if not node:
            return QtCore.Qt.NoItemFlags

        if node.type == NodeType.ServerNode:
            return super().flags(index)
        if node.type == NodeType.JobNode:
            return super().flags(index)
        if node.type == NodeType.BookmarkNode:
            return super().flags(index) | QtCore.Qt.ItemIsDragEnabled

        return super().flags(index)

    def supportedDropActions(self):
        return QtCore.Qt.NoDropAction

    def supportedDragActions(self):
        return QtCore.Qt.CopyAction

    def mimeTypes(self):
        return ['text/plain']

    def mimeData(self, indexes):
        if not indexes:
            return None
        index = next((f for f in indexes), QtCore.QModelIndex())
        if not index.isValid():
            return None
        node = index.internalPointer()
        if not node:
            return None

        server = node.server
        job = node.job
        root = node.root

        data = {
            f'{server}/{job}/{root}': {
                'server': server,
                'job': job,
                'root': root
            }
        }

        json_data = json.dumps(data)

        mime_data = QtCore.QMimeData()
        mime_data.setData('text/plain', json_data.encode())
        return mime_data

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

        servers = ServerAPI.get_servers(force=True)
        self.beginInsertRows(QtCore.QModelIndex(), 0, len(servers) - 1)
        for server in servers:
            if server in [f.server for f in self._root_node.children()]:
                continue
            node = Node(server=server, parent=self._root_node)
            self._root_node.append_child(node)
        self.endInsertRows()
        self.endResetModel()

    @QtCore.Slot(str)
    def add_server(self, server):
        current_servers = ServerAPI.get_servers(force=True)
        current_servers = current_servers if current_servers else {}
        current_servers = list(current_servers.keys())
        all_servers = sorted(current_servers + [server, ], key=lambda s: s.lower())

        idx = all_servers.index(server)

        if server in [f.server for f in self._root_node.children()]:
            return

        self.beginInsertRows(QtCore.QModelIndex(), idx, idx)
        ServerAPI.add_server(server)
        node = Node(server=server, parent=self._root_node)
        self._root_node.insert_child(idx, node)
        self.endInsertRows()

    @QtCore.Slot(str)
    def remove_server(self, server):
        current_servers = ServerAPI.get_servers()
        current_servers = current_servers if current_servers else {}
        current_servers = list(current_servers.keys())
        current_servers = sorted(current_servers, key=lambda s: s.lower())

        idx = current_servers.index(server)

        ServerAPI.remove_server(server)

        self.beginRemoveRows(QtCore.QModelIndex(), idx, idx)
        self._root_node.remove_child(idx)
        self.endRemoveRows()

    @QtCore.Slot()
    def remove_servers(self):
        servers = ServerAPI.get_servers()
        for server in servers:
            self.remove_server(server)

    @QtCore.Slot()
    def reset_children_fetched(self):
        def _it(parent_index):
            for i in range(self.rowCount(parent_index)):
                child_index = self.index(i, 0, parent_index)
                node = child_index.internalPointer()
                if node.children_fetched:
                    node.children_fetched = False
                _it(child_index)

        index = self.index(0, 0, QtCore.QModelIndex())
        _it(index)
