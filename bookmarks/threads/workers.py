# -*- coding: utf-8 -*-
"""The threads and associated worker classes.

Thumbnail and file-load work on carried out on secondary threads.
Each thread is assigned a single Worker - usually responsible for taking
a *weakref.ref* from the thread's queue.

"""
import functools
import weakref
import uuid

from PySide2 import QtCore, QtGui, QtWidgets


from .. import log
from .. import common
from .. import images
from .. import database

from ..shotgun import shotgun


def get_widget(q):
    from .. import main
    from . import threads

    if not common.main_widget:
        return None

    if q == threads.TaskFolderInfo:
        widget = common.widget(common.TaskTab)
    elif threads.THREADS[q]['tab'] >= 0:
        idx = threads.THREADS[q]['tab']
        widget = common.widget(idx)
    else:
        widget = None
    return widget


def get_model(q):
    widget = get_widget(q)

    if widget is None:
        return None

    # Make sure the queue is associated with this widget
    if q not in widget.queues:
        return None

    return widget.model().sourceModel()


def verify_thread_affinity():
    """Prohibits running methods from the main gui thread.

    Raises:
        RuntimeError: If the calling thread is the main gui thread.

    """
    if QtCore.QThread.currentThread() == QtWidgets.QApplication.instance().thread():
        raise RuntimeError('Method cannot be called from the main gui thread')


def process(func):
    """Decorator for worker `process_data` slots.

    Takes and passes the next available data in the queue for processing
    and emits the `updateRow` signal if the data has been correctly loaded.

    """
    @functools.wraps(func)
    @common.error
    def func_wrapper(self, *args, **kwargs):
        verify_thread_affinity()

        if self.interrupt:
            return

        from . import threads

        try:
            ref = threads.queue(self.queue).pop()
            if not ref() or self.interrupt:
                return
        except IndexError:
            # Stopping the timer when reaching the end of the queue
            self.queue_timer.stop()
            return

        try:
            # Let the source model know that we loaded a data segment fully
            if ref().data_type in (common.FileItem, common.SequenceItem):
                # Mark the model loaded
                ref().loaded = True

                if not ref() or self.interrupt:
                    return
                self.sort_data_type(ref)
                return

            if not ref() or self.interrupt:
                return

            # Call process_data
            result = func(self, ref)
            common.check_type(result, bool)

            # Let the models/views know the data has been processed ok and
            # and request a row repaint
            if not ref() or self.interrupt or not result:
                return

            # Let's determine if the GUI should be notified of the change
            if threads.THREADS[self.queue]['tab'] == -1:
                return

            if common.QueueRole not in ref():
                return
            if self.queue in ref()[common.QueueRole]:
                self.updateRow.emit(ref)

        except:
            raise
        finally:
            self.interrupt = False

    return func_wrapper


