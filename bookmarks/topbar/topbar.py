# -*- coding: utf-8 -*-
"""Defines :class:`.TopBarWidget`, and all the buttons found on the bar located above the
:class:`bookmarks.main.StackedWidget`.


"""

from PySide2 import QtWidgets, QtGui, QtCore

from . import buttons
from . import tabs
from .. import actions
from .. import common
from .. import images

n = (f for f in range(common.FavouriteTab + 1, 999))


BUTTONS = {
    common.BookmarkTab: {
        'widget': tabs.BookmarksTabButton,
        'hidden': False,
    },
    common.AssetTab: {
        'widget': tabs.AssetsTabButton,
        'hidden': False,
    },
    common.FileTab: {
        'widget': tabs.FilesTabButton,
        'hidden': False,
    },
    common.FavouriteTab: {
        'widget': tabs.FavouritesTabButton,
        'hidden': False,
    },
    next(n): {
        'widget': buttons.RefreshButton,
        'hidden': False,
    },
    next(n): {
        'widget': buttons.FilterButton,
        'hidden': False,
    },
    next(n): {
        'widget': buttons.ToggleSequenceButton,
        'hidden': False,
    },
    next(n): {
        'widget': buttons.ToggleArchivedButton,
        'hidden': False,
    },
    next(n): {
        'widget': buttons.ToggleFavouriteButton,
        'hidden': False,
    },
    next(n): {
        'widget': buttons.SlackButton,
        'hidden': True,
    },
    next(n): {
        'widget': buttons.ToggleInlineIcons,
        'hidden': False,
    },
}


class SlackDropAreaWidget(QtWidgets.QWidget):
    """Widget used to receive a Slack message drop."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAcceptDrops(True)
        self.drop_target = True
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

    def paintEvent(self, event):
        if not self.drop_target:
            return

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.SeparatorColor))
        painter.drawRoundedRect(
            self.rect(), common.size(common.WidthIndicator),
            common.size(common.WidthIndicator))

        pixmap = images.ImageCache.get_rsc_pixmap(
            'slack', common.color(common.GreenColor),
            self.rect().height() - (common.size(common.WidthIndicator) * 1.5))
        rect = QtCore.QRect(0, 0, common.size(
            common.WidthMargin), common.size(common.WidthMargin))
        rect.moveCenter(self.rect().center())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        o = common.size(common.WidthIndicator)
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(common.color(common.GreenColor))
        pen.setWidthF(common.size(common.HeightSeparator) * 2.0)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, o, o)
        painter.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.source() == self:
            return  # Won't allow dropping an item from itself
        mime = event.mimeData()

        if not mime.hasUrls():
            return

        event.accept()

        message = []
        for f in mime.urls():
            file_info = QtCore.QFileInfo(f.toLocalFile())
            line = f'```{file_info.filePath()}```'
            message.append(line)

        message = '\n'.join(message)
        widget = actions.show_slack()
        widget.append_message(message)

    def showEvent(self, event):
        pos = self.parent().rect().topLeft()
        pos = self.parent().mapToGlobal(pos)
        self.move(pos)
        self.setFixedWidth(self.parent().rect().width())
        self.setFixedHeight(self.parent().rect().height())


class TopBarWidget(QtWidgets.QWidget):
    """The bar above the stacked widget containing the main app control buttons.

    """
    slackDragStarted = QtCore.Signal(QtCore.QModelIndex)
    slackDropFinished = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self._buttons = {}

        self._create_ui()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        height = common.size(common.WidthMargin) + \
                 (common.size(common.WidthIndicator) * 3)
        self.setFixedHeight(height)

        for idx in BUTTONS:
            self._buttons[idx] = BUTTONS[idx]['widget'](parent=self)
            self._buttons[idx].setHidden(BUTTONS[idx]['hidden'])

            if idx < common.FavouriteTab:
                self.layout().addWidget(self._buttons[idx], 1)
            else:
                self.layout().addWidget(self._buttons[idx], 0)
                self.layout().addSpacing(common.size(common.WidthIndicator))

            if idx == common.FavouriteTab:
                self.layout().addStretch()

        self.slack_drop_area_widget = SlackDropAreaWidget(parent=self)
        self.slack_drop_area_widget.setHidden(True)

    def button(self, idx):
        if idx not in self._buttons:
            raise ValueError('Button does not exist')
        return self._buttons[idx]

    def paintEvent(self, event):
        """`TopBarWidget`' paint event."""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)

        pixmap = images.ImageCache.get_rsc_pixmap(
            'gradient', None, self.height())
        t = QtGui.QTransform()
        t.rotate(90)
        pixmap = pixmap.transformed(t)
        painter.setOpacity(0.8)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()
