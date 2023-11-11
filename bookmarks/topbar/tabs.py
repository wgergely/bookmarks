"""Defines the main item tab buttons found on the left hand side of the top bar.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from .. import shortcuts
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
        o = common.size(common.size_indicator) * 6
        _, metrics = common.font_db.bold_font(
            common.size(common.size_font_medium)
        )
        return metrics.horizontalAdvance(self.text()) + o

    @QtCore.Slot()
    def adjust_size(self):
        """Slot responsible for setting the size of the widget to match the text."""
        o = common.size(common.size_margin) * 2
        if self.tab_idx == common.FavouriteTab:
            self.setMaximumWidth(o)
            self.setMinimumWidth(o)
        else:
            self.setMaximumWidth(self.get_width())
            self.setMinimumWidth(o)
        self.update()

    def showEvent(self, event):
        """Show event handler.

        """
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
                common.color_selected_text
            ) if hover else common.color(common.color_text)
            painter.setBrush(color)
        else:
            color = common.color(common.color_text) if hover else common.color(
                common.color_background
            )
            painter.setBrush(color)

        font, metrics = common.font_db.bold_font(
            common.size(common.size_font_medium)
        )

        if (metrics.horizontalAdvance(self.text()) + (
                common.size(common.size_margin) * 0.5)) < self.rect().width():
            # Draw label
            width = metrics.horizontalAdvance(self.text())
            x = (self.width() / 2.0) - (width / 2.0)
            y = self.rect().center().y() + (metrics.ascent() * 0.5)
            delegate.draw_painter_path(painter, x, y, font, self.text())
        else:
            # Draw icon
            pixmap = images.rsc_pixmap(
                self.icon,
                color,
                common.size(common.size_margin)
            )
            _rect = QtCore.QRect(
                0, 0, common.size(
                    common.size_margin
                ), common.size(common.size_margin)
            )
            _rect.moveCenter(self.rect().center())
            painter.drawPixmap(
                _rect,
                pixmap,
                pixmap.rect()
            )

        # Draw indicator line below icon or text
        rect.setHeight(common.size(common.size_separator) * 2.0)
        painter.setPen(QtCore.Qt.NoPen)
        rect.setWidth(self.rect().width())

        if common.current_tab() == self.tab_idx:
            painter.setOpacity(0.9)
            color = common.color(
                common.color_text
            ) if hover else common.color(common.color_selected_text)
        else:
            painter.setOpacity(0.3)
            color = common.color(
                common.color_text
            ) if hover else common.color(common.color_blue)

        painter.setBrush(color)
        painter.drawRect(rect)
        painter.end()


class BookmarksTabButton(BaseTabButton):
    icon = 'bookmark'

    def __init__(self, parent=None):
        s = shortcuts.string(
            shortcuts.MainWidgetShortcuts,
            shortcuts.ShowBookmarksTab
        )
        super().__init__(
            'Bookmarks',
            common.BookmarkTab,
            f'Bookmark items  -  {s}',
            parent=parent
        )



class AssetsTabButton(BaseTabButton):
    icon = 'asset'

    def __init__(self, parent=None):
        s = shortcuts.string(
            shortcuts.MainWidgetShortcuts,
            shortcuts.ShowAssetsTab
        )
        super().__init__(
            'Assets',
            common.AssetTab,
            f'Asset items  -  {s}',
            parent=parent
        )


    @QtCore.Slot()
    def emit_tab_changed(self):
        active = common.active('root')
        if not active:
            return
        super().emit_tab_changed()


class FilesTabButton(BaseTabButton):
    icon = 'file'

    def __init__(self, parent=None):
        s = shortcuts.string(
            shortcuts.MainWidgetShortcuts,
            shortcuts.ShowFilesTab
        )
        super().__init__(
            'Files',
            common.FileTab,
            f'File items  -  {s}',
            parent=parent
        )

    @QtCore.Slot()
    def emit_tab_changed(self):
        active = common.active('asset')
        if not active:
            return

        super().emit_tab_changed()



class FavouritesTabButton(BaseTabButton):
    icon = 'favourite'

    def __init__(self, parent=None):
        super().__init__(
            'Favourites',
            common.FavouriteTab,
            'Click to see your saved favourites',
            parent=parent
        )
