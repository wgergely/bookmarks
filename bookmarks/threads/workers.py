"""Defines :class:`bookmarks.threads.workers.BaseWorker`, the main thread worker base
class, and various other helper functions.

"""
import functools
import os
import uuid
import weakref

import bookmarks_openimageio
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
    elif threads.THREADS[q]['tab'] >= 0:
        idx = threads.THREADS[q]['tab']
        widget = common.widget(idx)
    else:
        widget = None
    return widget


def _model(q):
    widget = _widget(q)
    if widget is None:
        return None
    # Make sure the queue is associated with this widget
    if q not in widget.queues:
        return None
    return widget.model().sourceModel()


def _qlast_modified(n):
    return QtCore.QDateTime.fromMSecsSinceEpoch(int(n) * 1000)


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

            if ref().data_type in (common.FileItem, common.SequenceItem):
                # Mark the internal model loaded
                ref().loaded = True

                if not ref() or self.interrupt:
                    return

                # Sort the data
                data = self.sort_internal_data(ref)

                # Signal the world
                common.signals.internalDataReady.emit(weakref.ref(data))

                return

            if not ref() or self.interrupt:
                return

            # Call process_data
            result = func(self, ref)

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

    Each worker is associated with a thread controller and a data queue.
    See :mod:`bookmarks.threads.threads` for the definitions.

    """
    initWorker = QtCore.Signal()

    coreDataLoaded = QtCore.Signal(weakref.ref, weakref.ref)
    coreDataReset = QtCore.Signal()
    dataTypeAboutToBeSorted = QtCore.Signal(int)
    dataTypeSorted = QtCore.Signal(int)
    queueItems = QtCore.Signal(list)

    startTimer = QtCore.Signal()
    stopTimer = QtCore.Signal()

    refUpdated = QtCore.Signal(weakref.ref)
    databaseValueChanged = QtCore.Signal(str, str, str, object)

    sgEntityDataReady = QtCore.Signal(str, list)

    errorOccurred = QtCore.Signal(str)

    def __init__(self, queue, parent=None):
        super().__init__(parent=parent)

        self.setObjectName(f'{queue}Worker_{uuid.uuid1().hex}')

        self.interrupt = False
        self.queue_timer = None
        self.queue = queue

        self.initWorker.connect(self.init_worker)

    @common.error
    def init_worker(self):
        """Initialize the queue timer when the worker has been moved to the
        correct thread.

        """
        verify_thread_affinity()

        from . import threads

        self.queue_timer = common.Timer(parent=self)
        self.queue_timer.setObjectName(f'{self.queue}Timer_{uuid.uuid1().hex}')
        self.queue_timer.setInterval(1)

        # Local direct worker signal connections
        cnx = QtCore.Qt.DirectConnection

        self.startTimer.connect(self.queue_timer.start, cnx)
        self.stopTimer.connect(self.queue_timer.stop, cnx)

        self.queueItems.connect(self.queue_items, cnx)

        self.coreDataReset.connect(self.clear_queue, cnx)
        self.coreDataLoaded.connect(self.queue_model, cnx)

        self.queue_timer.timeout.connect(self.process_data, cnx)

        self.databaseValueChanged.connect(self.update_changed_database_value, cnx)

        q = self.queue
        cnx = QtCore.Qt.QueuedConnection
        widget = _widget(q)
        model = _model(q)

        # Timer controls
        threads.get_thread(self.queue).startTimer.connect(self.startTimer, cnx)
        threads.get_thread(self.queue).stopTimer.connect(self.stopTimer, cnx)

        # If the queue type allows preloading the model, queue all
        # model data when the core data has been loaded in the gui thread
        if widget:
            widget.queueItems.connect(self.queueItems, cnx)
            model.coreDataReset.connect(self.coreDataReset, cnx)
            self.refUpdated.connect(widget.refUpdated, cnx)

        if threads.THREADS[q]['preload'] and model and widget:
            model.coreDataLoaded.connect(self.coreDataLoaded, cnx)

            self.dataTypeAboutToBeSorted.connect(model.internal_data_about_to_be_sorted, cnx)
            self.dataTypeSorted.connect(model.internal_data_sorted, cnx)

            common.signals.databaseValueChanged.connect(self.databaseValueChanged, cnx)

        self.sgEntityDataReady.connect(common.signals.sgEntityDataReady, cnx)

    def update_changed_database_value(self, table, source, key, value):
        """Process changes when a database value changes.

        Args:
            table (str): The database table.
            source (str): A file path.
            key (str): The database value key (column).
            value (object): The value to set.

        Returns:
            type: Description of the returned object.

        """
        verify_thread_affinity()

        from . import threads
        if not threads.THREADS[self.queue]['preload']:
            return

        _source = common.proxy_path(source)
        file_item = common.get_data_from_value(
            _source,
            common.FileItem,
            role=common.PathRole,
            get_container=False
        )
        if file_item:
            file_item[common.FileInfoLoaded] = False
            threads.THREADS[self.queue]['queue'].append(weakref.ref(file_item))

        seq_item = common.get_data_from_value(
            _source,
            common.SequenceItem,
            role=common.PathRole,
            get_container=False
        )
        if seq_item:
            seq_item[common.FileInfoLoaded] = False
            threads.THREADS[self.queue]['queue'].append(weakref.ref(seq_item))

        if any((file_item, seq_item)):
            self.queue_timer.start()

    @common.error
    def queue_items(self, refs):
        """Queues the given list of weakrefs to the workers' associated queue.

        Args:
            refs (list or tuple): A list of ``weakref.ref`` instances.

        """
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
        """Queues the data items of the given list model.

        This method is used by the file item model and queues individual files and
        collapsed sequence items of the given model.
        """
        from . import threads

        q = self.queue

        # Skip if the model is not meant to be preloaded by the worker
        if not threads.THREADS[q]['preload']:
            return

        # Skip if the worker is not associated with a tab
        if threads.THREADS[q]['tab'] == -1:
            return

        role = threads.THREADS[q]['role']
        for ref in (data_type_ref1, data_type_ref2):
            if not ref():
                continue

            if ref().loaded:
                continue  # Skip if the model is loaded already

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
    def sort_internal_data(self, ref):
        """Sorts the data of the given data type.

        Args:
            ref (weakref.ref): A weakref to the data type.

        """
        verify_thread_affinity()

        model = _model(self.queue)
        if not model:
            return None

        sort_by = model.sort_by()
        sort_order = model.sort_order()

        p = model.parent_path()
        k = model.task()
        t = ref().data_type

        if not ref():
            return None

        if model.data_type() == t:
            self.dataTypeAboutToBeSorted.emit(t)

        d = common.sort_data(ref, sort_by, sort_order)

        if not ref():
            return None

        data = common.set_data(p, k, t, d)

        if model.data_type() == t:
            self.dataTypeSorted.emit(t)

        return data

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
        """Processes the given data item.

        Args:
            ref (weakref.ref): A data item.

        """
        # Do nothing by default
        if not ref() or self.interrupt:
            return False
        return True


def count_todos(asset_row_data):
    """Get the number of TODO items."""
    v = asset_row_data['notes']
    return len(v) if isinstance(v, dict) else 0


def count_assets(path):
    """Get the number of asset items.

    """
    n = 0

    if not os.path.isdir(path):
        return n

    with os.scandir(path) as it:
        for entry in it:
            if entry.name.startswith('.'):
                continue
            if not entry.is_dir():
                continue
            path = entry.path.replace('\\', '/')
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
    sep = '/'
    try:
        v = {}
        for k in ('description', 'width', 'height', 'framerate', 'prefix'):
            _v = bookmark_row_data[k]
            _v = _v if _v else None
            v[k] = _v

        description = f'{sep}{v["description"]}' if v['description'] else ''
        width = v['width'] if (v['width'] and v['height']) else ''
        height = f'*{v["height"]}' if (v['width'] and v['height']) else ''
        framerate = f'{sep}{v["framerate"]}fps' if v['framerate'] else ''

        s = f'{description}{sep}{width}{height}{framerate}'
        s = s.replace(sep + sep, sep)
        s = s.strip(sep).strip()
        return s
    except:
        log.error(__name__, 'Could not get description.')
        return ''


def get_ranges(arr, padding):
    """Given an array of numbers the method will return a string representation of
    the ranges contained in the array.

    Args:
        arr(list): An array of numbers.
        padding(int): The number of leading zeros before the number.

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
    return ','.join(['-'.join(sorted({blocks[k][0], blocks[k][-1]})) for k in blocks])


