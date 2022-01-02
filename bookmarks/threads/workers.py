# -*- coding: utf-8 -*-
"""The threads and associated worker classes across Bookmarks.



Thumbnail and file-load work on carried out on secondary threads.
Each thread is assigned a single Worker - usually responsible for taking
a *weakref.ref* from the thread's queue.

"""
import functools
import os
import uuid
import weakref

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import database
from .. import images
from .. import log
from ..shotgun import shotgun


def _widget(q):
    from . import threads

    if common.main_widget is None:
        return None

    if q == threads.TaskFolderInfo:
        widget = common.widget(common.TaskTab)
    elif threads.THREADS[q]['tab'] >= 0:
        idx = threads.THREADS[q]['tab']
        widget = common.widget(idx)
    else:
        widget = None
    return widget


def _qlast_modified(n):
    return QtCore.QDateTime.fromMSecsSinceEpoch(n * 1000)


def _model(q):
    widget = _widget(q)
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
    and emits the `refUpdated` signal if the data has been correctly loaded.

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
            if not ref() or self.interrupt:
                return

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
            # request a row repaint
            if not ref() or self.interrupt or not result:
                return

            # Let's determine if the GUI should be notified of the change
            if threads.THREADS[self.queue]['tab'] == -1:
                return

            if common.QueueRole not in ref():
                return
            if self.queue in ref()[common.QueueRole]:
                self.refUpdated.emit(ref)

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

    refUpdated = QtCore.Signal(weakref.ref)
    databaseValueUpdated = QtCore.Signal(str, str, str, object)

    sgEntityDataReady = QtCore.Signal(str, list)

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
        widget = _widget(q)
        model = _model(q)

        # Timer controls
        threads.get_thread(self.queue).startTimer.connect(self.startTimer, cnx)
        threads.get_thread(self.queue).stopTimer.connect(self.stopTimer, cnx)

        # If the queue type allows preloading the model, we will queue all
        # model data when the core data has been loaded in the gui thread
        if widget:
            widget.queueItems.connect(self.queueItems, cnx)
            model.coreDataReset.connect(self.coreDataReset, cnx)
            self.refUpdated.connect(widget.refUpdated, cnx)

        if threads.THREADS[q]['preload'] and model and widget:
            model.coreDataLoaded.connect(self.coreDataLoaded, cnx)
            self.dataTypeSorted.connect(model.dataTypeSorted, cnx)
            common.signals.databaseValueUpdated.connect(
                self.databaseValueUpdated, cnx)

        self.sgEntityDataReady.connect(
            common.signals.sgEntityDataReady, cnx)

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

        model = _model(self.queue)

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
        common.signals.threadItemsQueued.emit()

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

        model = _model(self.queue)
        if not model:
            return

        sort_role = model.sort_role()
        sort_order = model.sort_order()

        p = model.source_path()
        k = model.task()
        t = ref().data_type

        if not ref():
            return
        d = common.sort_data(
            ref,
            sort_role,
            sort_order
        )
        if not ref():
            return
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


