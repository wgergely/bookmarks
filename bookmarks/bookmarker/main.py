""":class:`BookmarkerWidget`, the main editor widget.

The editor is made up of :class:`~bookmarks.bookmarker.server_editor.ServerItemEditor`,
:class:`~bookmarks.bookmarker.job_editor.JobItemEditor` and
:class:`~bookmarks.bookmarker.bookmark_editor.BookmarkItemEditor`, and defines
functionality needed saver and remove bookmark items to and from the user settings file.

"""

from PySide2 import QtCore, QtWidgets

from . import bookmark_editor
from . import job_editor
from . import server_editor
from .. import actions
from .. import common
from .. import images
from .. import ui

HINT = 'Activate or disable existing bookmark items, or create new ones using the ' \
       'options below.'


def close():
    """Closes the :class:`BookmarkerWidget` editor.

    """
    if common.bookmarker_widget is None:
        return
    try:
        common.bookmarker_widget.close()
        common.bookmarker_widget.deleteLater()
    except:
        pass
    common.bookmarker_widget = None


def show():
    """Shows the :class:`BookmarkerWidget` editor.

    """
    if not common.bookmarker_widget:
        common.bookmarker_widget = BookmarkerWidget()

    common.restore_window_geometry(common.bookmarker_widget)
    common.restore_window_state(common.bookmarker_widget)


class BookmarkerWidget(QtWidgets.QDialog):
    """The main editor used to add or remove bookmark items, jobs and servers.

    """

    def __init__(self, parent=None):
        super().__init__(
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

        self.setObjectName('AddRemoveBookmarkItemsWidget')
        self.setWindowTitle('Manage Bookmarks Items')

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        """Create ui."""
        common.set_stylesheet(self)
        QtWidgets.QVBoxLayout(self)

        o = common.size(common.size_indicator * 1.5)
        self.layout().setContentsMargins(0, 0, 0, o)
        self.layout().setSpacing(0)

        h = common.size(common.size_row_height) * 0.8

        # =====================================================

        _o = common.size(common.size_margin)
        main_row = ui.add_row(None, height=None, parent=self, cls=QtWidgets.QSplitter)
        main_row.setObjectName('mainRow')
        main_row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        main_row.layout().setSpacing(o)
        main_row.layout().setContentsMargins(o, 0, o, 0)

        # =====================================================

        pixmap = images.ImageCache.rsc_pixmap(
            'icon',
            color=None,
            size=common.size(common.size_row_height * 4),
            opacity=0.8,
        )
        label = QtWidgets.QLabel(parent=self)
        label.setPixmap(pixmap)
        main_row.layout().addWidget(label)

        # =====================================================

        row = ui.add_row(None, vertical=True, height=None, parent=main_row)
        row.layout().setSpacing(o * 0.5)
        row.layout().setContentsMargins(0, o, 0, o)

        _grp = ui.get_group(
            parent=row, margin=common.size(
                common.size_indicator
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
                common.size_indicator
            ) * 0.66
        )
        grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        label = ui.PaintedLabel(
            'Servers',
            color=common.color(common.color_secondary_text)
        )
        self.server_editor = server_editor.ServerItemEditor(parent=grp)
        self.server_add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.color_green),
             common.color(common.color_selected_text)),
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
                common.size_indicator
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
                common.size_indicator
            ) * 0.66
        )
        grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        label = ui.PaintedLabel(
            'Jobs',
            color=common.color(common.color_secondary_text)
        )

        self.job_editor = job_editor.JobItemEditor(parent=self)
        self.job_add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.color_green),
             common.color(common.color_selected_text)),
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
                common.size_indicator
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
                common.size_indicator
            ) * 0.66
        )
        grp.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        label = ui.PaintedLabel(
            'Root folders',
            color=common.color(common.color_secondary_text)
        )

        self.bookmark_editor = bookmark_editor.BookmarkItemEditor(parent=self)
        self.bookmark_add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.color_green),
             common.color(common.color_selected_text)),
            h,
            description='Click to select a folder and use it as a bookmark item.',
            state=True,
            parent=self
        )

        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        _row.layout().addWidget(self.bookmark_add_button)
        grp.layout().addWidget(self.bookmark_editor, 1)

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
            'Show default_bookmark_items.json'
        )
        row.layout().addWidget(self.default_bookmarks_button, 0)
        self.prune_bookmarks_button = ui.PaintedButton(
            'Remove invalid'
        )
        row.layout().addWidget(self.prune_bookmarks_button, 0)
        row.layout().addWidget(self.done_button, 1)

    def _connect_signals(self):
        """Connect signals."""
        self.server_editor.selectionModel().selectionChanged.connect(
            self.bookmark_editor.clear
        )
        self.server_editor.selectionModel().selectionChanged.connect(
            self.job_editor.init_data
        )
        self.job_editor.selectionModel().selectionChanged.connect(
            self.bookmark_editor.init_data
        )

        self.server_add_button.clicked.connect(self.server_editor.add)
        self.job_add_button.clicked.connect(self.job_editor.add)
        self.bookmark_add_button.clicked.connect(self.bookmark_editor.add)

        self.done_button.clicked.connect(self.close)

        self.default_bookmarks_button.clicked.connect(
            actions.reveal_default_bookmarks_json
        )
        self.prune_bookmarks_button.clicked.connect(
            actions.prune_bookmarks
        )

        self.job_filter_widget.textChanged.connect(self.job_editor.set_filter)

    def server(self):
        """Get the selected server.

        Returns:
            str: The selected server.

        """
        index = common.get_selected_index(self.server_editor)
        if not index.isValid():
            return None
        return index.data(QtCore.Qt.DisplayRole)

    def job(self):
        """Get the selected job.

        Returns:
            str: The selected job.

        """
        index = common.get_selected_index(self.job_editor)
        if not index.isValid():
            return None
        return index.data(QtCore.Qt.UserRole + 1)

    def job_path(self):
        """Get the selected job path.

        Returns:
            str: The selected job path.

        """
        index = common.get_selected_index(self.job_editor)
        if not index.isValid():
            return None
        return index.data(QtCore.Qt.UserRole)

    def init_data(self):
        """Initializes data.

        """
        self.server_editor.init_data()

    def changeEvent(self, event):
        """Change event handler."""
        if event.type() == QtCore.QEvent.WindowStateChange:
            common.save_window_state(self)

    def hideEvent(self, event):
        """Hide event handler."""
        common.save_window_state(self)
        super().hideEvent(event)

    def closeEvent(self, event):
        """Close event handler."""
        common.save_window_state(self)
        super().closeEvent(event)

    def showEvent(self, event):
        """Show event handler.

        """
        QtCore.QTimer.singleShot(100, self.init_data)
        super().showEvent(event)

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width),
            common.size(common.size_height) * 1.33
        )
