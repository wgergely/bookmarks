# -*- coding: utf-8 -*-
"""The main Bookmark Editor widget.

The editor is used to add or remove bookmarks from the user settings.
The widget is also responsible for editing the list of servers and jobs that
will contain the bookmark items.

"""

from PySide2 import QtCore, QtWidgets

from . import bookmark_editor
from . import job_editor
from . import server_editor
from .. import actions
from .. import common
from .. import images
from .. import ui

HINT = "To start, add your server below. If the server does not have jobs, you \
can add new ones using *.zip templates.\nAll job items will contain a series of \
bookmark items - these are the folders used to store your project's files and \
are usually called 'Shots', 'Assets', etc.\nYou can create new bookmark items \
below or toggle existing ones by double-clicking their name (or clicking their \
label)."


def close():
    if common.bookmark_editor_widget is None:
        return
    try:
        common.bookmark_editor_widget.close()
        common.bookmark_editor_widget.deleteLater()
    except:
        pass
    common.bookmark_editor_widget = None


def show():
    if not common.bookmark_editor_widget:
        common.bookmark_editor_widget = BookmarkEditorWidget()

    state = common.settings.value(
        common.UIStateSection,
        common.BookmarkEditorStateKey,
    )
    state = QtCore.Qt.WindowNoState if state is None else QtCore.Qt.WindowState(
        state
    )

    common.bookmark_editor_widget.activateWindow()
    common.bookmark_editor_widget.restore_window()
    if state == QtCore.Qt.WindowNoState:
        common.bookmark_editor_widget.showNormal()
    elif state & QtCore.Qt.WindowMaximized:
        common.bookmark_editor_widget.showMaximized()
    elif state & QtCore.Qt.WindowFullScreen:
        common.bookmark_editor_widget.showFullScreen()
    else:
        common.bookmark_editor_widget.showNormal()

    common.bookmark_editor_widget.open()
    return common.bookmark_editor_widget


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
        self.job_subdir_toggle = None
        self.bookmark_editor = None
        self.bookmark_add_button = None
        self.persistent_bookmarks_button = None
        self.info_bar = None

        self.setObjectName('BookmarksEditorWidget')
        self.setWindowTitle('Edit Bookmarks')

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        common.set_stylesheet(self)
        QtWidgets.QVBoxLayout(self)

        o = common.size(common.WidthMargin) * 0.66
        self.layout().setContentsMargins(0, o, 0, o)
        self.layout().setSpacing(0)

        h = common.size(common.HeightRow) * 0.66

        _label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'bookmark', common.color(common.SeparatorColor), h * 0.8
        )
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
        label = ui.Label(
            HINT, color=common.color(
                common.TextSecondaryColor
            ), parent=_row
        )
        _row.layout().addWidget(label, 0)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum,
        )
        _row.layout().setContentsMargins(o, o, o, o)

        label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'gradient5', common.color(common.SeparatorColor), o
        )
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

        _grp = ui.get_group(
            parent=row, margin=common.size(
                common.WidthIndicator
            ) * 1.5
        )
        _row = ui.add_row(None, height=None, parent=_grp)
        _row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )
        grp = ui.get_group(
            parent=row, margin=common.size(
                common.WidthIndicator
            ) * 0.66
        )
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
            (common.color(common.GreenColor),
             common.color(common.TextSelectedColor)),
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

        _grp = ui.get_group(
            parent=row, margin=common.size(
                common.WidthIndicator
            ) * 1.5
        )
        _row = ui.add_row(None, height=None, parent=_grp)
        _row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )

        grp = ui.get_group(
            parent=row, margin=common.size(
                common.WidthIndicator
            ) * 0.66
        )
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
            (common.color(common.GreenColor),
             common.color(common.TextSelectedColor)),
            common.size(common.HeightRow) * 0.5,
            description='Click to create a new job',
            state=True,
            parent=self
        )

        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        _row.layout().addWidget(self.job_add_button)

        self.job_filter_widget = ui.LineEdit(parent=self)
        self.job_filter_widget.setAlignment(
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight
        )
        self.job_filter_widget.setPlaceholderText('Search Jobs...')
        grp.layout().addWidget(self.job_filter_widget)

        grp.layout().addWidget(self.job_editor, 1)

        self.job_subdir_toggle = QtWidgets.QCheckBox('Use clients')
        grp.layout().addWidget(self.job_subdir_toggle, 1)

        # =====================================================

        row = ui.add_row(None, vertical=True, height=None, parent=main_row)
        row.layout().setSpacing(o * 0.5)
        row.layout().setContentsMargins(0, o, 0, o)

        _grp = ui.get_group(
            parent=row, margin=common.size(
                common.WidthIndicator
            ) * 1.5
        )
        _row = ui.add_row(None, height=None, parent=_grp)
        _row.layout().setAlignment(QtCore.Qt.AlignCenter)
        _row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )
        grp = ui.get_group(
            parent=row, margin=common.size(
                common.WidthIndicator
            ) * 0.66
        )
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
            (common.color(common.GreenColor),
             common.color(common.TextSelectedColor)),
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

        self.layout().addWidget(self.info_bar, 1)

        # =====================================================
        # Separator
        row = ui.add_row('', height=o, parent=self)

        label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'gradient2', common.color(common.SeparatorColor), o
        )
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
            'Edit Persistent Bookmarks'
        )
        row.layout().addWidget(self.persistent_bookmarks_button, 0)
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

        self.persistent_bookmarks_button.clicked.connect(
            actions.edit_persistent_bookmarks
        )

        self.job_subdir_toggle.stateChanged.connect(
            lambda v: common.settings.setValue(
                common.SettingsSection,
                common.JobsHaveSubdirs,
                int(v)
            )
        )
        self.job_subdir_toggle.stateChanged.connect(self.job_editor.init_data)

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
        self.init_job_subdir_toggle()
        self.server_editor.init_data()

    def init_job_subdir_toggle(self):
        v = common.settings.value(
            common.SettingsSection, common.JobsHaveSubdirs
        )
        v = QtCore.Qt.UnChecked if v is None else QtCore.Qt.CheckState(v)

        self.job_subdir_toggle.blockSignals(True)
        self.job_subdir_toggle.setCheckState(v)
        self.job_subdir_toggle.blockSignals(False)

    @common.error
    @common.debug
    @QtCore.Slot()
    def save_window(self, *args, **kwargs):
        common.settings.setValue(
            common.UIStateSection,
            common.BookmarkEditorGeometryKey,
            self.saveGeometry()
        )
        common.settings.setValue(
            common.UIStateSection,
            common.BookmarkEditorStateKey,
            int(self.windowState())
        )

    @common.error
    @common.debug
    def restore_window(self, *args, **kwargs):
        geometry = common.settings.value(
            common.UIStateSection,
            common.BookmarkEditorGeometryKey,
        )
        if geometry is not None:
            self.restoreGeometry(geometry)

    def hideEvent(self, event):
        self.save_window()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.save_window()
        super().closeEvent(event)

    def showEvent(self, event):
        QtCore.QTimer.singleShot(100, self.init_data)
        super(BookmarkEditorWidget, self).showEvent(event)

    def sizeHint(self):
        return QtCore.QSize(
            common.size(common.DefaultWidth),
            common.size(common.DefaultHeight) * 1.33
        )
