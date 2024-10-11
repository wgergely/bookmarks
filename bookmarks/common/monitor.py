"""QFileSystemWatchers used to monitor for file and directory changes.

"""
import weakref

from PySide2 import QtCore

from . import common


def get_watcher(tab_idx):
    """Returns a FileWatcher instance.

    """
    if tab_idx not in common.watchers:
        common.watchers[tab_idx] = FileWatcher(tab_idx)
    return common.watchers[tab_idx]


class FileWatcher(QtCore.QFileSystemWatcher):
    modelNeedsRefresh = QtCore.Signal(weakref.ref)

    def __init__(self, tab_idx, parent=None):
        super().__init__(parent=parent)

        self.tab_idx = tab_idx

        #: Timer used to limit the number of updates
        self.update_timer = common.Timer(parent=self)
        self.update_timer.setInterval(5000)
        self.update_timer.setTimerType(QtCore.Qt.CoarseTimer)
        self.update_timer.setSingleShot(True)

        self.update_queue = set()

        self._connect_signals()

    def _connect_signals(self):
        self.update_timer.timeout.connect(self.process_update_queue)

        self.directoryChanged.connect(self.queue_changed_item)

        self.modelNeedsRefresh.connect(common.signals.updateTopBarButtons)
        # self.modelNeedsRefresh.connect(self.update_model)

    @QtCore.Slot(str)
    def queue_changed_item(self, v):
        """Slot used to add an updated path to the update queue.

        Args:
            v (str): The path to add to the update queue.

    """
        if v not in self.update_queue.copy():
            self.update_queue.add(v)

        self.update_timer.start(self.update_timer.interval())

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
        """Reset the watcher to its initial state.

        """
        for v in self.directories():
            self.removePath(v)
        for v in self.files():
            self.removePath(v)
        self.update_queue.clear()

    @QtCore.Slot()
    def process_update_queue(self):
        """Slot used to mark a data dictionary as needing to be refreshed.

        Emits the modelNeedsRefresh signal for each data dictionary in the update queue.

        """
        processed_data_dicts = []

        for path in self.update_queue.copy():
            for data_type in (common.SequenceItem, common.FileItem):
                data_dict = common.get_data_from_value(path, data_type, role=common.PathRole)

                if not data_dict:
                    continue

                if data_dict in processed_data_dicts:
                    continue

                data_dict.refresh_needed = True
                common.widget(self.tab_idx).filter_indicator_widget.repaint()
                self.modelNeedsRefresh.emit(weakref.ref(data_dict))

                processed_data_dicts.append(data_dict)

        self.update_queue.clear()
        self.update_timer.stop()

    @QtCore.Slot(weakref.ref)
    def update_model(self, ref):
        """Slot used to update the model associated with the item tab index.

        Args:
            ref (weakref.ref): A weak reference to the data dictionary that needs updating.

        """
        if not ref():
            return

        # If the data is relatively small, we don't have to bail out...
        if len(ref()) > 999:
            return

        source_model = common.source_model(self.tab_idx)
        p = source_model.parent_path()
        k = source_model.task()

        for t in (common.FileItem, common.SequenceItem,):
            data = common.get_data(p, k, t)

            if not data:
                source_model.reset_data(force=True)
                return

            # Force reset the source model if we find a data match
            if data == ref():
                source_model.reset_data(force=True)
                return
