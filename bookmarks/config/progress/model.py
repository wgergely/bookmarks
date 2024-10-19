from PySide2 import QtCore, QtGui

from .node import Node
from ..default_configs import default_task_config
from ..lib import Section, Config
from ... import ui, common


class TaskModel(QtCore.QAbstractItemModel):
    """Model representing tasks in columns with a single row, supporting drag and drop.

    Attributes:
        root_node (Node): The root node of the model.
        tasks (list of Node): List of task nodes representing the columns.
        config (Config): The configuration interface for database operations.
    """

    def __init__(self, server, job, root, parent=None):
        super().__init__(parent)
        self.root_node = Node({'name': 'Root'})
        self.tasks = []  # List to hold task nodes representing columns
        self.config = Config(server=server, job=job, root=root)

    def init_data(self):
        """Initializes the model's data by fetching tasks from the database."""
        # Fetch task configuration data from the database
        tasks_data = self.config.data(Section.TaskConfig)

        # Ensure tasks_data is a dictionary
        if not isinstance(tasks_data, dict):
            tasks_data = {}

        self.beginResetModel()
        self.tasks = []
        self.root_node.children = []

        for task_id, task_data in tasks_data.items():
            node = Node(task_data, parent=self.root_node)
            self.root_node.add_child(node)
            self.tasks.append(node)

        self.endResetModel()

    def get_task_data_by_value(self, value):
        """Retrieves task data by its value.

        Args:
            value (str): The value identifier of the task.

        Returns:
            dict: The task data dictionary if found, else None.
        """
        tasks_data = self.config.data(Section.TaskConfig)
        for task in tasks_data.values():
            if task['value'] == value:
                return task
        return None

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 1  # Single row representing selected tasks

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
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return node.name
        elif role == QtCore.Qt.DecorationRole:
            icon_path = node.icon  # Assuming icon paths are stored in node.icon
            return QtGui.QIcon(icon_path)
        elif role == QtCore.Qt.ToolTipRole:
            return node.description
        elif role == QtCore.Qt.BackgroundRole:
            return QtGui.QBrush(node.color)
        elif role == QtCore.Qt.UserRole:
            return node.get_status()
        return None

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
            return QtCore.Qt.ItemIsEnabled
        return (
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEditable |
                QtCore.Qt.ItemIsDragEnabled |
                QtCore.Qt.ItemIsDropEnabled
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
        return mime_data

    def dropMimeData(self, mime_data, action, row, column, parent):
        if action == QtCore.Qt.IgnoreAction:
            return False
        if not mime_data.hasFormat('application/x-task'):
            return False
        encoded_data = mime_data.data('application/x-task')
        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)
        new_tasks = []
        while not stream.atEnd():
            value = stream.readQString()
            task_data = self.get_task_data_by_value(value)
            if task_data:
                node = Node(task_data, parent=self.root_node)
                new_tasks.append(node)
        if new_tasks:
            self.beginResetModel()
            for node in new_tasks:
                self.root_node.add_child(node)
                self.tasks.append(node)
            self.endResetModel()
            return True
        return False

    def removeColumns(self, position, columns, parent=QtCore.QModelIndex()):
        if position < 0 or columns <= 0 or position + columns > len(self.tasks):
            return False
        self.beginRemoveColumns(parent, position, position + columns - 1)
        for _ in range(columns):
            self.root_node.remove_child(position)
            del self.tasks[position]
        self.endRemoveColumns()
        return True


class TemplateModel(QtCore.QAbstractItemModel):
    """Model representing available task templates as rows, supporting drag and drop.

    Attributes:
        root_node (Node): The root node of the model.
        templates (list of Node): List of template nodes representing the rows.
    """

    def __init__(self, parent=None):
        super(TemplateModel, self).__init__(parent)
        self.root_node = Node({'name': 'Root'})
        self.templates = []  # List to hold template nodes representing rows
        self.init_data()

    def init_data(self):
        """Initializes the model's data with available task templates."""
        # Load task templates from default_task_config
        self.beginResetModel()
        self.templates = []
        self.root_node.children = []
        for task_id, task_data in default_task_config.items():
            node = Node(task_data, parent=self.root_node)
            self.root_node.add_child(node)
            self.templates.append(node)
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex(), **kwargs):
        if parent.isValid():
            return 0  # No children for items in this model
        return len(self.templates)

    def columnCount(self, parent=QtCore.QModelIndex(), **kwargs):
        return 1  # Single column for task templates

    def index(self, row, column, parent=QtCore.QModelIndex(), **kwargs):
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
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return node.name
        elif role == QtCore.Qt.DecorationRole:
            return ui.get_icon(node.icon, color=node.color, size=common.Size.Margin())
        elif role == QtCore.Qt.ToolTipRole:
            return node.description
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """Provides header data for the model.

        Args:
            section (int): Section number.
            orientation (Qt.Orientation): Horizontal or vertical.
            role (int): The role for the header data.

        Returns:
            QVariant: The header data.
        """
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return "Templates"
        return super(TemplateModel, self).headerData(section, orientation, role)

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled
        return (
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsDragEnabled
        )

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
            else:
                stream.writeQString('')
        mime_data.setData('application/x-task', encoded_data)
        return mime_data
