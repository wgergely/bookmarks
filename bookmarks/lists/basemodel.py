"""Defines the base model used to display bookmark, asset and files items.

The model loads and reset data via the :meth:`BaseModel.init_data()` and :meth:`BaseModel.reset_data()`
methods.


The model itself does not store data, but all retrieved data is cached to
:attr:`bookmarks.common.item_data`. The interface for getting and setting data can be found in the
:mod:`bookmarks.common.data`. However, the model is responsible for populating the data cache. See
:meth:`.BaseModel.item_generator()`.


The model exposes different datasets to the view using the :meth:`BaseModel.task` and
:meth:`BaseModel.data_type` switches. This is because file items are stored as sequence and individual items
simultaneously and because the file model also keeps separate data for each task folder it encounters.

The currently exposed data can be retrieved by `BaseModel.model_data()`. To change/set the data set emit
the :attr:`.BaseModel.taskFolderChanged` and :attr:`.BaseModel.dataTypeChanged` signals with their
appropriate arguments.

Actually, Bookmarks loads data in two passes. The model is responsible for discovering items,
but will not populate the items with all the data, and instead we offload that onto threads.
The model's associated threads are defined by overriding :attr:`.BaseModel.queues`.

The base model implements data sorting via :meth:`BaseModel.sort_data` but the filtering
is done using :class:`.FilterProxyModel`.

"""
import functools
import re
import weakref

from PySide2 import QtWidgets, QtCore

from .. import common
from .. import images
from .. import log

MAX_HISTORY = 20
DEFAULT_ITEM_FLAGS = (
        QtCore.Qt.ItemNeverHasChildren |
        QtCore.Qt.ItemIsEnabled |
        QtCore.Qt.ItemIsSelectable
)


def initdata(func):
    """Wraps `init_data` calls.

    The decorator is responsible validating the current active paths, and emitting the ``beginResetModel``,
    ``endResetModel`` and :attr:`.BaseModel.coreDataLoaded` signals.

    """

    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
        common.settings.load_active_values()

        self.beginResetModel()
        self._interrupt_requested = False
        self._load_in_progress = True
        func(self, *args, **kwargs)
        self._interrupt_requested = False
        self._load_in_progress = False
        self.endResetModel()

        # Emit  references to the just loaded core data
        p = self.source_path()
        k = self.task()
        t1 = self.data_type()
        t2 = common.FileItem if t1 == common.SequenceItem else common.SequenceItem

        self.coreDataLoaded.emit(
            common.get_data_ref(p, k, t1),
            common.get_data_ref(p, k, t2),
        )

    return func_wrapper


