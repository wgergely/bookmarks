import math

from PySide2 import QtWidgets, QtCore, QtGui

from .model import ActiveTasksModel, TaskSourceModel, FilterTaskModel
from ... import ui, common


class BaseView(QtWidgets.QTableView):
    """View for displaying selected tasks, supports dropping and column rearrangement."""

    def __init__(self, server, job, root, parent=None):
        super().__init__(parent=parent)

        self.server = server
        self.job = job
        self.root = root

        self.drag_source_idx = None
        self.drag_indicator_rect = None

        # Enable accepting drops and internal drag-and-drop for rearrangement
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(False)

        # Selection and display settings
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setShowGrid(False)
        self.verticalHeader().hide()

        # Hide headers
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        if self.mode() == 'row':
            self.verticalHeader().setVisible(True)
        else:
            self.horizontalHeader().setVisible(True)


        self.setMinimumHeight(common.Size.RowHeight(1.5))

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )

        self.horizontalScrollBar().setSingleStep(common.Size.DefaultWidth(0.1))

        self._init_model()
        self._connect_signals()

    def wheelEvent(self, event):
        if self.mode() == 'column':
            QtCore.QCoreApplication.sendEvent(self.horizontalScrollBar(), event)
        else:
            super().wheelEvent(event)

    def startDrag(self, supported_actions):
        self.reset_drag()

        index = self.currentIndex()
        if not index.isValid():
            return

        # Set the drag source
        self.drag_source_idx = self._idx_from_index(index)

        # Create get mime and set source
        source_index = self.model().mapToSource(index)
        mime = self.model().sourceModel().mimeData([source_index, ])
        mime.setProperty('source_idx', self.drag_source_idx)

        # Start drag
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(supported_actions)

    def dragMoveEvent(self, event):
        mime = event.mimeData()
        if not mime.hasFormat('application/x-task'):
            event.ignore()
            return

        pos = event.pos()

        # Ignore self
        index = self.indexAt(event.pos())
        internal_move = mime.property('source_model') == self.model().sourceModel()
        if (
                internal_move and
                mime.property('source_idx') == self._idx_from_index(index)
        ):
            self.reset_drag()
            event.ignore()
            return

        # If the model is empty accept the event and set indicator
        if self.mode() == 'column':
            count = self.model().columnCount()
        elif self.mode() == 'row':
            count = self.model().rowCount()
        else:
            count = 0

        if count == 0:
            mime.setProperty('destination_idx', 0)
            mime.setProperty('position', 'before')
            rect = self.rect()
            rect.setWidth(common.Size.Indicator())
            self.drag_indicator_rect = rect
            self.viewport().update()
            event.acceptProposedAction()
            return

        # If the index isn't valid, find the closest index
        if not index.isValid():
            lengths = []
            _sibling = QtCore.QModelIndex()

            if self.mode() == 'column':
                for i in range(self.model().columnCount()):
                    rect = self.visualRect(self.model().index(0, i))
                    _pos = rect.center()
                    distance = math.sqrt((pos.x() - _pos.x()) ** 2 + (pos.y() - _pos.y()) ** 2)
                    lengths.append((i, distance))
                m = min(lengths, key=lambda x: x[1])[0] if lengths else 0
                _sibling = self.model().index(0, m)
            elif self.mode() == 'row':
                for i in range(self.model().rowCount()):
                    rect = self.visualRect(self.model().index(i, 0))
                    _pos = rect.center()
                    distance = math.sqrt((pos.x() - _pos.x()) ** 2 + (pos.y() - _pos.y()) ** 2)
                    lengths.append((i, distance))
                m = min(lengths, key=lambda x: x[1])[0] if lengths else 0
                _sibling = self.model().index(m, 0)

            threshold = common.Size.DefaultHeight(0.33)
            min_length = min(lengths, key=lambda x: x[1])[1] if lengths else threshold

            # The drag is too far away
            if min_length >= threshold:
                event.ignore()
                self.reset_drag()
                return

            if _sibling.isValid():
                index = _sibling

        if not index.isValid():
            index = self.model().index(0, 0)

        visual_rect = self.visualRect(index)

        if self.mode() == 'column':
            mid = visual_rect.left() + visual_rect.width() / 2
            if pos.x() <= mid:
                mime.setProperty('position', 'before')
            else:
                mime.setProperty('position', 'after')
        elif self.mode() == 'row':
            mid = visual_rect.top() + visual_rect.height() / 2
            if pos.y() < mid:
                mime.setProperty('position', 'before')
            else:
                mime.setProperty('position', 'after')

        current_idx = self._idx_from_index(index)

        # Set indicator position
        rect = self.visualRect(index)
        if mime.property('position') == 'before':
            if self.mode() == 'column':
                rect.setWidth(common.Size.Indicator())
                rect.moveRight(rect.right() - common.Size.Indicator(0.5))
            elif self.mode() == 'row':
                rect.setHeight(common.Size.Indicator())
                rect.moveBottom(rect.bottom() - common.Size.Indicator(0.5))
        elif mime.property('position') == 'after':
            if self.mode() == 'column':
                rect.moveLeft(rect.right() - common.Size.Indicator())
                rect.setWidth(common.Size.Indicator())
                rect.moveRight(rect.right() + common.Size.Indicator(0.5))
            elif self.mode() == 'row':
                rect.moveTop(rect.bottom() - common.Size.Indicator())
                rect.setHeight(common.Size.Indicator())
                rect.moveBottom(rect.bottom() + common.Size.Indicator(0.5))

        self.drag_indicator_rect = QtCore.QRect(rect)

        # Ignore self-drops
        if internal_move and current_idx == mime.property('source_idx'):
            event.ignore()
            return

        # Update mime and view
        mime.setProperty('destination_idx', current_idx)

        self.viewport().update()

        event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        if not mime.hasFormat('application/x-task'):
            event.ignore()
            return

        # Extract properties
        destination_idx = mime.property('destination_idx')
        position = mime.property('position')

        # Determine the final insertion index based on position
        if self.mode() == 'column':
            if position == 'after':
                destination_idx = min(destination_idx + 1, self.model().sourceModel().columnCount())
        elif self.mode() == 'row':
            if position == 'after':
                destination_idx = min(destination_idx + 1, self.model().sourceModel().rowCount())

        # Call the model's dropMimeData
        success = self.model().sourceModel().dropMimeData(
            mime,
            event.dropAction(),
            destination_idx if self.mode() == 'row' else -1,
            destination_idx if self.mode() == 'column' else -1,
            QtCore.QModelIndex()
        )

        if success:
            event.acceptProposedAction()
        else:
            event.ignore()

        self.reset_drag()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-task'):
            event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()
        else:
            self.reset_drag()
            event.ignore()

    def dragLeaveEvent(self, event):
        self.reset_drag()
        super().dragLeaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.drag_indicator_rect is None:
            return

        painter = QtGui.QPainter(self.viewport())

        painter.setPen(QtCore.Qt.NoPen)
        painter.fillRect(self.drag_indicator_rect, common.Color.Green())

        painter.end()

    def _idx_from_index(self, index):
        if not index.isValid():
            return 0
        source_index = self.model().mapToSource(index)

        if self.mode() == 'column':
            return source_index.column()
        elif self.mode() == 'row':
            return source_index.row()

    @QtCore.Slot()
    def reset_drag(self):
        self.drag_source_idx = None
        self.drag_indicator_rect = None
        self.model().invalidate()
        self.viewport().update()

    @classmethod
    def mode(cls):
        return 'column'

    @QtCore.Slot(str)
    def select_task(self, task_value):
        """Selects a task by its value.

        Args:
            task_value (str): The value of the task to select.

        """
        index = self.model().sourceModel().index_by_value(task_value)
        if not index.isValid():
            return
        self.selectionModel().select(index, QtCore.QItemSelectionModel.ClearAndSelect)

    def _init_model(self):
        pass

    def _connect_signals(self):
        self.model().modelReset.connect(
            lambda: self.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents))
        self.model().layoutChanged.connect(
            lambda: self.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents))

        self.model().sourceModel().taskChanged.connect(self.select_task)
        self.model().sourceModel().taskChanged.connect(self.reset_drag)
        self.model().sourceModel().taskChanged.connect(self.model().invalidate)