def update_sg_configured(pp, b, a, ref):
    """Slot called when a shotgun integration value was updated.

    """
    if not all((pp, b, a, ref())):
        return
    b_conf = (b['sg_domain'], b['sg_scriptname'], b['sg_api_key'])
    b_item_conf = (b['sg_id'], b['sg_name'], b['sg_type'])
    if len(pp) == 3:
        if all(b_conf + b_item_conf):
            ref()[common.SGLinkedRole] = True
            return True
    if len(pp) == 4:
        a_item_conf = (a['sg_id'], a['sg_name'], a['sg_type'])
        if all(b_conf + b_item_conf + a_item_conf):
            ref()[common.SGLinkedRole] = True
            return True

    ref()[common.SGLinkedRole] = False
    return False


class InfoWorker(BaseWorker):
    """A worker used to retrieve file information.

    We will query the file system for file size, and the bookmark database
    for the description, and file flags.

    """

    def is_valid(self, ref):
        return False if (not ref() or self.interrupt or ref()[common.FileInfoLoaded]) else True

    @process
    @common.error
    @QtCore.Slot(weakref.ref)
    def process_data(self, ref):
        """Populates the item with the missing file information.

        Args:
            ref (weakref.ref): A data item as created by the :meth:`bookmarks.items.models.ItemModel.init_data` method.

        Returns:
            bool: `True` on success, `False` otherwise.

        """
        if not self.is_valid(ref):
            return False

        try:
            self._process_data(ref)
            return True
        except TypeError:
            if ref():
                self.errorOccurred.emit('The worker failed to process an item.')
                log.error(f'Failed to process item.')
            return False
        except:
            self.errorOccurred.emit('The worker failed to process an item.')
            log.error(f'Failed to process item.')
            return False
        finally:
            if ref():
                ref()[common.FileInfoLoaded] = True

    def _process_data(self, ref):
        """Utility method for :meth:`process_data`.

        Args:
            ref (weakref.ref): A data item as created by the :meth:`bookmarks.items.models.ItemModel.init_data`.

        """
        pp = ref()[common.ParentPathRole]
        st = ref()[common.PathRole]
        if not pp or not st:
            raise RuntimeError('Failed to process item.')

        # Normalize and convert st to an absolute path
        st = os.path.abspath(os.path.normpath(st)).replace('\\', '/')
        ref()[common.PathRole] = st

        flags = ref()[common.FlagsRole]
        item_type = ref()[common.DataTypeRole]

        # Load values from the database
        db = database.get(*pp[0:3])

        _proxy_flags = 0
        proxy_k = None

        # Get the sequence proxy path if the item is collapsed
        if len(pp) > 4:
            collapsed = common.is_collapsed(st)
            proxy_k = common.proxy_path(st)
            proxy_k = os.path.abspath(os.path.normpath(proxy_k)).replace('\\', '/')
            k = proxy_k if collapsed else st
        else:
            k = st

        # Now normalize and convert k to an absolute path
        k = os.path.abspath(os.path.normpath(k)).replace('\\', '/')

        asset_row_data = db.get_row(k, database.AssetTable)
        bookmark_row_data = db.get_row(db.source(), database.BookmarkTable)
        bookmark_row_data['description'] = common.sanitize_hashtags(asset_row_data['description'])

        if len(pp) > 4:
            _proxy_flags = db.value(proxy_k, 'flags', database.AssetTable)

        # Description
        if len(pp) > 3:
            if asset_row_data:
                _h = common.sanitize_hashtags(asset_row_data['description'])
                ref()[common.DescriptionRole] = _h
                ref()[common.FilterTextRole] += '\n' + _h

        # Asset Progress Data
        if len(pp) == 4 and asset_row_data and asset_row_data.get('progress'):
            ref()[common.AssetProgressRole] = asset_row_data['progress']

        # Asset entry data
        if len(pp) == 4:
            ref()[common.EntryRole].append(
                common.get_entry_from_path(
                    ref()[common.PathRole],
                    is_dir=True,
                    force_exists=True
                )
            )

        # Asset ShotGrid task to list
        if (
                len(pp) == 4 and
                asset_row_data and
                asset_row_data.get('sg_task_name') and
                not asset_row_data['flags'] & common.MarkedAsArchived
        ):
            if ref():
                _ref = ref()[common.DataDictRole]

                if _ref():
                    if asset_row_data['sg_task_name'] and asset_row_data['sg_task_name'] not in _ref().sg_task_names:
                        _ref().sg_task_names.append(asset_row_data['sg_task_name'])

                    if asset_row_data['sg_name'] and asset_row_data['sg_name'] not in _ref().sg_names:
                        _ref().sg_names.append(asset_row_data['sg_name'])

        # ShotGrid status
        if len(pp) <= 4:
            update_sg_configured(pp, bookmark_row_data, asset_row_data, ref)

        # Note count
        if asset_row_data:
            ref()[common.NoteCountRole] = count_todos(asset_row_data)

        # Flags
        if asset_row_data:
            _flags = asset_row_data['flags']
        else:
            _flags = 0
        flags |= _flags if _flags else 0
        if len(pp) > 4:
            flags |= _proxy_flags if _proxy_flags else 0
        ref()[common.FlagsRole] = QtCore.Qt.ItemFlags(flags)

        self._process_bookmark_item(ref, db.source(), bookmark_row_data, pp)
        self._process_file_item(ref, item_type)
        self._process_sequence_item(ref, item_type)

        # Add sequence tokens to file items
        if item_type == common.FileItem and len(pp) > 4 and common.get_sequence(st):
            _, h = common.split_text_and_hashtags(db.value(proxy_k, 'description', database.AssetTable))
            _v = ref()[common.DescriptionRole]
            __h = common.sanitize_hashtags(f'{_v if _v else ""}  {h if h else ""}').strip()
            ref()[common.DescriptionRole] = __h
            ref()[common.FilterTextRole] += '\n' + __h

    def _process_bookmark_item(self, ref, source, bookmark_row_data, pp):
        if not self.is_valid(ref):
            return False

        if len(pp) != 3:
            return

        description = get_bookmark_description(bookmark_row_data)
        count = count_assets(source)

        if not self.is_valid(ref):
            return False
        ref()[common.AssetCountRole] = count
        ref()[common.SortBySizeRole] = count
        ref()[common.DescriptionRole] = description
        ref()[common.FilterTextRole] += '\n' + description
        ref()[QtCore.Qt.ToolTipRole] = description

    def _process_sequence_item(self, ref, item_type):
        if not self.is_valid(ref):
            return False
        if item_type != common.SequenceItem:
            return

        seq = ref()[common.SequenceRole]
        frs = sorted(ref()[common.FramesRole], key=lambda x: int(x))
        ref()[common.FramesRole] = frs

        er = ref()[common.EntryRole]
        size = ref()[common.SortBySizeRole]

        intframes = [int(f) for f in frs]
        padding = len(frs[0])
        rangestring = get_ranges(intframes, padding)

        # Construct paths and normalize them
        startpath = common.normalize_path(
            seq.group(1) + str(min(intframes)).zfill(padding) + seq.group(3) + '.' + seq.group(4))
        endpath = common.normalize_path(
            seq.group(1) + str(max(intframes)).zfill(padding) + seq.group(3) + '.' + seq.group(4))
        seqpath = common.normalize_path(
            seq.group(1) + common.SEQSTART + rangestring + common.SEQEND + seq.group(3) + '.' + seq.group(4))

        # Compute relative path for display name
        try:
            source_path = '/'.join(ref()[common.ParentPathRole][0:5])
            seqname = os.path.relpath(seqpath, source_path).replace('\\', '/')
            if '..' in seqname or seqname.startswith('.'):
                seqname = os.path.basename(seqpath)
        except Exception as e:
            log.error(f'Failed to compute relative path: {e}')
            seqname = os.path.basename(seqpath)

        _mtime = 0
        info_string = ''
        if er:
            for entry in er:
                stat = entry.stat()
                size += stat.st_size
                _mtime = max(_mtime, stat.st_mtime)

            mtime = _qlast_modified(_mtime)
            info_string += f"{len(intframes)}f;{mtime.toString('dd/MM/yyyy hh:mm')};{common.byte_to_pretty_string(size)}"

        # Setting the path names
        if not self.is_valid(ref):
            return False

        ref()[common.StartPathRole] = startpath
        ref()[common.EndPathRole] = endpath
        ref()[common.PathRole] = seqpath
        #
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
        if not er or not all(er):
            return

        stat = er[0].stat()
        size = stat.st_size

        _mtime = stat.st_mtime
        mtime = _qlast_modified(_mtime)

        info_string = f"{mtime.toString('dd/MM/yyyy hh:mm')};{common.byte_to_pretty_string(size)}"

        if not self.is_valid(ref):
            return False
        ref()[common.SortByLastModifiedRole] = _mtime
        ref()[common.FileDetailsRole] = info_string
        ref()[common.SortBySizeRole] = size


