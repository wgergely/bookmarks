import logging

from PySide2 import QtCore, QtWidgets

from .lib import clear_records, get_logging_level, set_logging_level, save_tank_to_file
from .model import LogFilterProxyModel, LogModel
from .. import common
from .. import ui


def show():
    from .. import common
    if common.log_widget is not None:
        close()

    common.log_widget = LogWidget()
    common.log_widget.show()


def close():
    from .. import common

    if common.log_widget is None:
        return

    try:
        common.log_widget.close()
        common.log_widget.deleteLater()
        common.log_widget = None
    except Exception:
        pass


class LogView(QtWidgets.QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_ui()
        self.init_model()

    def init_model(self):
        proxy = LogFilterProxyModel(parent=self)
        model = LogModel(parent=self)
        proxy.setSourceModel(model)
        self.setModel(proxy)

        for column in range(proxy.columnCount()):
            if column == proxy.columnCount() - 1:
                self.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
            else:
                self.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Interactive)

        self._connect_signals()

    def _create_ui(self):
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setSortingEnabled(False)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.horizontalHeader().setSortIndicatorShown(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def _connect_signals(self):
        self.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.customContextMenuRequested.connect(self.on_custom_context_menu)

    @QtCore.Slot(QtCore.QPoint)
    def on_custom_context_menu(self, pos):
        # Create the context menu
        menu = QtWidgets.QMenu(self)

        indexes = self.selectionModel().selectedRows()
        if indexes:
            copy_action = menu.addAction("Copy")
            copy_action.triggered.connect(self.copy_selected_row)

        menu.exec_(self.viewport().mapToGlobal(pos))

    @QtCore.Slot()
    def copy_selected_row(self):
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        # Retrieve all display data from the row
        # Assuming columns: Time(0), Level(1), Name(2), Thread(3), Message(4)
        line_parts = []
        for col in range(self.model().columnCount()):
            val = self.model().index(row, col).data(QtCore.Qt.DisplayRole)
            line_parts.append(val if val else "")

        # Reconstruct a formatted line similar to the output format
        # "Time [Level] [Name] [thread.ThreadID] >> Message"
        # line_parts = [time_str, level_str, name_part, thread_part, msg]
        # We'll mimic the original format:
        # time [level] [name] [thread.XYZ] >> message
        if len(line_parts) == 5:
            time_str, level_str, name_part, thread_part, msg = line_parts
            formatted_line = f"{time_str} [{level_str}] [{name_part}] [thread.{thread_part}] >> {msg}"
        else:
            # Fallback if columns don't match expected format
            formatted_line = " ".join(line_parts)

        # Copy to clipboard
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(formatted_line)

    @QtCore.Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def on_selection_changed(self, selected, deselected):
        if not self.model():
            return

        # Restore deselected rows
        for idx in deselected.indexes():
            self.setRowHeight(idx.row(), self.verticalHeader().defaultSectionSize())

        # Adjust newly selected rows if multiline
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        message_index = self.model().index(row, 4)
        msg = message_index.data(QtCore.Qt.DisplayRole)

        if msg and '\n' in msg:
            self.resizeRowToContents(row)
        else:
            self.setRowHeight(row, self.verticalHeader().defaultSectionSize())


class LogWidget(QtWidgets.QDialog):
    """
    Main widget containing a toolbar, and the LogView below.
    Handles timers for automatic updates, filtering, and refresh/clear actions.
    """

    def __init__(self, parent=None):
        super().__init__(
            parent=parent,
            f=(
                    QtCore.Qt.CustomizeWindowHint |
                    QtCore.Qt.WindowTitleHint |
                    QtCore.Qt.WindowSystemMenuHint |
                    QtCore.Qt.WindowMinMaxButtonsHint |
                    QtCore.Qt.WindowCloseButtonHint
            )
        )

        self.log_view = None
        self.toolbar = None
        self._paused = False

        self.setWindowTitle('Log Viewer')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self._create_ui()
        self._connect_signals()

        if not self.parent():
            common.set_stylesheet(self)

        # Initialize the level combo with current global log level
        current_level = get_logging_level()
        self._select_current_level_in_combo(current_level)

        # Once model is set on log_view, connect to its signals
        self._connect_model_signals()

    def _create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        self.log_view = LogView(self)
        self.toolbar = QtWidgets.QToolBar(self)
        self.toolbar.setIconSize(QtCore.QSize(
            common.Size.Margin(1.0),
            common.Size.Margin(1.0)
        ))

        # Level filter
        self.level_combo = QtWidgets.QComboBox(self)
        self.level_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

        _icon_info = QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation)
        _icon_warning = QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
        _icon_error = QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)

        level_options = [
            ("DEBUG", logging.DEBUG, _icon_info),
            ("INFO", logging.INFO, _icon_info),
            ("WARNING", logging.WARNING, _icon_warning),
            ("ERROR", logging.ERROR, _icon_error),
            ("CRITICAL", logging.CRITICAL, _icon_error),
        ]

        for name, val, icon in level_options:
            self.level_combo.addItem(name, val)
            idx = self.level_combo.findText(name)
            if idx >= 0:
                self.level_combo.setItemIcon(idx, icon)

        self.toolbar.addWidget(self.level_combo)
        self.toolbar.addSeparator()

        # Name filter
        self.name_combo = QtWidgets.QComboBox(self)
        self.name_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.name_combo.addItem("All")
        self.toolbar.addWidget(QtWidgets.QLabel("Name:", self))
        self.toolbar.addWidget(self.name_combo)

        # Thread filter
        self.thread_combo = QtWidgets.QComboBox(self)
        self.thread_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.thread_combo.addItem("All")
        self.toolbar.addWidget(QtWidgets.QLabel("Thread:", self))
        self.toolbar.addWidget(self.thread_combo)

        # Text filter
        self.text_filter_edit = QtWidgets.QLineEdit(self)
        self.text_filter_edit.setPlaceholderText("Search text in message...")
        self.toolbar.addWidget(self.text_filter_edit)

        self.toolbar.addSeparator()

        # Refresh button
        icon = ui.get_icon('refresh')
        self.refresh_act = QtWidgets.QAction(icon, "Refresh", self)
        self.toolbar.addAction(self.refresh_act)

        # Clear button
        icon = ui.get_icon('close')
        self.clear_act = QtWidgets.QAction(icon, "Clear", self)
        self.toolbar.addAction(self.clear_act)

        # Pause button
        self.pause_action = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause), "Pause", self)
        self.pause_action.setCheckable(True)
        self.toolbar.addAction(self.pause_action)

        self.toolbar.addSeparator()

        # Save dropdown
        self.save_button = QtWidgets.QToolButton(self)
        self.save_button.setText("Save")
        self.save_button.setIcon(ui.get_icon('file'))
        self.save_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        save_menu = QtWidgets.QMenu(self.save_button)
        self.save_json_act = QtWidgets.QAction("Save as JSON...", self)
        self.save_text_act = QtWidgets.QAction("Save as Text...", self)
        save_menu.addAction(self.save_json_act)
        save_menu.addAction(self.save_text_act)
        self.save_button.setMenu(save_menu)

        self.toolbar.addWidget(self.save_button)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.log_view)
        self.setLayout(layout)

    def _connect_signals(self):
        self.level_combo.currentIndexChanged.connect(self.on_level_filter_changed)
        self.name_combo.currentTextChanged.connect(self.on_name_filter_changed)
        self.thread_combo.currentTextChanged.connect(self.on_thread_filter_changed)
        self.text_filter_edit.textChanged.connect(self.model().set_message_filter)
        self.refresh_act.triggered.connect(self.refresh)
        self.clear_act.triggered.connect(self.on_clear_clicked)
        self.pause_action.toggled.connect(self.on_pause_toggled)

        # Connect save actions
        self.save_json_act.triggered.connect(self._on_save_json)
        self.save_text_act.triggered.connect(self._on_save_text)

    def _connect_model_signals(self):
        sm = self.sourceModel()
        if sm is not None:
            sm.namesUpdated.connect(self.on_names_updated)
            sm.threadsUpdated.connect(self.on_threads_updated)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(1.5),
            common.Size.DefaultHeight()
        )

    def model(self):
        return self.log_view.model()

    def sourceModel(self):
        if self.model() is not None:
            return self.model().sourceModel()
        return None

    @QtCore.Slot(tuple)
    def on_names_updated(self, names):
        self._update_combo_from_values(self.name_combo, names)

    @QtCore.Slot(tuple)
    def on_threads_updated(self, threads):
        self._update_combo_from_values(self.thread_combo, threads)

    def _update_combo_from_values(self, combo, values):
        combo.blockSignals(True)
        current_text = combo.currentText()
        combo.clear()
        combo.addItem("All")
        for val in values:
            combo.addItem(val)
        idx = combo.findText(current_text)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def _select_current_level_in_combo(self, level_value):
        idx = self.level_combo.findData(level_value)
        if idx >= 0:
            self.level_combo.setCurrentIndex(idx)

    @common.debug
    @common.error
    @QtCore.Slot(str)
    def on_name_filter_changed(self, text):
        self.model().set_name_filter("" if text == "All" else text)

    @common.debug
    @common.error
    @QtCore.Slot(str)
    def on_thread_filter_changed(self, text):
        self.model().set_thread_filter("" if text == "All" else text)

    @common.debug
    @common.error
    @QtCore.Slot()
    def refresh(self):
        sm = self.sourceModel()
        if hasattr(sm, 'refresh'):
            sm.refresh()
        self.model().invalidate()

    @common.debug
    @common.error
    @QtCore.Slot()
    def on_clear_clicked(self):
        clear_records()
        sm = self.sourceModel()
        if hasattr(sm, 'refresh'):
            sm.refresh()
        self.model().invalidate()

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def on_level_filter_changed(self, index):
        level_value = self.level_combo.itemData(index)
        if level_value is not None:
            set_logging_level(level_value)
            self.model().set_min_level(level_value)
            self.refresh()

    @common.debug
    @common.error
    @QtCore.Slot(bool)
    def on_pause_toggled(self, paused):
        self._paused = paused
        sm = self.sourceModel()
        if sm is None:
            return

        if hasattr(sm, '_disconnect_signals') and hasattr(sm, '_connect_signals'):
            if paused:
                sm._disconnect_signals()
                self.pause_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
                self.pause_action.setText("Resume")
            else:
                sm._connect_signals()
                self.pause_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
                self.pause_action.setText("Pause")

    @QtCore.Slot()
    def _on_save_json(self):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save as JSON", "",
                                                            "JSON Files (*.json);;All Files (*)")
        if filepath:
            save_tank_to_file(filepath)

    @QtCore.Slot()
    def _on_save_text(self):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save as Text", "",
                                                            "Log Files (*.log);;All Files (*)")
        if filepath:
            save_tank_to_file(filepath)