def byte_to_pretty_string(num, suffix='B'):
    """Converts a numeric byte value to a human-readable string.

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


def count_todos(asset_row_data):
    v = asset_row_data['notes']
    return len(v) if isinstance(v, dict) else 0


def count_assets(path, ASSET_IDENTIFIER):
    n = 0
    for entry in os.scandir(path):
        if entry.name.startswith('.'):
            continue
        if not entry.is_dir():
            continue
        if not ASSET_IDENTIFIER:
            n += 1
            continue
        path = entry.path.replace('\\', '/')
        identifier = '/'.join((path, ASSET_IDENTIFIER))
        if not QtCore.QFileInfo(identifier).exists():
            continue
        n += 1
    return n


def get_bookmark_description(bookmark_row_data):
    """Utility method for constructing a short description for a bookmark item.

    The description includes currently set properties and the description of
    the bookmark.

    Args:
        bookmark_row_data (dict): Data retrieved from the database.

    Returns:
        str:    The description of the bookmark.

    """
    sep = '  |  '
    try:
        v = {}
        for k in ('description', 'width', 'height', 'framerate', 'prefix'):
            _v = bookmark_row_data[k]
            _v = _v if _v else None
            v[k] = _v

        description = f'{v["description"]}{sep}' if v['description'] else ''
        width = v['width'] if (v['width'] and v['height']) else ''
        height = f'x{v["height"]}px' if (v['width'] and v['height']) else ''
        framerate = f'{sep}{v["framerate"]}fps' if v['framerate'] else ''
        prefix = f'{sep}{v["prefix"]}' if v['prefix'] else ''

        s = f'{description}{width}{height}{framerate}{prefix}'
        s = s.replace(sep + sep, sep)
        s = s.strip(sep).strip()
        return s
    except:
        log.error('Could not get description.')
        return ''


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


def update_slack_configured(source_paths, bookmark_row_data, ref):
    v = bookmark_row_data['slacktoken']
    ref()[common.SlackLinkedRole] = True if v else False


def update_shotgun_configured(pp, b, a, ref):
    if not all((pp, b, a, ref())):
        return
    b_conf = (b['shotgun_domain'], b['shotgun_scriptname'], b['shotgun_api_key'])
    b_item_conf = (b['shotgun_id'], b['shotgun_name'], b['shotgun_type'])
    if pp == 3:
        if all(b_conf + b_item_conf):
            ref()[common.ShotgunLinkedRole] = True
            return
    if pp == 4:
        a_item_conf = (a['shotgun_id'], a['shotgun_name'], a['shotgun_type'])
        if all(b_conf + b_item_conf + a_item_conf):
            ref()[common.ShotgunLinkedRole] = True
            return

    ref()[common.ShotgunLinkedRole] = False


class InfoWorker(BaseWorker):
    """A worker used to retrieve file information.

    We will query the file system for file size, and the bookmark database
    for the description, and file flags.

    """

    def is_valid(self, ref):
        return False if (
                not ref() or
                self.interrupt or
                ref()[common.FileInfoLoaded]
        ) else True

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
        if not self.is_valid(ref):
            return False

        try:
            self._process_data(ref)
            return True
        except TypeError:
            if ref():
                log.error(f'Failed to process item.')
            return False
        except:
            log.error(f'Failed to process item.')
            return False
        finally:
            if ref():
                ref()[common.FileInfoLoaded] = True

    def _process_data(self, ref):
        pp = ref()[common.ParentPathRole]
        st = ref()[QtCore.Qt.StatusTipRole]
        flags = ref()[common.FlagsRole] | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled
        item_type = ref()[common.TypeRole]

        if not st:
            raise RuntimeError('Not processable.')

        if len(pp) > 4:
            collapsed = common.is_collapsed(st)
            proxy_k = common.proxy_path(st)
            k = proxy_k if collapsed else st
        else:
            k = st

        # Load values from the database
        db = database.get_db(*pp[0:3])
        asset_row_data = db.get_row(k, database.AssetTable)
        bookmark_row_data = db.get_row(db.source(), database.BookmarkTable)
        if len(pp) > 4:
            _proxy_flags = db.value(proxy_k, 'flags', database.AssetTable)

        # Description
        if len(pp) > 3:
            if asset_row_data:
                ref()[common.DescriptionRole] = asset_row_data['description']
        # Shotgun status
        if len(pp) <= 4:
            update_shotgun_configured(pp, bookmark_row_data, asset_row_data, ref)
        # Note count
        if asset_row_data:
            ref()[common.TodoCountRole] = count_todos(asset_row_data)

        # Flags
        if asset_row_data:
            _flags = asset_row_data['flags']
        else:
            _flags = 0
        flags |= _flags if _flags else 0
        if len(pp) > 4:
            flags |= _proxy_flags if _proxy_flags else 0
        ref()[common.FlagsRole] = QtCore.Qt.ItemFlags(flags)

        self.count_items(ref, st)

        self._process_bookmark_item(ref, db.source(), bookmark_row_data, pp)
        self._process_file_item(ref, item_type)
        self._process_sequence_item(ref, item_type)

    def _process_bookmark_item(self, ref, source, bookmark_row_data, pp):
        if not self.is_valid(ref):
            return False

        if len(pp) != 3:
            return

        description = get_bookmark_description(bookmark_row_data)
        count = count_assets(source, bookmark_row_data['identifier'])

        if not self.is_valid(ref):
            return False
        ref()[common.AssetCountRole] = count
        ref()[common.DescriptionRole] = description
        ref()[QtCore.Qt.ToolTipRole] = description

        # Let's load and verify Slack status
        update_slack_configured(pp, bookmark_row_data, ref)

    def _process_sequence_item(self, ref, item_type):
        if not self.is_valid(ref):
            return False
        if item_type != common.SequenceItem:
            return

        seq = ref()[common.SequenceRole]
        frs = ref()[common.FramesRole]
        er = ref()[common.EntryRole]
        size = ref()[common.SortBySizeRole]

        intframes = [int(f) for f in frs]
        padding = len(frs[0])
        rangestring = get_ranges(intframes, padding)

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

        _mtime = 0
        info_string = ''
        if er:
            for entry in er:
                stat = entry.stat()
                size += stat.st_size
                _mtime = stat.st_mtime if stat.st_mtime > _mtime else _mtime

            mtime = _qlast_modified(_mtime)
            info_string += \
                str(len(intframes)) + 'f;' + \
                mtime.toString('dd') + '/' + \
                mtime.toString('MM') + '/' + \
                mtime.toString('yyyy') + ' ' + \
                mtime.toString('hh') + ':' + \
                mtime.toString('mm') + ';' + \
                byte_to_pretty_string(size)

        # Setting the path names
        if not self.is_valid(ref):
            return False
        ref()[common.StartPathRole] = startpath
        ref()[common.EndPathRole] = endpath
        ref()[QtCore.Qt.StatusTipRole] = seqpath
        ref()[QtCore.Qt.ToolTipRole] = seqpath
        ref()[QtCore.Qt.DisplayRole] = seqname
        ref()[QtCore.Qt.EditRole] = seqname
        ref()[common.SortByLastModifiedRole] = _mtime
        ref()[common.SortBySizeRole] = size
        ref()[common.FileDetailsRole] = info_string

    def _process_file_item(self, ref, item_type):
        if not self.is_valid(ref):
            return False
        if item_type != common.FileItem:
            return

        er = ref()[common.EntryRole]
        if not er:
            return

        size = 0
        if er:
            stat = er[0].stat()
            size = stat.st_size

        _mtime = stat.st_mtime
        mtime = _qlast_modified(_mtime)

        info_string = \
            mtime.toString('dd') + '/' + \
            mtime.toString('MM') + '/' + \
            mtime.toString('yyyy') + ' ' + \
            mtime.toString('hh') + ':' + \
            mtime.toString('mm') + ';' + \
            byte_to_pretty_string(size)

        if not self.is_valid(ref):
            return False
        ref()[common.SortByLastModifiedRole] = _mtime
        ref()[common.FileDetailsRole] = info_string
        ref()[common.SortBySizeRole] = size

    def count_items(self, ref, source):
        pass


class ThumbnailWorker(BaseWorker):
    """Thread worker responsible for creating and loading thumbnails.

    The resulting image data is saved in the `ImageCache` and used by the item
    delegates to paint thumbnails.

    """
    def is_valid(self, ref):
        return False if (
                not ref() or
                self.interrupt or
                ref()[common.ThumbnailLoaded] or
                ref()[common.FlagsRole] & common.MarkedAsArchived
        ) else True


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
        if not self.is_valid(ref):
            return False
        size = ref()[QtCore.Qt.SizeHintRole].height()
        if not self.is_valid(ref):
            return False
        _p = ref()[common.ParentPathRole]
        if not self.is_valid(ref):
            return False
        source = ref()[QtCore.Qt.StatusTipRole]

        # Resolve the thumbnail's path...
        destination = images.get_cached_thumbnail_path(
            _p[0],
            _p[1],
            _p[2],
            source,
        )

        with images.lock:
            # ...and use it to load the resource
            image = images.ImageCache.get_image(
                destination,
                int(size),
                force=True  # force=True will refresh the cache
            )

        # If the image successfully loads we can wrap things up here
        if image and not image.isNull():
            with images.lock:
                images.ImageCache.make_color(destination)
            return True

        try:
            # Otherwise, we will try to generate a thumbnail using OpenImageIO

            # If the items is a sequence, we'll use the first image of the
            # sequence to make the thumbnail.
            if not self.is_valid(ref):
                return False
            if ref()[common.TypeRole] == common.SequenceItem:
                if not self.is_valid(ref):
                    return False
                source = ref()[common.EntryRole][0].path.replace('\\', '/')

            with images.lock:
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
                with images.lock:
                    images.ImageCache.get_image(destination, int(size), force=True)
                    images.ImageCache.make_color(destination)
                return True

            # We should never get here ideally, but if we do we'll mark the item
            # with a bespoke 'failed' thumbnail
            fpath = common.get_rsc(f'{common.GuiResource}/failed.{common.thumbnail_format}')
            hash = common.get_hash(fpath)

            with images.lock:
                images.ImageCache.get_image(fpath, int(size), hash=hash)
                images.ImageCache.make_color(fpath, hash=hash)

            return True
        except TypeError:
            return False
        except:
            log.error('Failed to generate thumbnail')
            return False
        finally:
            if ref():
                ref()[common.ThumbnailLoaded] = True

    @common.error
    def queue_items(self, refs):
        v = common.settings.value(common.SettingsSection, common.DontGenerateThumbnailsKey)
        v = False if v is None else v
        if v:
            return None
        return super().queue_items(refs)


class TaskFolderWorker(InfoWorker):
    """Used by the TaskFolderModel to count the number of files in a folder."""

    def count_items(self, ref, source):
        count = 0
        for _ in self.item_generator(source):
            count += 1
            if count > 999:
                break

        if not self.is_valid(ref):
            return
        ref()[common.TodoCountRole] = count

    @classmethod
    def item_generator(cls, path):
        """Used to iterate over all files in a given folder.

        Yields:
            DirEntry:   A DirEntry instance.

        """
        try:
            it = os.scandir(path)
        except:
            return

        n = 0
        while True:
            n += 1
            if n > 9999:
                return

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
                for entry in cls.item_generator(entry.path):
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
            self.sgEntityDataReady.emit(idx, entities)
        except IndexError:
            pass  # ignore index errors
        except:
            raise
