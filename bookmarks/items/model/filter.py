"""Proxy model responsible for item filtering.

Attributes:
    filterFlagChanged (QtCore.Signal -> int, bool): Emitted when the user changes the
        current filter flags.
    filterTextChanged (QtCore.Signal -> str): Emitted when the user changes the current filter
        text.
    invalidated (QtCore.Signal): Emitted after the model has been reset or invalidated.

"""

from PySide2 import QtCore, QtWidgets

from ... import common

MAX_HISTORY = 15


class FilterProxyModel(QtCore.QSortFilterProxyModel):
    filterFlagChanged = QtCore.Signal(int, bool)  # FilterFlag, value
    filterTextChanged = QtCore.Signal(str)
    invalidated = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
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

        self.queued_invalidate_timer = common.Timer(parent=self)
        self.queued_invalidate_timer.setSingleShot(True)
        self.queued_invalidate_timer.setInterval(100)

        self._filter = common.SyntaxFilter('')
        self._filter_flags = {
            common.MarkedAsActive: None,
            common.MarkedAsArchived: None,
            common.MarkedAsFavourite: None,
        }

        self._connect_signals()

    def _connect_signals(self):
        self.filterTextChanged.connect(self.invalidateFilter)
        self.filterFlagChanged.connect(self.invalidateFilter)

        self.modelAboutToBeReset.connect(self.verify_items.stop)
        self.modelReset.connect(self.verify_items.start)
        common.signals.databaseValueChanged.connect(self.verify_items.start)

        # self.modelReset.connect(self.invalidateFilter)
        self.modelReset.connect(common.signals.updateTopBarButtons)
        self.modelReset.connect(self.init_filter_values)

        self.filterTextChanged.connect(self.verify_items.start)
        self.filterFlagChanged.connect(self.verify_items.start)

        self.filterTextChanged.connect(common.signals.updateTopBarButtons)
        self.filterFlagChanged.connect(common.signals.updateTopBarButtons)

        self.queued_invalidate_timer.timeout.connect(self.delayed_invalidate)

        # Notify the outside world that the filter text has changed
        self.filterTextChanged.connect(common.signals.filterTextChanged)

    @property
    def filter(self):
        return self._filter

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
        result = super().invalidateFilter()
        self.invalidated.emit()
        return result

    def invalidate(self, *args, **kwargs):
        """Invalidates the filter.

        """
        result = super().invalidate()
        self.invalidated.emit()
        return result

    def reset(self, *args, **kwargs):
        """Resets and invalidates the proxy model.

        """
        result = super().reset()
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

        This determines if for example, archived items are visible in the view.

        """
        model = self.sourceModel()
        if not model:
            raise ValueError('No source model found.')

        # Filter text
        v = model.get_filter_setting('filters/text')
        v = v if v is not None else ''
        self._filter.set_filter_string(v)

        v = model.get_filter_setting('filters/active')
        self._filter_flags[common.MarkedAsActive] = v if v is not None else False
        v = model.get_filter_setting('filters/archived')
        self._filter_flags[common.MarkedAsArchived] = v if v is not None else False
        v = model.get_filter_setting('filters/favourites')
        self._filter_flags[common.MarkedAsFavourite] = v if v is not None else False

    def filter_text(self):
        """Filters the list of items containing this path segment."""
        return self._filter.filter_string or ''

    @QtCore.Slot(str)
    def set_filter_text(self, v):
        """Slot called when a filter text has been set by the filter text editor
        widget.

        """
        v = v if v is not None else ''

        # Save the set text in the model
        self.filter.set_filter_string(v)

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
        if not model:
            return True  # No model, no filtering :)

        p = model.parent_path()
        k = model.task()
        t = model.data_type()

        ref = common.get_data_ref(p, k, t)
        if not ref or not ref() or idx not in ref():
            return False

        # Item flag filters
        flags = ref()[idx][common.FlagsRole]
        if not isinstance(flags, QtCore.Qt.ItemFlags):
            return False
        archived = flags & common.MarkedAsArchived
        favourite = flags & common.MarkedAsFavourite
        active = flags & common.MarkedAsActive

        if self.filter_flag(common.MarkedAsActive) and active:
            return True
        if self.filter_flag(common.MarkedAsActive) and not active:
            return False
        if archived and not self.filter_flag(common.MarkedAsArchived):
            return False
        if not favourite and self.filter_flag(common.MarkedAsFavourite):
            return False

        # Apply text filter
        r = []
        try:
            for line in ref()[idx][common.FilterTextRole].split('\n'):
                r.append(self._filter.match_string(line.strip()))
        except Exception as e:
            raise

        return any(r)
