# -*- coding: utf-8 -*-
"""Defines the main item tab buttons found on the left hand side of the top bar.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from . import quickswitch
from .. import actions
from .. import common
from .. import images
from ..items import delegate


class BaseTabButton(QtWidgets.QLabel):
    """The base class of our item tab buttons.

    """
    icon = 'asset'

    clicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()

    def __init__(self, label, idx, description, parent=None):
        super().__init__(parent=parent)
        self._label = label
        self.tab_idx = idx

        self.setStatusTip(description)
        self.setToolTip(description)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self.clicked.connect(self.emit_tab_changed)
        common.signals.updateTopBarButtons.connect(self.update)

    @QtCore.Slot()
    def emit_tab_changed(self):
        if common.current_tab() == self.tab_idx:
            return
        common.signals.tabChanged.emit(self.tab_idx)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def mouseReleaseEvent(self, event):
        """Only triggered when the left buttons is pressed."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.doubleClicked.emit()

    def text(self):
        return self._label

    def get_width(self):
        o = common.size(common.WidthIndicator) * 6
        _, metrics = common.font_db.primary_font(
            common.size(common.FontSizeMedium))
        return metrics.horizontalAdvance(self.text()) + o

    @QtCore.Slot()
    def adjust_size(self):
        """Slot responsible for setting the size of the widget to match the text."""
        self.setMaximumWidth(self.get_width())
        self.setMinimumWidth(common.size(common.WidthMargin) * 2)
        self.update()

    def showEvent(self, event):
        self.adjust_size()

    def paintEvent(self, event):
        """The control button's paint method - shows the set text and
        an underline if the tab is active."""
        if common.main_widget is None or not common.main_widget.is_initialized:
            return

        rect = QtCore.QRect(self.rect())

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        option = QtWidgets.QStyleOptionButton()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        painter.setPen(QtCore.Qt.NoPen)

        if common.current_tab() == self.tab_idx:
            color = common.color(
                common.TextSelectedColor) if hover else common.color(common.TextColor)
            painter.setBrush(color)
        else:
            color = common.color(common.TextColor) if hover else common.color(
                common.BackgroundColor)
            painter.setBrush(color)

        font, metrics = common.font_db.primary_font(
            common.size(common.FontSizeMedium))

        # When the width of the button is very small, we'll switch to an icon
        # representation instead of text:
        if (
                self.tab_idx == common.FileTab and
                common.current_tab() == common.FileTab and
                hover
        ):
            # Draw icon
            pixmap = images.ImageCache.get_rsc_pixmap(
                'branch_open',
                common.color(common.TextSelectedColor),
                common.size(common.WidthMargin)
            )
            _rect = QtCore.QRect(0, 0, common.size(
                common.WidthMargin), common.size(common.WidthMargin))
            _rect.moveCenter(self.rect().center())
            painter.drawPixmap(
                _rect,
                pixmap,
                pixmap.rect()
            )
        else:
            if (metrics.horizontalAdvance(self.text()) + (
                    common.size(common.WidthMargin) * 0.5)) < self.rect().width():
                # Draw label
                width = metrics.horizontalAdvance(self.text())
                x = (self.width() / 2.0) - (width / 2.0)
                y = self.rect().center().y() + (metrics.ascent() * 0.5)
                path = delegate.get_painter_path(x, y, font, self.text())
                painter.drawPath(path)
            else:
                # Draw icon
                pixmap = images.ImageCache.get_rsc_pixmap(
                    self.icon,
                    color,
                    common.size(common.WidthMargin)
                )
                _rect = QtCore.QRect(0, 0, common.size(
                    common.WidthMargin), common.size(common.WidthMargin))
                _rect.moveCenter(self.rect().center())
                painter.drawPixmap(
                    _rect,
                    pixmap,
                    pixmap.rect()
                )

        # Draw indicator line below icon or text
        rect.setHeight(common.size(common.HeightSeparator) * 2.0)
        painter.setPen(QtCore.Qt.NoPen)
        rect.setWidth(self.rect().width())

        if common.current_tab() == self.tab_idx:
            painter.setOpacity(0.9)
            color = common.color(
                common.TextColor) if hover else common.color(common.RedColor)
        else:
            painter.setOpacity(0.3)
            color = common.color(
                common.TextColor) if hover else common.color(common.BlueColor)

        painter.setBrush(color)
        painter.drawRect(rect)
        painter.end()


class BookmarksTabButton(BaseTabButton):
    icon = 'bookmark'

    def __init__(self, parent=None):
        super(BookmarksTabButton, self).__init__(
            'Bookmarks',
            common.BookmarkTab,
            'Click to see the list of added bookmarks',
            parent=parent
        )

    def contextMenuEvent(self, event):
        menu = quickswitch.SwitchBookmarkMenu(QtCore.QModelIndex(), parent=self)
        pos = self.mapToGlobal(event.pos())
        menu.move(pos)
        menu.exec_()


class AssetsTabButton(BaseTabButton):
    icon = 'asset'

    def __init__(self, parent=None):
        super().__init__(
            'Assets',
            common.AssetTab,
            'Click to see the list of available assets',
            parent=parent
        )

    def contextMenuEvent(self, event):
        menu = quickswitch.SwitchAssetMenu(QtCore.QModelIndex(), parent=self)
        pos = self.mapToGlobal(event.pos())
        menu.move(pos)
        menu.exec_()

    @QtCore.Slot()
    def emit_tab_changed(self):
        active = common.active('root')
        if not active:
            return
        super().emit_tab_changed()


class FilesTabButton(BaseTabButton):
    icon = 'file'

    def __init__(self, parent=None):
        super().__init__(
            'Files',
            common.FileTab,
            'Click to see or change the current task folder',
            parent=parent)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        common.signals.taskViewToggled.connect(self.update)

    @QtCore.Slot()
    def emit_tab_changed(self):
        active = common.active('asset')
        if not active:
            return

        if common.current_tab() == common.FileTab:
            actions.toggle_task_view()
            return

        super().emit_tab_changed()

    def contextMenuEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        """Indicating the visibility of the TaskItemView."""
        if common.widget(common.TaskTab).isHidden():
            super().paintEvent(event)
            return

        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        rect = self.rect()
        rect.setHeight(common.size(common.HeightSeparator) * 2.0)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.GreenColor))
        painter.drawRect(rect)

        o = common.size(common.WidthMargin)
        pixmap = images.ImageCache.get_rsc_pixmap('gradient2', None, o)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())

        rect = QtCore.QRect(0, 0, o, o)
        rect.moveCenter(self.rect().center())
        pixmap = images.ImageCache.get_rsc_pixmap(
            'folder', common.color(common.GreenColor), o)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        painter.drawPixmap(rect, pixmap, pixmap.rect())
        painter.end()

    def text(self):
        w = common.widget(common.FileTab)
        model = w.model().sourceModel()
        t = model.task()

        if not t:
            return super().text()
        return t

        return active_index.data(common.ParentPathRole)['task'].lower()


class FavouritesTabButton(BaseTabButton):
    icon = 'favourite'

    def __init__(self, parent=None):
        super().__init__(
            'Starred',
            common.FavouriteTab,
            'Click to see your saved favourites',
            parent=parent
        )
