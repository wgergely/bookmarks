"""Defines the base model used to display bookmark, asset and files items.

The model loads and reset data via the :meth:`ItemModel.init_data()` and
:meth:`ItemModel.reset_data()` methods.

The model itself does not store data, but all retrieved data is cached independently to
:attr:`bookmarks.common.item_data`. The interface for getting and
setting data can be found in the :mod:`bookmarks.common.data`. However, the model is
responsible for populating the data cache. See :meth:`.ItemModel.item_generator()`.

The model exposes different datasets to the view using the :meth:`ItemModel.task` and
:meth:`ItemModel.data_type` switches. This is because file items are stored as sequence
and individual items simultaneously and because the file model also keeps separate data
for each task folder it encounters.

The currently exposed data can be retrieved by :meth:`.ItemModel.model_data()`. To
change/set the data set emit the :attr:`.ItemModel.taskFolderChanged` and
:attr:`.ItemModel.dataTypeChanged` signals with their appropriate arguments.

Worth keeping in mind that Bookmarks loads data in two passes. The model is responsible
for discovering items, but will not populate all item the data, and instead uses helper
threads to offload work. The model's associated threads are defined by overriding
:attr:`.ItemModel.queues`.

Each base model is nested inside a QSortFilterProxy used for filtering **only**. Sorting
is implemented separately to run directly over the source data.

"""
import functools
import re
import uuid
import weakref

from PySide2 import QtWidgets, QtCore

from .. import common
from .. import images
from .. import importexport
from .. import log

MAX_HISTORY = 20
DEFAULT_ITEM_FLAGS = (
        QtCore.Qt.ItemNeverHasChildren |
        QtCore.Qt.ItemIsEnabled |
        QtCore.Qt.ItemIsEditable |
        QtCore.Qt.ItemIsSelectable |
        QtCore.Qt.ItemIsDropEnabled |
        QtCore.Qt.ItemIsDragEnabled
)

#: A default container used to sort items by name
DEFAULT_SORT_BY_NAME_ROLE = [str()] * 8


def initdata(func):
    """The decorator is responsible validating the current active paths, and emitting
    the ``beginResetModel``, ``endResetModel`` and :attr:`.ItemModel.coreDataLoaded`
    signals.

    """

    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
        """Func wrapper.

        """
        common.settings.load_active_values()

        self.beginResetModel()
        self._interrupt_requested = False
        self._load_in_progress = True

        try:
            func(self, *args, **kwargs)
        except:
            raise
        finally:
            self._interrupt_requested = False
            self._load_in_progress = False
            self.endResetModel()

        # Emit  references to the just loaded core data
        p = self.source_path()
        k = self.task()
        t1 = self.data_type()
        t2 = common.FileItem if t1 == common.SequenceItem else common.SequenceItem

        if all((p, k)):
            self.coreDataLoaded.emit(
                common.get_data_ref(p, k, t1),
                common.get_data_ref(p, k, t2),
            )

    return func_wrapper


@functools.lru_cache(maxsize=4194304)
def filter_includes_row(filter_text, searchable):
    """Checks if the filter string contains any double dashes (--) and if the filter
    text is found in the searchable string.

    If both true, the row will be hidden.

    """
    _filter_text = filter_text
    it = re.finditer(
        r'(--[^\"\'\[\]\*\s]+)',
        filter_text,
        flags=re.IGNORECASE | re.MULTILINE
    )
    it_quoted = re.finditer(
        r'(--".*?")',
        filter_text,
        flags=re.IGNORECASE | re.MULTILINE
    )

    for match in it:
        _filter_text = re.sub(match.group(1), '', _filter_text)
    for match in it_quoted:
        _filter_text = re.sub(match.group(1), '', _filter_text)

    for text in _filter_text.split():
        text = text.strip('"')
        if text not in searchable:
            return False
    return True


