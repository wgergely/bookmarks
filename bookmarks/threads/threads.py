# -*- coding: utf-8 -*-
"""The threads and associated worker classes.

Thumbnail and file-load work on carried out on secondary threads.
Each thread is assigned a single Worker - usually responsible for taking
a *weakref.ref* from the thread's queue.

"""
import uuid
import time
import weakref
import collections

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from . import workers


class DataType(object):
    """Used to signify the end of a data type."""

    def __repr__(self):
        return '<< DataType({}, {}) >>'.format(self.data_type, self.queue)

    def __init__(self, q, t):
        self.queue = q
        self.data_type = t


FileThumbnail = 'FileThumbnail'
FavouriteThumbnail = 'FavouriteThumbnail'
AssetThumbnail = 'AssetThumbnail'
BookmarkThumbnail = 'BookmarkThumbnail'
FileInfo = 'FileInfo'
FavouriteInfo = 'FavouriteInfo'
AssetInfo = 'AssetInfo'
BookmarkInfo = 'BookmarkInfo'
TaskFolderInfo = 'TaskFolderInfo'
QueuedDatabaseTransaction = 'QueuedDatabaseTransaction'
QueuedSettingsTransaction = 'QueuedSettingsTransaction'
QueuedShotgunQuery = 'QueuedShotgunQuery'


controllers = {}


THREADS = {
    BookmarkInfo: {
        'queue': collections.deque([], common.max_list_items),
        'preload': True,
        'data_types': {
            common.FileItem: DataType(BookmarkInfo, common.FileItem),
        },
        'worker': workers.InfoWorker,
        'role': common.FileInfoLoaded,
        'tab': common.BookmarkTab,
        'mutex': QtCore.QMutex()
    },
    BookmarkThumbnail: {
        'queue': collections.deque([], 99),
        'preload': False,
        'data_types': {
            common.FileItem: DataType(BookmarkThumbnail, common.FileItem),
        },
        'worker': workers.ThumbnailWorker,
        'role': common.ThumbnailLoaded,
        'tab': common.BookmarkTab,
        'mutex': QtCore.QMutex()
    },
    AssetInfo: {
        'queue': collections.deque([], common.max_list_items),
        'preload': True,
        'data_types': {
            common.FileItem: DataType(AssetInfo, common.FileItem),
        },
        'worker': workers.InfoWorker,
        'role': common.FileInfoLoaded,
        'tab': common.AssetTab,
        'mutex': QtCore.QMutex()
    },
    AssetThumbnail: {
        'queue': collections.deque([], 99),
        'preload': False,
        'data_types': {
            common.FileItem: DataType(AssetThumbnail, common.FileItem),
        },
        'worker': workers.ThumbnailWorker,
        'role': common.ThumbnailLoaded,
        'tab': common.AssetTab,
        'mutex': QtCore.QMutex()
    },
    FileInfo: {
        'queue': collections.deque([], common.max_list_items),
        'preload': True,
        'data_types': {
            common.FileItem: DataType(FileInfo, common.FileItem),
            common.SequenceItem: DataType(FileInfo, common.SequenceItem),
        },
        'worker': workers.InfoWorker,
        'role': common.FileInfoLoaded,
        'tab': common.FileTab,
        'mutex': QtCore.QMutex()
    },
    FileThumbnail: {
        'queue': collections.deque([], 99),
        'preload': False,
        'data_types': {
            common.FileItem: DataType(FileThumbnail, common.FileItem),
            common.SequenceItem: DataType(FileThumbnail, common.SequenceItem),
        },
        'worker': workers.ThumbnailWorker,
        'role': common.ThumbnailLoaded,
        'tab': common.FileTab,
        'mutex': QtCore.QMutex()
    },
    FavouriteInfo: {
        'queue': collections.deque([], common.max_list_items),
        'preload': True,
        'data_types': {
            common.FileItem: DataType(FavouriteInfo, common.FileItem),
            common.SequenceItem: DataType(FavouriteInfo, common.SequenceItem),
        },
        'worker': workers.InfoWorker,
        'role': common.FileInfoLoaded,
        'tab': common.FavouriteTab,
        'mutex': QtCore.QMutex()
    },
    FavouriteThumbnail: {
        'queue': collections.deque([], 99),
        'preload': False,
        'data_types': {
            common.FileItem: DataType(FavouriteThumbnail, common.FileItem),
            common.SequenceItem: DataType(FavouriteThumbnail, common.SequenceItem),
        },
        'worker': workers.ThumbnailWorker,
        'role': common.ThumbnailLoaded,
        'tab': common.FavouriteTab,
        'mutex': QtCore.QMutex()
    },
    TaskFolderInfo: {
        'queue': collections.deque([], common.max_list_items),
        'preload': True,
        'data_types': {
            common.FileItem: DataType(TaskFolderInfo, common.FileItem),
        },
        'worker': workers.TaskFolderWorker,
        'role': common.FileInfoLoaded,
        'tab': -1,
        'mutex': QtCore.QMutex()
    },
    QueuedDatabaseTransaction: {
        'queue': collections.deque([], common.max_list_items),
        'preload': False,
        'data_types': {},
        'worker': workers.TransactionsWorker,
        'role': None,
        'tab': -1,
        'mutex': QtCore.QMutex()
    },
    QueuedShotgunQuery: {
        'queue': collections.deque([], common.max_list_items),
        'preload': False,
        'data_types': {},
        'worker': workers.ShotgunWorker,
        'role': None,
        'tab': -1,
        'mutex': QtCore.QMutex()
    },
}