class BaseWorker(QtCore.QObject):
    """Base worker class used to load and process item data.

    Each worker is associated with global queues using `queue` and their signals
    are connected to the respective thread signals. This is so that we can
    rely on Qt's event queue for communicating between threads.

    """
    initWorker = QtCore.Signal()

    coreDataLoaded = QtCore.Signal(weakref.ref, weakref.ref)
    coreDataReset = QtCore.Signal()
    dataTypeSorted = QtCore.Signal(int)
    queueItems = QtCore.Signal(list)

    startTimer = QtCore.Signal()
    stopTimer = QtCore.Signal()

    updateRow = QtCore.Signal(weakref.ref)
    databaseValueUpdated = QtCore.Signal(str, str, str, object)

    shotgunEntityDataReady = QtCore.Signal(str, list)

    def __init__(self, queue, parent=None):
        super(BaseWorker, self).__init__(parent=parent)

        self.setObjectName('{}Worker_{}'.format(
            queue, uuid.uuid1().hex))

        self.interrupt = False
        self.queue_timer = None
        self.queue = queue

        # cnx = QtCore.Qt.QueuedConnection
        self.initWorker.connect(self.init_worker)

    @common.error
    def init_worker(self):
        """Initialize the queue timer when the worker has been moved to the
        correct thread.

        """
        verify_thread_affinity()

        from . import threads

        self.queue_timer = common.Timer(parent=self)
        self.queue_timer.setObjectName(
            '{}Timer_{}'.format(self.queue, uuid.uuid1().hex))
        self.queue_timer.setInterval(1)

        # Local direct worker signal connections
        cnx = QtCore.Qt.DirectConnection

        self.startTimer.connect(self.queue_timer.start, cnx)
        self.stopTimer.connect(self.queue_timer.stop, cnx)

        self.queueItems.connect(self.queue_items, cnx)

        self.coreDataReset.connect(self.clear_queue, cnx)
        self.coreDataLoaded.connect(self.queue_model, cnx)
        self.queue_timer.timeout.connect(self.process_data, cnx)

        self.databaseValueUpdated.connect(
            self.update_changed_database_value, cnx)

        ###########################################

        q = self.queue
        cnx = QtCore.Qt.QueuedConnection
        widget = get_widget(q)
        model = get_model(q)

        # Timer controls
        threads.get_thread(self.queue).startTimer.connect(self.startTimer, cnx)
        threads.get_thread(self.queue).stopTimer.connect(self.stopTimer, cnx)

        # If the queue type allows preloading the model, we will queue all
        # model data when the core data has been loaded in the gui thread
        if widget:
            widget.queueItems.connect(self.queueItems, cnx)
            model.coreDataReset.connect(self.coreDataReset, cnx)
            self.updateRow.connect(widget.updateRow)

        if threads.THREADS[q]['preload'] and model and widget:
            from .. import actions
            model.coreDataLoaded.connect(self.coreDataLoaded, cnx)
            self.dataTypeSorted.connect(model.dataTypeSorted, cnx)
            common.signals.databaseValueUpdated.connect(
                self.databaseValueUpdated, cnx)

        from ..shotgun import actions as sg_actions
        self.shotgunEntityDataReady.connect(
            common.signals.shotgunEntityDataReady, cnx)

    def update_changed_database_value(self, table, source, key, value):
        """Process changes when any bookmark database value changes.

        Args:
            tab_type (idx): A tab type used to match the slot with the model type.
            source (str): A file path.
            role (int): An item role.
            v (object): The value to set.

        Returns:
            type: Description of returned object.

        """
        from . import threads

        if not threads.THREADS[self.queue]['preload']:
            return

        model = get_model(self.queue)

        p = model.source_path()
        k = model.task()
        source = common.proxy_path(source)
        n = -1

        t1 = model.data_type()
        t2 = common.FileItem if t1 == common.SequenceItem else common.SequenceItem

        for t in (t1, t2):
            ref = common.get_data_ref(p, k, t)
            for idx in ref():
                if not ref():
                    raise RuntimeError('Data changed during update.')
                # Impose a limit on how many items we'll querry
                n += 1
                if n > 99999:
                    return

                s = common.proxy_path(ref()[idx][QtCore.Qt.StatusTipRole])
                if source == s:
                    ref()[idx][common.FileInfoLoaded] = False
                    threads.THREADS[self.queue]['queue'].append(
                        weakref.ref(ref()[idx]))
                    self.queue_timer.start()

    @common.error
    def queue_items(self, refs):
        from . import threads

        q = self.queue
        for ref in reversed(refs):
            if ref in threads.THREADS[q]['queue']:
                continue

            threads.THREADS[q]['queue'].append(ref)
        self.queue_timer.start()

    @common.error
    @QtCore.Slot(weakref.ref)
    @QtCore.Slot(weakref.ref)
    def queue_model(self, data_type_ref1, data_type_ref2):

        from . import threads

        # Skip if the model is not meant to be preloaded by the worker
        q = self.queue
        if not threads.THREADS[q]['preload']:
            return
        if threads.THREADS[q]['tab'] == -1:
            return

        role = threads.THREADS[q]['role']
        for ref in (data_type_ref1, data_type_ref2):
            if not ref():
                continue

            if ref().loaded:
                continue  # Skip if the model is loaded already

            # Skip if the model has already been queued
            if ref in threads.THREADS[q]['queue']:
                continue

            idxs = ref().keys()
            for idx in idxs:
                if not ref() or self.interrupt:
                    return

                # Skip if item is loaded already
                if ref()[idx][role]:
                    continue

                threads.THREADS[q]['queue'].appendleft(weakref.ref(ref()[idx]))

            # Adding the model's data_type ref at the end of the queue to signal
            # the end of the queue
            threads.THREADS[q]['queue'].appendleft(ref)

        self.queue_timer.start()

    @common.error
    def sort_data_type(self, ref):
        verify_thread_affinity()

        model = get_model(self.queue)
        if not model:
            return

        sortrole = model.sort_role()
        sortorder = model.sort_order()

        p = model.source_path()
        k = model.task()
        t = ref().data_type

        d = common.sort_data(
            ref,
            sortrole,
            sortorder
        )

        common.set_data(p, k, t, d)

        if model.data_type() == t:
            self.dataTypeSorted.emit(t)

    @QtCore.Slot()
    def clear_queue(self):
        """Slot called by the `resetQueue` signal and is responsible for
        clearing the worker's queue.

        """
        verify_thread_affinity()

        from . import threads

        self.interrupt = True

        q = self.queue
        threads.THREADS[q]['queue'].clear()

        self.interrupt = False

    @process
    @common.error
    @QtCore.Slot(weakref.ref)
    def process_data(self, ref):
        # Do nothing by default
        if not ref() or self.interrupt:
            return False
        return True


