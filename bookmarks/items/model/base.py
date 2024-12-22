import functools
import uuid
import weakref

from PySide2 import QtCore, QtWidgets

from ... import common, images, importexport, log

DEFAULT_ITEM_FLAGS = (
        QtCore.Qt.ItemNeverHasChildren |
        QtCore.Qt.ItemIsEnabled |
        QtCore.Qt.ItemIsEditable |
        QtCore.Qt.ItemIsSelectable |
        QtCore.Qt.ItemIsDropEnabled |
        QtCore.Qt.ItemIsDragEnabled
)

DEFAULT_SORT_BY_NAME_ROLE = [str()] * 8


def initdata(func):
    """Decorator used by init_data to validate the active items, and emitting
    the ``beginResetModel``, ``endResetModel`` and :attr:`.ItemModel.coreDataLoaded`
    signals.

    """

    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
        """Func wrapper.

        """
        common.init_active(
            load_settings=True,
            clear_all=False,
            load_private=False,
        )

        self._interrupt_requested = False
        self._load_in_progress = True

        try:
            self.beginResetModel()
            func(self, *args, **kwargs)
        except:
            raise
        finally:
            self._interrupt_requested = False
            self._load_in_progress = False
            self.endResetModel()

        p = self.parent_path()
        t1 = self.data_type()
        t2 = common.FileItem if t1 == common.SequenceItem else common.SequenceItem

        if all((p, k)):
            # Signal that the the gui thread has finished loading the bare model data
            self.coreDataLoaded.emit(
                common.get_data_ref(p, k, t1),
                common.get_data_ref(p, k, t2),
            )

    return func_wrapper


