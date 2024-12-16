"""Contains the model for interacting with server, job, and link items and bookmarking them for use.

This implementation uses a worker thread to perform long-running fetch operations
asynchronously, preventing the UI from freezing. To avoid multiple simultaneous fetches
that can cause duplicate items, a mutex is used only around the data modifications
triggered by fetchMore and the worker callbacks. Other methods remain unlocked to avoid
freezing the UI.
"""
import enum
import json
import os

from PySide2 import QtCore, QtGui

from .lib import ServerAPI, JobDepth
from .. import common, ui, log, images
from ..links.lib import LinksAPI
from ..templates import lib as templates_lib


class NodeType(enum.IntEnum):
    RootNode = -1
    ServerNode = 0
    JobNode = 1
    LinkNode = 2


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
        self._children.insert(row, child)

    def append_child(self, child):
        self._children.append(child)

    def remove_child(self, row):
        if 0 <= row < len(self._children):
            del self._children[row]

    def children(self):
        return self._children

    def child(self, row):
        if 0 <= row < len(self._children):
            return self._children[row]
        return None

    def child_count(self):
        return len(self._children)

    def has_children(self):
        return bool(self._children)

    def parent(self):
        return self._parent

    def exists(self):
        if self._exists is None:
            p = self.path()
            self._exists = os.path.exists(p) if p else False
        return self._exists

    def is_bookmarked(self):
        if not common.bookmarks:
            return False
        p = self.path()
        return any(p in f for f in common.bookmarks.keys())

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
        if self._server is None and self._job is None and self._root is None:
            return NodeType.RootNode
        elif all([self._server, self._job, self._root]):
            return NodeType.LinkNode
        elif all([self._server, self._job]):
            return NodeType.JobNode
        elif self._server:
            return NodeType.ServerNode
        return NodeType.RootNode

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

        if node.type == NodeType.JobNode and self.hide_non_candidates and not node.job_candidate:
            return False

        if not self.text_filter:
            return True

        tf = self.text_filter.lower()

        def matches_node(n):
            if tf in n.path().lower():
                return True
            if n.type == NodeType.ServerNode:
                children = [c for gc in n.children() for c in gc.children()]
                candidates = [ch.path().lower() for ch in children]
                candidates += [' / '.join(ch.path().lower().split('/')) for ch in children]
            else:
                candidates = [n.path().lower(), ' / '.join(n.path().lower().split('/'))]
            return any(tf in c for c in candidates)

        return matches_node(node)


class Worker(QtCore.QObject):
    job_found = QtCore.Signal(str)
    links_found = QtCore.Signal(list)
    progress = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(self, node, job_style):
        super().__init__()
        self.node = node
        self.job_style = job_style
        self.n = 0
        self.nth = 13

    def run(self):
        if self.node.type == NodeType.ServerNode:
            self._fetch_jobs()
        elif self.node.type == NodeType.JobNode and self.node.job_candidate:
            self._fetch_links()
        self.finished.emit()

    def _fetch_jobs(self):
        root_path = self.node.path()

        def _it(path, depth):
            self.n += 1
            depth += 1
            if depth > self.job_style:
                return
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_dir() and entry.name[0] not in {'.', '$'} and \
                            entry.name not in templates_lib.template_file_blacklist and \
                            os.access(entry.path, os.R_OK | os.W_OK):
                        p = entry.path.replace('\\', '/')
                        rel_path = p.replace(root_path, '').strip('/')
                        if depth == self.job_style:
                            yield rel_path
                        abs_path = entry.path.replace('\\', '/')
                        images.ImageCache.flush(abs_path)
                        if self.n % self.nth == 0:
                            self.progress.emit('Parsing...')
                        yield from _it(entry.path, depth)

        current_jobs = [child.job for child in self.node.children()]
        new_jobs = sorted([j for j in _it(root_path, -1)], key=lambda s: s.lower())
        missing = set(new_jobs) - set(current_jobs)
        for job_path in missing:
            if self.n % self.nth == 0:
                self.progress.emit('Adding job...')
            self.job_found.emit(job_path)

    def _fetch_links(self):
        api = LinksAPI(self.node.path())
        links = api.get(force=True)
        bookmarks = [v['root'] for v in common.bookmarks.values()
                     if v['server'] == self.node.server and v['job'] == self.node.job]
        links += bookmarks
        links = sorted(set(links), key=lambda s: s.lower())

        self.links_found.emit(links)


