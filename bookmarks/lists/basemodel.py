"""
The model is used to wrap data needed to display bookmark, asset and file
items. Data is stored in :const:`common.DATA` and populated by
:func:`.BaseModel.__initdata__`. The model can be initiated by the
`BaseModel.modelDataResetRequested` signal.

The model refers to multiple data sets simultaneously. This is because file
items are stored as file sequences and individual items in two separate data
sets (both cached in the datacache module). The file model also keeps this
data in separate sets for each subfolder it encounters in an asset's root
folder.

The current data exposed to the model can be retrieved by
`BaseModel.model_data()`. To change/set the data set emit the `taskFolderChanged` and
`dataTypeChanged` signals with their apporpiate arguments.

Each `BaseModel` instance can be initiated with worker threads used to load
secondary file information, like custom descriptions and thumbnails. See
:mod:`.bookmarks.threads` for more information.

Data is filtered with QSortFilterProxyModels but we're not using the default
sorting mechanisms because of performance considerations. Instead, sorting
is implemented in the :class:`.BaseModel` directly.

"""
DEFAULT_ITEM_FLAGS = (
    QtCore.Qt.ItemNeverHasChildren |
    QtCore.Qt.ItemIsEnabled |
    QtCore.Qt.ItemIsSelectable
)

def initdata(func):
    """Wraps `__initdata__` calls.

    The decorator is responsible for emiting the begin- and endResetModel
    signals and sorting resulting data.

    """
    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
        self.coreDataReset.emit()

        self.beginResetModel()
        self._interrupt_requested = False
        self._load_in_progress = True
        func(self, *args, **kwargs)
        self._interrupt_requested = False
        self._load_in_progress = False
        self.endResetModel()

        # Emit  references to the just loaded core data
        p = self.parent_path()
        k = self.task()
        t1 = self.data_type()
        t2 = common.FileItem if t1 == common.SequenceItem else common.SequenceItem

        self.coreDataLoaded.emit(
            common.get_data_ref(p, k, t1),
            common.get_data_ref(p, k, t2),
        )

    return func_wrapper


