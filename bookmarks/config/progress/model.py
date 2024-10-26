import functools

from PySide2 import QtCore, QtGui

from .node import Node
from ..lib import Section, Config
from ... import ui, common, log


class FilterTaskModel(QtCore.QSortFilterProxyModel):
    def __init__(self, enabled=True, parent=None):
        super().__init__(parent=parent)

        self._enabled = enabled

    def filterAcceptsColumn(self, idx, source_parent):
        if not self._enabled:
            return True

        mode = self.sourceModel().mode()
        if mode == 'column':
            root_node = self.sourceModel().root_node
            node = root_node.children[idx]
            return node.task['enabled']
        elif mode == 'row':
            return True
        else:
            return False

    def filterAcceptsRow(self, idx, source_parent):
        if not self._enabled:
            return True

        mode = self.sourceModel().mode()
        if mode == 'column':
            return True
        elif mode == 'row':
            root_node = self.sourceModel().root_node
            node = root_node.children[idx]
            return node.task['enabled']
        else:
            return False


class BaseTasksModel(QtCore.QAbstractItemModel):
    taskChanged = QtCore.Signal(str)  # Signal emitted when a task is added

    def __init__(self, server, job, root, mode='row', parent=None):
        super().__init__(parent=parent)

        self.server = server
        self.job = job
        self.root = root

        self._mode = mode

        self.root_node = Node({
            'name': 'root',
            'value': 'root',
        })

        self._connect_signals()

    def mode(self):
        return self._mode

    def _connect_signals(self):
        common.signals.databaseValueChanged.connect(functools.partial(self.init_data, force=True))

    def node_from_value(self, task_value):
        node = next((f for f in self.root_node.children if f.value == task_value), None)
        return node

    def index_by_value(self, task_value):
        node = self.node_from_value(task_value)
        if node is None:
            return QtCore.QModelIndex()

        idx = self.root_node.children.index(node)
        if self.mode() == 'column':
            return self.createIndex(0, idx, node)
        elif self.mode() == 'row':
            return self.createIndex(idx, 0, node)
        return QtCore.QModelIndex()

    def rowCount(self, parent=QtCore.QModelIndex()):
        if self.mode() == 'column':
            return 1
        return len(self.root_node.children)

    def columnCount(self, parent=QtCore.QModelIndex()):
        if self.mode() == 'column':
            return len(self.root_node.children)
        return 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        node = index.internalPointer()

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return node.task['name']
        elif role == QtCore.Qt.UserRole:
            return node.task['value']
        elif role == QtCore.Qt.DecorationRole:
            color = QtGui.QColor(*node.task['color'])
            return ui.get_icon(node.task['icon'], color, common.Size.Margin())
        elif (
                role == QtCore.Qt.ToolTipRole or
                role == QtCore.Qt.StatusTipRole or
                role == QtCore.Qt.WhatsThisRole
        ):
            return node.task['description']
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setBold(node.task['enabled'])
            font.setItalic(not node.task['enabled'])
            return font

        return None

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        if self.mode() == 'column':
            if column >= len(self.root_node.children):
                return QtCore.QModelIndex()
            node = self.root_node.children[column]
            return self.createIndex(row, column, node)
        elif self.mode() == 'row':
            if row >= len(self.root_node.children):
                return QtCore.QModelIndex()
            node = self.root_node.children[row]
            return self.createIndex(row, column, node)
        return QtCore.QModelIndex()

    def parent(self, index):
        return QtCore.QModelIndex()

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled
        return (
                QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsDragEnabled
                | QtCore.Qt.ItemIsDropEnabled
        )

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def supportedDragActions(self):
        return QtCore.Qt.MoveAction

    def mimeTypes(self):
        return ['application/x-task']

    def mimeData(self, indexes, **kwargs):
        mime = QtCore.QMimeData()
        encoded_data = QtCore.QByteArray()

        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.WriteOnly)

        index = next((f for f in indexes), QtCore.QModelIndex())
        if not index.isValid():
            stream.writeQString('')
        else:
            node = index.internalPointer()
            stream.writeQString(node.value)

        mime.setData('application/x-task', encoded_data)
        mime.setProperty('source_model', self)
        mime.setProperty('source_idx', index.column())
        mime.setProperty('destination_idx', -1)
        mime.setProperty('position', '')

        return mime

    @property
    def config(self):
        return Config(self.server, self.job, self.root)

    @QtCore.Slot()
    def init_data(self, *args, force=False, **kwargs):
        """Initializes the model's data by fetching tasks from the database.

        Args:
            force (bool): If True, force fetches data from the database.

        """

        self.beginResetModel()
        self.root_node.children.clear()

        tasks = self.config.data(Section.TaskConfig, force=force).values()
        for task in tasks:
            node = Node(task, parent=self.root_node)
            self.root_node.add_child(node)

        self.endResetModel()

    @QtCore.Slot()
    def enable_task(self, task_value):
        self.layoutAboutToBeChanged.emit()
        self.config.set_enabled(task_value, True, force=True)
        self.layoutChanged.emit()

        self.taskChanged.emit(task_value)

    @QtCore.Slot()
    def disable_task(self, task_value):
        self.layoutAboutToBeChanged.emit()
        self.config.set_enabled(task_value, False, force=True)
        self.layoutChanged.emit()

        self.taskChanged.emit(task_value)

    @QtCore.Slot(str, int)
    def move(self, task_value, source_idx, destination_idx):
        """Handles internal moving of tasks."""
        node = self.node_from_value(task_value)

        if node is None:
            log.error(f'Could not find task node with value: {task_value}')
            return

        # Check source and destination bounds
        if source_idx < 0 or source_idx >= len(self.root_node.children):
            log.error(f'Invalid source index: {source_idx}')
            return

        if destination_idx < 0 or destination_idx > len(self.root_node.children):
            log.error(f'Invalid destination index: {destination_idx}')
            return

        self.layoutAboutToBeChanged.emit()

        self.root_node.children.pop(source_idx)
        self.root_node.children.insert(destination_idx, node)

        self.layoutChanged.emit()

        self.taskChanged.emit(task_value)