class ServerModel(QtCore.QAbstractItemModel):
    row_size = QtCore.QSize(1, common.Size.RowHeight(0.8))
    fetchAboutToStart = QtCore.Signal()
    fetchInProgress = QtCore.Signal(str)
    fetchFinished = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_node = None
        self._job_style = None
        self._init_job_style()
        self._worker_thread = None
        self._worker = None
        self._data_lock = QtCore.QMutex()  # Only used in fetchMore and insert methods

    def _init_job_style(self):
        v = common.settings.value(ServerAPI.job_style_settings_key)
        if isinstance(v, int):
            e = JobDepth(v)
        else:
            e = JobDepth.Job
        self._job_style = int(e)

    def clear(self):
        # Clearing doesn't need concurrency protection if done on main thread only
        if not self.root_node():
            return
        self.beginResetModel()
        self.root_node().children().clear()
        self.endResetModel()

    def root_node(self):
        return self._root_node

    def rowCount(self, parent=QtCore.QModelIndex()):
        # Reading methods should be done only on the main thread, no lock needed
        if self.root_node() is None:
            return 0
        if not parent.isValid():
            return self.root_node().child_count()
        node = parent.internalPointer()
        if node is None:
            return 0
        return node.child_count()

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 3

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
        return QtCore.QModelIndex()

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            if section == 0:
                return 'Name'
            elif section == 1:
                return 'Type'
            elif section == 2:
                return 'Count'
        return None

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if not node:
            return None

        if role == QtCore.Qt.FontRole:
            if index.column() == 0:
                font, _ = common.Font.BoldFont(common.Size.MediumText())
            else:
                font, _ = common.Font.ThinFont(common.Size.SmallText())
            return font

        if index.column() == 0:
            if role == QtCore.Qt.DisplayRole:
                if node.type == NodeType.ServerNode:
                    return '/'.join(node.server.split('/'))
                elif node.type == NodeType.JobNode:
                    return ' / '.join(node.job.split('/'))
                elif node.type == NodeType.LinkNode:
                    return ' / '.join(node.root.split('/'))
            if role == QtCore.Qt.UserRole:
                if node.type == NodeType.ServerNode:
                    return node.server
                elif node.type == NodeType.JobNode:
                    return f'{node.server}/{node.job}'
                elif node.type == NodeType.LinkNode:
                    return f'{node.server}/{node.job}/{node.root}'
            if role in (QtCore.Qt.ToolTipRole, QtCore.Qt.StatusTipRole, QtCore.Qt.WhatsThisRole):
                return node.path()
            if role == QtCore.Qt.FontRole:
                font, _ = common.Font.LightFont(common.Size.MediumText())
                return font
            if role == QtCore.Qt.DecorationRole:
                if not node.exists():
                    if node.is_bookmarked():
                        return ui.get_icon('alert', color=common.Color.Yellow())
                    return ui.get_icon('alert', color=common.Color.Red())
                if node.type == NodeType.ServerNode:
                    return ui.get_icon('server', active_brightness=100)
                elif node.type == NodeType.JobNode:
                    return ui.get_icon('asset', color=common.Color.Yellow(), active_brightness=100)
                elif node.type == NodeType.LinkNode:
                    return ui.get_icon('link', color=common.Color.Blue(), active_brightness=100)

        if index.column() == 1 and role == QtCore.Qt.DisplayRole:
            if node.type == NodeType.ServerNode:
                return 'Server'
            elif node.type == NodeType.JobNode:
                return 'Job'
            elif node.type == NodeType.LinkNode:
                return 'Link'

        if index.column() == 2 and role == QtCore.Qt.DisplayRole:
            if not self.canFetchMore(index):
                return ''
            if not node.children_fetched:
                return '...'
            c = len(node.children())
            if c == 0:
                return ''
            if c == 1:
                return '1 item'
            return f'{c} items'

        if index.column() in (1, 2):
            if role == QtCore.Qt.FontRole:
                font, _ = common.Font.LightFont(common.Size.MediumText(0.8))
                return font
            if role == QtCore.Qt.ForegroundRole:
                return QtGui.QBrush(common.Color.DisabledText())
            if role == QtCore.Qt.BackgroundRole:
                return QtGui.QBrush(common.Color.Transparent())
            if role == QtCore.Qt.DecorationRole:
                return None

        if role == QtCore.Qt.SizeHintRole:
            return self.row_size

    def canFetchMore(self, parent):
        if not parent.isValid():
            return True
        node = parent.internalPointer()
        if not node:
            return False
        if not node.exists():
            return False
        if node.type == NodeType.RootNode:
            return node.has_children()
        if node.type == NodeType.ServerNode:
            with os.scandir(node.path()) as it:
                for entry in it:
                    if entry.is_dir():
                        return True
        if node.type == NodeType.JobNode:
            bookmarks = [v['root'] for v in common.bookmarks.values()
                         if v['server'] == node.server and v['job'] == node.job]
            if bookmarks:
                return True
            if LinksAPI(node.path()).has_links():
                return True
            node.job_candidate = False
        if node.type == NodeType.LinkNode:
            return False
        return False

    def fetchMore(self, parent):
        # Lock only around the code that might start a worker or check worker state
        locker = QtCore.QMutexLocker(self._data_lock)
        if self._worker_thread and self._worker_thread.isRunning():
            return
        node = parent.internalPointer()
        if not node or (node.type != NodeType.LinkNode and node.children_fetched):
            return
        if not self.canFetchMore(parent):
            return
        if node.type == NodeType.RootNode:
            return

        self.fetchAboutToStart.emit()
        self._worker_thread = QtCore.QThread(self)
        self._worker = Worker(node, self._job_style)
        self._worker.moveToThread(self._worker_thread)

        cnx = QtCore.Qt.QueuedConnection
        self._worker.job_found.connect(lambda job_path: self._insert_job(node, parent, job_path), type=cnx)
        self._worker.links_found.connect(lambda links: self._insert_links(node, parent, links), type=cnx)
        self._worker.progress.connect(self.fetchInProgress.emit, type=cnx)

        def on_finished():
            with QtCore.QMutexLocker(self._data_lock):
                node.children_fetched = True
            self.fetchFinished.emit()
            self.dataChanged.emit(parent, parent)
            self._worker_thread.quit()
            self._worker_thread.wait()

        self._worker.finished.connect(on_finished)
        self._worker_thread.started.connect(self._worker.run)
        self._worker_thread.start()

    def _insert_job(self, node, parent, job_path):
        with QtCore.QMutexLocker(self._data_lock):
            current_job_names = [child.job for child in node.children()]
            if job_path in current_job_names:
                return
            current_job_names.append(job_path)
            current_job_names = sorted(current_job_names, key=lambda s: s.lower())
            idx = current_job_names.index(job_path)
            self.beginInsertRows(parent, idx, idx)
            job_node = Node(server=node.server, job=job_path, parent=node)
            node.insert_child(idx, job_node)
            self.endInsertRows()
            if os.path.exists(f'{node.server}/{job_path}/.links'):
                job_node.job_candidate = True

    def _insert_links(self, node, parent, links):
        with QtCore.QMutexLocker(self._data_lock):
            existing_roots = [f.root for f in node.children()]
            new_links = [l for l in links if l not in existing_roots]
            if node.children():
                self.beginRemoveRows(parent, 0, len(node.children()) - 1)
                node.children().clear()
                self.endRemoveRows()
            if not new_links:
                return
            self.beginInsertRows(parent, 0, len(new_links) - 1)
            for link in new_links:
                link_node = Node(server=node.server, job=node.job, root=link, parent=node)
                link_node.exists()
                node.append_child(link_node)
            self.endInsertRows()

    def hasChildren(self, parent):
        if not parent.isValid():
            return True
        node = parent.internalPointer()
        if node.type == NodeType.LinkNode:
            return False
        return self.canFetchMore(parent)

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        node = index.internalPointer()
        if not node:
            return QtCore.Qt.NoItemFlags
        if node.type == NodeType.LinkNode:
            return super().flags(index) | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemNeverHasChildren
        return super().flags(index)

    def supportedDropActions(self):
        return QtCore.Qt.NoDropAction

    def supportedDragActions(self):
        return QtCore.Qt.CopyAction

    def mimeTypes(self):
        return ['text/plain']

    def mimeData(self, indexes):
        # Reading state only, no lock needed
        if not indexes:
            return None
        index = next((f for f in indexes), QtCore.QModelIndex())
        if not index.isValid():
            return None
        node = index.internalPointer()
        if not node:
            return None
        server = node.server or ''
        job = node.job or ''
        root = node.root or ''
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
        # This should be main thread only
        if v not in JobDepth:
            raise ValueError(f'Invalid job style: {v}. Expected one of {list(JobDepth)}.')
        common.settings.setValue(ServerAPI.job_style_settings_key, v.value)
        self._job_style = v.value
        self.init_data()

    @QtCore.Slot()
    def init_data(self, *args, **kwargs):
        # Model initialization should happen in main thread
        self.beginResetModel()
        self._root_node = Node(None)
        self.endResetModel()

        servers = ServerAPI.get_servers(force=True)
        servers = servers if servers else {}
        servers = sorted(servers.keys(), key=lambda s: s.lower())
        if servers:
            self.beginInsertRows(QtCore.QModelIndex(), 0, len(servers) - 1)
            for server in servers:
                if server in [f.server for f in self._root_node.children()]:
                    continue
                node = Node(server=server, parent=self._root_node)
                self._root_node.append_child(node)
            self.endInsertRows()

    @QtCore.Slot(str)
    def add_server(self, server):
        # Main thread only
        current_servers = ServerAPI.get_servers(force=True)
        current_servers = current_servers if current_servers else {}
        current_servers = list(current_servers.keys())
        all_servers = sorted(current_servers + [server], key=lambda s: s.lower())
        idx = all_servers.index(server)
        if server in [f.server for f in self._root_node.children()]:
            return
        self.beginInsertRows(QtCore.QModelIndex(), idx, idx)
        ServerAPI.add_server(server)
        node = Node(server=server, parent=self._root_node)
        self._root_node.insert_child(idx, node)
        self.endInsertRows()
        self.dataChanged.emit(self.index(0, 0), self.index(0, 0))

    @QtCore.Slot(str)
    def remove_server(self, server):
        # Main thread only
        current_servers = ServerAPI.get_servers()
        current_servers = current_servers if current_servers else {}
        current_servers = sorted(current_servers.keys(), key=lambda s: s.lower())
        if server not in current_servers:
            return
        idx = current_servers.index(server)
        ServerAPI.remove_server(server)
        self.beginRemoveRows(QtCore.QModelIndex(), idx, idx)
        self._root_node.remove_child(idx)
        self.endRemoveRows()
        self.dataChanged.emit(self.index(0, 0), self.index(0, 0))

    @QtCore.Slot()
    def remove_servers(self):
        # Main thread only
        servers = ServerAPI.get_servers()
        if not servers:
            return
        for server in list(servers.keys()):
            self.remove_server(server)

    @QtCore.Slot()
    def reset_children_fetched(self):
        # Main thread only, read-only iteration
        def _it(parent_index):
            for i in range(self.rowCount(parent_index)):
                child_index = self.index(i, 0, parent_index)
                node = child_index.internalPointer()
                if node and node.children_fetched:
                    node.children_fetched = False
                _it(child_index)

        index = self.index(0, 0, QtCore.QModelIndex())
        _it(index)
