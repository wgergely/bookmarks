from PySide2 import QtCore

from .node import Node
from ..default_configs import default_task_config
from ..lib import Section, Config
from ... import ui, common


class TaskModel(QtCore.QAbstractItemModel):
    """Model representing tasks in columns with a single row, supporting drag and drop."""

    task_added = QtCore.Signal(str)  # Signal emitted when a task is added
    task_removed = QtCore.Signal(str)  # Signal emitted when a task is removed

    def __init__(self, server, job, root, parent=None):
        super().__init__(parent)
        self.root_node = Node({'name': 'Root'})
        self.tasks = []  # List to hold task nodes representing columns
        self.task_values = set()
        self.config = Config(server=server, job=job, root=root)

    @QtCore.Slot()
    def init_data(self):
        """Initializes the model's data by fetching tasks from the database."""
        tasks_data = self.config.data(Section.TaskConfig)

        # Ensure tasks_data is a dictionary
        if not isinstance(tasks_data, dict):
            tasks_data = {}

        self.beginResetModel()
        self.tasks = []
        self.root_node.children = []
        self.task_values.clear()

        for task_id, task_data in tasks_data.items():
            node = Node(task_data, parent=self.root_node)
            self.root_node.add_child(node)
            self.tasks.append(node)
            self.task_values.add(node.value)

        self.endResetModel()

    def get_task_data_by_value(self, value):
        """Retrieves task data by its value."""
        tasks_data = default_task_config  # Use default_task_config for task data
        return tasks_data.get(value)

    @QtCore.Slot(str)
    def remove_task(self, task_value):
        """Removes a task from the model."""
        for i, node in enumerate(self.tasks):
            if node.value == task_value:
                self.beginRemoveColumns(QtCore.QModelIndex(), i, i)
                del self.tasks[i]
                self.root_node.children.pop(i)
                self.task_values.remove(task_value)
                self.endRemoveColumns()
                self.task_removed.emit(task_value)
                break

    @QtCore.Slot(dict)
    def add_task(self, task_data):
        """Adds a task to the model."""
        if task_data['value'] in self.task_values:
            return

        self.beginResetModel()

        node = Node(task_data, parent=self.root_node)
        self.root_node.add_child(node)
        self.tasks.insert(0, node)
        self.task_values.add(node.value)

        self.endResetModel()

        self.task_added.emit(task_data['value'])

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 1

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.tasks)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        task_node = self.tasks[column]
        return self.createIndex(row, column, task_node)

    def parent(self, index):
        return QtCore.QModelIndex()  # Flat structure; parent is invalid

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return node.name
        elif role == QtCore.Qt.DecorationRole:
            return ui.get_icon(node.icon, node.color, common.Size.Margin())
        elif role == QtCore.Qt.ToolTipRole:
            return node.description
        elif role == QtCore.Qt.UserRole:
            return node.get_status()
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if 0 <= section < len(self.tasks):
                return self.tasks[section].name
        return super().headerData(section, orientation, role)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False
        node = index.internalPointer()
        if role == QtCore.Qt.EditRole:
            node.name = value
            self.dataChanged.emit(index, index, [role])
            return True
        elif role == QtCore.Qt.UserRole:
            node.set_status(value)
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled
        return (
                QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsEditable
                | QtCore.Qt.ItemIsDragEnabled
                | QtCore.Qt.ItemIsDropEnabled
        )

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def supportedDragActions(self):
        return QtCore.Qt.MoveAction

    def mimeTypes(self):
        return ['application/x-task']

    def mimeData(self, indexes):
        mime_data = QtCore.QMimeData()
        encoded_data = QtCore.QByteArray()
        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.WriteOnly)
        for index in indexes:
            if index.isValid():
                node = index.internalPointer()
                stream.writeQString(node.value)
            else:
                stream.writeQString('')
        mime_data.setData('application/x-task', encoded_data)
        mime_data.setProperty('source_model', self)
        return mime_data

    def dropMimeData(self, mime_data, action, row, column, parent):
        if action != QtCore.Qt.MoveAction:
            return False
        if not mime_data.hasFormat('application/x-task'):
            return False

        # Read the dropped task values
        encoded_data = mime_data.data('application/x-task')
        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)
        dropped_values = []
        while not stream.atEnd():
            value = stream.readQString()
            dropped_values.append(value)

        if not dropped_values:
            return False

        # Determine the insertion position
        if parent.isValid():
            insert_position = parent.column()
        elif column != -1:
            insert_position = column
        else:
            insert_position = self.columnCount()

        source_model = mime_data.property('source_model')
        if source_model == self:
            # Internal move
            self._move_tasks(dropped_values, insert_position)
            return True
        else:
            # External drop
            self._insert_tasks(dropped_values, insert_position)
            # Notify the source model to remove the task
            for value in dropped_values:
                self.task_added.emit(value)
            return True

    def _move_tasks(self, task_values, insert_position):
        """Handles internal moving of tasks."""
        # Find the indexes of the tasks being moved
        source_indexes = [i for i, node in enumerate(self.tasks) if node.value in task_values]

        # Remove tasks from their original positions
        nodes_to_move = []
        for idx in sorted(source_indexes, reverse=True):
            node = self.tasks.pop(idx)
            self.root_node.children.pop(idx)
            nodes_to_move.insert(0, node)  # Maintain original order

        # Adjust insert position if needed
        if insert_position > max(source_indexes):
            insert_position -= len(nodes_to_move)

        # Insert tasks at the new position
        for i, node in enumerate(nodes_to_move):
            self.tasks.insert(insert_position + i, node)
            self.root_node.children.insert(insert_position + i, node)

        self.layoutChanged.emit()

    def _insert_tasks(self, task_values, insert_position):
        """Handles inserting new tasks from an external source."""
        dropped_tasks = []
        for value in task_values:
            if value in self.task_values:
                continue  # Skip duplicates
            task_data = self.get_task_data_by_value(value)
            if task_data:
                node = Node(task_data)
                dropped_tasks.append(node)

        if not dropped_tasks:
            return False

        # Insert tasks at the determined position
        self.beginInsertColumns(QtCore.QModelIndex(), insert_position, insert_position + len(dropped_tasks) - 1)
        for i, node in enumerate(dropped_tasks):
            node.parent = self.root_node
            self.root_node.children.insert(insert_position + i, node)
            self.tasks.insert(insert_position + i, node)
            self.task_values.add(node.value)
        self.endInsertColumns()

        return True


