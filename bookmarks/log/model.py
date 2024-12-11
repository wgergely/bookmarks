"""
Logging Model Module with signals for updated names and threads.

Fixes to ensure all new records are appended when multiple records arrive quickly.
"""

import logging
import re

from PySide2 import QtCore, QtWidgets

from .lib import get_handler, HandlerType, get_logging_level
from .. import common


class LogModel(QtCore.QAbstractTableModel):
    """
    A table model that displays log records directly from an in-memory log tank.
    Pre-parses logs and maintains sets of unique names and threads.

    Emits:
        namesUpdated(tuple): Emitted when the set of unique names changes.
        threadsUpdated(tuple): Emitted when the set of unique thread IDs changes.
    """

    namesUpdated = QtCore.Signal(tuple)
    threadsUpdated = QtCore.Signal(tuple)

    LOG_LINE_REGEX = re.compile(
        r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) "
        r"\[(?P<level>[A-Za-z]+)\] "
        r"\[(?P<name>.*?)\] "
        r"\[thread\.(?P<thread>\d+)\] >> "
        r"(?P<message>[\s\S]*)$",
        re.MULTILINE | re.DOTALL
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []
        self.headers = ["Time", "Level", "Name", "Thread", "Message"]
        self._names = set()
        self._threads = set()
        self._last_loaded_count = 0  # Tracks how many memory records are currently loaded into the model

        self._icon_info = None
        self._icon_warning = None
        self._icon_error = None

        self._connect_signals()
        self._init_icons()

    def _connect_signals(self):
        common.signals.logRecordAdded.connect(self.append_new_record, QtCore.Qt.QueuedConnection)

    def _disconnect_signals(self):
        common.signals.logRecordAdded.disconnect(self.append_new_record)

    def _init_icons(self):
        self._icon_info = QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation)
        self._icon_warning = QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
        self._icon_error = QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.records)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.headers)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            if 0 <= section < len(self.headers):
                return self.headers[section]
        return None

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        record = self.records[index.row()]
        # record tuple: (levelno, time_str, level_str, name_part, thread_part, msg, numeric_level)
        levelno, time_str, level_str, name_part, thread_part, msg, numeric_level = record

        col = index.column()
        if role == QtCore.Qt.DisplayRole:
            if col == 0:
                return time_str
            elif col == 1:
                return level_str
            elif col == 2:
                return name_part
            elif col == 3:
                return thread_part
            elif col == 4:
                return msg

        elif role == QtCore.Qt.UserRole:
            if col == 0:
                return time_str
            elif col == 1:
                return numeric_level
            elif col == 2:
                return name_part
            elif col == 3:
                return thread_part
            elif col == 4:
                return msg

        elif role == QtCore.Qt.DecorationRole and col == 1:
            if numeric_level >= logging.ERROR:
                return self._icon_error
            elif numeric_level == logging.WARNING:
                return self._icon_warning
            else:
                return self._icon_info

        elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.StatusTipRole, QtCore.Qt.WhatsThisRole):
            return msg

        return None

    @QtCore.Slot()
    def refresh(self):
        """
        Fully refresh the model by re-fetching and re-parsing all records.
        Update the names and threads sets accordingly and emit signals if they changed.
        """
        self.beginResetModel()
        current_level = get_logging_level()

        mem_records = get_handler(HandlerType.Memory).records
        old_names = self._names.copy()
        old_threads = self._threads.copy()

        self._names.clear()
        self._threads.clear()

        # Now mem_records contains tuples (levelno, formatted_msg, raw_msg)
        self.records = [
            self._parse_record(levelno, formatted_msg)
            for (levelno, formatted_msg, raw_msg) in mem_records
            if levelno >= current_level
        ]
        self._last_loaded_count = len(mem_records)

        self.endResetModel()

        # Check if sets have changed
        self._emit_if_changed(old_names, self._names, self.namesUpdated)
        self._emit_if_changed(old_threads, self._threads, self.threadsUpdated)

    @QtCore.Slot()
    def append_new_record(self):
        """
        Called when logRecordAdded is emitted.
        Appends all new log items that have appeared in the memory tank since last load.
        """
        mem_handler = get_handler(HandlerType.Memory)
        mem_records = list(mem_handler.records)
        current_level = get_logging_level()

        if len(mem_records) <= self._last_loaded_count:
            # No new records since last load
            return

        # Extract new records since last load
        new_records = mem_records[self._last_loaded_count:]

        # Filter by log level
        new_filtered = [(levelno, formatted_msg, raw_msg)
                        for (levelno, formatted_msg, raw_msg) in new_records
                        if levelno >= current_level]

        if not new_filtered:
            # No new records that meet the level filter
            self._last_loaded_count = len(mem_records)
            return

        old_names = self._names.copy()
        old_threads = self._threads.copy()

        start_row = len(self.records)
        end_row = start_row + len(new_filtered) - 1

        self.beginInsertRows(QtCore.QModelIndex(), start_row, end_row)
        for (levelno, formatted_msg, raw_msg) in new_filtered:
            parsed = self._parse_record(levelno, formatted_msg)
            self.records.append(parsed)
        self.endInsertRows()

        # Update last_loaded_count after successfully loading new records
        self._last_loaded_count = len(mem_records)

        # Check if sets have changed
        self._emit_if_changed(old_names, self._names, self.namesUpdated)
        self._emit_if_changed(old_threads, self._threads, self.threadsUpdated)

    def _parse_record(self, levelno, formatted_msg):
        """
        Parse the given line (formatted_msg) using the precompiled regex to extract fields.
        Update the names and threads sets.
        Returns a tuple:
        (levelno, time_str, level_str, name_part, thread_part, msg, numeric_level)
        """
        match = self.LOG_LINE_REGEX.match(formatted_msg)
        numeric_level = levelno
        raw_level_name = logging.getLevelName(levelno)

        if match:
            time_str = match.group("time")
            level_str = match.group("level")
            name_part = match.group("name")
            thread_part = match.group("thread")
            msg = match.group("message")

            # Convert level_str to numeric if possible
            numeric_level = logging._nameToLevel.get(level_str.upper(), numeric_level)

            # Attempt to parse time for localization
            dt = QtCore.QDateTime.fromString(time_str, "yyyy-MM-dd HH:mm:ss,zzz")
            if dt.isValid():
                locale = QtCore.QLocale.system()
                time_str = locale.toString(dt, QtCore.QLocale.ShortFormat)

            self._names.add(name_part)
            self._threads.add(thread_part)

            return (levelno, time_str, level_str, name_part, thread_part, msg, numeric_level)
        else:
            # If parsing fails, treat the entire formatted_msg as the message
            self._names.add("Unknown")
            self._threads.add("N/A")
            return (levelno, "N/A", raw_level_name, "Unknown", "N/A", formatted_msg, numeric_level)

    def _emit_if_changed(self, old_set, new_set, signal):
        """
        Emit the given signal with a sorted tuple of new_set if old_set != new_set.
        """
        if old_set != new_set:
            signal.emit(tuple(sorted(new_set)))