class ActiveTasksModel(BaseTasksModel):
    """A column-based model representing tasks, supporting drag and drop."""

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                visible_indexes = [f for f in self.root_node.children if f.task['enabled']]
                idx = visible_indexes.index(self.root_node.children[section])
                return f'Task #{idx}'
            elif orientation == QtCore.Qt.Vertical:
                return f'Task #{section}'
        return super().headerData(section, orientation, role)

    def dropMimeData(self, mime_data, action, row, column, parent):
        if action != QtCore.Qt.MoveAction:
            return False

        if not mime_data.hasFormat('application/x-task'):
            return False

        # Read the dropped task values
        encoded_data = mime_data.data('application/x-task')
        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)

        task_value = None
        while not stream.atEnd():
            task_value = stream.readQString()

        if not task_value:
            return

        source_model = mime_data.property('source_model')
        source_idx = mime_data.property('source_idx')
        destination_idx = mime_data.property('destination_idx')

        if source_model == self and source_idx == destination_idx:
            # Internal move
            if source_idx == destination_idx:
                return False
            self.move(task_value, source_idx, destination_idx)
            return True
        else:
            # External drop
            self.enable_task(task_value)
            source_idx = self.root_node.children.index(self.node_from_value(task_value))
            self.move(task_value, source_idx, destination_idx)
            return True


class TaskSourceModel(BaseTasksModel):
    """A row-based model representing tasks, supporting drag and drop."""

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """Provides header data for the model."""
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return 'Templates'
        return super().headerData(section, orientation, role)

    def dropMimeData(self, mime_data, action, row, column, parent):
        if action != QtCore.Qt.MoveAction:
            return False

        if not mime_data.hasFormat('application/x-task'):
            return False

        # Read the dropped task values
        encoded_data = mime_data.data('application/x-task')
        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)

        task_value = None
        while not stream.atEnd():
            task_value = stream.readQString()

        if not task_value:
            return

        source_model = mime_data.property('source_model')

        if source_model == self:
            # Internal move isn't supported
            return False
        else:
            # Disable the task on drop
            self.disable_task(task_value)
            return True
