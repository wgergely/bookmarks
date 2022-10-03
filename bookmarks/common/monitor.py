"""QFileSystemWatchers used to monitor for file and directory changes.

"""
import functools

from PySide2 import QtCore

from . import common

#: The file system watcher type
FileItemMonitor = 0


def init_monitor():
    """Initialize the file monitor instances.
    
    """
    common.monitors = {
        FileItemMonitor: QtCore.QFileSystemWatcher(),
    }
    common.monitors[FileItemMonitor].directoryChanged.connect(
        functools.partial(directory_changed, FileItemMonitor))


def add_watch_directories(key, paths):
    """Adds the given list of directories to the file system watcher.

    Args:
        key (int): The file system watcher type, e.g. ``FileItemMonitor``
        paths (list): The list of directories to add to the file system watcher.
        
    """
    if key not in (FileItemMonitor,):
        raise ValueError('Invalid monitor value.')

    directories = common.monitors[key].directories()
    for path in paths:
        if path not in directories:
            common.monitors[key].addPath(path)


def clear_watch_directories(key):
    """Remove all watch directories from the given file system watcher.

    Args:


    """
    if key not in (FileItemMonitor,):
        raise ValueError('Invalid monitor value.')
    for v in common.monitors[key].directories():
        common.monitors[key].removePath(v)


@QtCore.Slot(str)
def directory_changed(idx, path):
    """Slot connected to the file system watcher's directoryChanged signal.

    Args:
        idx (int): The file system watcher type, e.g. ``FileItemMonitor``.
        path (str): The path of the directory just changed.

    """
    if idx == FileItemMonitor:
        if common.active('task', path=True) in path:
            model = common.source_model(common.FileTab)
            model.set_refresh_needed(True)
            common.widget(common.FileTab).filter_indicator_widget.repaint()