@functools.lru_cache(maxsize=4194304)
def _filter_excludes_row(filter_text, searchable):
    it = re.finditer(
        r'--([^\"\'\[\]\*\s]+)',
        filter_text,
        flags=re.IGNORECASE | re.MULTILINE
    )
    it_quoted = re.finditer(
        r'--"(.*?)"',
        filter_text,
        flags=re.IGNORECASE | re.MULTILINE
    )

    for match in it:
        if match.group(1).lower() in searchable:
            return True
    for match in it_quoted:
        if match.group(1).lower() in searchable:
            return True
    return False


class ItemModel(QtCore.QAbstractTableModel):
    """The base model used for interacting with all bookmark, asset and file items.

    Data is stored in the datacache module that can be fetched using the model's
    `source_path`, `task` and `data_type`.

    Attributes:

        coreDataLoaded (QtCore.Signal -> weakref.ref, weakref.ref): Signals that the
            bare model data finished loading and that threads can start loading
            missing data.
        coreDataReset (QtCore.Signal): Signals that the underlying model data has
            been reset. Used by the thread workers to empty their queues.
        dataTypeSorted (QtCore.Signal -> int): Signals that the underlying model
            data was sorted.
        sortingChanged (QtCore.Signal -> int, bool): Emitted when the sorting
            order or sorting role was changed by the user.
        activeChanged (QtCore.Signal): Signals :meth:`.ItemModel.active_index`
            change.
        dataTypeChanged (QtCore.Signal -> int): Emitted when the exposed data type
            changes, e.g. from ``FileItem`` to ``SequenceItem``.
        updateIndex (QtCore.Signal -> QtCore.QModelIndex): Emitted when an index
            repaint is requested.
        queues (tuple): A list of threads associated with the model.

    """
    coreDataLoaded = QtCore.Signal(weakref.ref, weakref.ref)
    coreDataReset = QtCore.Signal()

    dataTypeSorted = QtCore.Signal(int)
    sortingChanged = QtCore.Signal(int, bool)  # (SortRole, SortOrder)

    activeChanged = QtCore.Signal(QtCore.QModelIndex)
    dataTypeChanged = QtCore.Signal(int)

    # Update signals
    updateIndex = QtCore.Signal(QtCore.QModelIndex)

    queues = ()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = parent

        self._interrupt_requested = False
        self._load_in_progress = False
        self._load_message = ''
        self._generate_thumbnails = True
        self._task = None
        self._sort_by = None
        self._sort_order = None
        self.row_size = QtCore.QSize(self.default_row_size())

        self._datatype = {}  # used  by the files model only

        self.sortingChanged.connect(self.set_sorting)
        self.dataTypeSorted.connect(self.emit_reset_model)

        self.modelAboutToBeReset.connect(common.signals.updateTopBarButtons)
        self.modelReset.connect(common.signals.updateTopBarButtons)

    def rowCount(self, parent=QtCore.QModelIndex()):
        """The model's row count.

        """
        p = self.source_path()
        k = self.task()
        t = self.data_type()
        if not all((p, k)) or t is None:
            return 0
        return common.data_count(p, k, t)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """Number of columns the model has."""
        return 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """Returns and item data associated with the given index.

        """
        if not index.isValid():
            return None
        data = self.model_data()
        if index.column() == 0:
            if index.row() not in data:
                return None
            if role in data[index.row()]:
                return data[index.row()][role]

        # Return the column 0 flags for all columns
        if role == common.FlagsRole:
            if role in data[index.row()]:
                return data[index.row()][role]

        return None

    def setData(self, index, v, role=QtCore.Qt.DisplayRole):
        """

        """
        if not index.isValid():
            return False
        if index.column() != 0:
            return False

        data = self.model_data()
        if index.row() not in data:
            return False
        data[index.row()][role] = v
        self.dataChanged.emit(index, index)
        return True

    def headerData(self, idx, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.SizeHintRole:
                v = QtCore.QSize(common.size(common.size_margin), self.row_size.height())
                return v
        return None

    def flags(self, index):
        """Returns the item's flags.

        """
        v = self.data(index, role=common.FlagsRole)
        if not isinstance(v, QtCore.Qt.ItemFlags) or not v:
            return QtCore.Qt.NoItemFlags
        return v

    def parent(self, child):
        """The parent of an item.

        """
        return QtCore.QModelIndex()

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction

    def supportedDragActions(self):
        return QtCore.Qt.MoveAction

    def mimeData(self, indexes):
        """Returns the drag mime data for the given indexes.

        """
        mime = super().mimeData(indexes)
        index = next((f for f in indexes if f.column() == 0), None)
        path = index.data(common.PathRole)
        if not index.isValid() or not path:
            return QtCore.QMimeData()

        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier

        if no_modifier:
            return QtCore.QMimeData()

        if alt_modifier:
            b_path = QtCore.QByteArray(path.encode('utf-8'))
            mime.setData('application/item-property', b_path)
            return mime

        return QtCore.QMimeData()

    def canDropMimeData(self, mime, action, row, column, parent=QtCore.QModelIndex()):
        """Checks drop support for the given mime data.

        """
        if not self.supportedDropActions() & action:
            return False
        if self.can_drop_image_file(mime, action, row, column, parent):
            return True
        if self.can_drop_properties(mime, action, row, column, parent):
            return True
        return False

    def can_drop_image_file(self, mime, action, row, column, parent=QtCore.QModelIndex()):
        if mime.hasUrls():
            source = next(f for f in mime.urls())
            source = source.toLocalFile()
            if images.oiio_get_buf(source):
                images.ImageCache.flush(source)
                return True
        return False

    def can_drop_properties(self, mime, action, row, column, parent=QtCore.QModelIndex()):
        if 'application/item-property' in mime.formats():
            return True
        return False

    def dropMimeData(self, mime, action, row, column, parent):
        """Handles drop actions.

        """
        if not action & self.supportedDropActions():
            return False

        if self.can_drop_image_file(mime, action, row, column, parent):
            return self._drop_image_action(mime, action, row, column, parent)

        if self.can_drop_properties(mime, action, row, column, parent):
            return self._drop_properties_action(mime, action, row, column, parent)

        return False

    def _drop_image_action(self, mime, action, row, column, parent):
        """Handles an image drop.

        """
        image = next((f for f in mime.urls()), None)
        if not image:
            return False

        image = image.toLocalFile()
        if not images.oiio_get_buf(image):
            images.ImageCache.flush(image)
            return False

        index = self.index(row, 0)
        source = index.data(common.PathRole)

        proxy = bool(common.is_collapsed(source))
        server, job, root = index.data(common.ParentPathRole)[0:3]

        images.create_thumbnail_from_image(
            server,
            job,
            root,
            source,
            image,
            proxy=proxy
        )
        images.ImageCache.flush(image)
        return True

    def _drop_properties_action(self, mime, action, row, column, parent):
        b_path = mime.data('application/item-property')
        source_path = bytes(b_path).decode()

        temp_path = f'{common.temp_path()}/{uuid.uuid1().hex}.preset'

        data = self.model_data()
        for idx in data:
            if not data[idx][common.PathRole] == source_path:
                continue

            importexport.export_item_properties(
                self.index(idx, 0),
                destination=temp_path
            )
            importexport.import_item_properties(
                self.index(row, 0),
                source=temp_path,
                prompt=False
            )
            if not QtCore.QFile(temp_path).remove():
                log.error('Could not remove temp file.')
            return

    def item_generator(self):
        """A generator method used by :func:`init_data` to yield the items the model
        should load.

        Yields:
            DirEntry: os.scandir DirEntry objects.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    @common.debug
    @common.error
    @initdata
    def init_data(self):
        """The main method used by the model to fetch and store item information
        from the file system.

        The model itself does not store any data, instead, we're using the
        :mod:`bookmarks.common.data` module to store item data.

        The individual items are returned by :func:`item_generator`.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    @common.error
    @common.debug
    @QtCore.Slot()
    def reset_data(self, *args, force=False, emit_active=True):
        """Resets the model's internal data.

        The underlying data is cached in the :mod:`datacache` module, so here
        we'll make sure the data is available for the model to use. When the
        optional `force` flag is set, we'll use `init_data` to load the item
        data from disk.

        Otherwise, the method will check if our cached data is available and if
        not, uses `init_data` to fetch it.

        """
        common.check_type(force, bool)
        common.check_type(emit_active, bool)

        p = self.source_path()
        k = self.task()
        if not p or not all(p) or not k:
            return

        if force:
            common.reset_data(p, k)
            self.coreDataReset.emit()
            self.init_data()
            return

        d = common.get_task_data(p, k)
        if not d[common.FileItem]:
            self.coreDataReset.emit()
            self.init_data()

        # The let's signal the model reset and emit the current active index
        self.beginResetModel()
        self.endResetModel()
        index = self.active_index()
        if not index.isValid():
            return

        if emit_active:
            self.set_active(index)

    @QtCore.Slot(int)
    def emit_reset_model(self, data_type):
        """Slot used to emit the reset model signals.

        """
        if self.data_type() != data_type:
            return
        self.beginResetModel()
        self.endResetModel()

    @QtCore.Slot(bool)
    @QtCore.Slot(int)
    def set_sorting(self, role, order):
        """Slot responsible for setting the sort role, order and sorting the model
        data. Sorting is only possible when the model data is fully loaded.

        """
        if not self.is_data_type_loaded():
            return
        self.set_sort_by(role)
        self.set_sort_order(order)
        self.sort_data()

    def source_path(self):
        """Source path of the model data as a tuple of path segments.

        Returns:
            tuple: A tuple of path segments.

        """
        return ()

    def default_row_size(self):
        """Returns the default item size.

        """
        return QtCore.QSize(1, common.size(common.size_row_height))

    @common.debug
    @common.error
    def init_sort_values(self, *args, **kwargs):
        """Load the current sort role from the local preferences.

        """
        val = self.get_filter_setting('filters/sort_by')

        # Set default if an invalid value is encountered
        if val not in common.DEFAULT_SORT_VALUES:
            val = common.SortByNameRole
        # Let's make sure the type is correct
        if isinstance(val, int):
            val = QtCore.Qt.ItemDataRole(val)

        self._sort_by = val

        val = self.get_filter_setting('filters/sort_order')
        self._sort_order = val if isinstance(val, bool) else False

    @common.debug
    @common.error
    def init_row_size(self, *args, **kwargs):
        """Load the current row size from the user settings file.

        """
        val = self.get_filter_setting('filters/row_heights')
        h = self.default_row_size().height()
        val = h if val is None else val
        val = h if val < h else val
        val = int(common.thumbnail_size) if val >= int(
            common.thumbnail_size) else val
        self.row_size.setHeight(int(val))

    def sort_by(self):
        """Current sort role.

        """
        return self._sort_by

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def set_sort_by(self, val):
        """Sets and saves the sort by value."""
        if val == self.sort_by():
            return

        self._sort_by = val
        self.set_filter_setting('filters/sort_by', val)

    def sort_order(self):
        """The currently set order of the items e.g. 'descending'."""
        return self._sort_order

    @common.status_bar_message('Sorting items...')
    @common.debug
    @common.error
    @QtCore.Slot()
    def sort_data(self, *args, **kwargs):
        """Sorts the model data using the current sort order and role.

        """
        sort_by = self.sort_by()
        sort_order = self.sort_order()

        p = self.source_path()
        k = self.task()
        t1 = self.data_type()
        t2 = common.FileItem if t1 == common.SequenceItem else common.SequenceItem

        self.beginResetModel()
        try:
            for t in (t1, t2):
                ref = common.get_data_ref(p, k, t)
                if not ref():
                    continue
                d = common.sort_data(ref, sort_by, sort_order)
                common.set_data(p, k, t, d)
        except:
            log.error('Sorting error')
        finally:
            self.endResetModel()

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def set_sort_order(self, val):
        """Sets and saves the sort order.

        Args:
            val (int): The new sort order.

        """
        if val == self.sort_order():
            return

        self._sort_order = val
        self.set_filter_setting('filters/sort_order', val)

    @QtCore.Slot()
    def set_interrupt_requested(self):
        """Load interrupt requested by user.

        """
        self._interrupt_requested = True

    @QtCore.Slot(int)
    def is_data_type_loaded(self):
        """Checks whether the current data type is fully loaded.

        """
        p = self.source_path()
        k = self.task()
        t = self.data_type()

        if not p or not all(p) or not k or t is None:
            return False

        return common.is_data_loaded(p, k, t)

    def model_data(self):
        """The pointer to the model's internal data.

        """
        p = self.source_path()
        k = self.task()
        t = self.data_type()

        if not p or not all(p) or not k or t is None:
            return common.DataDict()

        return common.get_data(p, k, t)

    def _active_idx(self):
        data = self.model_data()
        if not data:
            return None
        for idx in data:
            if data[idx][common.FlagsRole] & common.MarkedAsActive:
                return idx
        return None

    def active_index(self):
        """The model's active_index.

        """
        idx = self._active_idx()
        if idx is None:
            return QtCore.QModelIndex()
        return self.index(idx, 0)

    def set_active(self, index):
        """Set the given index as the model's :meth:`.active_index`.

        """
        if not index.isValid():
            return

        self.unset_active()

        data = self.model_data()
        idx = index.row()
        data[idx][common.FlagsRole] = (
                data[idx][common.FlagsRole] | common.MarkedAsActive
        )

        self.save_active()
        self.updateIndex.emit(index)
        self.activeChanged.emit(index)

        common.signals.favouritesChanged.emit()

    def unset_active(self):
        """Remove the model's :meth:`.active_index`.

        """
        idx = self._active_idx()
        if idx is None:
            return

        data = self.model_data()
        data[idx][common.FlagsRole] = (
                data[idx][common.FlagsRole] & ~common.MarkedAsActive
        )

        index = self.index(idx, 0)
        self.updateIndex.emit(index)

        common.signals.favouritesChanged.emit()

    def save_active(self):
        """Saves the model's active item to the user preferences.

        """
        pass

    def data_type(self):
        """Current key to the data dictionary."""
        return common.FileItem

    def task(self):
        """The model's associated task.

        """
        return 'default'

    def filter_setting_dict_key(self):
        """The custom dictionary key used to save filter settings to the user settings
        file.

        See :meth:`.get_filter_setting()` and :meth:`set_filter_setting()`.

        Returns:
            str: The dictionary key.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    @common.error
    @common.debug
    def get_filter_setting(self, key):
        """Get a filter value stored in the user settings file.
        
        Each filter setting is associated with :meth:`filter_setting_dict_key` and stored
        in a dictionary object inside the user settings file.

        Args:
            key (str): Settings key type.

        Returns:
            The value saved in user settings, or `None` if not found.

        """
        dict_key = self.filter_setting_dict_key()
        if not dict_key:
            return None
        v = common.settings.value(key)
        if not isinstance(v, dict) or dict_key not in v:
            return None
        return v[dict_key]

    @common.error
    @common.debug
    def set_filter_setting(self, key, v):
        """Set a filter value in the user settings file.

        Args:
            key (str): A filter key.
            v (object): A filter value to store.

        """
        dict_key = self.filter_setting_dict_key()
        if not dict_key:
            return None
        _v = common.settings.value(key)
        _v = _v if _v else {}
        _v[dict_key] = v
        common.settings.setValue(key, _v)


class FilterProxyModel(QtCore.QSortFilterProxyModel):
    """Proxy model responsible for data filtering.

    We filter items using item flags defined in :mod:`bookmarks.common.core` and their
    display and description roles. Sorting is not implemented by this model, and instead is
    we're sorting the underlying data directly using :func:`common.data.sort_data`


    Attributes:
        filterFlagChanged (QtCore.Signal -> int, bool): Emitted when the user changes the
            current filter flags.
        filterTextChanged (QtCore.Signal -> str): Emitted when the user changes the current filter
            text.
        invalidated (QtCore.Signal): Emitted after the model has been reset or invalidated.

    """
    filterFlagChanged = QtCore.Signal(int, bool)  # FilterFlag, value
    filterTextChanged = QtCore.Signal(str)
    invalidated = QtCore.Signal()

    def __init__(self, parent=None):
        super(FilterProxyModel, self).__init__(parent=parent)
        self.setSortLocaleAware(False)
        self.setDynamicSortFilter(False)

        self.setFilterRole(common.PathRole)
        self.setSortCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitive)

        self.verify_items = common.Timer(parent=self)
        self.verify_items.setObjectName('VerifyVisibleItemsTimer')
        self.verify_items.setSingleShot(False)
        self.verify_items.setInterval(10)
        self.verify_items.timeout.connect(self.verify)

        self.queued_invalidate_timer = common.Timer()
        self.queued_invalidate_timer.setSingleShot(True)
        self.queued_invalidate_timer.setInterval(100)

        self._filter_text = None
        self._filter_flags = {
            common.MarkedAsActive: None,
            common.MarkedAsArchived: None,
            common.MarkedAsFavourite: None,
        }

        self.filterTextChanged.connect(self.invalidateFilter)
        self.filterFlagChanged.connect(self.invalidateFilter)

        self.modelAboutToBeReset.connect(self.verify_items.stop)
        self.modelReset.connect(self.verify_items.start)
        common.signals.databaseValueUpdated.connect(self.verify_items.start())
        self.modelReset.connect(self.invalidateFilter)

        self.filterTextChanged.connect(self.verify_items.start)
        self.filterFlagChanged.connect(self.verify_items.start)

        self.filterTextChanged.connect(common.signals.updateTopBarButtons)
        self.filterFlagChanged.connect(common.signals.updateTopBarButtons)
        self.modelReset.connect(common.signals.updateTopBarButtons)

        self.queued_invalidate_timer.timeout.connect(self.delayed_invalidate)

    def verify(self):
        """Verify the filter model contents to make sure archived items
        remain hidden when they're not meant to be visible.

        """
        if QtWidgets.QApplication.instance().mouseButtons() != QtCore.Qt.NoButton:
            return

        is_archived_visible = self.filter_flag(common.MarkedAsArchived)
        is_favourite_visible = self.filter_flag(common.MarkedAsFavourite)
        for n in range(self.rowCount()):
            index = self.index(n, 0)
            is_archived = index.flags() & common.MarkedAsArchived
            if is_archived and not is_archived_visible:
                self.invalidateFilter()
                return

            is_favourite = index.flags() & common.MarkedAsFavourite
            if not is_favourite and is_favourite_visible:
                self.invalidateFilter()
                return

        self.verify_items.stop()

    def invalidateFilter(self, *args, **kwargs):
        """Instead of calling invalidate directly, we'll pool consequent calls
        together.

        """
        self.queued_invalidate_timer.start(self.queued_invalidate_timer.interval())

    @QtCore.Slot()
    def delayed_invalidate(self, *args, **kwargs):
        """Slot called by the queued invalidate timer's timeout signal."""
        result = super(FilterProxyModel, self).invalidateFilter()
        self.invalidated.emit()
        return result

    def invalidate(self, *args, **kwargs):
        """Invalidates the filter.

        """
        result = super(FilterProxyModel, self).invalidate()
        self.invalidated.emit()
        return result

    def reset(self, *args, **kwargs):
        """Resets and invalidates the proxy model.

        """
        result = super(FilterProxyModel, self).reset()
        self.invalidated.emit()
        return result

    def sort(self, column, order=QtCore.Qt.AscendingOrder):
        """Disables sorting.

        """
        raise NotImplementedError('Sorting is not implemented.')

    @common.error
    @common.debug
    def init_filter_values(self, *args, **kwargs):
        """Load the saved widget filters from `user_settings`.

        This determines if e.g. archived items are visible in the view.

        """
        model = self.sourceModel()
        self._filter_text = model.get_filter_setting('filters/text')
        if self._filter_text is None:
            self._filter_text = ''

        v = model.get_filter_setting('filters/active')
        self._filter_flags[common.MarkedAsActive] = v if v is not None else False
        v = model.get_filter_setting('filters/archived')
        self._filter_flags[common.MarkedAsArchived] = v if v is not None else False
        v = model.get_filter_setting('filters/favourites')
        self._filter_flags[common.MarkedAsFavourite] = v if v is not None else False

    def filter_text(self):
        """Filters the list of items containing this path segment."""
        if self._filter_text is None:
            return ''
        return self._filter_text

    @QtCore.Slot(str)
    def set_filter_text(self, v):
        """Slot called when a filter text has been set by the filter text editor
        widget.

        """
        v = v if v is not None else ''
        v = str(v).strip()

        # Save the set text in the model
        self._filter_text = v

        # Save the text in the user settings file
        self.sourceModel().set_filter_setting('filters/text', v)
        self.save_history(v)
        self.filterTextChanged.emit(v)

    def save_history(self, v):
        """Saves the filter text history.

        """
        if not v:
            return

        _v = self.sourceModel().get_filter_setting('filters/text_history')
        _v = _v.split(';') if _v else []

        if v.lower() in [f.lower() for f in _v]:
            return

        _v.append(v)
        s = ';'.join(_v[0:MAX_HISTORY])
        self.sourceModel().set_filter_setting('filters/text_history', s)

    def filter_flag(self, flag):
        """Returns the current flag-filter."""
        return self._filter_flags[flag]

    @QtCore.Slot(int, bool)
    def set_filter_flag(self, flag, v):
        """Save a filter value to user settings.

        Args:
            flag (int): The flag to set.
            v (bool): The value to set.
        """
        if self._filter_flags[flag] == v:
            return
        self._filter_flags[flag] = v
        if flag == common.MarkedAsActive:
            self.sourceModel().set_filter_setting('filters/active', v)
        if flag == common.MarkedAsArchived:
            self.sourceModel().set_filter_setting('filters/archived', v)
        if flag == common.MarkedAsFavourite:
            self.sourceModel().set_filter_setting('filters/favourites', v)

    def filterAcceptsColumn(self, source_column, parent=QtCore.QModelIndex()):
        """Checks if the filter accepts the column.

        """
        return True

    def filterAcceptsRow(self, idx, parent=None):
        """Filters rows of the proxy model based on the current flags and
        filter string.

        """
        model = self.sourceModel()
        p = model.source_path()
        k = model.task()
        t = model.data_type()

        ref = common.get_data_ref(p, k, t)
        if not ref or not ref() or idx not in ref():
            return False

        flags = ref()[idx][common.FlagsRole]
        if not isinstance(flags, QtCore.Qt.ItemFlags):
            return False
        archived = flags & common.MarkedAsArchived
        if not ref():
            return False
        favourite = flags & common.MarkedAsFavourite
        if not ref():
            return False
        active = flags & common.MarkedAsActive
        if not ref():
            return False

        filter_text = self.filter_text()
        if filter_text:
            filter_text = filter_text.strip().lower()
            if not ref():
                return False
            d = ref()[idx][common.DescriptionRole]
            d = d.strip().lower() if d else ''

            if not ref():
                return False
            f = ref()[idx][common.FileDetailsRole]
            f = f.strip().lower() if f else ''

            if not ref():
                return False

            # Let's construct the string to be filtered. This will include
            # the path, display name and label text
            searchable = (
                f'{ref()[idx][QtCore.Qt.DisplayRole].lower()}\n'
                f'{ref()[idx][common.PathRole].lower()}\n'
                f'{d.strip().lower()}\n{f.strip().lower()}'
            )
            if not filter_includes_row(filter_text, searchable):
                return False
            if _filter_excludes_row(filter_text, searchable):
                return False

        if self.filter_flag(common.MarkedAsActive) and active:
            return True
        if self.filter_flag(common.MarkedAsActive) and not active:
            return False
        if archived and not self.filter_flag(common.MarkedAsArchived):
            return False
        if not favourite and self.filter_flag(common.MarkedAsFavourite):
            return False
        return True