class ActiveTasksView(BaseView):

    def __init__(self, server, job, root, parent=None):
        super().__init__(server, job, root, parent=parent)

    def mode(self):
        return 'column'

    def _init_model(self):
        model = FilterTaskModel(parent=self)
        model.setSourceModel(ActiveTasksModel(self.server, self.job, self.root, mode=self.mode(), parent=self))
        self.setModel(model)

        self.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)


class SourceTasksView(BaseView):
    """View for displaying task templates, supports dragging and dropping."""

    def mode(self):
        return 'row'

    def _connect_signals(self):
        super()._connect_signals()

        self.model().modelReset.connect(self.set_fixed_width)
        self.model().layoutChanged.connect(self.set_fixed_width)
        self.model().sourceModel().taskChanged.connect(self.set_fixed_width)

    @QtCore.Slot()
    def set_fixed_width(self):
        header_width = self.horizontalHeader().length()
        self.setFixedWidth(header_width + common.Size.Margin())

    def _init_model(self):
        model = FilterTaskModel(enabled=False, parent=self)
        model.setSourceModel(TaskSourceModel(self.server, self.job, self.root, mode=self.mode(), parent=self))
        self.setModel(model)

        self.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)


class TaskEditorDialog(QtWidgets.QDialog):
    """Dialog for editing tasks, containing SourceTasksView and ActiveTasksView."""

    def __init__(self, server, job, root, parent=None):
        super().__init__(parent=parent)

        if not parent:
            common.set_stylesheet(self)

        self.server = server
        self.job = job
        self.root = root

        self.setWindowTitle('Task Editor')

        self.source_tasks_view = None
        self.active_tasks_view = None

        self.save_button = None
        self.cancel_button = None

        self._create_ui()
        self._connect_signals()

        QtCore.QTimer.singleShot(50, self.active_tasks_view.model().sourceModel().init_data)
        QtCore.QTimer.singleShot(50, self.source_tasks_view.model().sourceModel().init_data)

    def _create_ui(self):
        """Creates and sets up the UI components."""
        layout = QtWidgets.QVBoxLayout(self)

        o = common.Size.Indicator()
        layout.setContentsMargins(o, o, o, o)
        layout.setSpacing(o)

        # Create the views
        self.source_tasks_view = SourceTasksView(self.server, self.job, self.root, parent=self)
        self.active_tasks_view = ActiveTasksView(self.server, self.job, self.root, parent=self)

        # Create the splitter
        splitter = QtWidgets.QSplitter(parent=self)
        splitter.setOrientation(QtCore.Qt.Horizontal)
        splitter.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding
        )
        splitter.addWidget(self.source_tasks_view)
        splitter.addWidget(self.active_tasks_view)

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
    def _connect_signals(self):
        """Connects signals between models and views."""

        # Connect buttons
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
