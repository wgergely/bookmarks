import functools
import os
import re

from PySide2 import QtWidgets, QtCore, QtGui

from . import drag
from ..delegate import base as delegate
from ..editor import filter as filtereditor
from ..model import filter as filtermodel
from ..model import base as basemodel
from ... import common, contextmenu, ui, actions, database, log
from ...threads import threads


class ThumbnailsContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with thumbnail actions.

    """

    def setup(self):
        """Creates the context menu.

        """
        self.thumbnail_menu()
        self.separator()
        self.sg_thumbnail_menu()


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
        event.accept()
        self.hide()

    @QtCore.Slot(str)
    def set_message(self, text):
        """Sets the message to be displayed when saving the widget."""
        self._message = text


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

        self.drop_indicator_widget = DropIndicatorWidget(parent=self)
        self.drop_indicator_widget.hide()

        self.drag_current_row = -1
        self.drag_source_row = -1

        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.setDefaultDropAction(QtCore.Qt.CopyAction)
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
        self.filter_editor = filtereditor.TextFilterEditor(parent=self.parent())
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
        self.delayed_layout_timer.setInterval(100)

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

        self._connect_signals()

        self.init_model()

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

    def dragMoveEvent(self, event):
        """Drag move events checks source validity against available drop actions.

        """
        self._thumbnail_drop = (-1, False)

        index = self.indexAt(event.pos())

        if not index.isValid():
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
        if model._can_drop_properties(
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

        _drag = drag.ItemDrag(index, self)
        QtCore.QTimer.singleShot(1, self.viewport().update)
        _drag.exec_(supported_actions)
        QtCore.QTimer.singleShot(10, self._reset_drag_indicators)

    def dropEvent(self, event):
        """Event handler.

        """
        pos = event.pos()

        index = self.indexAt(pos)
        if not index.isValid():
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

        self._reset_drag_indicators()

    def showEvent(self, event):
        """Show event handler.

        """
        self.scheduleDelayedItemsLayout()

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
        self.resized.emit(self.viewport().geometry())
        self.scheduleDelayedItemsLayout()

    def keyPressEvent(self, event):
        """Key press event handler.

        Define the default behavior of the list-items, including
        the actions needed to navigate the list using the keyboard.

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
                if self.state() != QtWidgets.QAbstractItemView.EditingState:
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

    def mousePressEvent(self, event):
        """Deselect the current index when clicked on an empty space.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return

        event.accept()
        index = self.indexAt(event.pos())
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

    def mouseReleaseEvent(self, event):
        """Event handler.

        """
        event.ignore()
        self.delay_save_selection()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Custom doubleclick event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double click location before deciding what action to take.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return

        index = self.indexAt(event.pos())
        if not index.isValid():
            event.ignore()
            return

        if index.flags() & common.MarkedAsArchived:
            event.ignore()
            return

        if index.column() == 1:
            event.accept()
            actions.capture_thumbnail()
            return

        if index.column() == 2:
            rect, text = self.itemDelegate().get_filter_rectangle(index.data(common.IdRole), event.pos())
            rects = self.itemDelegate().filter_rectangles()
            last_rect = list(rects[index.data(common.IdRole)].values())[-1][0]

            # Edit the description if the last rectangle is double-clicked
            if rect and rect.contains(event.pos()) and rect == last_rect:
                event.accept()
                self.edit(index)
                return

            # Otherwise, activate the item
            event.accept()
            self.activate(index)
            return

        event.ignore()
        super().mouseDoubleClickEvent(event)

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

        if index.isValid() and index.column() == 1:
            widget = self.ThumbnailContextMenu(index, parent=self)
        else:
            widget = self.ContextMenu(index, parent=self)

        widget.move(event.globalPos())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def _reset_drag_indicators(self):
        self._thumbnail_drop = (-1, False)
        self.drag_source_row = -1
        self.drag_current_row = -1
        self.stopAutoScroll()
        self.setState(QtWidgets.QAbstractItemView.NoState)
        self.viewport().update()

    def get_source_model(self):
        """Returns the model class associated with this view.

        """
        model = basemodel.ItemModel(parent=self)
        return model

    @common.debug
    def init_model(self):
        """Add a model to the view.

        The ItemModel subclasses are wrapped in a QSortFilterProxyModel. All
        the necessary internal signal-slot connections needed for the proxy, model
        and the view to communicate are made here.

        """
        proxy = filtermodel.FilterProxyModel(parent=self)
        self.setModel(proxy)

        model = self.get_source_model()
        proxy.setSourceModel(model)

        self.verticalHeader().setDefaultSectionSize(int(model.row_size.height()))

        # Connect signals
        proxy.filterTextChanged.connect(self.filter_editor.editor.setText)

        model.rowHeightChanged.connect(self.row_size_changed)
        model.modelReset.connect(
            lambda: self.delayed_layout_timer.start(self.delayed_layout_timer.interval())
        )

        self.interruptRequested.connect(model.set_interrupt_requested)

        self.filter_editor.finished.connect(proxy.set_filter_text)

        model.modelReset.connect(self.delay_restore_selection)
        proxy.invalidated.connect(self.delay_restore_selection)

        model.updateIndex.connect(
            self.update, type=QtCore.Qt.DirectConnection
        )

        common.signals.paintThumbnailBGChanged.connect(
            self.repaint_visible_rows
        )


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

        for c in (0, 1, 2):
            sibling = index.siblingAtColumn(c)
            self.repaint(self.visualRect(sibling))

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

        # If the item is already active, emit activated
        # signal. This will change tabs but won't trigger a model update
        if index.flags() & common.MarkedAsActive:
            self.activated.emit(index)
            return

        # If the current item isn't active yet, the current MarkedAsActive flag
        # and emit the activated signal. This will load the model and change tabs.
        proxy = self.model()
        model = proxy.sourceModel()
        source_index = proxy.mapToSource(index)
        model.set_active(source_index)
        self.activated.emit(index)

    def delay_save_selection(self):
        """Delays saving the current item selection to the user settings file to reduce
        the number hits on the file system.

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

        p = model.parent_path()
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
            current_index = next((f for f in model.selectedIndexes()), QtCore.QModelIndex())
        else:
            current_index = QtCore.QModelIndex()

        first_index = self.model().index(0, 0)
        last_index = self.model().index(self.model().rowCount() - 1, 0)

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
            self.setCurrentIndex(first_index)
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
            self.setCurrentIndex(first_index)
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
        self.setCurrentIndex(self.model().index(current_index.row() + 1, 0))

    def key_up(self):
        """Custom action to perform when the `up` arrow is pressed
        on the keyboard.

        We're implementing a continuous scroll: when reaching the last
        item in the list, we'll jump to the beginning, and vice-versa.

        """

        model = self.selectionModel()
        if model.hasSelection():
            current_index = next((f for f in model.selectedIndexes()), QtCore.QModelIndex())
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

        # Map to column 2
        sibling = index.sibling(index.row(), 2)
        self.setCurrentIndex(sibling)
        self.edit(sibling)

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

        _painter_path = QtGui.QPainterPath()
        _painter_path.addText(x, y, font, text)
        painter.drawPath(_painter_path.simplified())

        painter.end()

    @QtCore.Slot()
    def repaint_visible_rows(self):
        """Slot used to repaint all currently visible items.

        """
        if QtWidgets.QApplication.instance().mouseButtons() != QtCore.Qt.NoButton:
            return

        for idx in self.visible_rows['proxy_rows']:
            index = self.model().index(idx, 0)
            self.update(index)

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

        p = model.parent_path()

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
                log.debug(__name__, 'Removing asset cache:', cache)
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