class ThumbnailWorker(BaseWorker):
    """Thread worker responsible for creating and loading thumbnails.

    The resulting image data is saved in the `ImageCache` and used by the item
    delegates to paint thumbnails.

    """

    def is_valid(self, ref):
        return False if (not ref() or self.interrupt or ref()[common.ThumbnailLoaded] or ref()[
            common.FlagsRole] & common.MarkedAsArchived or ref()[common.ItemTabRole] != common.FileTab) else True

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
            ref (weakref.ref): A data item as created by the :meth:`bookmarks.items.models.ItemModel.init_data` method.

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
        source = ref()[common.PathRole]

        # A hard-coded exception for Royal Render's broken files
        if '_broken__' in source:
            return False

        # Check the file extension
        ext = QtCore.QFileInfo(source).suffix().lower()
        if ext not in images.get_oiio_extensions():
            return True

        # Resolve the thumbnail's path...
        destination = images.get_cached_thumbnail_path(_p[0], _p[1], _p[2], source, )
        # ...and use it to load the resource
        image = images.ImageCache.get_image(
            destination, int(size), force=True
        )

        # If the items is a sequence, use the first image of to make the thumbnail
        if not self.is_valid(ref):
            return False

        if ref()[common.DataTypeRole] == common.SequenceItem:
            if not self.is_valid(ref):
                return False
            source = ref()[common.EntryRole][0].path.replace('\\', '/')

        # If the thumbnail successfully loads, there's a previously generated image.
        # Let's check it against the source to make sure it's still valid.
        if image and not image.isNull():
            res = bookmarks_openimageio.is_up_to_date(source, destination)
            if res == 1:
                images.make_color(destination)
                return True
            else:
                images.ImageCache.flush(destination)

        # Skip if the file is too large
        if QtCore.QFileInfo(source).size() >= pow(1024, 3) * 2:
            return True

        try:
            error = bookmarks_openimageio.convert_image(
                source,
                destination,
                source_color_space='',
                target_color_space='sRGB',
                size=int(common.Size.Thumbnail(apply_scale=False)),
            )
            images.ImageCache.flush(source)

            if error != 1:
                images.ImageCache.get_image(destination, int(size), force=True)
                images.make_color(destination)
                return True

            fpath = common.rsc(f'{common.GuiResource}/failed.{common.thumbnail_format}')
            hash = common.get_hash(destination)

            images.ImageCache.get_image(fpath, int(size), hash=hash, force=True)
            images.ImageCache.setValue(hash, common.Color.DarkBackground(), images.ColorType)
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
        v = common.settings.value('settings/disable_oiio')
        v = False if v is None else v
        if v:
            return None
        return super().queue_items(refs)