class InfoWorker(BaseWorker):
    """A worker used to retrieve file information.

    We will query the file system for file size, and the bookmark database
    for the description, and file flags.

    """
    @process
    @common.error
    @QtCore.Slot(weakref.ref)
    def process_data(self, ref):
        """Populates the item with the missing file information.

        Args:
            ref (weakref): An internal model data DataDict instance's weakref.

        Returns:
            bool: `True` if all went well, `False` otherwise.

        """
        def is_valid():
            return (
                False if not ref() or
                self.interrupt or
                ref()[common.FileInfoLoaded] else
                True
            )

        if not is_valid():
            return False

        try:
            pp = ref()[common.ParentPathRole]

            if not is_valid():
                return False

            collapsed = common.is_collapsed(ref()[QtCore.Qt.StatusTipRole])
            seq = ref()[common.SequenceRole]

            if not is_valid():
                return False
            proxy_k = common.proxy_path(ref())
            if collapsed:
                k = proxy_k
            else:
                if not is_valid():
                    return False
                k = ref()[QtCore.Qt.StatusTipRole]

            # Load values from the database
            db = database.get_db(pp[0], pp[1], pp[2])
            # Bookmark items
            if len(pp) == 3:
                identifier = db.value(
                    db.source(),
                    'identifier',
                    table=database.BookmarkTable
                )
                count = self.count_assets(db.source(), identifier)
                if not is_valid():
                    return False
                ref()[common.AssetCountRole] = count

                description = self.get_bookmark_description(db)
                if not is_valid():
                    return False
                ref()[common.DescriptionRole] = description
                if not is_valid():
                    return False
                ref()[QtCore.Qt.ToolTipRole] = description
                if not is_valid():
                    return False

            if len(pp) > 3:
                # I made a mistake and didn't realise I was settings things
                # up so that bookmark descriptions won't be stored in
                # the asset table. Well. This just means, I'll have to make
                # sure I won't overwrite the previously retrieved bookmark
                # description here.
                v = db.value(k, 'description')
                if not is_valid():
                    return False
                ref()[common.DescriptionRole] = v

            # Let's load an verify the shotgun status
            self.update_shotgun_configured(pp, db, ref())

            v = self.count_todos(db, k)
            if not is_valid():
                return False
            ref()[common.TodoCountRole] = v

            # Item flags
            if not is_valid():
                return False
            flags = ref()[
                common.FlagsRole] | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled

            v = db.value(k, 'flags', table=database.AssetTable)
            if v:
                flags = flags | v
            v = db.value(proxy_k, 'flags', table=database.AssetTable)
            if v:
                flags = flags | v

            if not is_valid():
                return False
            ref()[common.FlagsRole] = QtCore.Qt.ItemFlags(flags)

            # For sequences we will work out the name of the sequence based on
            # the frames.
            if not is_valid():
                return False
            if ref()[common.TypeRole] == common.SequenceItem:
                if not is_valid():
                    return False
                frs = ref()[common.FramesRole]
                intframes = [int(f) for f in frs]
                padding = len(frs[0])
                rangestring = self.get_ranges(intframes, padding)

                if not is_valid():
                    return False
                seq = ref()[common.SequenceRole]
                startpath = \
                    seq.group(1) + \
                    str(min(intframes)).zfill(padding) + \
                    seq.group(3) + \
                    '.' + \
                    seq.group(4)
                endpath = \
                    seq.group(1) + \
                    str(max(intframes)).zfill(padding) + \
                    seq.group(3) + \
                    '.' + \
                    seq.group(4)
                seqpath = \
                    seq.group(1) + \
                    common.SEQSTART + rangestring + common.SEQEND + \
                    seq.group(3) + \
                    '.' + \
                    seq.group(4)
                seqname = seqpath.split('/')[-1]

                # Setting the path names
                if not is_valid():
                    return False
                ref()[common.StartpathRole] = startpath
                if not is_valid():
                    return False
                ref()[common.EndpathRole] = endpath
                if not is_valid():
                    return False
                ref()[QtCore.Qt.StatusTipRole] = seqpath
                if not is_valid():
                    return False
                ref()[QtCore.Qt.ToolTipRole] = seqpath
                if not ref():
                    return False
                ref()[QtCore.Qt.DisplayRole] = seqname
                if not is_valid():
                    return False
                ref()[QtCore.Qt.EditRole] = seqname
                if not is_valid():
                    return False
                # We saved the DirEntry instances previously in `init_data` but
                # only for the thread to extract the information from it.
                if not is_valid():
                    return False
                er = ref()[common.EntryRole]
                if er:
                    mtime = 0
                    for entry in er:
                        stat = entry.stat()
                        mtime = stat.st_mtime if stat.st_mtime > mtime else mtime
                        if not is_valid():
                            return False
                        ref()[common.SortBySizeRole] += stat.st_size
                    if not is_valid():
                        return False
                    ref()[common.SortByLastModifiedRole] = mtime
                    mtime = common.qlast_modified(mtime)

                    if not is_valid():
                        return False
                    info_string = \
                        str(len(intframes)) + 'f;' + \
                        mtime.toString('dd') + '/' + \
                        mtime.toString('MM') + '/' + \
                        mtime.toString('yyyy') + ' ' + \
                        mtime.toString('hh') + ':' + \
                        mtime.toString('mm') + ';' + \
                        self.byte_to_string(ref()[common.SortBySizeRole])
                    if not is_valid():
                        return False
                    ref()[common.FileDetailsRole] = info_string

            if not is_valid():
                return False
            if ref()[common.TypeRole] == common.FileItem:
                if not is_valid():
                    return False
                er = ref()[common.EntryRole]
                if er:
                    stat = er[0].stat()
                    mtime = stat.st_mtime
                    ref()[common.SortByLastModifiedRole] = mtime
                    mtime = common.qlast_modified(mtime)
                    ref()[common.SortBySizeRole] = stat.st_size
                    info_string = \
                        mtime.toString('dd') + '/' + \
                        mtime.toString('MM') + '/' + \
                        mtime.toString('yyyy') + ' ' + \
                        mtime.toString('hh') + ':' + \
                        mtime.toString('mm') + ';' + \
                        self.byte_to_string(ref()[common.SortBySizeRole])
                    if not is_valid():
                        return False
                    ref()[common.FileDetailsRole] = info_string
                if not is_valid():
                    return False

            # Finally, set flag to mark this item loaded
            if not is_valid():
                return False
            return True
        except OSError:
            log.error('Failed to retrieve the bookmark.')
            return False
        except:
            log.error('Error processing file info.')
            return False
        finally:
            if ref():
                ref()[common.FileInfoLoaded] = True


    def count_todos(self, db, k):
        v = db.value(k, 'notes')
        return len(v) if isinstance(v, dict) else 0


    @staticmethod
    def update_shotgun_configured(source_paths, db, data):
        server, job, root = source_paths[0:3]
        asset = None if len(source_paths) == 3 else source_paths[3]

        sg_properties = shotgun.ShotgunProperties(server, job, root, asset)
        sg_properties.init(db=db)

        data[common.ShotgunLinkedRole] = sg_properties.verify()

    @staticmethod
    def count_assets(path, ASSET_IDENTIFIER):
        n = 0
        for entry in os.scandir(path):
            if entry.name.startswith('.'):
                continue
            if not entry.is_dir():
                continue

            filepath = entry.path.replace('\\', '/')

            if not ASSET_IDENTIFIER:
                n += 1
                continue

            identifier = '/'.join((filepath, ASSET_IDENTIFIER))
            if not QtCore.QFileInfo(identifier).exists():
                continue
            n += 1
        return n

    @staticmethod
    def get_bookmark_description(db):
        """Utility method for contructing a short description for a bookmark item.

        The description includes currently set properties and the description of
        the bookmark.

        Args:
            server (str):   Server name.
            job (str):   Job name.
            root (str):   Root folder name.

        Returns:
            str:    The description of the bookmark.

        """
        BOOKMARK_DESCRIPTION = '{description}{width}{height}{framerate}{prefix}'
        sep = '  |  '
        try:
            v = {}
            for k in ('description', 'width', 'height', 'framerate', 'prefix'):
                _v = db.value(db.source(), k, table=database.BookmarkTable)
                _v = _v if _v else None
                v[k] = _v

            description = v['description'] + sep if v['description'] else ''
            width = v['width'] if (v['width'] and v['height']) else ''
            height = 'x{}px'.format(v['height']) if (
                v['width'] and v['height']) else ''
            framerate = '{}{}fps'.format(
                sep, v['framerate']) if v['framerate'] else ''
            prefix = '{}{}'.format(sep, v['prefix']) if v['prefix'] else ''

            s = BOOKMARK_DESCRIPTION.format(
                description=description,
                width=width,
                height=height,
                framerate=framerate,
                prefix=prefix
            )
            s = s.replace(sep + sep, sep)
            s = s.strip(sep).strip()  # pylint: disable=E1310
            return s
        except:
            log.error('Error constructing description.')
            return ''

    @staticmethod
    def byte_to_string(num, suffix='B'):
        """Converts a numeric byte value to a human readable string.

        Args:
            num (int):          The number of bytes.
            suffix (str):   A custom suffix.

        Returns:
            str:            Human readable byte value.

        """
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return u"%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return u"%.1f%s%s" % (num, 'Yi', suffix)

    @staticmethod
    def get_ranges(arr, padding):
        """Given an array of numbers the method will return a string representation of
        the ranges contained in the array.

        Args:
            arr(list):       An array of numbers.
            padding(int):    The number of leading zeros before the number.

        Returns:
            str: A string representation of the given array.

        """
        arr = sorted(list(set(arr)))
        blocks = {}
        k = 0
        for idx, n in enumerate(arr):  # blocks
            zfill = str(n).zfill(padding)

            if k not in blocks:
                blocks[k] = []
            blocks[k].append(zfill)

            if idx + 1 != len(arr):
                if arr[idx + 1] != n + 1:  # break coming up
                    k += 1
        return ','.join(['-'.join(sorted(list(set([blocks[k][0], blocks[k][-1]])))) for k in blocks])


