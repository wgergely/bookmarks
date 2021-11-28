# -*- coding: utf-8 -*-
"""The main Bookmark Editor widget.

The editor is used to add or remove bookmarks from the bookmark list.
The widget is also responsible for editing the list of servers and jobs that
will contain the bookmarks.

The definitions for the server, job and bookmark editor editors are found
in the `bookmark_editor` submodule.

"""
import functools

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import ui
from .. import images
from .. import actions

from . import server_editor
from . import job_editor
from . import bookmark_editor


instance = None

HINT = "To start, add your server below. If the server does not have jobs, you \
can add new ones using *.zip templates.\nAll job items will contain a series of \
bookmark items - these are the folders used to store your project's files and \
are usually called 'Shots', 'Assets', etc.\nYou can create new bookmark items \
below or toggle existing ones by double-clicking their name (or clicking their \
label)."


def close():
    global instance
    if instance is None:
        return
    try:
        instance.close()
        instance.deleteLater()
    except:
        pass
    instance = None


def show():
    global instance

    close()
    instance = BookmarkEditorWidget()
    instance.open()
    return instance


HELP = 'Add and remove bookmark items in this window. \
Start by adding a server\
\
'


class BookmarkEditorWidget(QtWidgets.QDialog):
    """The main editor used to add or remove bookmarks, jobs and servers.

    """

    def __init__(self, parent=None):
        super(BookmarkEditorWidget, self).__init__(
            parent=parent,
            f=QtCore.Qt.CustomizeWindowHint |
            QtCore.Qt.WindowTitleHint |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMaximizeButtonHint
        )

        self.server_editor = None
        self.server_add_button = None
        self.job_editor = None
        self.job_add_button = None
        self.bookmark_editor = None
        self.bookmark_add_button = None
        self.persistent_bookmarks_button = None

        self.setObjectName('BookmarksEditorWidget')
        self.setWindowTitle('Edit Bookmarks')

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)

        o = common.size(common.WidthMargin) * 0.66
        self.layout().setContentsMargins(0, o, 0, o)
        self.layout().setSpacing(0)

        h = common.size(common.HeightRow) * 0.66

        _label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'bookmark', common.color(common.SeparatorColor), h * 0.8)
        _label.setPixmap(pixmap)
        label = ui.PaintedLabel(
            'Edit Bookmarks',
            size=common.size(common.FontSizeLarge),
            color=common.color(common.TextColor),
            parent=self
        )

        row = ui.add_row('', height=h, parent=self)
        row.layout().addStretch(1)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        row.layout().addWidget(_label, 0)
        row.layout().addWidget(label, 0)
        row.layout().addStretch(1)

        # Separator
        row = ui.add_row('', height=o, parent=self)

        _row = ui.add_row('', height=None, parent=None)
        self.layout().addWidget(_row, 0)
        _row.layout().setSpacing(0)
        label = ui.Label(HINT, color=common.color(common.TextSecondaryColor), parent=_row)
        _row.layout().addWidget(label, 0)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum,
        )
        _row.layout().setContentsMargins(o, o, o, o)

        label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'gradient5', common.color(common.SeparatorColor), o)
        label.setPixmap(pixmap)
        label.setScaledContents(True)
        row.layout().addWidget(label, 1)

        # =====================================================

        _o = common.size(common.WidthMargin)
        main_row = ui.add_row(None, height=None, parent=self)
        main_row.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        main_row.setAttribute(QtCore.Qt.WA_NoSystemBackground, False)
        main_row.setObjectName('mainRow')
        main_row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        main_row.layout().setSpacing(o * 0.5)
        main_row.layout().setContentsMargins(o, 0, o, o)

        # =====================================================

        row = ui.add_row(None, vertical=True, height=None, parent=main_row)
        row.layout().setSpacing(o * 0.5)
        row.layout().setContentsMargins(0, o, 0, o)

        _grp = ui.get_group(parent=row, margin=common.size(common.WidthIndicator) * 1.5)
        _row = ui.add_row(None, height=None, parent=_grp)
        _row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )
        grp = ui.get_group(parent=row, margin=common.size(common.WidthIndicator) * 0.66)
        grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        label = ui.PaintedLabel(
            'Servers',
            color=common.color(common.TextSecondaryColor)
        )
        self.server_editor = server_editor.ServerListWidget(parent=grp)
        self.server_add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.GreenColor), common.color(common.TextSelectedColor)),
            common.size(common.HeightRow) * 0.5,
            description='Add Server',
            state=True,
            parent=self
        )
        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        _row.layout().addWidget(self.server_add_button)
        grp.layout().addWidget(self.server_editor, 1)

        # =====================================================

        row = ui.add_row(None, vertical=True, height=None, parent=main_row)
        row.layout().setSpacing(o * 0.5)
        row.layout().setContentsMargins(0, o, 0, o)

        _grp = ui.get_group(parent=row, margin=common.size(common.WidthIndicator) * 1.5)
        _row = ui.add_row(None, height=None, parent=_grp)
        _row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )

        grp = ui.get_group(parent=row, margin=common.size(common.WidthIndicator) * 0.66)
        grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        label = ui.PaintedLabel(
            'Jobs',
            color=common.color(common.TextSecondaryColor)
        )

        self.job_editor = job_editor.JobListWidget(parent=self)
        self.job_add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.GreenColor), common.color(common.TextSelectedColor)),
            common.size(common.HeightRow) * 0.5,
            description='Click to create a new job',
            state=True,
            parent=self
        )

        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        _row.layout().addWidget(self.job_add_button)
        grp.layout().addWidget(self.job_editor, 1)

        # =====================================================

        row = ui.add_row(None, vertical=True, height=None, parent=main_row)
        row.layout().setSpacing(o * 0.5)
        row.layout().setContentsMargins(0, o, 0, o)

        _grp = ui.get_group(parent=row, margin=common.size(common.WidthIndicator) * 1.5)
        _row = ui.add_row(None, height=None, parent=_grp)
        _row.layout().setAlignment(QtCore.Qt.AlignCenter)
        _row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )
        grp = ui.get_group(parent=row, margin=common.size(common.WidthIndicator) * 0.66)
        grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        label = ui.PaintedLabel(
            'Bookmarks',
            color=common.color(common.TextSecondaryColor)
        )

        self.bookmark_editor = bookmark_editor.BookmarkListWidget(parent=self)
        self.bookmark_add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.GreenColor), common.color(common.TextSelectedColor)),
            common.size(common.HeightRow) * 0.5,
            description='Click to select a folder and use it as a bookmark item.',
            state=True,
            parent=self
        )

        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        _row.layout().addWidget(self.bookmark_add_button)
        grp.layout().addWidget(self.bookmark_editor, 1)

        # =====================================================
        # Separator
        row = ui.add_row('', height=o, parent=self)

        label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'gradient2', common.color(common.SeparatorColor), o)
        label.setPixmap(pixmap)
        label.setScaledContents(True)
        row.layout().addWidget(label, 1)

        row = ui.add_row(None, height=None, parent=self)
        row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum,
        )
        row.layout().setContentsMargins(o, 0, o, 0)
        self.done_button = ui.PaintedButton(
            'Done',
            parent=self
        )
        self.done_button.setFixedHeight(common.size(common.HeightRow))

        self.persistent_bookmarks_button = ui.PaintedButton(
            'Edit Persistent Bookmarks')
        row.layout().addWidget(self.persistent_bookmarks_button, 0)
        row.layout().addWidget(self.done_button, 1)

    def _connect_signals(self):
        self.server_editor.serverChanged.connect(
            functools.partial(self.set_hidden, self.job_editor.parent().parent()))

        self.server_editor.serverChanged.connect(
            functools.partial(self.set_hidden, self.job_add_button.parent().parent()))
        self.server_editor.serverChanged.connect(
            functools.partial(self.set_hidden, self.bookmark_editor.parent().parent()))
        self.server_editor.serverChanged.connect(
            functools.partial(self.set_hidden, self.bookmark_add_button.parent().parent()))

        self.job_editor.jobChanged.connect(
            functools.partial(self.set_hidden, self.bookmark_editor.parent().parent()))
        self.job_editor.jobChanged.connect(
            functools.partial(self.set_hidden, self.bookmark_add_button.parent().parent()))

        self.server_editor.serverChanged.connect(
            self.job_editor.server_changed)
        self.job_editor.jobChanged.connect(self.bookmark_editor.job_changed)

        self.server_add_button.clicked.connect(self.server_editor.add)
        self.job_add_button.clicked.connect(self.job_editor.add)
        self.bookmark_add_button.clicked.connect(self.bookmark_editor.add)

        self.done_button.clicked.connect(self.close)

        self.server_editor.serverChanged.connect(self.job_editor.update_status)
        self.job_editor.jobChanged.connect(self.job_editor.update_status)

        self.persistent_bookmarks_button.clicked.connect(
            actions.edit_persistent_bookmarks)

    def init_data(self):
        self.server_editor.init_data()
        self.server_editor.restore_current()

        self.job_editor.init_data()
        self.job_editor.restore_current()

        self.bookmark_editor.init_data()

    @QtCore.Slot(QtWidgets.QWidget)
    @QtCore.Slot(bool)
    def set_hidden(self, widget, v, *args, **kwargs):
        if not v:
            widget.setHidden(True)
        else:
            widget.setHidden(False)

    def showEvent(self, event):
        common.center_window(self)
        QtCore.QTimer.singleShot(100, self.init_data)
        super(BookmarkEditorWidget, self).showEvent(event)

    def sizeHint(self):
        return QtCore.QSize(common.size(common.DefaultWidth), common.size(common.DefaultHeight) * 1.33)
