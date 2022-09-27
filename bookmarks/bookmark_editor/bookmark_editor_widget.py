# -*- coding: utf-8 -*-
"""The main Bookmark Editor widget.

The editor is used to add or remove bookmarks from the user settings. The widget is
also responsible for editing the list of servers and jobs that will contain the
bookmark items.

"""

from PySide2 import QtCore, QtWidgets

from . import bookmark_editor
from . import job_editor
from . import server_editor
from .. import actions
from .. import common
from .. import images
from .. import log
from .. import ui

HINT = 'Activate or disable existing bookmark items, or create new ones using the ' \
       'options below.'


def close():
    if common.bookmark_editor_widget is None:
        return
    try:
        common.bookmark_editor_widget.close()
        common.bookmark_editor_widget.deleteLater()
    except:
        log.error('Could not delete widget.')
    common.bookmark_editor_widget = None


def show():
    if not common.bookmark_editor_widget:
        common.bookmark_editor_widget = BookmarkEditorWidget()

    common.restore_window_geometry(common.bookmark_editor_widget)
    common.restore_window_state(common.bookmark_editor_widget)


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
        self.default_bookmarks_button = None
        self.prune_bookmarks_button = None
        self.info_bar = None

        self.setObjectName('BookmarksEditorWidget')
        self.setWindowTitle('Edit Active Bookmarks')

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        common.set_stylesheet(self)
        QtWidgets.QVBoxLayout(self)

        o = common.size(common.WidthIndicator * 1.5)
        self.layout().setContentsMargins(0, o, 0, o)
        self.layout().setSpacing(0)

        h = common.size(common.HeightRow) * 0.66

        _label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'bookmark', common.color(common.SeparatorColor), h
        )
        _label.setPixmap(pixmap)
        label = ui.PaintedLabel(
            'Edit Active Bookmarks',
            size=common.size(common.FontSizeLarge),
            color=common.color(common.TextColor),
            parent=self
        )

        self.info_bar = QtWidgets.QLabel(parent=self)
        self.info_bar.setStyleSheet(
            'QLabel {{font-family: "{family}";font-size: {size}px;margin: {o} {o} '
            '{o} {o};}}'.format(
                size=common.size(common.FontSizeSmall) * 0.2,
                family=common.font_db.secondary_font(
                    common.FontSizeSmall
                )[0].family(),
                o=common.size(common.WidthIndicator)
            )
        )
        self.info_bar.setWordWrap(False)
        self.info_bar.setFixedHeight(common.size(common.WidthMargin) * 2)

        row = ui.add_row('', height=h, parent=self)
        row.layout().setAlignment(QtCore.Qt.AlignLeft)
        row.layout().addSpacing(o)
        row.layout().addWidget(_label, 0)
        row.layout().addWidget(label, 0)
        row.layout().addWidget(self.info_bar, 1)

        self.layout().addSpacing(o)

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

        main_row.layout().setSpacing(o)
        main_row.layout().setContentsMargins(o, 0, o, 0)

        # =====================================================

        row = ui.add_row(None, vertical=True, height=None, parent=main_row)
        row.layout().setSpacing(o * 0.5)
        row.layout().setContentsMargins(0, o, 0, o)

        _grp = ui.get_group(
            parent=row, margin=common.size(
                common.WidthIndicator
            ) * 1.5
        )
        _grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        _row = ui.add_row(None, height=None, parent=_grp)
        _row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )
        grp = ui.get_group(
            parent=_grp, margin=common.size(
                common.WidthIndicator
            ) * 0.66
        )
        grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        label = ui.PaintedLabel(
            'Select or add server',
            color=common.color(common.TextSecondaryColor)
        )
        self.server_editor = server_editor.ServerListWidget(parent=grp)
        self.server_add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.GreenColor),
             common.color(common.TextSelectedColor)),
            h,
            description='Click to add a new server',
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

        _grp = ui.get_group(
            parent=row, margin=common.size(
                common.WidthIndicator
            ) * 1.5
        )
        _grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        _row = ui.add_row(None, height=None, parent=_grp)
        _row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )

        self.job_filter_widget = ui.LineEdit(parent=self)
        self.job_filter_widget.setAlignment(
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight
        )
        self.job_filter_widget.setPlaceholderText('Search...')
        _grp.layout().addWidget(self.job_filter_widget)

        grp = ui.get_group(
            parent=_grp, margin=common.size(
                common.WidthIndicator
            ) * 0.66
        )
        grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        label = ui.PaintedLabel(
            'Select or add job folder',
            color=common.color(common.TextSecondaryColor)
        )

        self.job_editor = job_editor.JobListWidget(parent=self)
        self.job_add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.GreenColor),
             common.color(common.TextSelectedColor)),
            h,
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

        _grp = ui.get_group(
            parent=row, margin=common.size(
                common.WidthIndicator
            ) * 1.5
        )
        _grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        _row = ui.add_row(None, height=None, parent=_grp)
        _row.layout().setAlignment(QtCore.Qt.AlignCenter)
        _row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )
        grp = ui.get_group(
            parent=_grp, margin=common.size(
                common.WidthIndicator
            ) * 0.66
        )
        grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        label = ui.PaintedLabel(
            'Select or add root folder',
            color=common.color(common.TextSecondaryColor)
        )

        self.bookmark_editor = bookmark_editor.BookmarkListWidget(parent=self)
        self.bookmark_add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.GreenColor),
             common.color(common.TextSelectedColor)),
            h,
            description='Click to select a folder and use it as a bookmark item.',
            state=True,
            parent=self
        )

        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        _row.layout().addWidget(self.bookmark_add_button)
        grp.layout().addWidget(self.bookmark_editor, 1)

        # =====================================================

        self.layout().addSpacing(o * 2)

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

        self.default_bookmarks_button = ui.PaintedButton(
            'Edit Default Bookmark Items'
        )
        row.layout().addWidget(self.default_bookmarks_button, 0)
        self.prune_bookmarks_button = ui.PaintedButton(
            'Prune Bookmark Items'
        )
        row.layout().addWidget(self.prune_bookmarks_button, 0)
        row.layout().addWidget(self.done_button, 1)

    def _connect_signals(self):
        self.server_editor.selectionModel().selectionChanged.connect(
            self.bookmark_editor.clear
        )
        self.server_editor.selectionModel().selectionChanged.connect(
            self.job_editor.init_data
        )
        self.job_editor.selectionModel().selectionChanged.connect(
            self.bookmark_editor.init_data
        )

        self.server_editor.progressUpdate.connect(self.set_info_message)
        self.job_editor.progressUpdate.connect(self.set_info_message)
        self.bookmark_editor.progressUpdate.connect(self.set_info_message)

        self.server_add_button.clicked.connect(self.server_editor.add)
        self.job_add_button.clicked.connect(self.job_editor.add)
        self.bookmark_add_button.clicked.connect(self.bookmark_editor.add)

        self.done_button.clicked.connect(self.close)

        self.default_bookmarks_button.clicked.connect(
            actions.edit_default_bookmarks
        )
        self.prune_bookmarks_button.clicked.connect(
            actions.prune_bookmarks
        )

        self.job_filter_widget.textChanged.connect(self.job_editor.set_filter)

    def server(self):
        index = common.get_selected_index(self.server_editor)
        if not index.isValid():
            return None
        return index.data(QtCore.Qt.DisplayRole)

    def job(self):
        index = common.get_selected_index(self.job_editor)
        if not index.isValid():
            return None
        return index.data(QtCore.Qt.UserRole + 1)

    def job_path(self):
        index = common.get_selected_index(self.job_editor)
        if not index.isValid():
            return None
        return index.data(QtCore.Qt.UserRole)

    @QtCore.Slot(str)
    def set_info_message(self, v):
        font, metrics = common.font_db.primary_font(
            common.size(common.FontSizeMedium)
        )
        v = metrics.elidedText(
            v,
            QtCore.Qt.ElideRight,
            self.window().rect().width() - common.size(common.WidthMargin) * 2
        )
        self.info_bar.setText(v)
        self.info_bar.repaint()

    def init_data(self):
        self.server_editor.init_data()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            common.save_window_state(self)

    def hideEvent(self, event):
        common.save_window_state(self)
        super().hideEvent(event)

    def closeEvent(self, event):
        common.save_window_state(self)
        super().closeEvent(event)

    def showEvent(self, event):
        QtCore.QTimer.singleShot(100, self.init_data)
        super(BookmarkEditorWidget, self).showEvent(event)

    def sizeHint(self):
        return QtCore.QSize(
            common.size(common.DefaultWidth),
            common.size(common.DefaultHeight) * 1.33
        )