def queue_database_transaction(*args):
    if args not in queue(QueuedDatabaseTransaction):
        queue(QueuedDatabaseTransaction).append(args)
    get_thread(QueuedDatabaseTransaction).startTimer.emit()


def queue_shotgun_query(*args):
    if args not in queue(QueuedShotgunQuery):
        queue(QueuedShotgunQuery).append(args)
    get_thread(QueuedShotgunQuery).startTimer.emit()


def reset_all_queues():
    for k in THREADS:
        THREADS[k]['queue'].clear()


def quit_threads():
    for k in THREADS:
        thread = get_thread(k)
        if thread.isRunning():
            THREADS[k]['queue'].clear()
            thread.quit()
            thread.wait()

    n = 0
    while any([get_thread(k).isRunning() for k in THREADS]):
        if n >= 20:
            for thread in THREADS.values():
                thread.terminate()
            break
        n += 1
        time.sleep(0.3)


def get_thread(k):
    """Get a cached thread controller instance.

    If the controller does not yet exist we will create and cache it.
    All threads are associated with worker, defined by `THREADS`.

    """
    if k not in THREADS:
        raise KeyError('{} is invalid. Must be one of {}'.format(
            k, '\n'.join(THREADS.keys())))

    if k in controllers:
        return controllers[k]

    controllers[k] = BaseThread(THREADS[k]['worker'](k))
    return controllers[k]


def queue(k):
    """Returns a queue associated with a thread."""
    if k not in THREADS:
        raise KeyError('Wrong key')
    return THREADS[k]['queue']


def add_to_queue(k, ref):
    """Adds a wekref item to the worker's queue.

    Args:
        ref (weakref.ref): A weak reference to a data segment.
        end (bool): Add to the end of the queue instead if `True`.

    """
    common.check_type(ref, weakref.ref)

    if ref not in queue(k) and ref():
        queue(k).append(ref)


class BaseThread(QtCore.QThread):
    """Thread controller.

    The threads are associated with workers and are used to consume items
    from their associated queues.

    """
    initWorker = QtCore.Signal()
    startTimer = QtCore.Signal()
    stopTimer = QtCore.Signal()

    def __init__(self, worker, parent=None):
        super(BaseThread, self).__init__(parent=parent)
        self.setObjectName('{}Thread_{}'.format(
            worker.queue, uuid.uuid1().hex))
        self.setTerminationEnabled(True)

        self.worker = worker
        self._connect_signals()

    def _connect_signals(self):
        if QtCore.QCoreApplication.instance():
            QtCore.QCoreApplication.instance().aboutToQuit.connect(self.quit)
        if QtGui.QGuiApplication.instance():
            QtGui.QGuiApplication.instance().lastWindowClosed.connect(self.quit)
        self.started.connect(self.move_worker_to_thread)

    @common.debug
    @QtCore.Slot()
    def move_worker_to_thread(self):
        """Slot called when the thread is started.

        We'll move the worker to the thread and connect all signals needed to
        communicate with the worker. Thread affinity seems to be tricky
        thing to manage but as far as I can see starting

        """
        # Start the timer in this thread
        self.worker.moveToThread(self)

        cnx = QtCore.Qt.QueuedConnection
        self.initWorker.connect(self.worker.initWorker, cnx)
        self.initWorker.emit()

        if self.worker.thread() == QtWidgets.QApplication.instance().thread():
            s = 'Could not move worker to thread.'
            raise RuntimeError(s)