class TemplateModel(QtCore.QAbstractItemModel):
    """Model representing available task templates as rows, supporting drag and drop."""

    task_added = QtCore.Signal(str)  # Signal emitted when a task is added back
    task_removed = QtCore.Signal(str)  # Signal emitted when a task is removed

    def __init__(self, exclude_task_values=None, parent=None):
        super(TemplateModel, self).__init__(parent)
        self.root_node = Node({'name': 'Root'})
        self.templates = []  # List to hold template nodes representing rows
        self.task_values = set()
        self.exclude_task_values = exclude_task_values or set()

    @QtCore.Slot()
    def init_data(self):
        """Initializes the model's data with available task templates."""
        self.beginResetModel()
        self.templates = []
        self.root_node.children = []
        self.task_values.clear()
        for task_id, task_data in default_task_config.items():
            if task_data['value'] in self.exclude_task_values:
                continue  # Skip tasks that are in the exclude list
            node = Node(task_data, parent=self.root_node)
            self.root_node.add_child(node)
            self.templates.append(node)
            self.task_values.add(node.value)
        self.endResetModel()

    @QtCore.Slot(dict)
    def add_task(self, task_data):
        """Adds a task to the model."""
        if task_data['value'] in self.task_values:
            return

        # Ensure that the task is not in `exclude_task_values`
        if task_data['value'] in self.exclude_task_values:
            self.exclude_task_values.remove(task_data['value'])

        node = Node(task_data, parent=self.root_node)
        self.beginInsertRows(QtCore.QModelIndex(), len(self.templates), len(self.templates))
        self.templates.append(node)
        self.root_node.add_child(node)
        self.task_values.add(node.value)
        self.endInsertRows()
        self.task_added.emit(task_data['value'])

    @QtCore.Slot(str)
    def remove_task(self, task_value):
        """Removes a task from the model."""
        for i, node in enumerate(self.templates):
            if node.value == task_value:
                self.beginRemoveRows(QtCore.QModelIndex(), i, i)
                del self.templates[i]
                self.root_node.children.pop(i)
                self.task_values.remove(task_value)
                self.endRemoveRows()
                self.task_removed.emit(task_value)
                break

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0  # No children for items in this model
        return len(self.templates)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1  # Single column for task templates

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if self.hasIndex(row, column, parent):
            if not parent.isValid():
                node = self.templates[row]
                return self.createIndex(row, column, node)
        return QtCore.QModelIndex()

    def parent(self, index):
        return QtCore.QModelIndex()  # Flat structure; parent is invalid

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return node.name
        elif role == QtCore.Qt.DecorationRole:
            return ui.get_icon(node.icon, color=node.color, size=common.Size.Margin())
        elif role == QtCore.Qt.ToolTipRole:
            return node.description
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """Provides header data for the model."""
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return "Templates"
        return super(TemplateModel, self).headerData(section, orientation, role)

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
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def supportedDragActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def mimeTypes(self):
        return ['application/x-task']

    def mimeData(self, indexes):
        mime_data = QtCore.QMimeData()
        encoded_data = QtCore.QByteArray()
        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.WriteOnly)
        for index in indexes:
            if index.isValid():
                node = index.internalPointer()
                stream.writeQString(node.value)
        mime_data.setData('application/x-task', encoded_data)
        mime_data.setProperty('source_model', self)
        return mime_data

    def dropMimeData(self, data, action, row, column, parent):
        if not data.hasFormat('application/x-task'):
            return False
        # Read the dropped task values
        encoded_data = data.data('application/x-task')
        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)
        dropped_values = []
        while not stream.atEnd():
            value = stream.readQString()
            dropped_values.append(value)

        if not dropped_values:
            return False

        source_model = data.property('source_model')
        if source_model == self:
            # Internal move (unlikely for a QTreeView, but handle just in case)
            return False  # Or implement internal move logic if needed

        # Insert tasks at the end
        for value in dropped_values:
            task_data = next((v for v in default_task_config.values() if v['value'] == value), None)

            if not task_data:
                raise RuntimeError(f'Could not find task data for value: {value}')

            if task_data and value not in self.task_values:
                self.add_task(task_data)
                # Notify the source model to remove the task
                self.task_added.emit(value)
        return True
