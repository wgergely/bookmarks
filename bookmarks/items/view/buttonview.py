from PySide2 import QtCore, QtGui, QtWidgets

from . import base
from ... import common, actions


class ButtonView(base.BaseItemView):
    """Adds multi-toggle and clickable in-line icons to :class:`BaseItemView`.

    """
    buttonRectangleEntered = QtCore.Signal(QtCore.QRect)
    buttonRectangleLeft = QtCore.Signal()

    indicatorColorChanged = QtCore.Signal(QtGui.QColor)

    icons = {
        common.idx(start=0, reset=True): {
            'icon': None,
            'tooltip': 'ShotGrid',
            'action': actions.reveal_url,
        },
        common.idx(): {
            'icon': 'settings',
            'tooltip': 'Edit item properties...',
            'action': actions.edit_item_properties,
        },
        common.idx(): {
            'icon': 'todo',
            'tooltip': 'Edit item notes...',
            'action': actions.show_notes,
        },
        common.idx(): {
            'icon': 'folder',
            'tooltip': 'Show item in file manager...',
            'action': actions.reveal_selected,
        },
        common.idx(): {
            'icon': 'favourite',
            'tooltip': 'Mark as favourite',
            'action': actions.toggle_favourite,
        },
        common.idx(): {
            'icon': 'archivedHidden',
            'tooltip': 'Archive item',
            'action': actions.toggle_archived,
        },
    }

    def __init__(self, icon='bw_icon', parent=None):
        super().__init__(icon=icon, parent=parent)

        self._clicked_rect = QtCore.QRect()

        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_flag = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

        self._progress_hidden = True

        self._indicator_link = None

    @common.debug
    def init_model(self):
        super().init_model()

        model = self.model().sourceModel()

        self.init_buttons_hidden()
        model.modelReset.connect(self.init_buttons_hidden)
        model.modelReset.connect(self.reset_multi_toggle)

    @common.debug
    def init_buttons_hidden(self):
        """Restore the previous state of the inline icon buttons.

        """
        if not self.model():
            raise RuntimeError('Model must be set!')
        if not self.model().sourceModel():
            raise RuntimeError('Source model must be set!')

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

    @QtCore.Slot(bool)
    def set_buttons_hidden(self, val):
        """Sets the visibility of the inline icon buttons.

        """
        self.model().sourceModel().set_filter_setting('filters/buttons', val)
        self._buttons_hidden = val

    @QtCore.Slot()
    def set_indicator_link(self, current, previous):
        """Sets the indicator color based on the current state.

        """
        curr_link = self._indicator_link

        index = next((f for f in current.indexes()), QtCore.QModelIndex())

        if not index.isValid():
            new_link = None
        elif not index.data(common.PathRole):
            new_link = None
        elif not index.data(common.ParentPathRole):
            new_link = None
        elif len(index.data(common.ParentPathRole)) != 4:
            new_link = None
        elif not index.data(common.AssetLinkRole):
            new_link = None
        else:
            new_link = index.data(common.AssetLinkRole)

        if curr_link == new_link:
            return

        self._indicator_link = index.data(common.AssetLinkRole)
        self.itemDelegate().set_indicator_link(new_link)
        self.viewport().update()

    def set_row_size(self, v):
        super().set_row_size(v)
        self.adjust_headers()

    @QtCore.Slot()
    def adjust_headers(self, *args, **kwargs):
        if not self.model():
            return
        if not self.model().sourceModel():
            return
        if not self.model().sourceModel().model_data():
            return

        self.setColumnHidden(3, self.inline_icons_count() == 0)
        self.horizontalHeader().setHidden(self._progress_hidden)
        self.verticalHeader().setHidden(True)

        self.horizontalHeader().setMinimumSectionSize(0)

        # Indicator
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.setColumnWidth(0, common.Size.Indicator())

        # Thumbnail - always the same width as the current row height
        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.setColumnWidth(1, self.model().sourceModel().row_size.height())

        # Name, description, etc column
        self.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        # Control buttons calculated based on the inline_icons_count
        self.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)

        if self.inline_icons_count() == 0:
            self.setColumnWidth(3, 0)
        else:
            icon_width = common.Size.Margin()
            spacing = common.Size.Indicator(2.5)
            count = self.inline_icons_count()
            inline_buttons_column_width = (icon_width + spacing) * count + spacing
            self.setColumnWidth(3, inline_buttons_column_width)

        # Make sure the geometries are up to date after toggling the header
        self.updateGeometries()
        self.viewport().update()

    def _connect_signals(self):
        super()._connect_signals()

        self.buttonRectangleEntered.connect(self.itemDelegate().set_button_candidate_rectangle)
        self.buttonRectangleLeft.connect(self.itemDelegate().clear_button_candidate_rectangle)
        self.buttonRectangleLeft.connect(common.signals.clearStatusBarMessage)

    def init_model(self):
        super().init_model()

        self.model().sourceModel().modelReset.connect(self.adjust_headers)

        self.model().sourceModel().modelAboutToBeReset.connect(self.itemDelegate().clear_rectangles)
        self.model().sourceModel().modelAboutToBeReset.connect(self.itemDelegate().clear_rectangles)
        self.model().invalidated.connect(self.itemDelegate().clear_rectangles)

        self.selectionModel().selectionChanged.connect(self.set_indicator_link)

        self.adjust_headers()

    def inline_icons_count(self):
        """Inline buttons count.

        """
        if self.columnWidth(2) < common.Size.DefaultWidth(0.66):
            return 0
        if self.buttons_hidden():
            return 0
        return len(self.icons)

    def reset_multi_toggle(self):
        """Resets the multi-toggle state.

        """
        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_flag = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

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

    def mousePressEvent(self, event):
        """The `ButtonView`'s mousePressEvent initiates multi-row
        flag toggling.

        This event is responsible for setting ``multi_toggle_pos``, the start
        position of the toggle, ``multi_toggle_state`` & ``multi_toggle_flag``
        the modes of the toggle, based on the state of the state and location of
        the clicked item.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            self.reset_multi_toggle()
            return

        index = self.indexAt(event.pos())

        if index.column() == 3:
            if not index.isValid() or not index.flags() & QtCore.Qt.ItemIsEnabled:
                self._clicked_rect = QtCore.QRect()
                self.reset_multi_toggle()
                super().mousePressEvent(event)
                return

            self.reset_multi_toggle()

            rect, idx = self.itemDelegate().get_button_rectangle(index.data(common.IdRole), event.pos())
            if not rect:
                self.reset_multi_toggle()
                self.buttonRectangleLeft.emit()
                event.ignore()
                super().mouseReleaseEvent(event)
                return

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
            event.accept()

            self._clicked_rect = rect

            if self.icons[idx]['icon'] == 'favourite':
                self.multi_toggle_pos = QtCore.QPoint(0, event.pos().y())
                self.multi_toggle_state = not index.flags() & common.MarkedAsFavourite
                self.multi_toggle_flag = common.MarkedAsFavourite

            if self.icons[idx]['icon'] == 'archivedHidden':
                self.multi_toggle_pos = event.pos()
                self.multi_toggle_state = not index.flags() & common.MarkedAsArchived
                self.multi_toggle_flag = common.MarkedAsArchived

            return

        event.ignore()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Concludes `ButtonView`'s multi-item toggle operation, and
        resets the associated variables.

        The inline icon actions are triggered based on the position of the
        click event.

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
            self.reset_multi_toggle()
            super().mouseReleaseEvent(event)
            return

        if not index.data(common.FlagsRole):
            self.reset_multi_toggle()
            super().mouseReleaseEvent(event)
            return

        if index.column() == 3:
            if self.multi_toggle_items:
                event.ignore()
                self.reset_multi_toggle()
                super().mouseReleaseEvent(event)
                self.model().invalidateFilter()
                return

            event.accept()
            self.reset_multi_toggle()

            rect, idx = self.itemDelegate().get_button_rectangle(index.data(common.IdRole), event.pos())
            if not rect:
                self.reset_multi_toggle()
                self.buttonRectangleLeft.emit()
                event.ignore()
                super().mouseReleaseEvent(event)
                return

            # Let's make sure the click event is within the clicked rectangle and bail out if not
            if rect != self._clicked_rect:
                self.reset_multi_toggle()
                event.ignore()
                super().mouseReleaseEvent(event)
                return

            super().mouseReleaseEvent(event)

            # Trigger action
            if self.icons[idx]['icon'] == 'folder':
                if alt_modifier:
                    actions.reveal_url()
                    return
                if shift_modifier:
                    actions.reveal('/'.join(index.data(common.ParentPathRole)[:2]))
                    return
                if control_modifier:
                    actions.reveal('/'.join(index.data(common.ParentPathRole)[:1]))
                    return

            func = self.icons[idx]['action']
            if func:
                func()
                self.repaint(self.visualRect(index))

            # Refresh filters
            if self.icons[idx]['icon'] == 'favourite':
                if not self.model().filter_flag(common.MarkedAsFavourite):
                    self.model().invalidateFilter()
            elif self.icons[idx]['icon'] == 'archivedHidden':
                if not self.model().filter_flag(common.MarkedAsArchived):
                    self.model().invalidateFilter()

            self._clicked_rect = QtCore.QRect()

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """``ButtonView``'s mouse move event is responsible for
        handling the multi-toggle operations and repainting the current index
        under the mouse.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            super().mouseMoveEvent(event)
            return

        if self.verticalScrollBar().isSliderDown():
            super().mouseMoveEvent(event)
            return

        index = self.indexAt(event.pos())
        if not index.isValid():
            super().mouseMoveEvent(event)
            return

        if index.column() == 3:  # Inline icons and multi-toggle
            rect, idx = self.itemDelegate().get_button_rectangle(index.data(common.IdRole), event.pos())

            if rect:
                self.buttonRectangleEntered.emit(rect)
                common.signals.showStatusTipMessage.emit(self.icons[idx]['tooltip'])
            else:
                self.buttonRectangleLeft.emit()

            self.repaint(self.visualRect(index))

            # There's no multi-toggle operation in progress - we'll just update the icon and emit the tooltip
            if self.multi_toggle_pos is None:
                if rect:
                    self.buttonRectangleEntered.emit(rect)
                super().mouseMoveEvent(event)
                return

            # Ignore operation if no mouse buttons are pressed
            if event.buttons() == QtCore.Qt.NoButton:
                super().mouseMoveEvent(event)
                return

            # Continue with the multi-toggle operation
            initial_index = self.indexAt(self.multi_toggle_pos)
            idx = index.row()

            # Exclude the current item
            if index == self.multi_toggle_item:
                super().mouseMoveEvent(event)
                return

            self.multi_toggle_item = index

            favourite = index.flags() & common.MarkedAsFavourite
            archived = index.flags() & common.MarkedAsArchived

            if idx not in self.multi_toggle_items:

                if self.multi_toggle_flag == common.MarkedAsFavourite:
                    self.multi_toggle_items[idx] = favourite
                    self.toggle_item_flag(
                        index,
                        common.MarkedAsFavourite,
                        state=self.multi_toggle_state,
                        commit_now=False,
                    )
                    self.repaint(self.visualRect(index))

                    super().mouseMoveEvent(event)
                    return

                if self.multi_toggle_flag == common.MarkedAsArchived:
                    self.multi_toggle_items[idx] = archived
                    self.toggle_item_flag(
                        index,
                        common.MarkedAsArchived,
                        state=self.multi_toggle_state,
                        commit_now=False,
                    )
                    self.repaint(self.visualRect(index))

                    super().mouseMoveEvent(event)
                    return

            if index == initial_index:
                super().mouseMoveEvent(event)
                return

        super().mouseMoveEvent(event)