class ItemModel(QtCore.QAbstractTableModel):
    """The base model used for interacting with all bookmark, asset, and file items.

    Data is stored in the datacache module that can be fetched using the model's
    `parent_path`, `task` and `data_type`.


    """
    coreDataLoaded = QtCore.Signal(weakref.ref, weakref.ref)
    coreDataReset = QtCore.Signal()

    sortingChanged = QtCore.Signal(int, bool)  # (SortRole, SortOrder)

    activeChanged = QtCore.Signal(QtCore.QModelIndex)
    dataTypeChanged = QtCore.Signal(int)

    # Update signals
    updateIndex = QtCore.Signal(QtCore.QModelIndex)

    # Row size change signal
    rowHeightChanged = QtCore.Signal(int)

    queues = ()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._load_message = ''

        self._interrupt_requested = False
        self._load_in_progress = False

        self._generate_thumbnails = True

        self._sort_by = None
        self._sort_order = None
        self._datatype = {}

        self.row_size = self.default_row_size()

        self._connect_signals()

        self.init_sort_values()
        self.init_row_size()

    def _connect_signals(self):
        self.sortingChanged.connect(self.on_sorting_changed)
        self.modelReset.connect(self.init_sort_values)
        self.modelReset.connect(self.init_row_size)

        self.modelAboutToBeReset.connect(common.signals.updateTopBarButtons)
        self.modelReset.connect(common.signals.updateTopBarButtons)

    def rowCount(self, parent=QtCore.QModelIndex()):
        p = self.parent_path()
        t = self.data_type()
        if not all((p, k)) or t is None:
            return 0
        return common.data_count(p, k, t)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """Number of columns the model has."""
        return 4

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """Returns and item data associated with the given index.

        """
        if not index.isValid():
            return None
        data = self.model_data()

        if role == QtCore.Qt.SizeHintRole:
            return self.row_size

        if index.row() not in data:
            return None
        if role in data[index.row()]:
            return data[index.row()][role]

        return None

    def setData(self, index, v, role=QtCore.Qt.DisplayRole):
        """

        """
        if not index.isValid():
            return False

        data = self.model_data()
        if index.row() not in data:
            return False

        data[index.row()][role] = v
        self.dataChanged.emit(index, index)

        return True

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.SizeHintRole:
                v = QtCore.QSize(common.Size.Margin(), self.row_size.height())
                return v
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                if section == 0:
                    return 'Indicator'
                if section == 1:
                    return 'Thumbnail'
                if section == 2:
                    return 'Name'
                if section == 3:
                    return 'Buttons'
        return None

    def flags(self, index):
        """Returns the item's flags.

        """
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        v = self.data(index, role=common.FlagsRole)
        if not isinstance(v, QtCore.Qt.ItemFlags):
            return QtCore.Qt.NoItemFlags
        return v

    def parent(self, child):
        """The parent of an item.

        """
        return QtCore.QModelIndex()

    # ====================== Row size methods ======================

    @common.debug
    def init_row_size(self, *args, **kwargs):
        """Load the current row size from the user settings file.

        """
        val = self.get_filter_setting('filters/row_heights')
        h = self.default_row_size().height()
        val = h if val is None else val
        val = h if val < h else val
        val = int(common.Size.Thumbnail(apply_scale=False)) if val >= int(
            common.Size.Thumbnail(apply_scale=False)) else val
        self.row_size.setHeight(int(val))
        self.rowHeightChanged.emit(self.row_size.height())

    @classmethod
    @functools.cache
    def default_row_size(cls):
        """Returns the default item size.

        """
        return QtCore.QSize(1, common.Size.RowHeight())

    # ====================== Data loading methods ======================

    def item_generator(self, path):
        """A generator method used by :func:`init_data` to yield the items the model
        should load.

        Args:
            path (string): Path to a directory.

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

        Internal data is stored in the :mod:`bookmarks.common.data` but the model is responsible
        for populating the data via the :meth:`init_data` method.
        When the optional `force` flag is set, `init_data` to loads data from the file system,
        otherwise, if the data is already cached, the cache will be used instead.

        Args:
            force (bool): Whether to force data loading from the file system.
            emit_active (bool): Whether to emit the active index changed signal.

        """
        p = self.parent_path()
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

    @QtCore.Slot()
    def set_interrupt_requested(self):
        """Load interrupt requested by user.

        """
        self._interrupt_requested = True

    # ====================== Sorting methods ======================

    @common.debug
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

    def sort_order(self):
        """The currently set order of the items for example, 'descending'."""
        return self._sort_order

    @common.debug
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

    def sort_by(self):
        """Current sort role.

        """
        return self._sort_by

    @common.debug
    @QtCore.Slot(int)
    def set_sort_by(self, val):
        """Sets and saves the sort by value."""
        if val == self.sort_by():
            return

        self._sort_by = val
        self.set_filter_setting('filters/sort_by', val)

    @common.debug
    @common.error
    @QtCore.Slot()
    def sort_model_data(self, *args, **kwargs):
        """Sorts the model data using the current sort order and role.

        """
        sort_by = self.sort_by()
        sort_order = self.sort_order()

        p = self.parent_path()
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
            log.error(__name__, 'Sorting error')
        finally:
            self.endResetModel()

    @QtCore.Slot(bool)
    @QtCore.Slot(int)
    def on_sorting_changed(self, role, order):
        """Slot responsible for setting the sort role, order, and sorting the model
        data. Sorting is only possible when the model data is fully loaded.

        """
        if not self.is_data_type_loaded():
            return
        self.set_sort_by(role)
        self.set_sort_order(order)
        self.sort_model_data()

    @QtCore.Slot(int)
    def on_internal_data_about_to_be_sorted(self, data_type):
        if self.data_type() != data_type:
            return
        self.layoutAboutToBeChanged.emit()

    @QtCore.Slot(int)
    def on_internal_data_sorted(self, data_type):
        """Slot used to emit the reset model signals.

        """
        if self.data_type() != data_type:
            return
        self.layoutChanged.emit()

    # ====================== Data access methods ======================

    def parent_path(self):
        """Source path of the model data as a tuple of path segments.

        Returns:
            tuple: A tuple of path segments.

        """
        return ()

    def model_data(self):
        """The pointer to the model's internal data.

        """
        p = self.parent_path()
        t = self.data_type()

        if not p or not all(p) or not k or t is None:
            return common.DataDict()

        return common.get_data(p, k, t)

    def data_type(self):
        """Current key to the data dictionary."""
        return common.FileItem

    @QtCore.Slot(int)
    def is_data_type_loaded(self):
        """Checks whether the current data type is fully loaded.

        """
        p = self.parent_path()
        t = self.data_type()

        if not p or not all(p) or not k or t is None:
            return False

        return common.is_data_loaded(p, k, t)

    # ====================== Active item methods ======================

    def active_idx(self):
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
        idx = self.active_idx()
        if idx is None:
            return QtCore.QModelIndex()
        return self.index(idx, 0)

    @common.debug
    @QtCore.Slot(QtCore.QModelIndex)
    def set_active(self, index):
        """Set the given index as the model's :meth:`.active_index`.

        """
        if not index.isValid():
            return

        self.unset_active()

        data = self.model_data()
        idx = index.row()

        self.setData(index, data[idx][common.FlagsRole] | common.MarkedAsActive, common.FlagsRole)

        self.save_active()
        self.updateIndex.emit(index)
        self.activeChanged.emit(index)

        common.signals.favouritesChanged.emit()

    @common.debug
    @QtCore.Slot()
    def unset_active(self):
        """Remove the model's :meth:`.active_index`.

        """
        idx = self.active_idx()
        if idx is None:
            return

        data = self.model_data()
        data[idx][common.FlagsRole] = (
                data[idx][common.FlagsRole] & ~common.MarkedAsActive
        )

        index = self.index(idx, 0)
        self.updateIndex.emit(index)

        common.signals.favouritesChanged.emit()

    @common.debug
    @QtCore.Slot()
    def save_active(self):
        """Saves the model's active item to the user preferences.

        """
        pass

    # ====================== Filter methods ======================

    def filter_setting_key(self):
        """The custom dictionary key used to save filter settings to the user settings
        file.

        See :meth:`.get_filter_setting()` and :meth:`set_filter_setting()`.

        Returns:
            str: The dictionary key.

        """
        return 'no-filters'

    @common.error
    @common.debug
    def get_filter_setting(self, key):
        """Get a filter value stored in the user settings file.

        Each filter setting is associated with :meth:`filter_setting_key` and stored
        in a dictionary object inside the user settings file.

        Args:
            key (str): Settings key type.

        Returns:
            The value saved in user settings, or `None` if not found.

        """
        dict_key = self.filter_setting_key()
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
        dict_key = self.filter_setting_key()
        if not dict_key:
            return None
        _v = common.settings.value(key)
        _v = _v if _v else {}
        _v[dict_key] = v
        common.settings.setValue(key, _v)

    # ====================== Drag and drop methods ======================

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction

    def supportedDragActions(self):
        return QtCore.Qt.CopyAction

    def dropMimeData(self, mime, action, row, column, parent):
        """Handles drop actions.

        """
        if not action & self.supportedDropActions():
            return False

        if self._can_drop_image_file(mime, action, row, column, parent):
            return self._drop_image_action(mime, action, row, column, parent)

        if self._can_drop_properties(mime, action, row, column, parent):
            return self._drop_properties_action(mime, action, row, column, parent)

        return False

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
        if self._can_drop_properties(mime, action, row, column, parent):
            return True
        return False

    def _can_drop_image_file(self, mime, action, row, column, parent=QtCore.QModelIndex()):
        if mime.hasUrls():
            source = next(f for f in mime.urls())
            source = source.toLocalFile()
            # Try and load the image using OpenImageIO
            if images.ImageCache.get_buf(source):
                images.ImageCache.flush(source)
                return True
        return False

    def _can_drop_properties(self, mime, action, row, column, parent=QtCore.QModelIndex()):
        if 'application/item-property' in mime.formats():
            return True
        return False

    def _drop_image_action(self, mime, action, row, column, parent):
        """Handles an image drop.

        """
        image = next((f for f in mime.urls()), None)
        if not image:
            return False

        image = image.toLocalFile()
        if not images.ImageCache.get_buf(image):
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
                log.error(__name__, 'Could not remove temp file.')
            return
