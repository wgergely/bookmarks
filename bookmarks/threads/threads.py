"""Thread definitions and associated worker classes.

"""
import collections
import time
import uuid
import weakref

from PySide2 import QtCore, QtGui, QtWidgets

from . import workers
from .. import common


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
FileInfo2 = 'FileInfo2'
FileInfo3 = 'FileInfo3'
FavouriteInfo = 'FavouriteInfo'
AssetInfo = 'AssetInfo'
BookmarkInfo = 'BookmarkInfo'
QueuedDatabaseTransaction = 'QueuedDatabaseTransaction'
QueuedSGQuery = 'QueuedSGQuery'

controllers = {}

# Main thread definitions
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
    },
    FileInfo2: {
        'queue': collections.deque([], common.max_list_items),
        'preload': True,
        'data_types': {
            common.FileItem: DataType(FileInfo, common.FileItem),
            common.SequenceItem: DataType(FileInfo, common.SequenceItem),
        },
        'worker': workers.InfoWorker,
        'role': common.FileInfoLoaded,
        'tab': common.TaskItemSwitch,
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
    },
    QueuedDatabaseTransaction: {
        'queue': collections.deque([], common.max_list_items),
        'preload': False,
        'data_types': {},
        'worker': workers.TransactionsWorker,
        'role': None,
        'tab': -1,
    },
    QueuedSGQuery: {
        'queue': collections.deque([], common.max_list_items),
        'preload': False,
        'data_types': {},
        'worker': workers.SGWorker,
        'role': None,
        'tab': -1,
    },
}


def queue_database_transaction(*args):
    """A utility method used to execute a delayed database transaction.

    """
    if args not in queue(QueuedDatabaseTransaction):
        queue(QueuedDatabaseTransaction).append(args)
    get_thread(QueuedDatabaseTransaction).startTimer.emit()


def queue_sg_query(*args):
    if args not in queue(QueuedSGQuery):
        queue(QueuedSGQuery).append(args)
    get_thread(QueuedSGQuery).startTimer.emit()


def quit_threads():
    """Terminate all running threads."""

    # First, attempt to quit all threads
    for k in THREADS:
        thread = get_thread(k)
        if thread.isRunning():
            THREADS[k]['queue'].clear()
            thread.quit()
            # thread.wait(5000)  # Wait up to 5 seconds for the thread to quit.

    # Now, wait for all threads to finish, up to a maximum of 10 seconds
    timeout = time.time() + 10.0
    while any(get_thread(k).isRunning() for k in THREADS):
        time.sleep(0.01)
        if time.time() >= timeout:
            # Forcefully terminate any threads still running
            for k in THREADS:
                thread = get_thread(k)
                if thread.isRunning():
                    thread.terminate()
            break



def get_thread(k):
    """Get a cached thread controller instance.

    Args:
        k (str): Name of the thread controller to return, for example
            ``threads.QueuedSGQuery``.

    If the controller does not yet exist we will create and cache it.
    All threads are associated with worker, defined by `THREADS`.

    """
    if k not in THREADS:
        raise KeyError(
            '{} is invalid. Must be one of {}'.format(
                k, '\n'.join(THREADS.keys())
            )
        )

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
    """Base QThread controller.

    Attributes:
        initWorker (QtCore.Signal): Signal emitted when the thread has spun up.
        startTimer (QtCore.Signal): Starts the thread's queue timer.
        stopTimer (QtCore.Signal): Stops the thread's queue timer.

    """
    initWorker = QtCore.Signal()
    startTimer = QtCore.Signal()
    stopTimer = QtCore.Signal()

    def __init__(self, worker, parent=None):
        super().__init__(parent=parent)

        if hasattr(worker, 'queue'):
            self.setObjectName(f'{worker.queue}Thread_{uuid.uuid1().hex}')
        else:
            self.setObjectName(f'Thread_{uuid.uuid1().hex}')

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
        communicate with the worker.

        """
        self.worker.moveToThread(self)

        cnx = QtCore.Qt.QueuedConnection
        if hasattr(self.worker, 'initWorker'):
            self.initWorker.connect(self.worker.initWorker, cnx)
            self.initWorker.emit()

        if self.worker.thread() == QtWidgets.QApplication.instance().thread():
            s = 'Could not move worker to thread.'
            raise RuntimeError(s)