class LogFilterProxyModel(QtCore.QSortFilterProxyModel):
    """
    A proxy model for filtering and sorting log records.
    Filters by severity, logger name, thread ID, and message substring.
    Uses pre-parsed data stored under UserRole.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_level = logging.NOTSET
        self.name_filter = ""
        self.thread_filter = ""
        self.message_filter = ""

    def set_min_level(self, level):
        self.min_level = level
        self.invalidateFilter()

    def set_name_filter(self, text):
        self.name_filter = text.lower()
        self.invalidateFilter()

    def set_thread_filter(self, text):
        self.thread_filter = text.strip().lower()
        self.invalidateFilter()

    def set_message_filter(self, text):
        self.message_filter = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if not model:
            return True

        level_value = model.index(source_row, 1, source_parent).data(QtCore.Qt.UserRole)
        name = model.index(source_row, 2, source_parent).data(QtCore.Qt.UserRole)
        thread = model.index(source_row, 3, source_parent).data(QtCore.Qt.UserRole)
        message = model.index(source_row, 4, source_parent).data(QtCore.Qt.UserRole)

        # Check level
        if level_value < self.min_level:
            return False

        # Check name filter
        if self.name_filter and self.name_filter not in name.lower():
            return False

        # Check thread filter
        if self.thread_filter and self.thread_filter not in thread.lower():
            return False

        # Check message filter
        if self.message_filter and self.message_filter not in message.lower():
            return False

        return True

    def lessThan(self, left, right):
        model = self.sourceModel()
        if not model:
            return super().lessThan(left, right)

        left_data = left.data(QtCore.Qt.UserRole)
        right_data = right.data(QtCore.Qt.UserRole)

        col = left.column()

        if col == 0:
            return str(left_data) < str(right_data)
        elif col == 1:
            return left_data < right_data
        else:
            return str(left_data) < str(right_data)
