"""Base views used to show :mod:`bookmark <bookmarks.items.bookmark_items>`,
:mod:`asset <bookmarks.items.asset_items>`, and :mod:`file <bookmarks.items.file_items>`
items.

The view uses :class:`~bookmarks.items.models.ItemModel` for getting the item data,
:class:`~bookmarks.items.delegate.rst.ItemDelegate` to paint the items.

:class:`BaseItemView` is a customised QListView widget augmented by
:class:`.InlineIconView` (adds inline icon functionality),
and :class:`.ThreadedItemView` that implement threading related functionality.

"""
import collections
import functools
import re
import weakref

from PySide2 import QtWidgets, QtGui, QtCore

from . import delegate
from . import models
from .widgets import description_editor
from .widgets import filter_editor
from .. import actions
from .. import common
from .. import contextmenu
from .. import database
from .. import images
from .. import ui
from ..threads import threads


class ListsWidget(QtWidgets.QStackedWidget):
    """This stacked widget contains the main bookmark, asset, file and favourite item
    views.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('BrowserStackedWidget')
        common.signals.tabChanged.connect(self.setCurrentIndex)

    def setCurrentIndex(self, idx):
        """Sets the current index of the ``ListsWidget``.

        Args:
            idx (int): The index of the widget to set.

        """
        idx = common.BookmarkTab if idx is None or idx is False else idx
        idx = idx if idx >= common.BookmarkTab else common.BookmarkTab

        if (
                not common.active_index(common.BookmarkTab).isValid()
                and idx in (common.BookmarkTab, common.AssetTab, common.FileTab)
        ):
            idx = common.BookmarkTab

        if (
                common.active_index(common.BookmarkTab).isValid()
                and not common.active_index(common.AssetTab).isValid()
                and idx in (common.AssetTab, common.FileTab)
        ):
            idx = common.AssetTab

        if idx > common.FavouriteTab:
            idx = common.FavouriteTab

        # Save tab to user settings
        common.settings.setValue('selection/current_tab', idx)
        super().setCurrentIndex(idx)
        self.currentWidget().setFocus()

    def showEvent(self, event):
        """Event handler.

        """
        if self.currentWidget():
            self.currentWidget().setFocus()


class ThumbnailsContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with thumbnail actions.

    """

    def setup(self):
        """Creates the context menu.

        """
        self.thumbnail_menu()
        self.separator()
        self.sg_thumbnail_menu()