class ThumbnailWorker(BaseWorker):
    """Thread worker responsible for creating and loading thumbnails.

    The resulting image data is saved in the `ImageCache` and used by the item
    delegates to paint thumbnails.

    """
    @process
    @common.error
    @QtCore.Slot(weakref.ref)
    def process_data(self, ref):
        """Populates the ImageCache with an existing thumbnail or generates a
        new one if `ref` refers to a file understood by OpenImageIO.

        If the return value is not `None`, the model will request a repaint
        event for the row the `ref` corresponds to. See the `@process` decorator
        for details.

        Args:
            ref (weakref.ref): A weakref to a data segment.

        Returns:
            ref or None: `ref` if loaded successfully, else `None`.

        """
        def is_valid(): return False if not ref() or self.interrupt or ref()[
            common.ThumbnailLoaded] or ref()[common.FlagsRole] & common.MarkedAsArchived else True

        if not is_valid():
            return False
        size = ref()[QtCore.Qt.SizeHintRole].height()

        if not is_valid():
            return False
        _p = ref()[common.ParentPathRole]

        if not is_valid():
            return False
        source = ref()[QtCore.Qt.StatusTipRole]

        # Resolve the thumbnail's path...
        destination = images.get_cached_thumbnail_path(
            _p[0],
            _p[1],
            _p[2],
            source,
        )
        # ...and use it to load the resource
        image = images.ImageCache.get_image(
            destination,
            int(size),
            force=True  # force=True will refresh the cache
        )

        try:
            # If the image successfully loads we can wrap things up here
            if image and not image.isNull():
                images.ImageCache.get_image(destination, int(size), force=True)
                images.ImageCache.make_color(destination)
                return True

            # Otherwise, we will try to generate a thumbnail using OpenImageIO

            # If the items is a sequence, we'll use the first image of the
            # sequence to make the thumbnail.
            if not is_valid():
                return False
            if ref()[common.TypeRole] == common.SequenceItem:
                if not is_valid():
                    return False
                source = ref()[common.EntryRole][0].path.replace('\\', '/')

            buf = images.oiio_get_buf(source)
            if not buf:
                return True

            if QtCore.QFileInfo(source).size() >= pow(1024, 3) * 2:
                return True
            res = images.ImageCache.oiio_make_thumbnail(
                source,
                destination,
                common.thumbnail_size,
            )
            if res:
                images.ImageCache.get_image(destination, int(size), force=True)
                images.ImageCache.make_color(destination)
                return True

            # We should never get here ideally, but if we do we'll mark the item
            # with a bespoke 'failed' thumbnail
            fpath = '{}/../rsc/{}/{}.{}'.format(
                __file__, images.GuiResource, 'close', common.thumbnail_format)
            res = images.ImageCache.oiio_make_thumbnail(
                fpath,
                destination,
                common.thumbnail_size
            )
            if res:
                images.ImageCache.get_image(destination, int(size), force=True)
                images.ImageCache.make_color(destination)

            ref()[common.ThumbnailLoaded] = True
            return True
        except:
            ref()[common.ThumbnailLoaded] = True
            log.error('Failed to generate thumbnail')
            return False