class BaseModel(QtCore.QAbstractListModel):
    """The base model used for interacting with all bookmark, asset and file items.

    Data is stored in the datacache module that can be fetched using the model's
    `source_path`, `task` and `data_type`.

    Attributes:

        coreDataLoaded (QtCore.Signal -> weakref.ref, weakref.ref): Signals that the
            bare model data finished loading and that threads can start loading
            missing data.
        coreDataReset (QtCore.Signal):  Signals that the underlying model data has
            been reset. Used by the thread workers to empty their queues.
        dataTypeSorted (QtCore.Signal -> int):  Signals that the underlying model
            data was sorted.
        sortingChanged (QtCore.Signal -> int, bool): Emitted when the sorting
            order or sorting role was changed by the user.
        activeChanged (QtCore.Signal):  Signals :meth:`.BaseModel.active_index`
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
        self._sort_role = None
        self._sort_order = None
        self._row_size = QtCore.QSize(self.default_row_size())

        self._datatype = {}  # used  by the files model only

        self.sortingChanged.connect(self.set_sorting)
        self.dataTypeSorted.connect(self.emit_reset_model)

        self.modelAboutToBeReset.connect(common.signals.updateButtons)
        self.modelReset.connect(common.signals.updateButtons)

        self.init_sort_values()
        self.init_row_size()

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
        :mod:`datacache` module to store item data.

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

    def row_size(self):
        return self._row_size

    @QtCore.Slot(int)
    def emit_reset_model(self, data_type):
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
        if not self.is_data_type_loaded(self.data_type()):
            return
        self.set_sort_role(role)
        self.set_sort_order(order)
        self.sort_data()

    def source_path(self):
        """Source path of the model data as a tuple of path segments.

        Returns:
            tuple: A tuple of path segments.

        """
        return ()

    def default_row_size(self):
        return QtCore.QSize(1, common.size(common.HeightRow))

    @common.debug
    @common.error
    def init_sort_values(self, *args, **kwargs):
        """Load the current sort role from the local preferences.

        """
        val = self.get_local_setting(
            common.CurrentSortRole,
            key=self.__class__.__name__,
            section=common.UIStateSection
        )

        # Set default if an invalid value is encountered
        if val not in common.DEFAULT_SORT_VALUES:
            val = common.SortByNameRole
        # Let's make sure the type is correct
        if isinstance(val, int):
            val = QtCore.Qt.ItemDataRole(val)

        self._sort_role = val

        val = self.get_local_setting(
            common.CurrentSortOrder,
            key=self.__class__.__name__,
            section=common.UIStateSection
        )
        self._sort_order = val if isinstance(val, bool) else False

    @common.debug
    @common.error
    def init_row_size(self, *args, **kwargs):
        val = self.get_local_setting(
            common.CurrentRowHeight,
            section=common.UIStateSection
        )

        h = self.default_row_size().height()
        val = h if val is None else val
        val = h if val < h else val
        val = int(common.thumbnail_size) if val >= int(
            common.thumbnail_size) else val

        self._row_size.setHeight(val)

    def sort_role(self):
        return self._sort_role

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def set_sort_role(self, val):
        """Sets and saves the sort-key."""
        if val == self.sort_role():
            return

        self._sort_role = val
        self.set_local_setting(
            common.CurrentSortRole,
            val,
            key=self.__class__.__name__,
            section=common.UIStateSection
        )

    def sort_order(self):
        """The currently set order of the items eg. 'descending'."""
        return self._sort_order

    @common.status_bar_message('Sorting items...')
    @common.debug
    @common.error
    @QtCore.Slot()
    def sort_data(self, *args, **kwargs):
        """Sorts the model data using the current sort order and role."""
        sort_role = self.sort_role()
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
                d = common.sort_data(ref, sort_role, sort_order)
                common.set_data(p, k, t, d)
        except:
            log.error('Sorting error')
        finally:
            self.endResetModel()

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def set_sort_order(self, val):
        """Sets and saves the sort-key."""
        if val == self.sort_order():
            return

        self._sort_order = val
        self.set_local_setting(
            common.CurrentSortOrder,
            val,
            key=self.__class__.__name__,
            section=common.UIStateSection
        )

    @QtCore.Slot()
    def set_interrupt_requested(self):
        self._interrupt_requested = True

    @QtCore.Slot(int)
    def is_data_type_loaded(self, t):
        """Check if the given data type is loaded."""
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

    def save_active(self):
        """Saves the model's active item to the user preferences.

        """
        pass

    def data_type(self):
        """Current key to the data dictionary."""
        return common.FileItem

    def task(self):
        """The model's task folder. """
        return 'default'

    def user_settings_key(self):
        """Get the key used to by :meth:`.get_local_setting()` and :meth:`set_local_setting()`.

        Returns:
            str: A user_settings key value.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    def get_local_setting(self, key_type, key=None, section=common.ListFilterSection):
        """Get a value stored in the user settings.

        Args:
            key_type (str): A filter key type.
            key (str): A key the value is associated with.
            section (str): A settings `section`. Defaults to `common.ListFilterSection`.

        Returns:
            The value saved in `user_settings`, or `None` if not found.

        """
        key = key if key else self.user_settings_key()
        if not key:
            return None
        if not isinstance(key, str):
            key = key.decode('utf-8')
        k = '{}/{}'.format(key_type, common.get_hash(key))
        return common.settings.value(section, k)

    @common.error
    @common.debug
    def set_local_setting(self, key_type, v, key=None,
                          section=common.ListFilterSection):
        """Set a value to store in `user_settings`.

        Args:
            key_type (str): A filter key type.
            v (any):    A value to store.
            key (type): A key the value is associated with.
            section (type): A settings `section`. Defaults to `common.ListFilterSection`.

        """
        key = key if key else self.user_settings_key()
        if not key:
            return None
        k = f'{key_type}/{common.get_hash(key)}'
        common.settings.setValue(section, k, v)

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return False
        if index.row() not in self.model_data():
            return False
        data = self.model_data()
        data[index.row()][role] = data
        self.dataChanged.emit(index, index)
        return True

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction

    def canDropMimeData(self, data, action, row, column,
                        parent=QtCore.QModelIndex()):
        if not self.supportedDropActions() & action:
            return False
        if row == -1:
            return False

        if not data.hasUrls():
            return False
        else:
            source = data.urls()[0].toLocalFile()
            if not images.oiio_get_buf(source):
                return False

        data = self.model_data()
        if row not in data:
            return False
        if data[row][common.FlagsRole] & common.MarkedAsArchived:
            return False
        return True

    def dropMimeData(self, data, action, row, column, parent=QtCore.QModelIndex()):
        image = data.urls()[0].toLocalFile()
        if not images.oiio_get_buf(image):
            return False

        index = self.index(row, 0)
        source = index.data(QtCore.Qt.StatusTipRole)

        proxy = bool(common.is_collapsed(source))
        server, job, root = index.data(common.ParentPathRole)[0:3]
        images.load_thumbnail_from_image(
            server, job, root, source, image, proxy=proxy)

        return True

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        p = self.source_path()
        k = self.task()
        t = self.data_type()
        if not all((p, k)) or t is None:
            return 0
        return common.data_count(p, k, t)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        p = self.source_path()
        k = self.task()
        t = self.data_type()

        if not p or not all(p) or not k or t is None:
            return QtCore.QModelIndex()

        data = common.get_data(p, k, t)

        if row not in data:
            return QtCore.QModelIndex()

        ptr = weakref.ref(data[row])
        return self.createIndex(row, 0, ptr=ptr)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        data = self.model_data()
        if index.row() not in data:
            return None
        if role in data[index.row()]:
            return data[index.row()][role]

    def flags(self, index):
        v = self.data(index, role=common.FlagsRole)
        if not isinstance(v, QtCore.Qt.ItemFlags) or not v:
            return QtCore.Qt.NoItemFlags
        return v

    def parent(self, child):
        return QtCore.QModelIndex()


class FilterProxyModel(QtCore.QSortFilterProxyModel):
    """Proxy model responsible for **filtering** data for the view.

    We can filter items based on the data contained in the
    ``QtCore.Qt.StatusTipRole``, ``common.DescriptionRole`` and
    ``common.FileDetailsRole`` roles. Furthermore, based on flag values
    (``MarkedAsArchived``, ``MarkedAsActive``, ``MarkedAsFavourite`` are implemented.)

    Because of perfomarnce snags, sorting function are not implemented in the proxy
    model, rather in the source ``BaseModel``.

    Signals:
        filterFlagChanged (QtCore.Signal):  The signal emitted when the user changes a filter view setting
        filterTextChanged (QtCore.Signal):  The signal emitted when the user changes the filter text.

    """
    filterFlagChanged = QtCore.Signal(int, bool)  # FilterFlag, value
    filterTextChanged = QtCore.Signal(str)
    invalidated = QtCore.Signal()

    def __init__(self, parent=None):
        super(FilterProxyModel, self).__init__(parent=parent)
        self.setSortLocaleAware(False)
        self.setDynamicSortFilter(False)

        self.setFilterRole(QtCore.Qt.StatusTipRole)
        self.setSortCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitive)

        self.verify_items = common.Timer(parent=self)
        self.verify_items.setObjectName('VerifyVisibleItemsTimer')
        self.verify_items.setSingleShot(False)
        self.verify_items.setInterval(10)
        self.verify_items.timeout.connect(self.verify)

        self.queued_invalidate_timer = common.Timer()
        self.queued_invalidate_timer.setSingleShot(True)
        self.queued_invalidate_timer.setInterval(150)

        self.parentwidget = parent

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

        self.filterTextChanged.connect(common.signals.updateButtons)
        self.filterFlagChanged.connect(common.signals.updateButtons)
        self.modelReset.connect(common.signals.updateButtons)

        self.queued_invalidate_timer.timeout.connect(self._invalidateFilter)

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
        self.queued_invalidate_timer.start(
            self.queued_invalidate_timer.interval())

    def _invalidateFilter(self, *args, **kwargs):
        """Slot called by the queued invalidate timer's timeout signal."""
        result = super(FilterProxyModel, self).invalidateFilter()
        self.invalidated.emit()
        return result

    def invalidate(self, *args, **kwargs):
        result = super(FilterProxyModel, self).invalidate()
        self.invalidated.emit()
        return result

    def reset(self, *args, **kwargs):
        result = super(FilterProxyModel, self).reset()
        self.invalidated.emit()
        return result

    def sort(self, column, order=QtCore.Qt.AscendingOrder):
        raise NotImplementedError('Sorting is not implemented.')

    @common.error
    @common.debug
    def init_filter_values(self, *args, **kwargs):
        """Load the saved widget filters from `user_settings`.

        This determines if eg. archived items are visible in the view.

        """
        model = self.sourceModel()
        self._filter_text = model.get_local_setting(common.TextFilterKey)
        if self._filter_text is None:
            self._filter_text = ''

        v = model.get_local_setting(common.ActiveFlagFilterKey)
        self._filter_flags[common.MarkedAsActive] = v if v is not None else False
        v = model.get_local_setting(common.ArchivedFlagFilterKey)
        self._filter_flags[common.MarkedAsArchived] = v if v is not None else False
        v = model.get_local_setting(common.FavouriteFlagFilterKey)
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
        self.sourceModel().set_local_setting(common.TextFilterKey, v)
        self.save_history(v)
        self.filterTextChanged.emit(v)

    def save_history(self, v):
        if not v:
            return

        _v = self.sourceModel().get_local_setting(common.TextFilterKeyHistory)
        _v = _v.split(';') if _v else []

        if v.lower() in [f.lower() for f in _v]:
            return

        _v.append(v)
        self.sourceModel().set_local_setting(
            common.TextFilterKeyHistory,
            ';'.join(_v[0:MAX_HISTORY])
        )

    def filter_flag(self, flag):
        """Returns the current flag-filter."""
        return self._filter_flags[flag]

    @QtCore.Slot(int, bool)
    def set_filter_flag(self, flag, v):
        """Save a widget filter state to `user_settings`."""
        if self._filter_flags[flag] == v:
            return
        self._filter_flags[flag] = v
        if flag == common.MarkedAsActive:
            self.sourceModel().set_local_setting(common.ActiveFlagFilterKey, v)
        if flag == common.MarkedAsArchived:
            self.sourceModel().set_local_setting(common.ArchivedFlagFilterKey, v)
        if flag == common.MarkedAsFavourite:
            self.sourceModel().set_local_setting(common.FavouriteFlagFilterKey, v)

    def filterAcceptsColumn(self, source_column, parent=QtCore.QModelIndex()):
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
        if not ref() or idx not in ref():
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

        filtertext = self.filter_text()
        if filtertext:
            filtertext = filtertext.strip().lower()
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
            searchable = ref()[idx][QtCore.Qt.StatusTipRole].lower() + '\n' + \
                         d.strip().lower() + '\n' + \
                         f.strip().lower()

            if not self.filter_includes_row(filtertext, searchable):
                return False
            if self.filter_excludes_row(filtertext, searchable):
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

    def filter_includes_row(self, filtertext, searchable):
        """Checks if the filter string contains any double dashes (--) and if the
        the filter text is found in the searchable string.

        If both true, the row will be hidden.

        """
        _filtertext = filtertext
        it = re.finditer(
            r'(--[^\"\'\[\]\*\s]+)',
            filtertext,
            flags=re.IGNORECASE | re.MULTILINE
        )
        it_quoted = re.finditer(
            r'(--".*?")',
            filtertext,
            flags=re.IGNORECASE | re.MULTILINE
        )

        for match in it:
            _filtertext = re.sub(match.group(1), '', _filtertext)
        for match in it_quoted:
            _filtertext = re.sub(match.group(1), '', _filtertext)

        for text in _filtertext.split():
            text = text.strip('"')
            if text not in searchable:
                return False
        return True

    def filter_excludes_row(self, filtertext, searchable):
        it = re.finditer(
            r'--([^\"\'\[\]\*\s]+)',
            filtertext,
            flags=re.IGNORECASE | re.MULTILINE
        )
        it_quoted = re.finditer(
            r'--"(.*?)"',
            filtertext,
            flags=re.IGNORECASE | re.MULTILINE
        )

        for match in it:
            if match.group(1).lower() in searchable:
                return True
        for match in it_quoted:
            if match.group(1).lower() in searchable:
                return True
        return False
