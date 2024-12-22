import collections
import weakref

from PySide2 import QtCore

from . import filterview
from ... import common
from ...threads import threads


class ThreadedItemView(filterview.FilterView):
    """Extends the :class:`ButtonView` with the methods used to interface with
    threads.

    """
    workerInitialized = QtCore.Signal(str)
    refUpdated = QtCore.Signal(weakref.ref)
    queueItems = QtCore.Signal(list)

    queues = ()

    def __init__(self, icon='bw_icon', parent=None):
        self.delayed_queue_timer = common.Timer()
        self.delayed_queue_timer.setInterval(500)
        self.delayed_queue_timer.setSingleShot(True)

        self.update_queue = collections.deque([], common.max_list_items)
        self.update_queue_timer = common.Timer(parent=self)
        self.update_queue_timer.setSingleShot(True)
        self.update_queue_timer.setInterval(20)

        super().__init__(icon=icon, parent=parent)

        self.init_threads()

    def _connect_signals(self):
        super()._connect_signals()
        self.update_queue_timer.timeout.connect(self.queued_row_repaint)

        self.delayed_queue_timer.timeout.connect(self.save_visible_rows)
        self.delayed_queue_timer.timeout.connect(self.queue_visible_indexes)

        self.refUpdated.connect(self.update_row)

        self.verticalScrollBar().valueChanged.connect(self.start_delayed_queue_timer)
        self.verticalScrollBar().sliderReleased.connect(self.start_delayed_queue_timer)

        common.signals.tabChanged.connect(self.start_delayed_queue_timer)

    @common.debug
    @common.error
    def init_threads(self):
        """Starts and connects the threads."""
        for q in self.queues:
            thread = threads.get_thread(q)
            thread.start()

        # Wait for all threads to spin up before continuing
        n = 0.0
        import time
        while not all([threads.get_thread(f).isRunning() for f in self.queues]):
            n += 0.1
            time.sleep(0.1)
            if n > 2.0:
                break

    @common.error
    @common.debug
    def init_model(self, *args, **kwargs):
        """The methods responsible for connecting the associated item model with the view.

        """
        super().init_model(*args, **kwargs)

        self.model().invalidated.connect(self.start_delayed_queue_timer)
        self.model().sourceModel().modelReset.connect(self.start_delayed_queue_timer)

        self.model().filterTextChanged.connect(self.start_delayed_queue_timer)
        self.model().filterFlagChanged.connect(self.start_delayed_queue_timer)

    @QtCore.Slot()
    @common.debug
    def start_delayed_queue_timer(self, *args, **kwargs):
        """Starts the delayed queue timer.

        """
        self.delayed_queue_timer.start(self.delayed_queue_timer.interval())

    @common.status_bar_message('Updating items...')
    @common.debug
    def queue_visible_indexes(self, *args, **kwargs):
        """Send all currently visible items to the worker
        threads for processing.

        """
        proxy = self.model()
        if not proxy:
            return
        model = proxy.sourceModel()
        if not model:
            return

        data = model.model_data()

        show_archived = proxy.filter_flag(common.MarkedAsArchived)

        try:
            for q in self.queues:
                role = threads.THREADS[q]['role']

                # Skip queues that have their data already preloaded
                if threads.THREADS[q]['preload'] and data.loaded:
                    continue

                refs = []
                for idx in self.visible_rows['source_rows']:

                    # Item is already loaded, skip
                    if data[idx][role]:
                        continue

                    # Check if any of the current items are archived and invalidate
                    # the filter if it is meant to be hidden
                    is_archived = data[idx][common.FlagsRole] & common.MarkedAsArchived
                    if show_archived is False and is_archived:
                        proxy.invalidateFilter()
                        return

                    refs.append(weakref.ref(data[idx]))
                self.queueItems.emit(refs)
        except KeyError:
            pass
        except:
            raise

    @QtCore.Slot(weakref.ref)
    def update_row(self, ref):
        """Queues an update request by the threads for later processing."""
        if not ref():
            return
        if ref not in self.update_queue.copy():
            self.update_queue.append(ref)
            self.update_queue_timer.start(self.update_queue_timer.interval())

    def queued_row_repaint(self):
        """Process a repaint request."""
        try:
            ref = self.update_queue.popleft()
        except IndexError:
            return
        if not ref():
            return

        for row in self.visible_rows['proxy_rows']:
            index = self.model().index(row, 0)
            if index.data(common.PathRole) == ref()[common.PathRole]:
                super().update(index)
                break

        self.update_queue_timer.start(self.update_queue_timer.interval())

    @QtCore.Slot()
    def delayed_save_visible_rows(self):
        self.delayed_save_visible_timer.start(
            self.delayed_save_visible_timer.interval()
        )
