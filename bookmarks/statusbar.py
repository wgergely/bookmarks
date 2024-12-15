"""Bookmarks' status bar used to display item information.

"""
import functools

from PySide2 import QtWidgets, QtGui, QtCore

from . import actions
from . import common
from . import images
from . import ui

HEIGHT = common.Size.Margin() + (common.Size.Indicator(2.0))


class StatusBarWidget(QtWidgets.QStatusBar):
    """Bookmark's status bar, below the list widgets.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.thread_status_widget = None
        self.toggle_mode_widget = None

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.setSizeGripEnabled(False)
        self.setFixedHeight(HEIGHT)

        common.signals.showStatusBarMessage.connect(
            functools.partial(self.showMessage, timeout=1000)
        )
        common.signals.showStatusTipMessage.connect(
            functools.partial(self.showMessage, timeout=99999)
        )
        common.signals.clearStatusBarMessage.connect(self.clearMessage)

    def paintEvent(self, event):
        """Paint event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)

        font, _ = common.Font.MediumFont(common.Size.SmallText())
        common.draw_aliased_text(
            painter,
            font,
            self.rect().marginsRemoved(
                QtCore.QMargins(common.Size.Indicator(), 0, common.Size.Indicator(), 0)
            ),
            f'  {self.currentMessage()}  ',
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            common.Color.Text()
        )
        painter.end()


class ToggleSessionModeButton(ui.ClickableIconButton):
    """Button used to toggle between the active path mode between
    ``common.ActiveMode.Synchronized`` and ``common.ActiveMode.Private``.

    """
    ContextMenu = None

    def __init__(self, parent=None):
        super().__init__(
            'check',
            (common.Color.Green(), common.Color.Red()),
            common.Size.Margin(),
            description=f'Click to toggle {common.product.title()}.',
            parent=parent
        )
        self.setMouseTracking(True)
        self.clicked.connect(actions.toggle_active_mode)
        common.signals.activeModeChanged.connect(self.update)

    def pixmap(self):
        """Get pixmap based on the current status.

        """
        if common.active_mode == common.ActiveMode.Synchronized:
            return images.rsc_pixmap(
                'check',
                common.Color.Green(),
                self._size
            )
        elif common.active_mode == common.ActiveMode.Private:
            return images.rsc_pixmap(
                'crossed',
                common.Color.Red(),
                self._size
            )
        elif common.active_mode == common.ActiveMode.Explicit:
            return images.rsc_pixmap(
                'check',
                common.Color.Yellow(),
                self._size
            )
        else:
            return images.rsc_pixmap(
                'alert',
                common.Color.Red(),
                self._size
            )

    def statusTip(self):
        """Status tip message.

        """
        if common.active_mode == common.ActiveMode.Synchronized:
            return 'This session sets active paths. Click to toggle.'
        elif common.active_mode == common.ActiveMode.Private:
            return 'This session does not permanently save active paths. Click to toggle.'
        elif common.active_mode == common.ActiveMode.Explicit:
            return 'This session has overridden active paths.'
        else:
            return 'Invalid active mode.'


class StatusBar(QtWidgets.QWidget):
    """The main status bar widget.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.message_widget = None
        self.thread_status_widget = None
        self.toggle_mode_widget = None

        self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Fixed,
        )

        self.setFixedHeight(HEIGHT)

        self._connect_signals()

    def _connect_signals(self):
        """Connect signals.

        """
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.message_widget = StatusBarWidget(parent=self)
        self.layout().addWidget(self.message_widget, 1)

        self.toggle_mode_widget = ToggleSessionModeButton(
            parent=self
        )
        self.layout().addWidget(self.toggle_mode_widget, 0)
        self.layout().addSpacing(common.Size.Indicator(2.0))
