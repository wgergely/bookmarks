"""Base views used to show :mod:`bookmark <bookmarks.items.bookmark_items>`,
:mod:`asset <bookmarks.items.asset_items>`, and :mod:`file <bookmarks.items.file_items>`
items.

The view uses :class:`~bookmarks.items.models.ItemModel` for getting the item data,
:class:`~bookmarks.items.delegate.ItemDelegate` to paint the items.

:class:`BaseItemView` is a customised QListView widget augmented by
:class:`.InlineIconView` (adds inline icon functionality),
and :class:`.ThreadedItemView` that implement threading related functionality.

"""
import collections
import functools
import os
import re
import weakref

from PySide2 import QtWidgets, QtGui, QtCore

from . import delegate
from . import models
from .widgets import filter_editor
from .. import actions
from .. import common
from .. import contextmenu
from .. import database
from .. import images
from .. import log
from .. import ui
from ..threads import threads


class DropIndicatorWidget(QtWidgets.QWidget):
    """Widgets responsible for drawing an overlay."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        """Event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)
        pen = QtGui.QPen(common.Color.Blue())
        pen.setWidth(common.Size.Indicator())
        painter.setPen(pen)
        painter.setBrush(common.Color.Blue())
        painter.setOpacity(0.35)
        painter.drawRect(self.rect())
        painter.setOpacity(1.0)

        font, _ = common.Font.MediumFont(common.Size.MediumText())

        common.draw_aliased_text(
            painter,
            font,
            self.rect(),
            'Drop to add bookmark',
            QtCore.Qt.AlignCenter,
            common.Color.Blue()
        )

        painter.end()

    def show(self):
        """Shows and sets the size of the widget."""
        self.setGeometry(self.parent().geometry())
        super().show()


