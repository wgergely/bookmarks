# -*- coding: utf-8 -*-
"""Bookmarks's status bar used to display item information.

"""
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from . import actions
from . import images
from . import ui
from .threads import threads


HEIGHT = common.size(common.WidthMargin) + (common.size(common.WidthIndicator) * 2)


def get_thread_status():
    items = []
    for k in threads.THREADS:
        thread = threads.get_thread(k)
        items.append(repr(thread.worker.objectName()))
        try:
            for i in threads.THREADS[k]['queue']:
                items.append(repr(i))
        except RuntimeError:
            pass
    return '\n'.join(items)


class ThreadStatus(QtWidgets.QWidget):
    """A progress label used to display the number of items currently in the
    processing queues across all threads.

    """

    def __init__(self, parent=None):
        super(ThreadStatus, self).__init__(parent=parent)
        self.update_timer = common.Timer(parent=self)
        self.update_timer.setObjectName('ThreadStatusTimer')
        self.update_timer.setInterval(500)
        self.update_timer.setSingleShot(False)
        self.update_timer.timeout.connect(self.update)

        self.setFixedHeight(HEIGHT)

        self.metrics = common.font_db.primary_font(common.size(common.FontSizeSmall))[1]

    def show_debug_info(self):
        editor = QtWidgets.QTextBrowser(parent=self)
        editor.setWindowFlags(QtCore.Qt.Window)
        editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        editor.setMinimumWidth(common.size(common.DefaultWidth))
        editor.setMinimumHeight(common.size(common.DefaultHeight))
        timer = common.Timer(parent=editor)
        timer.setInterval(333)
        timer.setSingleShot(False)
        timer.timeout.connect(
            lambda: editor.setPlainText(get_thread_status()))
        timer.start()
        editor.show()

    def mouseReleaseEvent(self, event):
        if not self.rect().contains(event.pos()):
            return
        self.show_debug_info()

    def showEvent(self, event):
        self.update_timer.start()

    def hideEvent(self, event):
        self.update_timer.stop()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.size(common.FontSizeSmall))[0],
            self.rect(),
            self.text(),
            QtCore.Qt.AlignCenter,
            common.color(common.GreenColor)
        )
        painter.end()

    def update(self):
        self.setFixedWidth(self.metrics.horizontalAdvance(self.text()) + common.size(common.WidthMargin))
        super(ThreadStatus, self).update()

    @staticmethod
    def text():
        c = 0
        for k in threads.THREADS:
            c += len(threads.queue(k))
        if not c:
            return ''
        return 'Processing {} items'.format(c)

class MessageWidget(QtWidgets.QStatusBar):
    """Bookmark's status bar, below the list widgets.

    """

    def __init__(self, parent=None):
        super(MessageWidget, self).__init__(parent=parent)

        self.thread_status_widget = None
        self.toggle_mode_widget = None

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.setSizeGripEnabled(False)
        self.setFixedHeight(HEIGHT)

        common.signals.showStatusBarMessage.connect(
            functools.partial(self.showMessage, timeout=1000))
        common.signals.showStatusTipMessage.connect(
            functools.partial(self.showMessage, timeout=99999))
        common.signals.clearStatusBarMessage.connect(self.clearMessage)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        font, _ = common.font_db.secondary_font(common.size(common.FontSizeSmall))
        common.draw_aliased_text(
            painter,
            font,
            self.rect().marginsRemoved(QtCore.QMargins(
                common.size(common.WidthIndicator), 0, common.size(common.WidthIndicator), 0)),
            '  {}  '.format(self.currentMessage()),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            common.color(common.TextColor)
        )
        painter.end()


class ToggleSessionModeButton(ui.ClickableIconButton):
    """Button used to toggle between Synronised and Private modes.

    """
    ContextMenu = None

    def __init__(self, parent=None):
        super().__init__(
            'check',
            (common.color(common.GreenColor), common.color(common.RedColor)),
            common.size(common.WidthMargin),
            description=f'Click to toggle {common.product}.',
            parent=parent
        )
        self.setMouseTracking(True)
        self.clicked.connect(actions.toggle_session_mode)
        common.signals.sessionModeChanged.connect(self.update)

    def pixmap(self):
        if common.session_mode == common.SyncronisedActivePaths:
            return images.ImageCache.get_rsc_pixmap('check', common.color(common.GreenColor), self._size)
        if common.session_mode == common.PrivateActivePaths:
            return images.ImageCache.get_rsc_pixmap('crossed', common.color(common.RedColor), self._size)
        return images.ImageCache.get_rsc_pixmap('crossed', common.color(common.RedColor), self._size)

    def statusTip(self):
        if common.session_mode == common.SyncronisedActivePaths:
            return 'This session sets active paths. Click to toggle.'

        if common.session_mode == common.PrivateActivePaths:
            return 'This session does not modify active paths. Click to toggle.'

        return 'Invalid session lock.'

    def toolTip(self):
        return self.whatsThis()

    def whatsThis(self):
        return 'Private Active Paths:\n{}\n{}\n{}\n{}\n{}\n\n{}\n{}\n{}\n{}\n{}'.format(
            common.instance(
            )._active_section_values[common.ServerKey],
            common.settings._active_section_values[common.JobKey],
            common.settings._active_section_values[common.RootKey],
            common.settings._active_section_values[common.AssetKey],
            common.settings._active_section_values[common.TaskKey],
            common.active(common.ServerKey),
            common.active(common.JobKey),
            common.active(common.RootKey),
            common.active(common.AssetKey),
            common.active(common.TaskKey),
        )


class StatusBar(QtWidgets.QWidget):
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

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        pass

    def _connect_signals(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.message_widget = MessageWidget(parent=self)
        self.layout().addWidget(self.message_widget, 1)

        self.thread_status_widget = ThreadStatus(parent=self)
        self.layout().addWidget(self.thread_status_widget, 0)

        self.toggle_mode_widget = common.ToggleSessionModeButton(
            parent=self)
        self.layout().addWidget(self.toggle_mode_widget, 0)
        self.layout().addSpacing(common.size(common.WidthIndicator) * 2)
