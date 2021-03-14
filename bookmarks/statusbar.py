# -*- coding: utf-8 -*-
"""Bookmarks's status bar used to display item information.

"""
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from .threads import threads
from . import session_lock


HEIGHT = common.MARGIN() + (common.INDICATOR_WIDTH() * 2)


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
    return u'\n'.join(items)


class ThreadStatus(QtWidgets.QWidget):
    """A progress label used to display the number of items currently in the
    processing queues across all threads.

    """

    def __init__(self, parent=None):
        super(ThreadStatus, self).__init__(parent=parent)
        self.update_timer = common.Timer(parent=self)
        self.update_timer.setObjectName(u'ThreadStatusTimer')
        self.update_timer.setInterval(500)
        self.update_timer.setSingleShot(False)
        self.update_timer.timeout.connect(self.update)

        self.setFixedHeight(HEIGHT)

        self.metrics = common.font_db.primary_font(common.SMALL_FONT_SIZE())[1]

    def show_debug_info(self):
        editor = QtWidgets.QTextBrowser(parent=self)
        editor.setWindowFlags(QtCore.Qt.Window)
        editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        editor.setMinimumWidth(common.WIDTH())
        editor.setMinimumHeight(common.HEIGHT())
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
            common.font_db.primary_font(common.SMALL_FONT_SIZE())[0],
            self.rect(),
            self.text(),
            QtCore.Qt.AlignCenter,
            common.GREEN
        )
        painter.end()

    def update(self):
        self.setFixedWidth(self.metrics.width(self.text()) + common.MARGIN())
        super(ThreadStatus, self).update()

    @staticmethod
    def text():
        c = 0
        for k in threads.THREADS:
            c += len(threads.queue(k))
        if not c:
            return u''
        return u'Processing {} items'.format(c)

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

        font, _ = common.font_db.secondary_font(common.SMALL_FONT_SIZE())
        common.draw_aliased_text(
            painter,
            font,
            self.rect().marginsRemoved(QtCore.QMargins(
                common.INDICATOR_WIDTH(), 0, common.INDICATOR_WIDTH(), 0)),
            u'  {}  '.format(self.currentMessage()),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            common.TEXT
        )
        painter.end()


class StatusBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(StatusBar, self).__init__(parent=parent)
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

        self.toggle_mode_widget = session_lock.ToggleSessionModeButton(
            parent=self)
        self.layout().addWidget(self.toggle_mode_widget, 0)
        self.layout().addSpacing(common.INDICATOR_WIDTH() * 2)