class DragPixmapFactory(QtWidgets.QWidget):
    """Widget used to define the appearance of an item being dragged."""

    def __init__(self, pixmap, text, parent=None):
        super().__init__(parent=parent)
        self._pixmap = pixmap
        self._text = text

        _, metrics = common.MediumFont(common.Size.MediumText())
        self._text_width = metrics.horizontalAdvance(text)

        width = self._text_width + common.Size.Margin()
        width = (
            common.Size.DefaultWidth() + common.Size.Margin()
            if width > common.Size.DefaultWidth() else width
        )

        self.setFixedHeight(common.Size.RowHeight())

        longest_edge = max((pixmap.width(), pixmap.height()))
        o = common.Size.Indicator()
        self.setFixedWidth(
            longest_edge + (o * 2) + width
        )

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.adjustSize()

    @classmethod
    def pixmap(cls, pixmap, text):
        """Returns the widget as a rendered pixmap."""
        w = cls(pixmap, text)
        pixmap = QtGui.QPixmap(w.size() * common.pixel_ratio, )
        pixmap.setDevicePixelRatio(common.pixel_ratio)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        w.render(painter, QtCore.QPoint(), QtGui.QRegion())
        return pixmap

    def paintEvent(self, event):
        """Event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.Color.DarkBackground())
        painter.setOpacity(0.6)
        o = common.Size.Indicator()
        painter.drawRoundedRect(self.rect(), o, o)
        painter.setOpacity(1.0)

        pixmap_rect = QtCore.QRect(
            0, 0, common.Size.RowHeight(), common.Size.RowHeight()
        )
        painter.drawPixmap(pixmap_rect, self._pixmap, self._pixmap.rect())

        width = self._text_width + common.Size.Indicator()
        max_width = common.Size.DefaultWidth()
        width = max_width if width > max_width else width
        rect = QtCore.QRect(
            common.Size.RowHeight() + common.Size.Indicator(),
            0,
            width,
            self.height()
        )
        common.draw_aliased_text(
            painter,
            common.Font.MediumFont(common.Size.MediumText())[0],
            rect,
            self._text,
            QtCore.Qt.AlignCenter,
            common.Color.SelectedText()
        )
        painter.end()


class ItemDrag(QtGui.QDrag):
    """A utility class used to start a drag operation.

    """

    def __init__(self, index, widget):
        super().__init__(widget)

        model = index.model().sourceModel()
        self.setMimeData(model.mimeData([index, ]))

        def _get(s, color=common.Color.Green()):
            return images.rsc_pixmap(
                s, color,
                common.Size.Margin() * common.pixel_ratio
            )

        # Set drag icon
        self.setDragCursor(_get('add_circle'), QtCore.Qt.CopyAction)
        self.setDragCursor(_get('file'), QtCore.Qt.MoveAction)
        self.setDragCursor(
            _get('close', color=common.Color.Red()),
            QtCore.Qt.ActionMask
        )
        self.setDragCursor(
            _get('close', color=common.Color.Red()),
            QtCore.Qt.IgnoreAction
        )

        # Set file item apperance
        if index.data(common.ItemTabRole) in (common.BookmarkTab, common.AssetTab):
            pixmap = images.rsc_pixmap(
                'copy',
                common.Color.DisabledText(),
                common.Size.RowHeight()
            )
            pixmap = DragPixmapFactory.pixmap(pixmap, '< Item Properties >')
            self.setPixmap(pixmap)

        if index.data(common.ItemTabRole) in (common.FileTab, common.FavouriteTab):
            source = index.data(common.PathRole)

            modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
            no_modifier = modifiers == QtCore.Qt.NoModifier
            alt_modifier = modifiers & QtCore.Qt.AltModifier
            shift_modifier = modifiers & QtCore.Qt.ShiftModifier

            if no_modifier:
                source = common.get_sequence_end_path(source)
                pixmap, _ = images.get_thumbnail(
                    index.data(common.ParentPathRole)[0],
                    index.data(common.ParentPathRole)[1],
                    index.data(common.ParentPathRole)[2],
                    source,
                    size=common.Size.RowHeight(),
                )
            elif alt_modifier and shift_modifier:
                pixmap = images.rsc_pixmap(
                    'folder', common.Color.SecondaryText(),
                    common.Size.RowHeight()
                )
                source = QtCore.QFileInfo(source).dir().path()
            elif alt_modifier:
                pixmap = images.rsc_pixmap(
                    'file', common.Color.SecondaryText(),
                    common.Size.RowHeight()
                )
                source = common.get_sequence_start_path(source)
            elif shift_modifier:
                source = common.get_sequence_start_path(source) + ', ++'
                pixmap = images.rsc_pixmap(
                    'multiples_files', common.Color.SecondaryText(),
                    common.Size.RowHeight()
                )
            else:
                return

            if pixmap and not pixmap.isNull():
                pixmap = DragPixmapFactory.pixmap(pixmap, source)
                self.setPixmap(pixmap)


class ListsWidget(QtWidgets.QStackedWidget):
    """This stacked widget contains the main :class:`~bookmarks.items.bookmark_items.BookmarkItemView`,
    :class:`~bookmarks.items.asset_items.AssetItemView`, :class:`~bookmarks.items.file_items.FileItemView` and
    :class:`~bookmarks.items.favourite_items.FavouriteItemView`.
    widgets.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('BrowserStackedWidget')

        self.animation_in_progress = False

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

        current_index = self.currentIndex()
        if current_index == idx:
            return

        @QtCore.Slot()
        def animation_finished(a):
            anim = a.animationAt(1)
            if not anim:
                return
            if isinstance(anim.targetObject(), QtWidgets.QWidget):
                _idx = self.indexOf(anim.targetObject())
                super(ListsWidget, self).setCurrentIndex(_idx)
                common.signals.tabChanged.emit(_idx)

        @QtCore.Slot()
        def animation_state_changed(state, old_state):
            if state == QtCore.QAbstractAnimation.Running:
                self.animation_in_progress = True
            if state == QtCore.QAbstractAnimation.Stopped:
                self.animation_in_progress = False

        animation = QtCore.QParallelAnimationGroup()
        animation.finished.connect(functools.partial(animation_finished, animation))
        animation.stateChanged.connect(animation_state_changed)

        duration = 200

        # Create animation for outgoing widget
        out_anim = QtCore.QPropertyAnimation(self.widget(current_index), b"geometry")
        out_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        out_anim.setDuration(duration)

        out_rect = self.currentWidget().geometry()
        if current_index > idx:
            out_rect.moveLeft(self.width())
        else:
            out_rect.moveLeft(-self.width())
        out_anim.setStartValue(self.currentWidget().geometry())
        out_anim.setEndValue(out_rect)

        # Create animation for incoming widget
        in_anim = QtCore.QPropertyAnimation(self.widget(idx), b"geometry")
        in_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        in_anim.setDuration(duration)

        in_rect = self.currentWidget().geometry()
        if current_index > idx:
            in_rect.moveLeft(-in_rect.width())
        else:
            in_rect.moveLeft(in_rect.width())
        in_anim.setStartValue(in_rect)
        in_anim.setEndValue(self.currentWidget().geometry())

        out_op = QtCore.QPropertyAnimation(self.widget(current_index).graphicsEffect(), b"opacity")
        out_op.setStartValue(1.0)
        out_op.setEndValue(0.0)
        in_op = QtCore.QPropertyAnimation(self.widget(idx).graphicsEffect(), b"opacity")
        in_op.setStartValue(0.0)
        in_op.setEndValue(1.0)

        animation.addAnimation(out_anim)
        animation.addAnimation(in_anim)
        animation.addAnimation(out_op)
        animation.addAnimation(in_op)

        animation.start(QtCore.QPropertyAnimation.DeleteWhenStopped)
        self.widget(idx).show()

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
        super().__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setWindowFlags(QtCore.Qt.Widget)
        self._message = 'Loading...'

        self._connect_signals()

    def _connect_signals(self):
        pass

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
        color = common.Color.VeryDarkBackground()
        painter.setBrush(color)
        painter.drawRect(self.rect())
        painter.setOpacity(0.8)
        common.draw_aliased_text(
            painter,
            common.Font.MediumFont(common.Size.MediumText())[0],
            self.rect(),
            self._message,
            QtCore.Qt.AlignCenter,
            common.Color.Text()
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

    def _connect_signals(self):
        super()._connect_signals()

        common.signals.bookmarkItemActivated.connect(self.update)
        common.signals.assetItemActivated.connect(self.update)
        common.signals.tabChanged.connect(self.update)
        common.signals.updateTopBarButtons.connect(self.update)
        common.signals.filterTextChanged.connect(self.update)

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

        o = common.Size.Separator()
        rect = self.rect().adjusted(o, o, -o, -o)
        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(common.Color.Blue())
        pen.setWidth(common.Size.Separator(2.0))
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
        painter.setBrush(common.Color.Red())
        painter.setOpacity(0.8)

        rect = self.rect()
        rect.setHeight(common.Size.Separator(2.0))
        painter.drawRect(rect)
        rect.moveBottom(self.rect().bottom())
        painter.drawRect(rect)

        painter.restore()

    def showEvent(self, event):
        """Event handler.

        """
        self.repaint()


class BaseItemView(QtWidgets.QTableView):
    """The base view of all subsequent item views.

    """
    #: Emitted when the user shift+right-clicks on the view. Use this to show DCC
    #: specific context menus.
    customContextMenuRequested = QtCore.Signal(
        QtCore.QModelIndex, QtCore.QObject
    )
    #: Called when the user requests model data load by pressing the ESC key.
    interruptRequested = QtCore.Signal()

    #: Signals window size change
    resized = QtCore.Signal(QtCore.QRect)

    ThumbnailContextMenu = ThumbnailsContextMenu
    Delegate = delegate.ItemDelegate
    ContextMenu = None

    def __init__(self, icon='icon_bw', parent=None):
        super().__init__(parent=parent)
        self.visible_rows = {
            'source_rows': [],
            'ids': [],
            'proxy_rows': []
        }

        self.setGraphicsEffect(QtWidgets.QGraphicsOpacityEffect(self))
        self.graphicsEffect().setOpacity(1.0)

        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.verticalHeader().setHidden(True)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setHidden(True)

        self.drop_indicator_widget = DropIndicatorWidget(parent=self)
        self.drop_indicator_widget.hide()

        self.drag_current_row = -1
        self.drag_source_row = -1

        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(False)
        self.viewport().setAcceptDrops(True)
        self.setAcceptDrops(False)

        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed
        )

        self._buttons_hidden = False
        self._thumbnail_drop = (-1, False)  # row, accepted state
        self._background_icon = icon

        self.progress_indicator_widget = ProgressWidget(parent=self)
        self.progress_indicator_widget.setHidden(True)

        self.filter_indicator_widget = FilterOnOverlayWidget(parent=self)
        self.filter_editor = filter_editor.TextFilterEditor(parent=self.parent())
        self.filter_editor.setHidden(True)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setShowGrid(False)
        self.setMouseTracking(True)
        self.setWordWrap(False)

        self.installEventFilter(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        # Keyboard search timer and placeholder string.
        self.timer = common.Timer(parent=self)
        self.timer.setInterval(
            QtWidgets.QApplication.instance().keyboardInputInterval()
        )
        self.timer.setSingleShot(True)
        self.timed_search_string = ''

        self.delayed_layout_timer = common.Timer(parent=self)
        self.delayed_layout_timer.setSingleShot(True)
        self.delayed_layout_timer.setInterval(33)

        self.delayed_save_selection_timer = common.Timer(parent=self)
        self.delayed_save_selection_timer.setSingleShot(True)
        self.delayed_save_selection_timer.setInterval(100)

        self.delayed_restore_selection_timer = common.Timer(parent=self)
        self.delayed_restore_selection_timer.setInterval(100)
        self.delayed_restore_selection_timer.setSingleShot(True)

        self.delayed_save_visible_timer = common.Timer(parent=self)
        self.delayed_save_visible_timer.setInterval(100)
        self.delayed_save_visible_timer.setSingleShot(True)

        self.delayed_reset_row_layout_timer = common.Timer(parent=self)
        self.delayed_reset_row_layout_timer.setInterval(100)
        self.delayed_reset_row_layout_timer.setSingleShot(True)

        self.setItemDelegate(self.Delegate(parent=self))

        self.init_model()
        self._connect_signals()

    def _connect_signals(self):
        self.resized.connect(self.filter_indicator_widget.setGeometry)
        self.resized.connect(self.progress_indicator_widget.setGeometry)
        self.resized.connect(self.filter_editor.setGeometry)
        self.delayed_layout_timer.timeout.connect(self.scheduleDelayedItemsLayout)
        self.delayed_layout_timer.timeout.connect(self.repaint_visible_rows)
        self.delayed_save_selection_timer.timeout.connect(self.save_selection)
        self.delayed_restore_selection_timer.timeout.connect(self.restore_selection)
        self.delayed_save_visible_timer.timeout.connect(self.save_visible_rows)
        self.delayed_reset_row_layout_timer.timeout.connect(self.reset_row_layout)

    def get_source_model(self):
        """Returns the model class associated with this view.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    @common.error
    @common.debug
    def init_buttons_hidden(self):
        """Restore the previous state of the inline icon buttons.

        """
        model = self.model().sourceModel()
        v = model.get_filter_setting('filters/buttons')
        v = False if not v else v
        self._buttons_hidden = v

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons.

        """
        if self.width() < common.Size.DefaultWidth(0.66):
            return True
        return self._buttons_hidden

    def set_buttons_hidden(self, val):
        """Sets the visibility of the inline icon buttons.

        """
        self.model().sourceModel().set_filter_setting('filters/buttons', val)
        self._buttons_hidden = val

    @common.error
    @common.debug
    def init_model(self):
        """Add a model to the view.

        The ItemModel subclasses are wrapped in a QSortFilterProxyModel. All
        the necessary internal signal-slot connections needed for the proxy, model
        and the view to communicate are made here.

        """
        model = self.get_source_model()
        proxy = models.FilterProxyModel(parent=self)
        proxy.setSourceModel(model)
        self.setModel(proxy)

        self.init_buttons_hidden()
        model.init_sort_values()
        model.init_row_size()
        self.verticalHeader().setDefaultSectionSize(int(model.row_size.height()))
        proxy.init_filter_values()

        proxy.filterTextChanged.connect(self.filter_editor.editor.setText)

        model.modelReset.connect(model.init_sort_values)
        model.modelReset.connect(proxy.init_filter_values)
        model.modelReset.connect(model.init_row_size)
        model.modelReset.connect(self.init_buttons_hidden)
        model.modelReset.connect(self.reset_multi_toggle)
        model.modelReset.connect(
            lambda: self.delayed_layout_timer.start(self.delayed_layout_timer.interval())
        )

        self.interruptRequested.connect(model.set_interrupt_requested)

        self.filter_editor.finished.connect(proxy.set_filter_text)

        model.modelReset.connect(self.delay_restore_selection)
        proxy.invalidated.connect(self.delay_restore_selection)

        model.modelReset.connect(self.delayed_save_visible_rows)
        proxy.modelReset.connect(self.delayed_save_visible_rows)
        proxy.invalidated.connect(self.delayed_save_visible_rows)

        model.updateIndex.connect(
            self.update, type=QtCore.Qt.DirectConnection
        )

        common.signals.paintThumbnailBGChanged.connect(
            self.repaint_visible_rows
        )
        model.rowHeightChanged.connect(self.row_size_changed)

    @QtCore.Slot(int)
    def row_size_changed(self, v):
        v = int(v)
        self.verticalHeader().setDefaultSectionSize(v)
        self.delayed_reset_row_layout()
        self.delayed_save_visible_rows()

    @QtCore.Slot(QtCore.QModelIndex)
    def update(self, index):
        """This slot is used by all threads to repaint/update the given index
        after it's thumbnail or file information has been loaded.

        An actual repaint event will only trigger if the index is visible
        in the view.

        """
        if not index.isValid():
            return

        # If a source model index has been passed here, map it to the
        # proxy model index. This shouldn't be happening, but...
        if hasattr(index.model(), 'mapFromSource'):
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
            self.delayed_save_selection_timer.interval()
        )

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
            self.delayed_restore_selection_timer.interval()
        )

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
                self.selectionModel().select(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect |
                    QtCore.QItemSelectionModel.Rows
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
            self.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            self.selectionModel().setCurrentIndex(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
            return

        # Select the first item in the list
        index = proxy.index(0, 0)
        self.selectionModel().select(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )
        self.selectionModel().setCurrentIndex(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )
        self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def toggle_item_flag(self, index, flag, state=None, commit_now=True):
        """Sets the index's filter flag value based on the passed state.

        We're using the method to mark items archived, or favourite and save the
        changes to the database and the user settings file.

        Args:
            index (QModelIndex): Model index.
            flag (int): A filter flag, for example, ``MarkedAsArchived``.
            state (bool): Pass an explicit state value. Defaults to None.
            commit_now (bool): When `True`, commits database values immediately.

        Returns:
            str: The key used to find and match items.

        """

        def _save_to_db(k, mode, flag):
            if not commit_now:
                threads.queue_database_transaction(
                    server, job, root, k, mode, flag
                )
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
                common.FlagsRole
        ) & common.MarkedAsDefault:
            common.show_message('Default bookmark items cannot be archived.', message_type='error')
            return
        # Ignore active items
        if flag == common.MarkedAsArchived and index.data(
                common.FlagsRole
        ) & common.MarkedAsActive:
            common.show_message('Active bookmark items cannot be archived.', message_type='error')
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
            # Set the item flag data
            if mode:
                data[common.FlagsRole] = data[common.FlagsRole] | flag
            else:
                data[common.FlagsRole] = data[common.FlagsRole] & ~flag

            # Save the flag value to the data container
            if commit:
                save_func(k, mode, flag)

            # Notify the flag value change
            if flag == common.MarkedAsArchived and mode:
                common.signals.itemArchived.emit(
                    data[common.ParentPathRole],
                    data[common.PathRole],
                )
            if flag == common.MarkedAsArchived and not mode:
                common.signals.itemUnarchived.emit(
                    data[common.ParentPathRole],
                    data[common.PathRole],
                )

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
                db = database.get(*index.data(common.ParentPathRole)[0:3])

                flags = db.value(
                    proxy_k,
                    'flags',
                    database.AssetTable
                )
                flags = flags if flags else 0

                # Active items can't be archived
                if flags & common.MarkedAsActive:
                    return False

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

        if hasattr(index.model(), 'mapToSource'):
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
                common.show_message(
                    'Looks like this item belongs to a sequence that has a flag set '
                    'already.',
                    body='To modify individual sequence items, remove the flag from the '
                         'sequence first and try again.',
                    message_type=None
                )
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
        model = self.selectionModel()
        if model.hasSelection():
            current_index = next(f for f in model.selectedIndexes())
        else:
            current_index = QtCore.QModelIndex()

        first_index = self.model().index(0, 0)
        last_index = self.model().index(
            self.model().rowCount() - 1, 0
        )

        if first_index == last_index:
            return
        if not current_index.isValid():  # No selection
            model.select(
                first_index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            model.setCurrentIndex(
                first_index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            return

        if current_index == last_index:  # Last item is selected
            model.select(
                first_index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            model.setCurrentIndex(
                first_index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            return

        model.select(
            self.model().index(current_index.row() + 1, 0),
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )
        model.setCurrentIndex(
            self.model().index(current_index.row() + 1, 0),
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )

    def key_up(self):
        """Custom action to perform when the `up` arrow is pressed
        on the keyboard.

        We're implementing a continuous scroll: when reaching the last
        item in the list, we'll jump to the beginning, and vice-versa.

        """

        model = self.selectionModel()
        if model.hasSelection():
            current_index = next(f for f in model.selectedIndexes())
        else:
            current_index = QtCore.QModelIndex()

        self.itemDelegate().closeEditor.emit(None, QtWidgets.QAbstractItemDelegate.NoHint)

        first_index = self.model().index(0, 0)
        last_index = self.model().index(self.model().rowCount() - 1, 0)

        if first_index == last_index:
            return

        if not current_index.isValid():  # No selection
            model.select(
                last_index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            model.setCurrentIndex(
                last_index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            return
        if current_index == first_index:  # First item is selected
            model.select(
                last_index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            model.setCurrentIndex(
                last_index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            return

        model.select(
            self.model().index(current_index.row() - 1, 0),
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )
        model.setCurrentIndex(
            self.model().index(current_index.row() - 1, 0),
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )

    def key_tab(self):
        """Custom key action
        
        """
        if not self.selectionModel().hasSelection():
            return
        index = next(f for f in self.selectionModel().selectedIndexes())
        if index.column() == 0:
            self.edit(index)

    def key_enter(self):
        """Custom key action
        
        """
        if self.state() == QtWidgets.QAbstractItemView.EditingState:
            self.key_down()
            self.key_up()
            return
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
        self._paint_message(text, color=common.Color.Green())

    def paint_loading(self, widget, event):
        """Paints the hint message.

        """
        text = 'Loading items. Please wait...'
        self._paint_message(text, color=common.Color.Text())

    def paint_status_message(self, widget, event):
        """Displays a visual hint for the user to indicate if the list
        has hidden items.

        """
        text = self.get_status_string()
        self._paint_message(text, color=common.Color.Red())

    def _paint_message(self, text, color=common.Color.Text()):
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
        o = common.Size.Indicator()

        rect = rect.adjusted(o * 3, o, -o * 3, -o)

        font, metrics = common.Font.MediumFont(common.Size.SmallText())
        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            rect.width()
        )

        x = rect.center().x() - (metrics.horizontalAdvance(text) / 2.0)
        y = rect.center().y() + (metrics.ascent() / 2.0)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)
        delegate.draw_painter_path(painter, x, y, font, text)
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

    def delayed_reset_row_layout(self):
        self.delayed_reset_row_layout_timer.start(
            self.delayed_reset_row_layout_timer.interval()
        )

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

        # Restore the selection
        if row >= 0:
            index = proxy.index(row, 0)
            self.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            self.selectionModel().setCurrentIndex(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            self.scrollTo(
                index, QtWidgets.QAbstractItemView.PositionAtCenter
            )

    def set_row_size(self, v):
        """Sets the row size.
        
        Args:
            v (int): The new row size
            
        """
        proxy = self.model()
        model = proxy.sourceModel()

        if model.row_size.height() == v:
            return

        model.row_size.setHeight(int(v))
        model.set_filter_setting('filters/row_heights', int(v))

        self.verticalHeader().setDefaultSectionSize(int(v))
        self.delayed_reset_row_layout()
        self.delayed_save_visible_rows()

    @common.error
    @common.debug
    @QtCore.Slot(str)
    def show_item(self, v, role=QtCore.Qt.DisplayRole, update=True, limit=10000):
        """Show an item in the view.

        Args:
            v (any): A value to match.
            role (QtCore.Qt.ItemRole): An item data role.
            update (bool): Refreshes the model if `True` (the default).
            limit (int): Maximum item search number.

        """
        proxy = self.model()
        model = proxy.sourceModel()

        p = model.source_path()

        if p and len(p) == 3:
            # Read from the cache if it exists
            source = '/'.join(p)
            assets_cache_dir = QtCore.QDir(
                f'{common.active("root", path=True)}/{common.bookmark_item_data_dir}/assets')
            if not assets_cache_dir.exists():
                assets_cache_dir.mkpath('.')

            assets_cache_name = common.get_hash(source)
            cache = f'{assets_cache_dir.path()}/{assets_cache_name}.cache'

            if assets_cache_dir.exists() and os.path.exists(cache):
                log.debug('Removing asset cache:', cache)
                os.remove(cache)

            if update and model.rowCount() < limit:
                model.reset_data(force=True, emit_active=False)

        # Delay the selection to let the model process events
        QtCore.QTimer.singleShot(
            100, functools.partial(
                self.select_item, v, role=role
            )
        )

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
                self.selectionModel().select(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect |
                    QtCore.QItemSelectionModel.Rows
                )
                self.selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect |
                    QtCore.QItemSelectionModel.Rows
                )
                self.scrollTo(
                    index,
                    hint=QtWidgets.QAbstractItemView.PositionAtCenter
                )
                self.save_selection()
                return

    def _reset_drag_indicators(self):
        self._thumbnail_drop = (-1, False)
        self.drag_source_row = -1
        self.drag_current_row = -1
        self.stopAutoScroll()
        self.setState(QtWidgets.QAbstractItemView.NoState)
        self.viewport().update()

    def dragMoveEvent(self, event):
        """Drag move events checks source validity against available drop actions.

        """
        self._thumbnail_drop = (-1, False)

        pos = self.viewport().mapFromGlobal(common.cursor.pos())
        index = self.indexAt(pos)

        if not index.isValid():
            event.ignore()
            self.viewport().update()
            return

        proxy = self.model()
        model = proxy.sourceModel()
        index = proxy.mapToSource(index)

        # Thumbnail image drop
        if model.can_drop_image_file(
                event.mimeData(),
                event.proposedAction(),
                index.row(),
                0,
                QtCore.QModelIndex()
        ):
            self._thumbnail_drop = (index.row(), True)
            event.accept()
            self.viewport().update()
            return

        # Internal property copy
        if model.can_drop_properties(
                event.mimeData(),
                event.proposedAction(),
                index.row(),
                0,
                QtCore.QModelIndex()
        ):
            event.accept()
            self._thumbnail_drop = (-1, False)
            self.viewport().update()
            return

        self._thumbnail_drop = (-1, False)
        self.viewport().update()
        return super().dragMoveEvent(event)

    def startDrag(self, supported_actions):
        """Drag action start.

        """
        index = common.get_selected_index(self)
        if not index.isValid():
            return super().startDrag(supported_actions)
        if not index.data(common.PathRole):
            return super().startDrag(supported_actions)
        if not index.data(common.ParentPathRole):
            return super().startDrag(supported_actions)

        self.drag_source_row = index.row()

        drag = ItemDrag(index, self)
        QtCore.QTimer.singleShot(1, self.viewport().update)
        drag.exec_(supported_actions)
        QtCore.QTimer.singleShot(10, self._reset_drag_indicators)

    def dropEvent(self, event):
        """Event handler.

        """

        pos = common.cursor.pos()
        pos = self.viewport().mapFromGlobal(pos)

        index = self.indexAt(pos)
        if not index.isValid():
            event.ignore()
            self._reset_drag_indicators()
            return

        proxy = self.model()
        model = proxy.sourceModel()
        index = proxy.mapToSource(index)

        if model.dropMimeData(
                event.mimeData(),
                event.proposedAction(),
                index.row(),
                0,
                QtCore.QModelIndex()
        ):
            event.accept()
            self._reset_drag_indicators()
            return

        event.ignore()
        self._reset_drag_indicators()

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
                if self.state() == QtWidgets.QAbstractItemView.EditingState:
                    self.key_down()
                    self.key_up()
                    return

                self.interruptRequested.emit()

                if self.selectionModel().hasSelection():
                    self.selectionModel().select(
                        QtCore.QModelIndex(),
                        QtCore.QItemSelectionModel.ClearAndSelect |
                        QtCore.QItemSelectionModel.Rows
                    )
                    self.selectionModel().setCurrentIndex(
                        QtCore.QModelIndex(),
                        QtCore.QItemSelectionModel.ClearAndSelect |
                        QtCore.QItemSelectionModel.Rows
                    )
                return
            if event.key() == QtCore.Qt.Key_Space:
                self.key_space()
                self.delay_save_selection()
                return
            if event.key() == QtCore.Qt.Key_Down:
                self.key_down()
                self.delay_save_selection()
                return
            if event.key() == QtCore.Qt.Key_Up:
                self.key_up()
                self.delay_save_selection()
                return
            if (event.key() == QtCore.Qt.Key_Return) or (
                    event.key() == QtCore.Qt.Key_Enter):
                self.key_enter()
                self.delay_save_selection()
                return
            if event.key() == QtCore.Qt.Key_Tab:
                if not self.state() == QtWidgets.QAbstractItemView.EditingState:
                    self.key_tab()
                    self.delay_save_selection()
                    return
                else:
                    self.key_down()
                    self.key_tab()
                    self.delay_save_selection()
                    return
            if event.key() == QtCore.Qt.Key_Backtab:
                if not self.state() == QtWidgets.QAbstractItemView.EditingState:
                    self.key_tab()
                    self.delay_save_selection()
                    return
                else:
                    self.key_up()
                    self.key_tab()
                    self.delay_save_selection()
                    return
            if event.key() == QtCore.Qt.Key_PageDown:
                super().keyPressEvent(event)
                self.delay_save_selection()
                return
            if event.key() == QtCore.Qt.Key_PageUp:
                super().keyPressEvent(event)
                self.delay_save_selection()
                return
            if event.key() == QtCore.Qt.Key_Home:
                super().keyPressEvent(event)
                self.delay_save_selection()
                return
            if event.key() == QtCore.Qt.Key_End:
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
                        self.selectionModel().select(
                            index,
                            QtCore.QItemSelectionModel.ClearAndSelect |
                            QtCore.QItemSelectionModel.Rows
                        )
                        self.selectionModel().setCurrentIndex(
                            index,
                            QtCore.QItemSelectionModel.ClearAndSelect |
                            QtCore.QItemSelectionModel.Rows
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
                        self.selectionModel().select(
                            index,
                            QtCore.QItemSelectionModel.ClearAndSelect |
                            QtCore.QItemSelectionModel.Rows
                        )
                        self.selectionModel().setCurrentIndex(
                            index,
                            QtCore.QItemSelectionModel.ClearAndSelect |
                            QtCore.QItemSelectionModel.Rows
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
        event.ignore()
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier

        if not control_modifier:
            shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier

            # Adjust the scroll amount based on the row size
            if self.model().sourceModel().row_size.height() > (
                    common.Size.RowHeight(2.0)):
                o = 9 if shift_modifier else 1
            else:
                o = 9 if shift_modifier else 3

            v = self.verticalScrollBar().value()
            if event.angleDelta().y() > 0:
                v = self.verticalScrollBar().setValue(v + o)
            else:
                v = self.verticalScrollBar().setValue(v - o)
            self.start_delayed_queue_timer()
            return

        if event.angleDelta().y() > 0:
            actions.increase_row_size()
        else:
            actions.decrease_row_size()
        self.start_delayed_queue_timer()

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        index = self.indexAt(event.pos())
        if index.isValid() and index.column() != 0:
            return

        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier

        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit(index, self)
            return

        if not self.ContextMenu:
            return

        rectangles = self.itemDelegate().get_rectangles(index)
        if index.isValid() and rectangles[delegate.ThumbnailRect].contains(event.pos()):
            widget = self.ThumbnailContextMenu(index, parent=self)
        else:
            widget = self.ContextMenu(index, parent=self)

        widget.move(common.cursor.pos())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def mousePressEvent(self, event):
        """Deselect the current index when clicked on an empty space.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return

        cursor_position = self.viewport().mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            self.selectionModel().select(
                QtCore.QModelIndex(),
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
            )
            self.selectionModel().setCurrentIndex(
                QtCore.QModelIndex(),
                QtCore.QItemSelectionModel.ClearAndSelect |
                QtCore.QItemSelectionModel.Rows
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

        cursor_position = self.viewport().mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        if index.column() == 0:
            rectangles = self.itemDelegate().get_rectangles(index)

            _rect = self.visualRect(index)
            rect = delegate.get_description_rectangle(index, _rect, self.buttons_hidden())

            if rect and rect.contains(cursor_position):
                self.edit(index)
                return

            if rectangles[delegate.ThumbnailRect].contains(cursor_position):
                actions.pick_thumbnail_from_file()
                return

            if rectangles[delegate.DataRect].contains(cursor_position):
                index = common.get_selected_index(self)
                if not index.isValid():
                    return
                self.activate(index)
        else:
            super().mouseDoubleClickEvent(event)


class InlineIconView(BaseItemView):
    """Adds multi-toggle and clickable in-line icons to :class:`BaseItemView`.

    """

    def __init__(self, icon='bw_icon', parent=None):
        super().__init__(icon=icon, parent=parent)

        self._clicked_rect = QtCore.QRect()

        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_flag = None
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
        self.multi_toggle_flag = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

    def clickable_rectangle_event(self, event):
        """Handle mouse press & release events on an item's interactive rectangle.

        The clickable rectangles are defined by and stored by the item delegate. See
        :meth:`~bookmarks.items.ItemDelegate.get_clickable_rectangles`.

        We're implementing filtering by reacting to clicks on item labels:
        ``shift`` modifier will add a _positive_ filter and hide all items not
        containing the clicked rectangle's text content.

        The ``alt`` and ``control`` modifiers will add a negative filter and hide all
        items containing the clicked rectangle's text content.

        """
        cursor_position = self.viewport().mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)

        if not index.isValid():
            return
        if not index.flags() & QtCore.Qt.ItemIsEnabled:
            return
        if not index.column() == 0:
            return

        # Get pressed keyboard modifiers
        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        # Get clickable rectangles from the delegate
        rect = self.visualRect(index)
        clickable_rectangles = delegate.get_clickable_rectangles(index, rect)
        if not clickable_rectangles:
            return

        cursor_position = self.viewport().mapFromGlobal(common.cursor.pos())

        for item in clickable_rectangles:
            if not item:
                continue

            rect, text = item
            if not text:
                continue
            if not rect.contains(cursor_position):
                continue

            text = f'"{text}"'

            # Shift modifier toggles a text filter
            if shift_modifier:
                if self.model().filter.has_string(text, positive_terms=True):
                    self.model().filter.remove_filter(text)
                else:
                    self.model().filter.add_filter(text)
                self.model().set_filter_text(self.model().filter.filter_string)
                self.update(index)
                return

            # Alt or control modifiers toggle a negative filter
            if alt_modifier or control_modifier:
                self.model().filter.remove_filter(text)
                self.model().set_filter_text(self.model().filter.filter_string)
                self.update(index)
                return

    def mousePressEvent(self, event):
        """The `InlineIconView`'s mousePressEvent initiates multi-row
        flag toggling.

        This event is responsible for setting ``multi_toggle_pos``, the start
        position of the toggle, ``multi_toggle_state`` & ``multi_toggle_flag``
        the modes of the toggle, based on the state of the state and location of
        the clicked item.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            self.reset_multi_toggle()
            return

        cursor_position = self.viewport().mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)

        if index.column() == 0:
            if not index.isValid() or not index.flags() & QtCore.Qt.ItemIsEnabled:
                super().mousePressEvent(event)
                self._clicked_rect = QtCore.QRect()
                self.reset_multi_toggle()
                return

            self.reset_multi_toggle()

            rectangles = self.itemDelegate().get_rectangles(index)

            self._clicked_rect = next(
                (rectangles[f] for f in (
                    delegate.AddItemRect,
                    delegate.TodoRect,
                    delegate.RevealRect,
                    delegate.PropertiesRect,
                    delegate.ArchiveRect,
                    delegate.FavouriteRect,
                ) if rectangles[f].contains(cursor_position)),
                QtCore.QRect()
            )

            if rectangles[delegate.FavouriteRect].contains(cursor_position):
                self.multi_toggle_pos = QtCore.QPoint(0, cursor_position.y())
                self.multi_toggle_state = not index.flags() & common.MarkedAsFavourite
                self.multi_toggle_flag = delegate.FavouriteRect

            if rectangles[delegate.ArchiveRect].contains(cursor_position):
                self.multi_toggle_pos = cursor_position
                self.multi_toggle_state = not index.flags() & common.MarkedAsArchived
                self.multi_toggle_flag = delegate.ArchiveRect

        super().mousePressEvent(event)

    def enterEvent(self, event):
        """Event handler.

        """
        QtWidgets.QApplication.instance().restoreOverrideCursor()
        super().enterEvent(event)

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

        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        index = self.indexAt(event.pos())

        if not index.isValid():
            return

        if index.column() == 0:
            if not index.data(common.FlagsRole):
                return
            archived = index.data(common.FlagsRole) & common.MarkedAsArchived

            # Let's handle the clickable rectangle event first
            if not archived:
                self.clickable_rectangle_event(event)

            if not index.isValid():
                self.reset_multi_toggle()
                super().mouseReleaseEvent(event)
                return

            if self.multi_toggle_items:
                self.reset_multi_toggle()
                super().mouseReleaseEvent(event)
                self.model().invalidateFilter()
                return

            # Responding the click-events based on the position:
            rectangles = self.itemDelegate().get_rectangles(index)
            cursor_position = self.viewport().mapFromGlobal(common.cursor.pos())

            self.reset_multi_toggle()

            def _check_rect(f):
                r = rectangles[f]
                p = cursor_position
                return r.contains(p) and r == self._clicked_rect

            if _check_rect(delegate.FavouriteRect) and not archived:
                actions.toggle_favourite()
                if not self.model().filter_flag(common.MarkedAsFavourite):
                    self.model().invalidateFilter()

            if _check_rect(delegate.ArchiveRect):
                actions.toggle_archived()
                if not self.model().filter_flag(common.MarkedAsArchived):
                    self.model().invalidateFilter()

            if _check_rect(delegate.RevealRect) and not archived:
                # Reveal the job folder if any of the modifiers are pressed
                if any((alt_modifier, shift_modifier, control_modifier)):
                    pp = index.data(common.ParentPathRole)
                    s = f'{pp[0]}/{pp[1]}'
                    actions.reveal(s)
                else:
                    actions.reveal(index)

            if _check_rect(delegate.TodoRect) and not archived:
                actions.show_notes()

            if _check_rect(delegate.AddItemRect) and not archived:
                self.add_item_action(index)

            if _check_rect(delegate.PropertiesRect) and not archived:
                self.edit_item_action(index)

            self._clicked_rect = QtCore.QRect()

        super().mouseReleaseEvent(event)

    def add_item_action(self, index):
        """Action to execute when the add item icon is clicked."""
        return

    def edit_item_action(self, index):
        """Action to execute when the edit item icon is clicked."""
        return

    def mouseMoveEvent(self, event):
        """``InlineIconView``'s mouse move event is responsible for
        handling the multi-toggle operations and repainting the current index
        under the mouse.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if self.verticalScrollBar().isSliderDown():
            return

        app = QtWidgets.QApplication.instance()
        if not app:
            return

        if not common.cursor:
            return
        cursor_position = self.viewport().mapFromGlobal(common.cursor.pos())

        index = self.indexAt(cursor_position)
        if not index.isValid():
            app.restoreOverrideCursor()
            return

        if not index.column() == 0:
            app.restoreOverrideCursor()
            return

        modifiers = app.keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier
        control_modifier = modifiers & QtCore.Qt.ControlModifier

        if alt_modifier or shift_modifier or control_modifier:
            self.update(index)

        rectangles = self.itemDelegate().get_rectangles(index)

        # Status messages
        if self.multi_toggle_pos is None:

            if event.buttons() == QtCore.Qt.NoButton:
                if rectangles[delegate.PropertiesRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Edit item properties...'
                    )
                    self.update(index)
                elif rectangles[delegate.AddItemRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Add New Item...'
                    )
                    self.update(index)
                elif rectangles[delegate.TodoRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Edit Notes...'
                    )
                    self.update(index)
                elif rectangles[delegate.RevealRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Show item in File Explorer...'
                    )
                    self.update(index)
                elif rectangles[delegate.ArchiveRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Archive item...'
                    )
                    self.update(index)
                elif rectangles[delegate.FavouriteRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Star item...'
                    )
                    self.update(index)
                elif rectangles[delegate.ThumbnailRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        'Drag and drop an image, or right-click to edit the thumbnail...'
                    )
                    self.update(index)
                elif rectangles[delegate.InlineBackgroundRect].contains(cursor_position):
                    common.signals.clearStatusBarMessage.emit()
                    self.update(index)
                elif rectangles[delegate.DataRect].contains(cursor_position):
                    common.signals.showStatusTipMessage.emit(
                        index.data(common.PathRole)
                    )
                else:
                    common.signals.clearStatusBarMessage.emit()
                    self.update(index)

            if not index.isValid():
                app.restoreOverrideCursor()
                return

            rect = delegate.get_description_rectangle(
                index, self.visualRect(index), self.buttons_hidden()
            )

            if rect and rect.contains(cursor_position):
                self.update(index)
                if app.overrideCursor():
                    app.changeOverrideCursor(
                        QtGui.QCursor(QtCore.Qt.IBeamCursor)
                    )
                else:
                    app.restoreOverrideCursor()
                    app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
            else:
                app.restoreOverrideCursor()
            super().mouseMoveEvent(event)
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

            if self.multi_toggle_flag == delegate.FavouriteRect:
                self.multi_toggle_items[idx] = favourite
                self.toggle_item_flag(
                    index,
                    common.MarkedAsFavourite,
                    state=self.multi_toggle_state,
                    commit_now=False,
                )
                return

            if self.multi_toggle_flag == delegate.ArchiveRect:
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
        self.delayed_queue_timer.setInterval(500)
        self.delayed_queue_timer.setSingleShot(True)

        super().__init__(icon=icon, parent=parent)

        self.update_queue = collections.deque([], common.max_list_items)
        self.update_queue_timer = common.Timer(parent=self)
        self.update_queue_timer.setSingleShot(True)
        self.update_queue_timer.setInterval(20)
        self.update_queue_timer.timeout.connect(self.queued_row_repaint)

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
    def init_model(self, *args, **kwargs):
        """The methods responsible for connecting the associated item model with the view.

        """
        super().init_model(*args, **kwargs)
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

    @QtCore.Slot(weakref.ref)
    def update_row(self, ref):
        """Queues an update request by the threads for later processing."""
        if not ref():
            return
        if ref not in self.update_queue.copy():
            self.update_queue.append(ref)
            self.update_queue_timer.start(self.update_queue_timer.interval())

    def queued_row_repaint(self):
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
                break

        self.update_queue_timer.start(self.update_queue_timer.interval())

    @QtCore.Slot()
    def delayed_save_visible_rows(self):
        self.delayed_save_visible_timer.start(
            self.delayed_save_visible_timer.interval()
        )

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

        rect = self.visualRect(index)
        i = 0

        while r.intersects(rect):
            if i >= 999:  # Don't check more than 999 items
                break
            i += 1

            self.visible_rows['proxy_rows'].append(index.row())
            self.visible_rows['source_rows'].append(index.data(common.IdRole))

            rect.moveTop(rect.top() + rect.height())
            index = self.indexAt(rect.topLeft())
            if not index.isValid():
                break
