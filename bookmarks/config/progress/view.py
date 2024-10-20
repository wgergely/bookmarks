from PySide2 import QtWidgets, QtCore

from .model import TemplateModel, TaskModel
from ..default_configs import default_task_config
from ... import ui, common


class TemplateView(QtWidgets.QTreeView):
    """View for displaying task templates, supports dragging and dropping."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Enable dragging and dropping
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(False)
        self.setRootIsDecorated(False)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-task'):
            event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-task'):
            event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat('application/x-task'):
            event.setDropAction(QtCore.Qt.MoveAction)
            # Get the drop position
            index = self.indexAt(event.pos())
            if not index.isValid():
                index = QtCore.QModelIndex()
            # Proceed with the drop
            if self.model().dropMimeData(event.mimeData(), QtCore.Qt.MoveAction, index.row(), index.column(), index):
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()


class TaskView(QtWidgets.QTableView):
    """View for displaying selected tasks, supports dropping and column rearrangement."""

    def __init__(self, server, job, root, parent=None):
        super().__init__(parent=parent)

        self.server = server
        self.job = job
        self.root = root

        # Enable accepting drops and internal drag-and-drop for rearrangement
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setDragDropOverwriteMode(False)

        # Selection and display settings
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setShowGrid(False)
        self.verticalHeader().hide()

        # Columns are resizable
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

        # Columns are movable and rearrangeable
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setDragEnabled(True)
        self.horizontalHeader().setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.horizontalHeader().setDefaultDropAction(QtCore.Qt.MoveAction)


class TaskEditorDialog(QtWidgets.QDialog):
    """Dialog for editing tasks, containing TemplateView and TaskView."""

    def __init__(self, server, job, root, parent=None):
        super().__init__(parent=parent)

        if not parent:
            common.set_stylesheet(self)

        self.server = server
        self.job = job
        self.root = root

        self.setWindowTitle('Task Editor')

        self.template_view = None
        self.task_view = None

        self.save_button = None
        self.cancel_button = None

        self._create_ui()

        QtCore.QTimer.singleShot(100, self._init_models)
        QtCore.QTimer.singleShot(150, self._connect_signals)
        QtCore.QTimer.singleShot(200, self._init_data)

    def _create_ui(self):
        """Creates and sets up the UI components."""
        layout = QtWidgets.QVBoxLayout(self)

        o = common.Size.Indicator()
        layout.setContentsMargins(o, o, o, o)
        layout.setSpacing(o)

        # Create the views
        self.template_view = TemplateView(parent=self)
        self.task_view = TaskView(self.server, self.job, self.root, parent=self)

        # Create the splitter
        splitter = QtWidgets.QSplitter(parent=self)
        splitter.setOrientation(QtCore.Qt.Horizontal)
        splitter.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding
        )
        splitter.addWidget(self.template_view)
        splitter.addWidget(self.task_view)

        splitter.setSizes([common.Size.DefaultWidth(0.5), common.Size.DefaultWidth(1.0)])

        layout.addWidget(splitter)

        # Create the button row
        button_layout = QtWidgets.QHBoxLayout()
        self.save_button = ui.PaintedButton('Save', parent=self)
        self.cancel_button = ui.PaintedButton('Cancel', parent=self)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button, 1)
        button_layout.addWidget(self.cancel_button, 0)
        layout.addLayout(button_layout)

    @QtCore.Slot()
    def _init_models(self):
        # Initialize TaskModel first
        task_model = TaskModel(self.server, self.job, self.root, parent=self)
        self.task_view.setModel(task_model)

        # Initialize TemplateModel with exclude_task_values from TaskModel
        exclude_task_values = task_model.task_values.copy()
        template_model = TemplateModel(exclude_task_values=exclude_task_values, parent=self)
        self.template_view.setModel(template_model)

    @QtCore.Slot()
    def _connect_signals(self):
        """Connects signals between models and views."""
        # Synchronize models
        self.task_view.model().task_added.connect(self.template_view.model().remove_task)
        self.task_view.model().task_removed.connect(
            lambda value: self.template_view.model().add_task(
                [v for v in default_task_config.values() if v['value'] == value][0])
        )
        self.template_view.model().task_added.connect(self.task_view.model().remove_task)
        self.template_view.model().task_removed.connect(
            lambda value: self.task_view.model().add_task(
                [v for v in default_task_config.values() if v['value'] == value][0])
        )

        self.task_view.model().task_added.connect(
            lambda: self.task_view.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        )
        self.task_view.model().modelReset.connect(
            lambda: self.task_view.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        )
        self.task_view.model().task_removed.connect(
            lambda: self.task_view.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        )
        self.task_view.horizontalHeader().sectionMoved.connect(
            lambda: self.task_view.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        )
        self.task_view.model().layoutChanged.connect(
            lambda: self.task_view.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        )

        # Connect buttons
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    @QtCore.Slot()
    def _init_data(self):
        # Initialize data in TaskModel first
        self.task_view.model().init_data()
        # Update exclude_task_values in TemplateModel
        self.template_view.model().exclude_task_values = self.task_view.model().task_values.copy()
        # Now initialize data in TemplateModel
        self.template_view.model().init_data()
