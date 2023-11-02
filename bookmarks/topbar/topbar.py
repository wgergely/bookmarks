"""Defines :class:`.TopBarWidget`, the main widget containing all control buttons.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from . import buttons
from . import filters
from . import tabs
from .. import common
from .. import images
from .. import ui


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
    common.idx(reset=True, start=common.FavouriteTab + 1): {
        'widget': buttons.ApplicationLauncherButton,
        'hidden': False,
    },
    common.idx(): {
        'widget': filters.JobsFilterButton,
        'hidden': True,
    },
    common.idx(): {
        'widget': filters.EntityFilterButton,
        'hidden': True,
    },
    common.idx(): {
        'widget': filters.TaskFilterButton,
        'hidden': True,
    },
    common.idx(): {
        'widget': filters.SubdirFilterButton,
        'hidden': True,
    },
    common.idx(): {
        'widget': filters.TypeFilterButton,
        'hidden': True,
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


class ContextStatusBar(QtWidgets.QWidget):
    """The widget used to draw an informative status label below the main bar.

    The status label will display the current active context.

    """

    def __init__(self, parent=None):
        super().__init__(
            parent=parent
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.label_widget = None
        self.note_widget = None

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        o = common.size(common.size_indicator) * 3
        height = common.size(common.size_margin) + o

        self.setFixedHeight(height)

        QtWidgets.QHBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        self.layout().setContentsMargins(o, 0, o, 0)
        self.layout().setSpacing(0)

        self.label_widget = ui.PaintedLabel(
            '',
            color=common.color(common.color_text),
            size=common.size(common.size_font_medium) * 1.1,
            parent=self
        )
        self.note_widget = ui.PaintedLabel(
            '',
            color=common.color(common.color_blue),
            size=common.size(common.size_font_medium) * 0.9,
            parent=self
        )


        self.arrow_left_button = ui.ClickableIconButton(
            'arrow_left',
            (common.color(common.color_text), common.color(common.color_text)),
            size=common.size(common.size_margin),
            description='Previous item',
            parent=self
        )

        self.arrow_right_button = ui.ClickableIconButton(
            'arrow_right',
            (common.color(common.color_text), common.color(common.color_text)),
            size=common.size(common.size_margin),
            description='Next item',
            parent=self
        )

        self.layout().addStretch()
        self.layout().addWidget(self.arrow_left_button)
        self.layout().addSpacing(o)
        self.layout().addWidget(self.label_widget)
        self.layout().addWidget(self.note_widget)
        self.layout().addSpacing(o)
        self.layout().addWidget(self.arrow_right_button)
        self.layout().addStretch()

    def _connect_signals(self):
        common.signals.bookmarkActivated.connect(self.update)
        common.signals.assetActivated.connect(self.update)
        common.signals.taskFolderChanged.connect(self.update)
        common.signals.tabChanged.connect(self.update)
        common.signals.updateTopBarButtons.connect(self.update)

        self.arrow_left_button.clicked.connect(self.arrow_left)
        self.arrow_right_button.clicked.connect(self.arrow_right)

        self.label_widget.clicked.connect(self.show_quick_switch_menu)

    @QtCore.Slot()
    def arrow_left(self):
        """Slot responsible for activating the previous index in the current tab's parent view.

        """
        idx = common.current_tab()
        if idx == common.BookmarkTab:
            return

        widget = common.widget(idx - 1)
        if not widget:
            return

        index = widget.model().mapFromSource(widget.model().sourceModel().active_index())

        widget.selectionModel().select(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )
        widget.selectionModel().setCurrentIndex(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )

        widget.key_up()
        widget.key_enter()

    @QtCore.Slot()
    def arrow_right(self):
        """Slot responsible for activating the next index in the current tab's parent view.

        """
        idx = common.current_tab()
        if idx == common.BookmarkTab:
            return

        widget = common.widget(idx - 1)
        if not widget:
            return

        index = widget.model().mapFromSource(widget.model().sourceModel().active_index())

        widget.selectionModel().select(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )
        widget.selectionModel().setCurrentIndex(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect |
            QtCore.QItemSelectionModel.Rows
        )

        widget.key_down()
        widget.key_enter()

    def contextMenuEvent(self, event):
        self.label_widget.clicked.emit()

    @QtCore.Slot()
    def show_quick_switch_menu(self):
        """Slot responsible for showing the quick switch menu.

        """
        idx = common.current_tab()

        from . import quickswitch
        if idx == common.AssetTab:
            menu = quickswitch.SwitchBookmarkMenu(
                QtCore.QModelIndex(),
                parent=self
            )
        elif idx == common.FileTab:
            menu = quickswitch.SwitchAssetMenu(
                QtCore.QModelIndex(),
                parent=self
            )
        else:
            return

        # Move the menu to the left of the label and just below it
        menu.move(
            self.label_widget.mapToGlobal(
                QtCore.QPoint(
                    0,
                    self.label_widget.height()
                )
            )
        )
        menu.exec_()


    @QtCore.Slot()
    def update(self, *args, **kwargs):
        """Update the informative labels based on the current context.

        """
        idx = common.current_tab()

        if idx == common.BookmarkTab:
            self.setHidden(True)
        else:
            self.setHidden(False)

        display_name = ''
        if idx > common.BookmarkTab:
            active_index = common.active_index(idx - 1)
            if active_index and active_index.isValid():
                display_name = active_index.data(QtCore.Qt.DisplayRole)

        if idx == common.FileTab:
            task = common.active('task')
            task = task if task else '(no asset folder selected)'
            display_name = f'{display_name}/{task}'

        display_name = display_name.strip(' _-').replace('/', '  •  ')

        if idx == common.FavouriteTab:
            display_name = 'Favourites'
            self.arrow_left_button.setHidden(True)
            self.arrow_right_button.setHidden(True)
        else:
            self.arrow_left_button.setHidden(False)
            self.arrow_right_button.setHidden(False)

        self.label_widget.setText(display_name)

        # Update note widget
        source_model = common.source_model(common.current_tab())
        p = source_model.source_path()
        k = source_model.task()
        t = source_model.data_type()

        data = common.get_data(p, k, t)
        if data and data.refresh_needed:
            self.note_widget.setHidden(False)
            self.note_widget.setText('(refresh needed)')
        else:
            self.note_widget.setHidden(True)
            self.note_widget.setText('')




class TopBarWidget(QtWidgets.QWidget):
    """The bar above the stacked widget containing the main app control buttons.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._buttons = {}

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        o = common.size(common.size_indicator) * 3
        height = common.size(common.size_margin) + o

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
        widget.layout().setSpacing(o)
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

        widget = ContextStatusBar(parent=self)
        self.layout().addWidget(widget, 1)
        widget.setHidden(True)

    def _connect_signals(self):
        pass

    def button(self, idx):
        if idx not in self._buttons:
            raise ValueError('Button does not exist')
        return self._buttons[idx]
