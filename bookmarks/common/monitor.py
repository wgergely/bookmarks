"""QFileSystemWatchers used to monitor for file and directory changes.

"""

from PySide2 import QtCore

from . import common


def get_watcher(tab_idx):
    """Returns a FileWatcher instance.

    """
    if tab_idx not in common.watchers:
        common.watchers[tab_idx] = FileWatcher(tab_idx)
    return common.watchers[tab_idx]


class FileWatcher(QtCore.QFileSystemWatcher):
    def __init__(self, tab_idx, parent=None):
        super().__init__(parent=parent)

        self.tab_idx = tab_idx

        self.update_queue_timer = common.Timer()
        self.update_queue_timer.setSingleShot(True)
        self.update_queue_timer.setInterval(500)

        self.changed_items = set()

        self._connect_signals()

    def _connect_signals(self):
        self.update_queue_timer.timeout.connect(self.item_changed)
        self.directoryChanged.connect(self.queue_changed_item)

    QtCore.Slot(str)
    def queue_changed_item(self, v):
        if v not in self.changed_items:
            self.changed_items.add(v)
        self.update_queue_timer.start(self.update_queue_timer.interval())

    def add_directories(self, paths):
        """Adds the given list of directories to the file system watcher.

        Args:
            paths (list): The list of directories to add to the file system watcher.

        """
        directories = self.directories()
        for path in paths:
            if path in directories:
                continue
            self.addPath(path)

    def reset(self):
        """Remove all watch directories.

        """
        for v in self.directories():
            self.removePath(v)
        for v in self.files():
            self.removePath(v)

    @QtCore.Slot()
    def item_changed(self):
        """Slot used to update the model status.

        """
        if self.tab_idx == common.FileTab:
            self._file_item_updated()

    def _file_item_updated(self):
        p = common.active('task', path=True)
        for v in self.changed_items.copy():
            if p in v:
                model = common.source_model(common.FileTab)
                model.set_refresh_needed(True)
                common.widget(common.FileTab).filter_indicator_widget.repaint()
                break
        self.changed_items = set()