class BaseModel(QtCore.QAbstractListModel):
    """The base model used for interacting with all bookmark, asset and
    file items.

    Data is stored in the datacache module that can be fetched using the model's
    `parent_path`, `task` and `data_type`.

    """
    modelDataResetRequested = QtCore.Signal()  # Main signal to load model data

    coreDataLoaded = QtCore.Signal(weakref.ref, weakref.ref)
    coreDataReset = QtCore.Signal()
    dataTypeSorted = QtCore.Signal(int)

    activeChanged = QtCore.Signal(QtCore.QModelIndex)
    taskFolderChanged = QtCore.Signal(str)
    dataTypeChanged = QtCore.Signal(int)

    sortingChanged = QtCore.Signal(int, bool)  # (SortRole, SortOrder)

    # Update signals
    updateIndex = QtCore.Signal(QtCore.QModelIndex)

    queues = ()

    def __init__(self, parent=None):
        super(BaseModel, self).__init__(parent=parent)
        self.view = parent

        # Custom data type for weakref compatibility
        self._interrupt_requested = False

        self._load_in_progress = False
        self._load_message = ''

        self._generate_thumbnails_enabled = True
        self._task = None
        self._sortrole = None
        self._sortorder = None
        self._row_size = QtCore.QSize(self.default_row_size())

        self._datatype = {}  # used  by the files model only

        self.sortingChanged.connect(self.set_sorting)
        self.dataTypeSorted.connect(self.data_type_sorted)

        self.modelAboutToBeReset.connect(common.signals.updateButtons)
        self.modelReset.connect(common.signals.updateButtons)

        self.init_sort_values()
        self.init_generate_thumbnails_enabled()
        self.init_row_size()

    @common.error
    @common.debug
    def data_type_sorted(self, data_type):
        """Update the GUI model/views when a thread has resorted the underlying data structure.

        """
        if self.data_type() == data_type:
            self.beginResetModel()
            self.endResetModel()

    @QtCore.Slot(bool)
    @QtCore.Slot(int)
    def set_sorting(self, role, order):
        # Sorting is disabled until the model data is fully loaded
        if not self.is_data_type_loaded(self.data_type()):
            return
        self.set_sort_role(role)
        self.set_sort_order(order)
        self.sort_data()

    def row_size(self):
        return self._row_size

    @common.debug
    @common.error
    @initdata
    def __initdata__(self):
        """The main method used by the model to fetch and store item information
        from the file system.

        The model itself does not store any data, instead, we're using the
        :mod:`datacache` module to store item data.

        The individual items are returned by :func:`item_generator`.

        """
        raise NotImplementedError(
            'Abstract method has to be implemented in subclass.')

    def item_iterator(self):
        """A generator function used by :func:`__initdata__` find and yield the
        items the model should load.

        Eg. for assets, the function should return a series of `_scandir` entries
        referring to folders, or for files a series of file entires.

        """
        raise NotImplementedError(
            'Abstract method has to be implemented in subclass.')

    def __resetdata__(self, force=False):
        """Resets the model's internal data.

        The underlying data is cached in the :mod:`datacache` module, so here
        we'll make sure the data is available for the model to use. When the
        optional `force` flag is set, we'll use `__initdata__` to load the item
        data from disk.

        Otherwise, the method will check if our cached data is available and if
        not, uses `__initdata__` to fetch it.

        """
        p = self.parent_path()
        k = self.task()

        if force:
            common.reset_data(p, k)
            self.__initdata__()
            return

        d = common.get_task_data(p, k)
        if not d[common.FileItem]:
            self.__initdata__()

        # The let's signal the model reset and emit the current active index
        self.beginResetModel()
        self.endResetModel()
        index = self.active_index()
        if not index.isValid():
            return
        self.set_active(index)

    def parent_path(self):
        return ()

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

        self._sortrole = val

        val = self.get_local_setting(
            common.CurrentSortOrder,
            key=self.__class__.__name__,
            section=common.UIStateSection
        )
        self._sortorder = val if isinstance(val, bool) else False

    def default_row_size(self):
        return QtCore.QSize(1, common.size(common.HeightRow))

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

    @common.debug
    @common.error
    def init_generate_thumbnails_enabled(self):
        v = self.get_local_setting(
            common.GenerateThumbnails,
            key=self.__class__.__name__,
            section=common.UIStateSection
        )
        v = True if v is None else v
        self._generate_thumbnails_enabled = v

    def sort_role(self):
        return self._sortrole

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def set_sort_role(self, val):
        """Sets and saves the sort-key."""
        if val == self.sort_role():
            return

        self._sortrole = val
        self.set_local_setting(
            common.CurrentSortRole,
            val,
            key=self.__class__.__name__,
            section=common.UIStateSection
        )

    def sort_order(self):
        """The currently set order of the items eg. 'descending'."""
        return self._sortorder

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def set_sort_order(self, val):
        """Sets and saves the sort-key."""
        if val == self.sort_order():
            return

        self._sortorder = val
        self.set_local_setting(
            common.CurrentSortOrder,
            val,
            key=self.__class__.__name__,
            section=common.UIStateSection
        )

    @common.debug
    @common.error
    @common.status_bar_message('Sorting items...')
    @QtCore.Slot()
    def sort_data(self, *args, **kwargs):
        """Sorts the current data set using current `sort_role` and
        `sort_order`.

        """
        sortrole = self.sort_role()
        sortorder = self.sort_order()

        p = self.parent_path()
        k = self.task()
        t1 = self.data_type()
        t2 = common.FileItem if t1 == common.SequenceItem else common.SequenceItem

        self.beginResetModel()
        try:
            for t in (t1, t2):
                ref = common.get_data_ref(p, k, t)
                if not ref():
                    continue
                d = common.sort_data(ref, sortrole, sortorder)
                common.set_data(p, k, t, d)
        except:
            log.error('Sorting error')
        finally:
            self.endResetModel()

    @QtCore.Slot()
    def set_interrupt_requested(self):
        self._interrupt_requested = True

    @QtCore.Slot(int)
    def is_data_type_loaded(self, t):
        """Check if the given data type is loaded."""
        p = self.parent_path()
        k = self.task()
        t = self.data_type()
        return common.is_loaded(p, k, t)

    def generate_thumbnails_enabled(self):
        return self._generate_thumbnails_enabled

    @QtCore.Slot(bool)
    def set_generate_thumbnails_enabled(self, val):
        self.set_local_setting(
            common.GenerateThumbnails,
            val,
            key=self.__class__.__name__,
            section=common.UIStateSection
        )
        self._generate_thumbnails_enabled = val

    def model_data(self):
        """The pointer to the model's internal data.

        """
        return common.get_data(
            self.parent_path(),
            self.task(),
            self.data_type(),
        )

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
        """Set the given item as the model's active item.

        """
        if not index.isValid():
            return

        self.unset_active()

        data = self.model_data()
        idx = index.row()
        data[idx][common.FlagsRole] = data[idx][common.FlagsRole] | common.MarkedAsActive

        self.save_active()
        self.updateIndex.emit(index)
        self.activeChanged.emit(index)

    def save_active(self):
        """Set a newly activated item in globally active item.

        The active items are stored in `common.active` and are used by the
        models to locate items to load (see `BaseModel.parent_paths()`).

        """
        pass

    def unset_active(self):
        """Unsets the current data set's active item.

        """
        idx = self._active_idx()
        if idx is None:
            return

        data = self.model_data()
        data[idx][common.FlagsRole] = data[idx][common.FlagsRole] & ~common.MarkedAsActive

        index = self.index(idx, 0)
        self.updateIndex.emit(index)

    def data_type(self):
        """Current key to the data dictionary."""
        return common.FileItem

    def task(self):
        return 'default'

    def set_task(self, v):
        pass

    def local_settings_key(self):
        """Should return a key to be used to associated current filter and item
        selections when storing them in the the `local_settings`.

        Returns:
            str: A local_settings key value.

        """
        raise NotImplementedError(
            'Abstract class "local_settings_key" has to be implemented in the subclasses.')

    def get_local_setting(self, key_type, key=None, section=common.ListFilterSection):
        """Get a value stored in the local_common.

        Args:
            key_type (str): A filter key type.
            key (str): A key the value is associated with.
            section (str): A settings `section`. Defaults to `common.ListFilterSection`.

        Returns:
            The value saved in `local_settings`, or `None` if not found.

        """
        key = key if key else self.local_settings_key()
        if not key:
            return None
        if not isinstance(key, str):
            key = key.decode('utf-8')
        k = '{}/{}'.format(key_type, common.get_hash(key))
        return common.settings.value(section, k)

    @common.error
    @common.debug
    def set_local_setting(self, key_type, v, key=None, section=common.ListFilterSection):
        """Set a value to store in `local_settings`.

        Args:
            key_type (str): A filter key type.
            v (any):    A value to store.
            key (type): A key the value is associated with.
            section (type): A settings `section`. Defaults to `common.ListFilterSection`.

        """
        key = key if key else self.local_settings_key()
        if not key:
            return None
        k = '{}/{}'.format(key_type, common.get_hash(key))
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

    def canDropMimeData(self, data, action, row, column, parent=QtCore.QModelIndex()):
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

        proxy = True if common.is_collapsed(source) else False
        server, job, root = index.data(common.ParentPathRole)[0:3]
        images.load_thumbnail_from_image(
            server, job, root, source, image, proxy=proxy)

        return True

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        p = self.parent_path()
        k = self.task()
        t = self.data_type()
        return common.data_count(p, k, t)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        p = self.parent_path()
        k = self.task()
        t = self.data_type()
        d = common.get_data(p, k, t)

        if not d:
            return QtCore.QModelIndex()
        if row not in d:
            return QtCore.QModelIndex()

        ptr = weakref.ref(d[row])
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
        raise NotImplementedError(
            'Sorting on the proxy model is not implemented.')

    @common.error
    @common.debug
    def init_filter_values(self, *args, **kwargs):
        """Load the saved widget filters from `local_settings`.

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

        # Save the text in the local settings file
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
        """Save a widget filter state to `local_settings`."""
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
        p = model.parent_path()
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
