import logging

from PySide2 import QtCore, QtWidgets

from .lib import clear_records, get_logging_level, set_logging_level
from .model import LogFilterProxyModel, LogModel
from .. import common


class LogView(QtWidgets.QTableView):
    """
    A QTableView subclass for displaying log data.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_ui()
        self._connect_signals()

        self.init_model()

    def init_model(self):
        """
        Set the model (proxy model) for this view.
        """
        proxy = LogFilterProxyModel(parent=self)
        model = LogModel(parent=self)

        proxy.setSourceModel(model)
        self.setModel(proxy)

        for column in range(proxy.columnCount()):
            if column == proxy.columnCount() - 1:
                self.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
            else:
                self.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)

    def _create_ui(self):
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.horizontalHeader().setSortIndicatorShown(True)

        self.setWordWrap(True)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def _connect_signals(self):
        # Connect signals if needed, for example sorting changed
        pass


class LogWidget(QtWidgets.QWidget):
    """
    Main widget containing a toolbar, and the LogView below.
    Handles timers for automatic updates, filtering, and refresh/clear actions.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.log_view = None
        self.toolbar = None
        self._paused = False  # Track whether updates are paused

        self.setWindowTitle("Log Viewer")

        self._create_ui()
        self._connect_signals()

        if not self.parent():
            common.set_stylesheet(self)

        # Initialize the level combo with current global log level
        current_level = get_logging_level()
        self._select_current_level_in_combo(current_level)

    def _create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        self.log_view = LogView(self)
        self.toolbar = QtWidgets.QToolBar(self)

        # Level filter (QComboBox)
        self.level_combo = QtWidgets.QComboBox(self)
        self.level_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        # Populate only from DEBUG upwards (no NOTSET)
        level_options = [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ]
        for name, val in level_options:
            self.level_combo.addItem(name, val)

        self.toolbar.addWidget(QtWidgets.QLabel("Level:", self))
        self.toolbar.addWidget(self.level_combo)

        # Name filter (QComboBox)
        self.name_combo = QtWidgets.QComboBox(self)
        self.name_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.name_combo.addItem("All")
        self.toolbar.addWidget(QtWidgets.QLabel("Name:", self))
        self.toolbar.addWidget(self.name_combo)

        # Thread filter (QComboBox)
        self.thread_combo = QtWidgets.QComboBox(self)
        self.thread_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.thread_combo.addItem("All")
        self.toolbar.addWidget(QtWidgets.QLabel("Thread:", self))
        self.toolbar.addWidget(self.thread_combo)

        # Text filter (QLineEdit)
        self.text_filter_edit = QtWidgets.QLineEdit(self)
        self.text_filter_edit.setPlaceholderText("Search text in message...")
        self.toolbar.addWidget(self.text_filter_edit)

        # Refresh button
        refresh_act = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload), "Refresh", self)
        self.toolbar.addAction(refresh_act)

        # Clear button (use a clearer icon)
        clear_act = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_LineEditClearButton), "Clear", self)
        self.toolbar.addAction(clear_act)

        # Pause button (toggle)
        self.pause_action = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause), "Pause", self)
        self.pause_action.setCheckable(True)
        self.toolbar.addAction(self.pause_action)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.log_view)
        self.setLayout(layout)

        # Store actions to connect signals later
        self.refresh_act = refresh_act
        self.clear_act = clear_act

    def _connect_signals(self):
        self.level_combo.currentIndexChanged.connect(self.on_level_filter_changed)
        self.name_combo.currentTextChanged.connect(self.on_name_filter_changed)
        self.thread_combo.currentTextChanged.connect(self.on_thread_filter_changed)
        self.text_filter_edit.textChanged.connect(self.model().set_message_filter)
        self.refresh_act.triggered.connect(self.refresh)
        self.clear_act.triggered.connect(self.on_clear_clicked)
        self.pause_action.toggled.connect(self.on_pause_toggled)

        common.signals.logRecordAdded.connect(self.populate_filter_combos)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(1.5),
            common.Size.DefaultHeight()
        )

    def model(self):
        """
        Convenience method to access the proxy model.
        """
        return self.log_view.model()

    def sourceModel(self):
        """
        Convenience method to access the source model.
        """
        return self.log_view.model().sourceModel()

    def _select_current_level_in_combo(self, level_value):
        # Find index for given level_value
        idx = self.level_combo.findData(level_value)
        if idx >= 0:
            self.level_combo.setCurrentIndex(idx)

    @QtCore.Slot()
    def populate_filter_combos(self):
        """
        Populate the name/thread combos based on the data in the source model.
        """
        names = set()
        threads = set()

        sm = self.sourceModel()
        if sm is None:
            return

        for row in range(sm.rowCount()):
            name = sm.index(row, 2).data(QtCore.Qt.UserRole)
            thread = sm.index(row, 3).data(QtCore.Qt.UserRole)
            if name:
                names.add(name)
            if thread:
                threads.add(thread)

        self.name_combo.blockSignals(True)
        self.thread_combo.blockSignals(True)

        current_name = self.name_combo.currentText()
        current_thread = self.thread_combo.currentText()

        self.name_combo.clear()
        self.name_combo.addItem("All")
        for n in sorted(names):
            self.name_combo.addItem(n)

        self.thread_combo.clear()
        self.thread_combo.addItem("All")
        for t in sorted(threads):
            self.thread_combo.addItem(t)

        # Restore selection if possible
        idx = self.name_combo.findText(current_name)
        if idx >= 0:
            self.name_combo.setCurrentIndex(idx)

        idx = self.thread_combo.findText(current_thread)
        if idx >= 0:
            self.thread_combo.setCurrentIndex(idx)

        self.name_combo.blockSignals(False)
        self.thread_combo.blockSignals(False)

    @common.debug
    @common.error
    @QtCore.Slot(str)
    def on_name_filter_changed(self, text):
        if text == "All":
            self.model().set_name_filter("")
        else:
            self.model().set_name_filter(text)

    @common.debug
    @common.error
    @QtCore.Slot(str)
    def on_thread_filter_changed(self, text):
        if text == "All":
            self.model().set_thread_filter("")
        else:
            self.model().set_thread_filter(text)

    @common.debug
    @common.error
    @QtCore.Slot()
    def refresh(self):
        sm = self.sourceModel()
        if hasattr(sm, 'refresh'):
            sm.refresh()
        self.model().invalidate()
        self.populate_filter_combos()

    @common.debug
    @common.error
    @QtCore.Slot()
    def on_clear_clicked(self):
        clear_records()
        sm = self.sourceModel()
        if hasattr(sm, 'refresh'):
            sm.refresh()
        self.model().invalidate()
        self.populate_filter_combos()

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def on_level_filter_changed(self, index):
        # Update global log level and proxy min level
        level_value = self.level_combo.itemData(index)
        if level_value is not None:
            set_logging_level(level_value)
            self.model().set_min_level(level_value)
            # Refresh to ensure we show/hide logs according to the new level
            self.refresh()

    @common.debug
    @common.error
    @QtCore.Slot(bool)
    def on_pause_toggled(self, paused):
        self._paused = paused
        sm = self.sourceModel()
        if sm is None:
            return

        # If paused, disconnect signals to stop automatic appending of logs
        # If unpaused, reconnect signals
        if hasattr(sm, '_disconnect_signals') and hasattr(sm, '_connect_signals'):
            if paused:
                sm._disconnect_signals()
                # Optionally, change icon to play icon
                self.pause_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
                self.pause_action.setText("Resume")
            else:
                sm._connect_signals()
                # Change icon back to pause icon
                self.pause_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
                self.pause_action.setText("Pause")
