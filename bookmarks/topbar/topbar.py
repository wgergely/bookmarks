"""Defines :class:`.TopBarWidget`, the main widget containing all control buttons.

"""
from PySide2 import QtWidgets, QtCore

from . import buttons
from . import tabs
from .control import ItemControlBar
from .. import common

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
    common.idx(): {
        'widget': buttons.FilterButton,
        'hidden': False,
    },
    common.idx(): {
        'widget': buttons.RefreshButton,
        'hidden': False,
    },
    common.idx(): {
        'widget': buttons.ApplicationLauncherButton,
        'hidden': False,
    },
    common.idx(): {
        'widget': buttons.ToggleSequenceButton,
        'hidden': False,
    },
    common.idx(): {
        'widget': buttons.ToggleArchivedButton,
        'hidden': False,
    },
    common.idx(): {
        'widget': buttons.ToggleFavouriteButton,
        'hidden': False,
    },
    common.idx(): {
        'widget': buttons.ToggleInlineIcons,
        'hidden': False,
    },
}



class TopBarWidget(QtWidgets.QWidget):
    """The bar above the stacked widget containing the main app control buttons.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._buttons = {}

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        o = common.Size.Indicator(3.0)
        height = common.Size.Margin() + o

        QtWidgets.QVBoxLayout(self)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignTop)
        self.setAttribute(QtCore.Qt.WA_NoBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )
        # Buttons bar
        widget = QtWidgets.QWidget()

        QtWidgets.QHBoxLayout(widget)

        widget.layout().setContentsMargins(0, 0, o, 0)
        widget.layout().setSpacing(0)
        widget.setFixedHeight(height)

        widget.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        widget.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        for idx in BUTTONS:
            self._buttons[idx] = BUTTONS[idx]['widget'](parent=self)
            self._buttons[idx].setHidden(BUTTONS[idx]['hidden'])

            if idx > common.FavouriteTab:
                widget.layout().addWidget(self._buttons[idx], 0)
            else:
                widget.layout().addWidget(self._buttons[idx], 1)

            if idx == common.FavouriteTab:
                widget.layout().addStretch()

        self.layout().addWidget(widget)

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QHBoxLayout(widget)
        o = common.Size.Indicator(1.0)

        widget.layout().setContentsMargins(o * 2, o, o * 2, o)
        widget.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        widget.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        widget.layout().addWidget(ItemControlBar(parent=self), 1)
        self.layout().addWidget(widget, 1)

    def _connect_signals(self):
        pass

    def button(self, idx):
        if idx not in self._buttons:
            raise ValueError('Button does not exist')
        return self._buttons[idx]