class TransactionsWorker(BaseWorker):
    """This worker processes database transactions.

    """

    @common.error
    def process_data(self, *args, **kwargs):
        verify_thread_affinity()

        if self.interrupt:
            return

        from . import threads

        try:
            args = threads.queue(self.queue).pop()
            database.set_flag(*args)
        except IndexError:
            pass  # ignore index errors


class SGWorker(BaseWorker):
    """This worker is used to retrieve data from ShotGrid."""

    @common.error
    def process_data(self, *args, **kwargs):
        verify_thread_affinity()

        if self.interrupt:
            return

        from . import threads

        try:
            args = threads.queue(self.queue).pop()
            idx, server, job, root, asset, user, entity_type, filters, fields = args

            # We'll favor the user's credentials if they exist
            login = common.settings.value('sg_auth/login')
            password = common.settings.value('sg_auth/password')
            auth_as_user = login and password

            sg_properties = shotgun.SGProperties(server, job, root, asset, auth_as_user=auth_as_user)
            sg_properties.init()

            if not sg_properties.verify(connection=True):
                return

            sg = shotgun.get_sg(
                sg_properties.domain,
                login if auth_as_user else sg_properties.script,
                password if auth_as_user else sg_properties.key,
                auth_as_user=auth_as_user
            )

            if entity_type == 'Status':
                from ..shotgun import actions as sg_actions
                entities = sg_actions.get_status_codes(sg)
            else:
                entities = sg.find(entity_type, filters, fields)

            # Sort the entities by code or name
            def key(x):
                if 'code' in x:
                    return x['code']
                elif 'name' in x:
                    return x['name']
                elif 'content' in x:
                    return x['content']
                elif 'id' in x:
                    return x['id']
                else:
                    return str(x)

            try:
                entities = sorted(entities, key=key)
            except:
                log.error('Could not sort entities')

            # Emit the retrieved data so the ui components can fetch it
            self.sgEntityDataReady.emit(idx, entities)
        except IndexError:
            pass  # ignore index errors
        except Exception as e:
            log.error(f'Error: {e}')
