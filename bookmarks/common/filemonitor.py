"""QFileSystemWatcher used to monitor for file and directory changes.

"""
import functools
from PySide2 import QtCore

from . import common


FileItemMonitor = 0
TaskItemMonitor = 1


def init_monitor():
    common.monitors = {
        FileItemMonitor: QtCore.QFileSystemWatcher(),
        TaskItemMonitor: QtCore.QFileSystemWatcher()
    }
    common.monitors[FileItemMonitor].directoryChanged.connect(
        functools.partial(directory_changed, FileItemMonitor))
    common.monitors[TaskItemMonitor].directoryChanged.connect(
        functools.partial(directory_changed, TaskItemMonitor))


def set_watchdirs(idx, paths):
    if idx not in (FileItemMonitor, TaskItemMonitor):
        raise ValueError('Invalid monitor value.')
    common.monitors[idx].addPaths(paths)


def clear_watchdirs(idx):
    if idx not in (FileItemMonitor, TaskItemMonitor):
        raise ValueError('Invalid monitor value.')
    for v in common.monitors[idx].directories():
        common.monitors[idx].removePath(v)


@QtCore.Slot(str)
def directory_changed(idx, path):
    if idx == FileItemMonitor:
        if common.active(common.TaskKey, path=True) in path:
            model = common.source_model(common.FileTab)
            model.set_refresh_needed(True)
            common.widget(common.FileTab).filter_indicator_widget.repaint()
