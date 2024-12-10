import logging

from PySide2 import QtCore, QtWidgets

from .lib import get_handler, HandlerType, get_logging_level
from .. import common


class LogModel(QtCore.QAbstractTableModel):
    """
    A table model that displays log records directly from an in-memory log tank.
    Stores a filtered snapshot of logs in self.records.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []
        self.headers = ["Time", "Level", "Name", "Thread", "Message"]

        self._connect_signals()

    def _connect_signals(self):
        common.signals.logRecordAdded.connect(self.append_new_record)

    def _disconnect_signals(self):
        common.signals.logRecordAdded.disconnect(self.append_new_record)

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

        levelno, line = self.records[index.row()]

        try:
            prefix, msg = line.split(' >> ', 1)
            parts = prefix.split(']')
            time_part = parts[0].strip()  # "2024-12-10 15:21:05,123 [INFO"
            name_part = parts[1].strip().strip('[')
            thread_part = parts[2].strip().strip('[thread.')

            # Extract level from time_part
            time_str, level_str = time_part.split(' [', 1)
            level_str = level_str.strip()
            numeric_level = logging._nameToLevel.get(level_str.upper(), logging.DEBUG)

            dt = QtCore.QDateTime.fromString(time_str, "yyyy-MM-dd HH:mm:ss,zzz")
            if dt.isValid():
                locale = QtCore.QLocale.system()
                time_str_localized = locale.toString(dt, QtCore.QLocale.ShortFormat)
            else:
                time_str_localized = time_str  # fallback if parsing fails

            col = index.column()
            if role == QtCore.Qt.DisplayRole:
                if col == 0:
                    return time_str_localized
                elif col == 1:
                    return level_str
                elif col == 2:
                    return name_part
                elif col == 3:
                    return thread_part
                elif col == 4:
                    return msg

            elif role == QtCore.Qt.UserRole:
                # Return raw data for UserRole
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

            elif role == QtCore.Qt.DecorationRole:
                # Return an icon for the Level column based on numeric_level
                if col == 1:
                    style = QtWidgets.QApplication.style()
                    if numeric_level >= logging.CRITICAL or numeric_level == logging.ERROR:
                        return style.standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)
                    elif numeric_level == logging.WARNING:
                        return style.standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
                    else:
                        # For DEBUG and INFO
                        return style.standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation)

        except:
            # Fallback if parsing fails
            col = index.column()
            raw_level_name = logging.getLevelName(levelno)
            numeric_level = levelno

            if role == QtCore.Qt.DisplayRole:
                if col == 0:
                    return "N/A"
                elif col == 1:
                    return raw_level_name
                elif col == 2:
                    return "Unknown"
                elif col == 3:
                    return "N/A"
                elif col == 4:
                    return line

            elif role == QtCore.Qt.UserRole:
                # Return fallback raw data
                if col == 0:
                    return "N/A"
                elif col == 1:
                    return numeric_level
                elif col == 2:
                    return "Unknown"
                elif col == 3:
                    return "N/A"
                elif col == 4:
                    return line

            elif role == QtCore.Qt.DecorationRole and col == 1:
                style = QtWidgets.QApplication.style()
                # If no parsing, try using numeric_level directly
                if numeric_level >= logging.CRITICAL or numeric_level == logging.ERROR:
                    return style.standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)
                elif numeric_level == logging.WARNING:
                    return style.standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
                else:
                    return style.standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation)

        return None

    @QtCore.Slot()
    def refresh(self):
        """
        Fully refresh the model by re-fetching all records that match the current level filter.
        """
        self.beginResetModel()
        self.records = [(levelno, line) for levelno, line in get_handler(HandlerType.Memory).records
                        if levelno >= get_logging_level()]
        self.endResetModel()

    @QtCore.Slot()
    def append_new_record(self):
        """
        When a new log item is emitted (via a global signal), fetch the latest record from the tank.
        If it matches the current level filter, append it to self.records.
        This avoids a full reset and only adds a single new row.
        """
        mem_handler = get_handler(HandlerType.Memory)
        if not mem_handler.records:
            return

        levelno, line = mem_handler.records[-1]
        if levelno >= get_logging_level():
            # Insert a new row at the end
            self.beginInsertRows(QtCore.QModelIndex(), len(self.records), len(self.records))
            self.records.append((levelno, line))
            self.endInsertRows()


class LogFilterProxyModel(QtCore.QSortFilterProxyModel):
    """
    A proxy model for filtering and sorting log records.
    Allows filtering by severity, logger name, thread ID, and message substring.
    Uses UserRole data for robust comparisons, including numeric log levels.
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

        # Retrieve data from UserRole for filtering
        time_str = model.index(source_row, 0, source_parent).data(QtCore.Qt.UserRole)
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
            # Time column: Parse and compare QDateTime
            left_dt = QtCore.QDateTime.fromString(left_data, "yyyy-MM-dd HH:mm:ss,zzz")
            right_dt = QtCore.QDateTime.fromString(right_data, "yyyy-MM-dd HH:mm:ss,zzz")
            if left_dt.isValid() and right_dt.isValid():
                return left_dt < right_dt
            return left_data < right_data

        elif col == 1:
            # Level column: left_data and right_data are numeric log levels
            return left_data < right_data

        else:
            # Other columns: lexicographic comparison of raw strings
            return str(left_data) < str(right_data)