class TaskFolderWorker(InfoWorker):
    """Used by the TaskFolderModel to count the number of files in a folder."""


    def count_todos(self, db, k):
        count = 0
        for _ in self.item_iterator(k):
            count += 1
            if count > 9999:
                break
        return count

    @classmethod
    def item_iterator(cls, path):
        """Used to iterate over all files in a given folder.

        Yields:
            DirEntry:   A DirEntry instance.

        """
        try:
            it = os.scandir(path)
        except:
            return

        while True:
            try:
                try:
                    entry = next(it)
                except StopIteration:
                    break
            except OSError:
                return

            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False

            if entry.name.startswith('.'):
                continue

            if not is_dir:
                yield entry

            try:
                is_symlink = entry.is_symlink()
            except OSError:
                is_symlink = False
            if not is_symlink:
                for entry in cls.item_iterator(entry.path):
                    yield entry


class TransactionsWorker(BaseWorker):
    @common.error
    def process_data(self):
        verify_thread_affinity()

        if self.interrupt:
            return

        from . import threads

        try:
            args = threads.queue(self.queue).pop()
            database.set_flag(*args)
        except IndexError:
            pass  # ignore index errors


class ShotgunWorker(BaseWorker):
    @common.error
    def process_data(self):
        verify_thread_affinity()

        if self.interrupt:
            return

        from . import threads

        try:
            args = threads.queue(self.queue).pop()
            idx, server, job, root, asset, entity_type, filters, fields = args

            sg_properties = shotgun.ShotgunProperties(server, job, root, asset)
            sg_properties.init()
            if not sg_properties.verify(connection=True):
                return

            sg = shotgun.get_sg(
                sg_properties.domain,
                sg_properties.script,
                sg_properties.key,
            )

            if entity_type == 'Status':
                from ..shotgun import actions as sg_actions
                entities = sg_actions.get_status_codes(sg)
            else:
                entities = sg.find(entity_type, filters, fields=fields)

            # Emit the retrieved data so the ui componenets can fetch it
            self.shotgunEntityDataReady.emit(idx, entities)
        except IndexError:
            pass  # ignore index errors
        except:
            raise
