"""Defines :class:`.TopBarWidget`, the main widget containing all control buttons.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from . import buttons
from . import tabs
from . import filters
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
        'widget': filters.EntityFilterButton,
        'hidden': False,
    },
    next(n): {
        'widget': filters.TaskFilterButton,
        'hidden': False,
    },
    next(n): {
        'widget': buttons.FilterButton,
        'hidden': False,
    },
    next(n): {
        'widget': buttons.RefreshButton,
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
        'widget': buttons.ToggleInlineIcons,
        'hidden': False,
    },
}


class TopBarWidget(QtWidgets.QWidget):
    """The bar above the stacked widget containing the main app control buttons.

    """

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

        o = common.size(common.size_indicator) * 3
        height = common.size(common.size_margin) + o
        self.setFixedHeight(height)

        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, o, 0)
        widget.layout().setSpacing(o)
        widget.setAttribute(QtCore.Qt.WA_NoBackground, True)
        widget.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        for idx in BUTTONS:
            self._buttons[idx] = BUTTONS[idx]['widget'](parent=self)
            self._buttons[idx].setHidden(BUTTONS[idx]['hidden'])

            if idx > common.FavouriteTab:
                widget.layout().addWidget(self._buttons[idx], 0)
            else:
                self.layout().addWidget(self._buttons[idx], 1)

            if idx == common.FavouriteTab:
                self.layout().addStretch()

        self.layout().addWidget(widget)

    def button(self, idx):
        if idx not in self._buttons:
            raise ValueError('Button does not exist')
        return self._buttons[idx]

    def paintEvent(self, event):
        """`TopBarWidget`' paint event."""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)

        pixmap = images.rsc_pixmap(
            'gradient', None, self.height()
        )
        t = QtGui.QTransform()
        t.rotate(90)
        pixmap = pixmap.transformed(t)
        painter.setOpacity(0.8)
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()