class ProgressWidget(QtWidgets.QWidget):
    """Widget responsible for indicating files are being loaded."""

    def __init__(self, parent=None):
        super(ProgressWidget, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setWindowFlags(QtCore.Qt.Widget)
        self._message = 'Loading...'

    def showEvent(self, event):
        """Event handler.

        """
        self.setGeometry(self.parent().geometry())

    @QtCore.Slot(str)
    def set_message(self, text):
        """Sets the message to be displayed when saving the widget."""
        self._message = text

    def paintEvent(self, event):
        """Event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        color = common.color(common.color_separator)
        painter.setBrush(color)
        painter.drawRect(self.rect())
        painter.setOpacity(0.8)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.size(common.size_font_medium))[0],
            self.rect(),
            self._message,
            QtCore.Qt.AlignCenter,
            common.color(common.color_text)
        )
        painter.end()

    def mousePressEvent(self, event):
        """Event handler.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.hide()


class FilterOnOverlayWidget(ProgressWidget):
    """An indicator widget drawn on top of the list widgets to signal
    if a model has filters set or if it requires a refresh.

    """

    def paintEvent(self, event):
        """Event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)

        self.paint_filter_indicator(painter)
        self.paint_needs_refresh(painter)

        painter.end()

    def paint_needs_refresh(self, painter):
        """Paints the data status indicator.

        """
        model = self.parent().model().sourceModel()
        if not hasattr(model, 'refresh_needed') or not model.refresh_needed():
            return

        painter.save()

        o = common.size(common.size_separator)
        rect = self.rect().adjusted(o, o, -o, -o)
        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(common.color(common.color_blue))
        pen.setWidth(common.size(common.size_separator) * 2.0)
        painter.setPen(pen)

        painter.drawRect(rect)

        painter.restore()

    def paint_filter_indicator(self, painter):
        """Paints the filter indicator.

        """
        model = self.parent().model()
        if model.rowCount() == model.sourceModel().rowCount():
            return

        painter.save()

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.color_red))
        painter.setOpacity(0.8)

        rect = self.rect()
        rect.setHeight(common.size(common.size_separator) * 2.0)
        painter.drawRect(rect)
        rect.moveBottom(self.rect().bottom())
        painter.drawRect(rect)

        painter.restore()

    def showEvent(self, event):
        """Event handler.

        """
        self.repaint()


class BaseItemView(QtWidgets.QListView):
    """The base view of all subsequent bookmark, asset and files item views.

    """
    customContextMenuRequested = QtCore.Signal(
        QtCore.QModelIndex, QtCore.QObject)
    interruptRequested = QtCore.Signal()

    resized = QtCore.Signal(QtCore.QRect)
    SourceModel = NotImplementedError

    Delegate = NotImplementedError
    ContextMenu = NotImplementedError
    ThumbnailContextMenu = ThumbnailsContextMenu

    def __init__(self, icon='icon_bw', parent=None):
        super().__init__(parent=parent)
        self.visible_rows = {
            'source_rows': [],
            'ids': [],
            'proxy_rows': []
        }

        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)

        self.delayed_layout_timer = common.Timer(parent=self)
        self.delayed_layout_timer.setObjectName('DelayedLayoutTimer')
        self.delayed_layout_timer.setSingleShot(True)
        self.delayed_layout_timer.setInterval(33)
        self.delayed_layout_timer.timeout.connect(self.scheduleDelayedItemsLayout)
        self.delayed_layout_timer.timeout.connect(self.repaint_visible_rows)

        self._buttons_hidden = False

        self._thumbnail_drop = (-1, False)  # row, accepted
        self._background_icon = icon

        self.progress_indicator_widget = ProgressWidget(parent=self)
        self.progress_indicator_widget.setHidden(True)

        self.filter_indicator_widget = FilterOnOverlayWidget(parent=self)
        self.filter_editor = filter_editor.FilterEditor(parent=self)
        self.filter_editor.setHidden(True)

        self.description_editor_widget = description_editor.DescriptionEditorWidget(
            parent=self)
        self.description_editor_widget.setHidden(True)

        # Keyboard search timer and placeholder string.
        self.timer = common.Timer(parent=self)
        self.timer.setInterval(
            QtWidgets.QApplication.instance().keyboardInputInterval())
        self.timer.setSingleShot(True)
        self.timed_search_string = ''

        self.delayed_save_selection_timer = common.Timer()
        self.delayed_save_selection_timer.setSingleShot(True)
        self.delayed_save_selection_timer.setInterval(100)

        self.delayed_restore_selection_timer = common.Timer()
        self.delayed_restore_selection_timer.setInterval(10)
        self.delayed_restore_selection_timer.setSingleShot(True)

        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setUniformItemSizes(True)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.setWordWrap(False)
        self.setLayoutMode(QtWidgets.QListView.Batched)
        self.setBatchSize(100)

        self.installEventFilter(self)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.set_model(self.SourceModel(parent=self))
        self.setItemDelegate(self.Delegate(parent=self))

        self.resized.connect(self.filter_indicator_widget.setGeometry)
        self.resized.connect(self.progress_indicator_widget.setGeometry)
        self.resized.connect(self.filter_editor.setGeometry)

        self.delayed_save_selection_timer.timeout.connect(self.save_selection)
        self.delayed_restore_selection_timer.timeout.connect(self.restore_selection)

        self.init_buttons_state()

    @common.error
    @common.debug
    def init_buttons_state(self):
        """Restore the previous state of the inline icon buttons.

        """
        model = self.model().sourceModel()
        v = model.get_filter_setting('filters/buttons')
        v = False if not v else v
        self._buttons_hidden = v

        common.sort_by_basename = (
            True if v else
            (False if common.sort_by_basename is None else common.sort_by_basename)
        )

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons.

        """
        if self.width() < common.size(common.size_width) * 0.66:
            return True
        return self._buttons_hidden

    def set_buttons_hidden(self, val):
        """Sets the visibility of the inline icon buttons.

        """
        self.model().sourceModel().set_filter_setting('filters/buttons', val)
        self._buttons_hidden = val

    @common.error
    @common.debug
    def set_model(self, model):
        """Add a model to the view.

        The ItemModel subclasses are wrapped in a QSortFilterProxyModel. All
        the necessary internal signal-slot connections needed for the proxy, model
        and the view to communicate are made here.

        """
        common.check_type(model, models.ItemModel)

        proxy = models.FilterProxyModel(parent=self)

        proxy.setSourceModel(model)
        self.setModel(proxy)

        self.init_buttons_state()
        model.init_sort_values()
        model.init_row_size()
        proxy.init_filter_values()

        model.modelReset.connect(proxy.init_filter_values)
        model.modelReset.connect(model.init_sort_values)
        model.modelReset.connect(model.init_row_size)
        model.modelReset.connect(self.init_buttons_state)
        model.modelReset.connect(self.reset_multi_toggle)

        self.interruptRequested.connect(model.set_interrupt_requested)

        self.filter_editor.finished.connect(proxy.set_filter_text)

        model.modelReset.connect(self.delay_restore_selection)
        proxy.invalidated.connect(self.delay_restore_selection)

        model.modelReset.connect(self.save_visible_rows)
        proxy.modelReset.connect(self.save_visible_rows)
        proxy.invalidated.connect(self.save_visible_rows)

        model.modelReset.connect(self.reset_row_layout)

        model.updateIndex.connect(
            self.update, type=QtCore.Qt.DirectConnection)

        common.signals.paintThumbnailBGChanged.connect(
            self.repaint_visible_rows
        )

    @QtCore.Slot(QtCore.QModelIndex)
    def update(self, index):
        """This slot is used by all threads to repaint/update the given index
        after it's thumbnail or file information has been loaded.

        An actual repaint event will only trigger if the index is visible
        in the view.

        """
        if not index.isValid():
            return
        if not hasattr(index.model(), 'sourceModel'):
            index = self.model().mapFromSource(index)
        super().update(index)

    @QtCore.Slot(QtCore.QModelIndex)
    def activate(self, index):
        """This method is called in response to a user action and is used
        to mark an item `active`.

        """
        if not index.isValid():
            return
        if index.flags() == QtCore.Qt.NoItemFlags:
            return
        if index.flags() & common.MarkedAsArchived:
            return

        # If the item is already active, we'll emit the standard activated
        # signal. This will change tabs but won't trigger a model update
        if index.flags() & common.MarkedAsActive:
            self.activated.emit(index)
            return

        # If the current item is not active, we'll unset the current active
        # item's MarkedAsActive flag and emit the activeChanged signal.
        proxy = self.model()
        model = proxy.sourceModel()
        source_index = proxy.mapToSource(index)

        model.set_active(source_index)
        self.activated.emit(index)

    def delay_save_selection(self):
        """Delays saving the current item selection to the user settings file to reduce
        the number of file writes.

        """
        self.delayed_save_selection_timer.start(
            self.delayed_save_selection_timer.interval())

    @QtCore.Slot()
    def save_selection(self):
        """Saves the current selection to the user settings file.

        """
        index = common.get_selected_index(self)
        if not index.isValid():
            return
        if not index.data(common.PathRole):
            return

        model = self.model().sourceModel()
        data_type = model.data_type()

        path = index.data(common.PathRole)
        if data_type == common.SequenceItem:
            path = common.get_sequence_start_path(path)

        model.set_filter_setting('filters/selection_file', path)
        model.set_filter_setting('filters/selection_sequence', common.proxy_path(path))

    @QtCore.Slot()
    def delay_restore_selection(self):
        """Delays getting the saved selection from the user settings file.

        """
        self.delayed_restore_selection_timer.start(
            self.delayed_restore_selection_timer.interval())

    @QtCore.Slot()
    def restore_selection(self):
        """Slot called to reselect a previously saved selection.

        """
        proxy = self.model()
        if not proxy or not proxy.rowCount():
            return

        model = proxy.sourceModel()
        data_type = model.data_type()

        if data_type == common.FileItem:
            previous = model.get_filter_setting('filters/selection_file')
        elif data_type == common.SequenceItem:
            previous = model.get_filter_setting('filters/selection_sequence')
        else:
            return

        # Restore previously saved selection
        if previous:
            for n in range(proxy.rowCount()):
                index = proxy.index(n, 0)

                if not index.isValid():
                    continue
                p = index.data(common.PathRole)
                if not p:
                    continue

                if data_type == common.SequenceItem:
                    current = common.proxy_path(p)
                else:
                    current = p

                if current != previous:
                    continue

                # When we found an item, let's make sure it is visible
                self.scrollTo(
                    index,
                    hint=QtWidgets.QAbstractItemView.PositionAtCenter
                )
                self.selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect |
                    QtCore.QItemSelectionModel.Rows
                )
                return

        # Select the active item
        index = proxy.sourceModel().active_index()
        if index.isValid():
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
            return

        # Select the first item in the list
        index = proxy.index(0, 0)
        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def toggle_item_flag(self, index, flag, state=None, commit_now=True):
        """Sets the index's filter flag value based on the passed state.

        We're using the method to mark items archived, or favourite and save the
        changes to the database and the user settings file.

        Args:
            index (QModelIndex): Model index.
            flag (int): A filter flag, e.g. ``MarkedAsArchived``.
            state (bool): Pass an explicit state value. Defaults to None.
            commit_now (bool): When `True`, commits database values immediately.

        Returns:
            str: The key used to find and match items.

        """

        def _save_to_db(k, mode, flag):
            if not commit_now:
                threads.queue_database_transaction(
                    server, job, root, k, mode, flag)
                return
            database.set_flag(server, job, root, k, mode, flag)

        def _save_to_user_settings(k, mode, flag):
            if mode:
                actions.add_favourite(index.data(common.ParentPathRole), k)
                return
            actions.remove_favourite(index.data(common.ParentPathRole), k)

        def _save_active(k, mode, flag):
            pass

        p = index.data(common.ParentPathRole)
        if not p:
            return
        server, job, root = index.data(common.ParentPathRole)[0:3]

        # Ignore default items
        if flag == common.MarkedAsArchived and index.data(
                common.FlagsRole) & common.MarkedAsDefault:
            return

        if flag == common.MarkedAsArchived:
            save_func = _save_to_db
        elif flag == common.MarkedAsFavourite:
            save_func = _save_to_user_settings
        elif flag == common.MarkedAsActive:
            save_func = _save_active
        else:
            save_func = lambda *args: None

        def _set_flag(k, mode, data, flag, commit=False):
            """Sets a single flag value based on the given mode."""
            if mode:
                data[common.FlagsRole] = data[common.FlagsRole] | flag
            else:
                data[common.FlagsRole] = data[common.FlagsRole] & ~flag
            if commit:
                save_func(k, mode, flag)

        def _set_flags(DATA, k, mode, flag, commit=False, proxy=False):
            """Sets flags for multiple items."""
            for item in DATA.values():
                if proxy:
                    _k = common.proxy_path(item[common.PathRole])
                else:
                    _k = item[common.PathRole]
                if k == _k:
                    _set_flag(_k, mode, item, flag, commit=commit)

        def can_toggle_flag(k, mode, data, flag):
            """Checks if the given flag can be toggled.

            """
            seq = common.get_sequence(k)

            if not seq:
                return True

            proxy_k = common.proxy_path(k)

            if flag == common.MarkedAsActive:
                pass  # not implemented

            elif flag == common.MarkedAsArchived:
                db = database.get_db(*index.data(common.ParentPathRole)[0:3])

                flags = db.value(
                    proxy_k,
                    'flags',
                    database.AssetTable
                )

                if not flags:
                    return True
                if flags & common.MarkedAsArchived:
                    return False
                return True

            elif flag == common.MarkedAsFavourite:
                if proxy_k in common.favourites:
                    return False
                return True
            return False

        if not index.isValid():
            return False

        if hasattr(index.model(), 'sourceModel'):
            source_index = self.model().mapToSource(index)
        else:
            source_index = index

        if not source_index.data(common.FileInfoLoaded):
            return False

        model = self.model().sourceModel()

        p = model.source_path()
        k = model.task()

        if not p or not all(p):
            return False

        idx = source_index.row()
        data = model.model_data()[idx]

        file_data = common.get_data(p, k, common.FileItem)
        seq_data = common.get_data(p, k, common.SequenceItem)

        applied = data[common.FlagsRole] & flag
        collapsed = common.is_collapsed(data[common.PathRole])

        # Determine the mode of operation
        if state is None and applied:
            mode = False
        elif state is None and not applied:
            mode = True
        elif state is not None:
            mode = state

        if collapsed:
            k = common.proxy_path(data[common.PathRole])
            _set_flag(k, mode, data, flag, commit=True)
            if self.model().sourceModel().model_data() == file_data:
                _set_flags(seq_data, k, mode, flag, commit=False, proxy=True)
            else:
                _set_flags(file_data, k, mode, flag, commit=False, proxy=True)
        else:
            k = data[common.PathRole]

            if not can_toggle_flag(k, mode, data, flag):
                ui.MessageBox(
                    'Looks like this item belongs to a sequence that has a flag set '
                    'already.',
                    'To modify individual sequence items, remove the flag from the '
                    'sequence first and try again.'
                ).open()
                self.reset_multi_toggle()
                return False

            _set_flag(k, mode, data, flag, commit=True)
            if self.model().sourceModel().model_data() == file_data:
                _set_flags(seq_data, k, mode, flag, commit=True, proxy=False)
            else:
                _set_flags(file_data, k, mode, flag, commit=True, proxy=False)

        return k

    def key_space(self):
        """Custom key action.
        
        """
        actions.preview_thumbnail()

    def key_down(self):
        """Custom action on `down` arrow key-press.

        We're implementing a continuous scroll: when reaching the last
        item in the list, we'll jump to the beginning, and vice-versa.

        """
        sel = self.selectionModel()
        current_index = sel.currentIndex()
        first_index = self.model().index(0, 0)
        last_index = self.model().index(
            self.model().rowCount() - 1, 0)

        if first_index == last_index:
            return
        if not current_index.isValid():  # No selection
            sel.setCurrentIndex(
                first_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return

        if current_index == last_index:  # Last item is selected
            sel.setCurrentIndex(
                first_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return

        sel.setCurrentIndex(
            self.model().index(current_index.row() + 1, 0),
            QtCore.QItemSelectionModel.ClearAndSelect
        )

    def key_up(self):
        """Custom action to perform when the `up` arrow is pressed
        on the keyboard.

        We're implementing a continuous scroll: when reaching the last
        item in the list, we'll jump to the beginning, and vice-versa.

        """
        sel = self.selectionModel()
        current_index = sel.currentIndex()
        first_index = self.model().index(0, 0)
        last_index = self.model().index(self.model().rowCount() - 1, 0)

        if first_index == last_index:
            return

        if not current_index.isValid():  # No selection
            sel.setCurrentIndex(
                last_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return
        if current_index == first_index:  # First item is selected
            sel.setCurrentIndex(
                last_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return

        sel.setCurrentIndex(
            self.model().index(current_index.row() - 1, 0),
            QtCore.QItemSelectionModel.ClearAndSelect
        )

    def key_tab(self):
        """Custom key action
        
        """
        self.description_editor_widget.show()

    def action_on_enter_key(self):
        """Custom key action
        
        """
        index = common.get_selected_index(self)
        if not index.isValid():
            return
        self.activate(index)

    def get_status_string(self):
        """Returns an informative string to indicate if the list has hidden items.

        """
        proxy = self.model()
        model = proxy.sourceModel()

        # Model is empty
        if model.rowCount() == 0:
            return 'No items'

        # All items are visible, we don't have to display anything
        if proxy.rowCount() == model.rowCount():
            return ''

        # Let's figure out the reason why the list has hidden items
        reason = ''
        if proxy.filter_text():
            reason = 'a search filter is applied'
        elif proxy.filter_flag(common.MarkedAsFavourite):
            reason = 'showing favourites only'
        elif proxy.filter_flag(common.MarkedAsActive):
            reason = 'showing active item only'
        elif not proxy.filter_flag(common.MarkedAsArchived):
            reason = 'archived items are hidden'

        # Items are hidden...
        count = model.rowCount() - proxy.rowCount()
        if count == 1:
            return f'{count} item is hidden ({reason})'
        return f'{count} items are hidden ({reason})'

    def get_hint_string(self):
        """Returns an informative hint text.

        """
        return ''

    def paint_hint(self, widget, event):
        """Paints the hint message.

        """
        text = self.get_hint_string()
        self._paint_message(text, color=common.color(common.color_green))

    def paint_loading(self, widget, event):
        """Paints the hint message.

        """
        text = 'Loading items. Please wait...'
        self._paint_message(text, color=common.color(common.color_text))

    def paint_status_message(self, widget, event):
        """Displays a visual hint for the user to indicate if the list
        has hidden items.

        """
        text = self.get_status_string()
        self._paint_message(text, color=common.color(common.color_red))

    def _paint_message(self, text, color=common.color(common.color_text)):
        """Utility method used to paint a message.

        """
        if not text:
            return

        proxy = self.model()
        model = proxy.sourceModel()

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        _ = painter.setOpacity(0.9) if hover else painter.setOpacity(0.75)

        n = 0
        rect = QtCore.QRect(
            0, 0,
            self.viewport().rect().width(),
            model.row_size.height()
        )

        while self.rect().intersects(rect):
            if n == proxy.rowCount():
                if n == 0:
                    rect.moveCenter(self.rect().center())
                break
            rect.moveTop(rect.top() + rect.height())
            n += 1

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        o = common.size(common.size_indicator)

        rect = rect.adjusted(o * 3, o, -o * 3, -o)

        font, metrics = common.font_db.primary_font(
            common.size(common.size_font_small))
        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            rect.width()
        )

        x = rect.center().x() - (metrics.horizontalAdvance(text) / 2.0)
        y = rect.center().y() + (metrics.ascent() / 2.0)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)
        path = delegate.get_painter_path(x, y, font, text)
        painter.drawPath(path)
        painter.end()


    @QtCore.Slot()
    def repaint_visible_rows(self):
        """Slot used to repaint all currently visible items.
        
        """
        if QtWidgets.QApplication.instance().mouseButtons() != QtCore.Qt.NoButton:
            return

        for idx in self.visible_rows['proxy_rows']:
            index = self.model().index(idx, 0)
            super().update(index)

    @common.error
    @common.debug
    @QtCore.Slot()
    def reset_row_layout(self, *args, **kwargs):
        """Re-initializes the rows to apply size and row height changes.

        """
        proxy = self.model()
        index = common.get_selected_index(self)

        # Save the current selection
        row = index.row() if index.isValid() else -1

        # Update the layout
        self.scheduleDelayedItemsLayout()
        self.save_visible_rows()
        self.repaint_visible_rows()

        # Restore the selection
        if row >= 0:
            index = proxy.index(row, 0)
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
            self.scrollTo(
                index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def set_row_size(self, v):
        """Sets the row size.
        
        Args:
            v (int): The new row size
            
        """
        proxy = self.model()
        model = proxy.sourceModel()
        model.row_size.setHeight(int(v))
        model.set_filter_setting('filters/row_heights', int(v))

    @common.error
    @common.debug
    @QtCore.Slot(str)
    def show_item(self, v, role=QtCore.Qt.DisplayRole, update=True, limit=10000):
        """Show an item in the viewer.

        Args:
            v (any): A value to match.
            role (QtCore.Qt.ItemRole): An item data role.
            update (bool): Refreshes the model if `True` (the default).
            limit (int): Maximum item search number.

        """
        proxy = self.model()
        model = proxy.sourceModel()
        if update and model.rowCount() < limit:
            model.reset_data(force=True, emit_active=False)

        # Delay the selection to let the model process events
        QtCore.QTimer.singleShot(100, functools.partial(
            self.select_item, v, role=role))

    def select_item(self, v, role=QtCore.Qt.DisplayRole):
        """Select an item in the viewer.

        """
        proxy = self.model()
        model = proxy.sourceModel()
        data = model.model_data()
        t = model.data_type()

        for idx in data:
            if t == common.SequenceItem and role == common.PathRole:
                k = common.proxy_path(data[idx][role])
            else:
                k = data[idx][role]

            if v == k:
                index = proxy.mapFromSource(model.index(idx, 0))
                self.selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                self.selectionModel().select(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                self.scrollTo(
                    index,
                    hint=QtWidgets.QAbstractItemView.PositionAtCenter
                )
                self.save_selection()
                return

    def dragEnterEvent(self, event):
        """Event handler.
        
        """
        self._thumbnail_drop = (-1, False)
        self.repaint(self.rect())
        if event.source() == self:
            event.ignore()
            return
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        event.accept()

    def dragLeaveEvent(self, event):
        """Event handler.
        
        """
        self._thumbnail_drop = (-1, False)
        self.repaint(self.rect())

    def dragMoveEvent(self, event):
        """Event handler.
        
        """
        self._thumbnail_drop = (-1, False)
        pos = common.cursor.pos()
        pos = self.mapFromGlobal(pos)

        index = self.indexAt(pos)
        row = index.row()

        if not index.isValid():
            self._thumbnail_drop = (-1, False)
            self.repaint(self.rect())
            event.ignore()
            return

        proxy = self.model()
        model = proxy.sourceModel()
        index = proxy.mapToSource(index)

        if not model.canDropMimeData(event.mimeData(), event.proposedAction(),
                                     index.row(), 0):
            self._thumbnail_drop = (-1, False)
            self.repaint(self.rect())
            event.ignore()
            return

        event.accept()
        self._thumbnail_drop = (row, True)
        self.repaint(self.rect())

    def dropEvent(self, event):
        """Event handler.
        
        """
        self._thumbnail_drop = (-1, False)

        pos = common.cursor.pos()
        pos = self.mapFromGlobal(pos)

        index = self.indexAt(pos)
        if not index.isValid():
            event.ignore()
            return
        proxy = self.model()
        model = proxy.sourceModel()
        index = proxy.mapToSource(index)

        if not model.canDropMimeData(event.mimeData(), event.proposedAction(),
                                     index.row(), 0):
            event.ignore()
            return
        model.dropMimeData(
            event.mimeData(), event.proposedAction(), index.row(), 0)

    def showEvent(self, event):
        """Show event handler.

        """
        self.scheduleDelayedItemsLayout()

    def mouseReleaseEvent(self, event):
        """Event handler.
        
        """
        super().mouseReleaseEvent(event)
        self.delay_save_selection()

    def eventFilter(self, widget, event):
        """Event filter handler.

        """
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            ui.paint_background_icon(self._background_icon, widget)

            if self.model().sourceModel()._load_in_progress:
                self.paint_loading(widget, event)
            elif self.model().sourceModel().rowCount() == 0:
                self.paint_hint(widget, event)
            else:
                self.paint_status_message(widget, event)
            return True
        return False

    def resizeEvent(self, event):
        """Event handler.

        """
        self.delayed_layout_timer.start(self.delayed_layout_timer.interval())
        self.resized.emit(self.viewport().geometry())

    def keyPressEvent(self, event):
        """Key press event handler.

        We're defining the default behaviour of the list-items here, including
        defining the actions needed to navigate the list using keyboard presses.

        """
        numpad_modifier = event.modifiers() & QtCore.Qt.KeypadModifier
        no_modifier = event.modifiers() == QtCore.Qt.NoModifier

        if no_modifier or numpad_modifier:
            if not self.timer.isActive():
                self.timed_search_string = ''
            self.timer.start()

            if event.key() == QtCore.Qt.Key_Escape:
                self.interruptRequested.emit()
                return
            if event.key() == QtCore.Qt.Key_Space:
                self.key_space()
                self.delay_save_selection()
                return
            if event.key() == QtCore.Qt.Key_Escape:
                self.selectionModel().setCurrentIndex(
                    QtCore.QModelIndex(), QtCore.QItemSelectionModel.ClearAndSelect)
                return
            elif event.key() == QtCore.Qt.Key_Down:
                self.key_down()
                self.delay_save_selection()
                return
            elif event.key() == QtCore.Qt.Key_Up:
                self.key_up()
                self.delay_save_selection()
                return
            elif (event.key() == QtCore.Qt.Key_Return) or (
                    event.key() == QtCore.Qt.Key_Enter):
                self.action_on_enter_key()
                self.delay_save_selection()
                return
            elif event.key() == QtCore.Qt.Key_Tab:
                if not self.description_editor_widget.isVisible():
                    self.key_tab()
                    self.delay_save_selection()
                    return
                else:
                    self.key_down()
                    self.key_tab()
                    self.delay_save_selection()
                    return
            elif event.key() == QtCore.Qt.Key_Backtab:
                if not self.description_editor_widget.isVisible():
                    self.key_tab()
                    self.delay_save_selection()
                    return
                else:
                    self.key_up()
                    self.key_tab()
                    self.delay_save_selection()
                    return
            elif event.key() == QtCore.Qt.Key_PageDown:
                super().keyPressEvent(event)
                self.delay_save_selection()
                return
            elif event.key() == QtCore.Qt.Key_PageUp:
                super().keyPressEvent(event)
                self.delay_save_selection()
                return
            elif event.key() == QtCore.Qt.Key_Home:
                super().keyPressEvent(event)
                self.delay_save_selection()
                return
            elif event.key() == QtCore.Qt.Key_End:
                super().keyPressEvent(event)
                self.delay_save_selection()
                return

            self.timed_search_string += event.text()

            sel = self.selectionModel()
            for n in range(self.model().rowCount()):
                index = self.model().index(n, 0, parent=QtCore.QModelIndex())
                # When only one key is pressed we want to cycle through
                # only items starting with that letter:
                if len(self.timed_search_string) == 1:
                    if n <= sel.currentIndex().row():
                        continue

                    if index.data(QtCore.Qt.DisplayRole)[
                        0].lower() == self.timed_search_string.lower():
                        sel.setCurrentIndex(
                            index,
                            QtCore.QItemSelectionModel.ClearAndSelect
                        )
                        self.delay_save_selection()
                        break
                else:
                    try:
                        match = re.search(
                            self.timed_search_string,
                            index.data(QtCore.Qt.DisplayRole),
                            flags=re.IGNORECASE
                        )
                    except:
                        match = None

                    if match:
                        sel.setCurrentIndex(
                            index,
                            QtCore.QItemSelectionModel.ClearAndSelect
                        )
                        self.delay_save_selection()
                        return

        if event.modifiers() & QtCore.Qt.ShiftModifier:
            if event.key() == QtCore.Qt.Key_Tab:
                self.key_up()
                self.key_tab()
                self.delay_save_selection()
                return
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.key_up()
                self.key_tab()
                self.delay_save_selection()
                return

    def wheelEvent(self, event):
        """Custom wheel event responsible for scrolling the list.

        """
        event.accept()
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier

        if not control_modifier:
            shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier

            # Adjust the scroll amount based on thw row size
            if self.model().sourceModel().row_size.height() > (
                    common.size(common.size_row_height) * 2):
                o = 9 if shift_modifier else 1
            else:
                o = 9 if shift_modifier else 3

            v = self.verticalScrollBar().value()
            if event.angleDelta().y() > 0:
                v = self.verticalScrollBar().setValue(v + o)
            else:
                v = self.verticalScrollBar().setValue(v - o)
            return

        if event.angleDelta().y() > 0:
            actions.increase_row_size()
        else:
            actions.decrease_row_size()

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        index = self.indexAt(event.pos())
        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier

        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit(index, self)
            return

        if not self.ContextMenu:
            return

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())
        if index.isValid() and rectangles[delegate.ThumbnailRect].contains(event.pos()):
            widget = self.ThumbnailContextMenu(index, parent=self)
        else:
            widget = self.ContextMenu(index, parent=self)

        widget.move(common.cursor.pos())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def mousePressEvent(self, event):
        """Deselecting item when the index is invalid."""
        if not isinstance(event, QtGui.QMouseEvent):
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            self.selectionModel().setCurrentIndex(
                QtCore.QModelIndex(),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Custom doubleclick event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double click location before deciding what action to take.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())
        description_rectangle = self.itemDelegate().get_description_rect(rectangles,
                                                                         index)

        if description_rectangle.contains(cursor_position):
            self.description_editor_widget.show()
            return

        if rectangles[delegate.ThumbnailRect].contains(cursor_position):
            actions.pick_thumbnail_from_file()
            return

        if rectangles[delegate.DataRect].contains(cursor_position):
            index = common.get_selected_index(self)
            if not index.isValid():
                return
            self.activate(index)


class InlineIconView(BaseItemView):
    """Adds multi-toggle and clickable in-line icons to :class:`BaseItemView`.

    """

    def __init__(self, icon='bw_icon', parent=None):
        super(InlineIconView, self).__init__(icon=icon, parent=parent)

        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

    def inline_icons_count(self):
        """Inline buttons count.

        """
        return 0

    def reset_multi_toggle(self):
        """Resets the multi-toggle state.
        
        """
        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

    def clickable_rectangle_event(self, event):
        """Handle mouse press & release events on an item's interactive rectangle.

        The clickable rectangles are defined by and stored by the item delegate. See
        :meth:`~bookmarks.items.ItemDelegate.get_clickable_rectangles`.

        We're implementing filtering by reacting to clicks on item labels:
        ``shift`` modifier will add a _positive_ filter and hide all items not
        containing the clicked rectangle's text content.

        The ``alt`` and ``control`` modifiers will add a _negative filter_ and hide all
        items containing the clicked rectangle's text content.

        """
        # Disable when buttons are hidden
        if self.buttons_hidden():
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)

        if not index.isValid():
            return
        if not index.flags() & QtCore.Qt.ItemIsEnabled:
            return

        # Get pressed keyboard modifiers
        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        # Get clickable rectangles from the delegate
        clickable_rectangles = self.itemDelegate().get_clickable_rectangles(index)
        if not clickable_rectangles:
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())

        for idx, item in enumerate(clickable_rectangles):
            if idx == 0:
                continue  # First rectangle is always the description editor

            rect, text = item
            text = text.lower()

            if rect.contains(cursor_position):
                filter_text = self.model().filter_text()
                filter_text = filter_text.lower() if filter_text else ''

                if shift_modifier:
                    # Shift modifier will add a "positive" filter and hide all items
                    # that does not contain the given text.
                    folder_filter = f'"{text}"'

                    if folder_filter in filter_text:
                        filter_text = filter_text.replace(folder_filter, '')
                    else:
                        filter_text = f'{filter_text} {folder_filter}'

                    self.model().set_filter_text(filter_text)
                    self.repaint(self.rect())
                elif alt_modifier or control_modifier:
                    # The alt or control modifiers will add a "negative filter"
                    # and hide the selected sub-folder from the view
                    folder_filter = f'--"{text}"'
                    _folder_filter = f'"{text}"'

                    if filter_text:
                        if _folder_filter in filter_text:
                            filter_text = filter_text.replace(_folder_filter, '')
                        if folder_filter not in filter_text:
                            folder_filter = f'{filter_text} {folder_filter}'

                    self.model().set_filter_text(folder_filter)
                    self.repaint(self.rect())
                    return

    def mousePressEvent(self, event):
        """The `InlineIconView`'s mousePressEvent initiates multi-row
        flag toggling.

        This event is responsible for setting ``multi_toggle_pos``, the start
        position of the toggle, ``multi_toggle_state`` & ``multi_toggle_idx``
        the modes of the toggle, based on the state of the state and location of
        the clicked item.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            self.reset_multi_toggle()
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid() or not index.flags() & QtCore.Qt.ItemIsEnabled:
            super(InlineIconView, self).mousePressEvent(event)
            self.reset_multi_toggle()
            return

        self.reset_multi_toggle()

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())

        if rectangles[delegate.FavouriteRect].contains(cursor_position):
            self.multi_toggle_pos = QtCore.QPoint(0, cursor_position.y())
            self.multi_toggle_state = not index.flags() & common.MarkedAsFavourite
            self.multi_toggle_idx = delegate.FavouriteRect

        if rectangles[delegate.ArchiveRect].contains(cursor_position):
            self.multi_toggle_pos = cursor_position
            self.multi_toggle_state = not index.flags() & common.MarkedAsArchived
            self.multi_toggle_idx = delegate.ArchiveRect

        super(InlineIconView, self).mousePressEvent(event)

    def enterEvent(self, event):
        """Event handler.

        """
        QtWidgets.QApplication.instance().restoreOverrideCursor()
        super(InlineIconView, self).enterEvent(event)

    def leaveEvent(self, event):
        """Event handler.

        """
        app = QtWidgets.QApplication.instance()
        app.restoreOverrideCursor()

    def mouseReleaseEvent(self, event):
        """Concludes `InlineIconView`'s multi-item toggle operation, and
        resets the associated variables.

        The inline icon buttons are also triggered here. We're using the
        delegate's ``get_rectangles`` function to determine which icon was
        clicked.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            self.reset_multi_toggle()
            return

        # Let's handle the clickable rectangle event first
        self.clickable_rectangle_event(event)

        index = self.indexAt(event.pos())
        if not index.isValid():
            self.reset_multi_toggle()
            super(InlineIconView, self).mouseReleaseEvent(event)
            return

        if self.multi_toggle_items:
            self.reset_multi_toggle()
            super(InlineIconView, self).mouseReleaseEvent(event)
            self.model().invalidateFilter()
            return

        # Responding the click-events based on the position:
        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())
        cursor_position = self.mapFromGlobal(common.cursor.pos())

        self.reset_multi_toggle()

        if rectangles[delegate.FavouriteRect].contains(cursor_position):
            actions.toggle_favourite()
            if not self.model().filter_flag(common.MarkedAsFavourite):
                self.model().invalidateFilter()

        if rectangles[delegate.ArchiveRect].contains(cursor_position):
            actions.toggle_archived()
            if not self.model().filter_flag(common.MarkedAsArchived):
                self.model().invalidateFilter()

        if rectangles[delegate.RevealRect].contains(cursor_position):
            actions.reveal(index)

        if rectangles[delegate.TodoRect].contains(cursor_position):
            actions.show_todos()

        super(InlineIconView, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """``InlineIconView``'s mouse move event is responsible for
        handling the multi-toggle operations and repainting the current index
        under the mouse.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if self.verticalScrollBar().isSliderDown():
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        app = QtWidgets.QApplication.instance()
        if not app:
            return
        index = self.indexAt(cursor_position)
        if not index.isValid():
            app.restoreOverrideCursor()
            return

        modifiers = app.keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        if alt_modifier or shift_modifier or control_modifier:
            self.update(index)

        # Status messages
        if self.multi_toggle_pos is None:
            rectangles = delegate.get_rectangles(
                self.visualRect(index), self.inline_icons_count())

            if event.buttons() == QtCore.Qt.NoButton:
                if rectangles[delegate.PropertiesRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Edit item properties...')
                    self.update(index)
                elif rectangles[delegate.AddAssetRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Add New Item...')
                    self.update(index)
                elif rectangles[delegate.TodoRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Edit Notes...')
                    self.update(index)
                elif rectangles[delegate.RevealRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Show item in File Explorer...')
                    self.update(index)
                elif rectangles[delegate.ArchiveRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Archive item...')
                    self.update(index)
                elif rectangles[delegate.FavouriteRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Star item...')
                    self.update(index)
                elif rectangles[delegate.ThumbnailRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Drag and drop an image, or right-click to edit the thumbnail...')
                    self.update(index)
                elif rectangles[delegate.InlineBackgroundRect].contains(cursor_position):
                    common.signals.clearStatusBarMessage.emit()
                    self.update(index)
                elif rectangles[delegate.DataRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        index.data(common.PathRole))
                else:
                    common.signals.clearStatusBarMessage.emit()
                    self.update(index)

            if not index.isValid():
                app.restoreOverrideCursor()
                return

            rect = self.itemDelegate().get_description_rect(rectangles, index)
            if rect.contains(cursor_position):
                self.update(index)
                if app.overrideCursor():
                    app.changeOverrideCursor(
                        QtGui.QCursor(QtCore.Qt.IBeamCursor))
                else:
                    app.restoreOverrideCursor()
                    app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
            else:
                app.restoreOverrideCursor()
            super(InlineIconView, self).mouseMoveEvent(event)
            return

        if event.buttons() == QtCore.Qt.NoButton:
            return

        initial_index = self.indexAt(self.multi_toggle_pos)
        idx = index.row()

        # Exclude the current item
        if index == self.multi_toggle_item:
            return

        self.multi_toggle_item = index

        favourite = index.flags() & common.MarkedAsFavourite
        archived = index.flags() & common.MarkedAsArchived

        if idx not in self.multi_toggle_items:
            if self.multi_toggle_idx == delegate.FavouriteRect:
                self.multi_toggle_items[idx] = favourite
                self.toggle_item_flag(
                    index,
                    common.MarkedAsFavourite,
                    state=self.multi_toggle_state,
                    commit_now=False,
                )

            if self.multi_toggle_idx == delegate.ArchiveRect:
                self.multi_toggle_items[idx] = archived
                self.toggle_item_flag(
                    index,
                    common.MarkedAsArchived,
                    state=self.multi_toggle_state,
                    commit_now=False,
                )
            return

        if index == initial_index:
            return


class ThreadedItemView(InlineIconView):
    """Extends the :class:`InlineIconView` with the methods used to interface with
    threads.

    """
    workerInitialized = QtCore.Signal(str)
    refUpdated = QtCore.Signal(weakref.ref)
    queueItems = QtCore.Signal(list)

    queues = ()

    def __init__(self, icon='bw_icon', parent=None):
        self.delayed_queue_timer = common.Timer()
        self.delayed_queue_timer.setInterval(100)
        self.delayed_queue_timer.setSingleShot(True)

        super().__init__(icon=icon, parent=parent)

        self.update_queue = collections.deque([], common.max_list_items)
        self.update_queue_timer = common.Timer()
        self.update_queue_timer.setSingleShot(True)
        self.update_queue_timer.setInterval(1)
        self.update_queue_timer.timeout.connect(self.queued_row_update)

        self.init_threads()

    @common.debug
    @common.error
    def init_threads(self):
        """Starts and connects the threads."""
        for q in self.queues:
            thread = threads.get_thread(q)
            thread.start()

        # Wait for all threads to spin up before continuing
        n = 0.0
        import time
        while not all([threads.get_thread(f).isRunning() for f in self.queues]):
            n += 0.1
            time.sleep(0.1)
            if n > 2.0:
                break

    @common.error
    @common.debug
    def set_model(self, *args, **kwargs):
        """The methods responsible for connecting the associated item model with the view.

        """
        super().set_model(*args, **kwargs)
        self.refUpdated.connect(self.update_row)

        self.delayed_queue_timer.timeout.connect(self.save_visible_rows)
        self.delayed_queue_timer.timeout.connect(self.queue_visible_indexes)

        self.model().invalidated.connect(self.start_delayed_queue_timer)
        self.model().sourceModel().modelReset.connect(self.start_delayed_queue_timer)

        self.verticalScrollBar().valueChanged.connect(self.start_delayed_queue_timer)
        self.verticalScrollBar().sliderReleased.connect(self.start_delayed_queue_timer)

        self.model().filterTextChanged.connect(self.start_delayed_queue_timer)
        self.model().filterFlagChanged.connect(self.start_delayed_queue_timer)

        common.signals.tabChanged.connect(self.start_delayed_queue_timer)

    @QtCore.Slot()
    @common.debug
    def start_delayed_queue_timer(self, *args, **kwargs):
        """Starts the delayed queue timer.

        """
        self.delayed_queue_timer.start(self.delayed_queue_timer.interval())

    @common.status_bar_message('Updating items...')
    @common.debug
    def queue_visible_indexes(self, *args, **kwargs):
        """This method will send all currently visible items to the worker
        threads for processing.

        """
        proxy = self.model()
        if not proxy:
            return
        model = proxy.sourceModel()
        if not model:
            return

        data = model.model_data()

        show_archived = proxy.filter_flag(common.MarkedAsArchived)

        try:
            for q in self.queues:
                role = threads.THREADS[q]['role']

                # Skip queues that have their data already preloaded
                if threads.THREADS[q]['preload'] and data.loaded:
                    continue

                refs = []
                for idx in self.visible_rows['source_rows']:

                    # Item is already loaded, skip
                    if data[idx][role]:
                        continue

                    # Check if any of the current items are archived and invalidate
                    # the filter if it is meant to be hidden
                    is_archived = data[idx][common.FlagsRole] & common.MarkedAsArchived
                    if show_archived is False and is_archived:
                        proxy.invalidateFilter()
                        return

                    refs.append(weakref.ref(data[idx]))
                self.queueItems.emit(refs)
        except KeyError:
            pass
        except:
            raise

    @QtCore.Slot(int)
    def update_row(self, ref):
        """Queues an update request by the threads for later processing."""
        if not ref():
            return
        if ref()[common.TypeRole] != self.model().sourceModel().data_type():
            return
        if ref not in self.update_queue:
            self.update_queue.append(ref)
            self.update_queue_timer.start(self.update_queue_timer.interval())

    def queued_row_update(self):
        """Process a repaint request."""
        try:
            ref = self.update_queue.popleft()
        except IndexError:
            return

        if not ref():
            return

        for row in self.visible_rows['proxy_rows']:
            index = self.model().index(row, 0)
            if index.data(common.PathRole) == ref()[common.PathRole]:
                super().update(index)

        self.update_queue_timer.start(self.update_queue_timer.interval())

    @QtCore.Slot()
    @common.debug
    def save_visible_rows(self, *args, **kwargs):
        """Cache the currently visible rows.

        """
        self.visible_rows = {
            'source_rows': [],
            'ids': [],
            'proxy_rows': [],
        }

        # Find the first visible index
        r = self.rect()
        index = self.indexAt(r.topLeft())
        if not index.isValid():
            return

        model = index.model()

        rect = self.visualRect(index)
        i = 0

        while r.intersects(rect):
            if i >= 999:  # Don't check more than 999 items
                break
            i += 1

            self.visible_rows['proxy_rows'].append(index.row())
            # self.visible_rows['source_rows'].append(model.mapToSource(index).row())
            self.visible_rows['source_rows'].append(index.data(common.IdRole))

            rect.moveTop(rect.top() + rect.height())
            index = self.indexAt(rect.topLeft())
            if not index.isValid():
                break

