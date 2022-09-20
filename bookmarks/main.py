# -*- coding: utf-8 -*-
"""Bookmarks' main widget.

:class:`.MainWidget` consist of :class:`bookmarks.topbar.TopBarWidget`,
:class:`bookmarks.statusbar.StatusBarWidget`,
and :class:`bookmarks.lists.basewidget.ListsWidget`. The latter is the container
for the three main list item widgets:
:class:`bookmarks.lists.bookmarks.BookmarksWidget`,
:class:`bookmarks.lists.assets.AssetsWidget` and
:class:`bookmarks.lists.files.FilesWidget`.

Important:

    :class:`.MainWidget` won't be fully set up until
    :meth:`.MainWidget.initialize` is called. In standalone mode, the widget will
    automatically be initialized, on first showing, however, in EmbeddedMode,
    :meth:`.MainWidget.initialize` must be called manually.


"""
import functools

from PySide2 import QtWidgets, QtGui, QtCore

from . import actions
from . import common
from . import images
from . import shortcuts
from . import statusbar
from .topbar import topbar
from .lists import assets
from .lists import basewidget
from .lists import bookmarks
from .lists import favourites
from .lists import files
from .lists import tasks


def init():
    if common.init_mode == common.StandaloneMode:
        raise RuntimeError("Cannot be initialized in `StandaloneMode`.")

    if isinstance(common.main_widget, MainWidget):
        raise RuntimeError("MainWidget already exists.")

    common.main_widget = MainWidget()


class MainWidget(QtWidgets.QWidget):
    """Bookmark's main widget when initialized in :attr:`common.EmbeddedMode`.
    See also :class:`bookmarks.standalone.StandaloneMainWidget`, a subclass used
    as the main widget when run in :attr:`common.StandaloneMode`.

    Attributes:
        aboutToInitialize (Signal): Emitted just before the main widget is about to
                be initialized.
        initialized (Signal): Emitted when the main widget finished initializing.

    """
    aboutToInitialize = QtCore.Signal()
    initialized = QtCore.Signal()

    def __init__(self, parent=None):
        if isinstance(common.main_widget, self.__class__):
            raise RuntimeError(f'{self.__class__.__name__} already exists.')

        super().__init__(parent=parent)

        self.is_initialized = False
        self.shortcuts = []

        self._contextMenu = None

        self.stacked_widget = None
        self.bookmarks_widget = None
        self.topbar_widget = None
        self.assets_widget = None
        self.files_widget = None
        self.tasks_widget = None
        self.favourites_widget = None
        self.statusbar = None

        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

    @common.debug
    @common.error
    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)

        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)

        self.stacked_widget = basewidget.ListsWidget(parent=self)
        self.bookmarks_widget = bookmarks.BookmarksWidget(parent=self)
        self.assets_widget = assets.AssetsWidget(parent=self)
        self.files_widget = files.FilesWidget(parent=self)
        self.tasks_widget = tasks.TaskFolderWidget(parent=self.files_widget)
        self.tasks_widget.setHidden(True)
        self.favourites_widget = favourites.FavouritesWidget(parent=self)

        self.stacked_widget.addWidget(self.bookmarks_widget)
        self.stacked_widget.addWidget(self.assets_widget)
        self.stacked_widget.addWidget(self.files_widget)
        self.stacked_widget.addWidget(self.favourites_widget)

        self.topbar_widget = topbar.TopBarWidget(parent=self)
        self.statusbar = statusbar.StatusBar(parent=self)

        self.layout().addWidget(self.topbar_widget)
        self.layout().addWidget(self.stacked_widget)
        self.layout().addWidget(self.statusbar)

    def _init_current_tab(self):
        """Sets our current tab based on the current user settings.

        We can't use model indexes when this method is called as the list models
        themselves are still uninitialized resulting in
        `self.stacked_widget.setCurrentIndex()` returning an incorrect tab.

        """
        idx = common.settings.value(
            common.UIStateSection,
            common.CurrentList
        )
        idx = common.BookmarkTab if idx is None or idx is False else idx
        idx = idx if idx >= common.BookmarkTab else common.BookmarkTab

        root = common.active_paths[common.SynchronisedActivePaths][common.RootKey]
        asset = common.active_paths[common.SynchronisedActivePaths][common.AssetKey]

        if (
            not root
            and idx in (common.BookmarkTab, common.AssetTab, common.FileTab)
        ):
            idx = common.BookmarkTab

        if (
            root
            and not asset
            and idx in (common.AssetTab, common.FileTab)
        ):
            idx = common.AssetTab

        if idx > common.FavouriteTab:
            idx = common.FavouriteTab

        # We'll invoke directly the original setCurrentIndex method
        super(basewidget.ListsWidget, self.stacked_widget).setCurrentIndex(idx)

    @common.debug
    @common.error
    def _connect_signals(self):
        """This is where the bulk of the model, view and control widget
        signals and slots are connected.

        """
        b = self.bookmarks_widget
        a = self.assets_widget
        f = self.files_widget
        lc = self.topbar_widget
        l = self.tasks_widget

        # Make sure the active values are correctly set
        self.aboutToInitialize.connect(common.settings.load_active_values)

        # Bookmark -> Asset
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().reset_data)
        # Asset -> File
        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().reset_data)
        # Asset -> Task
        a.model().sourceModel().activeChanged.connect(
            l.model().sourceModel().reset_data)
        #####################################################
        # Stacked widget navigation
        b.activated.connect(
            lambda: common.signals.tabChanged.emit(common.AssetTab))
        a.activated.connect(
            lambda: common.signals.tabChanged.emit(common.FileTab))

        l.connect_signals()

        common.signals.tabChanged.connect(common.signals.updateButtons)

        # Standard activation signals
        b.activated.connect(
            lambda x: common.signals.bookmarkActivated.emit(
                *x.data(common.ParentPathRole)[0:3]
            )
        )
        a.activated.connect(
            lambda x: common.signals.assetActivated.emit(
                *x.data(common.ParentPathRole)[0:4]
            )
        )
        f.activated.connect(
            lambda x: common.signals.fileActivated.emit(
                *x.data(common.ParentPathRole)[0:5]
            )
        )

        self.initialized.connect(b.model().sourceModel().reset_data)

    @QtCore.Slot()
    @common.error
    @common.debug
    def initialize(self):
        """The widget will be in ``uninitialized`` state after creation.
        This method must be called to create the UI layout and to load the item
        models.

        """
        if self.is_initialized:
            raise RuntimeError('Cannot initialize more than once.')

        self._init_shortcuts()
        self._create_ui()
        self._init_current_tab()
        self._connect_signals()

        self.aboutToInitialize.emit()
        QtWidgets.QApplication.instance().processEvents()

        # Update the window title to display the current active paths
        for n in range(3):
            model = self.stacked_widget.widget(n).model().sourceModel()
            model.activeChanged.connect(self.update_window_title)
            model.modelReset.connect(self.update_window_title)

        # Apply filter values to the filter models
        b = self.bookmarks_widget.model()
        b.filterTextChanged.emit(b.filter_text())
        a = self.assets_widget.model()
        a.filterTextChanged.emit(a.filter_text())
        f = self.files_widget.model()
        f.filterTextChanged.emit(f.filter_text())
        ff = self.favourites_widget.model()
        ff.filterTextChanged.emit(ff.filter_text())

        for flag in (common.MarkedAsActive, common.MarkedAsArchived, common.MarkedAsFavourite):
            b.filterFlagChanged.emit(flag, b.filter_flag(flag))
            a.filterFlagChanged.emit(flag, a.filter_flag(flag))
            f.filterFlagChanged.emit(flag, f.filter_flag(flag))
            ff.filterFlagChanged.emit(flag, ff.filter_flag(flag))

        # Let's load our favourite items
        common.signals.favouritesChanged.emit()

        # We're done, let other components know, we have finished initializing
        # the base widget
        self.is_initialized = True
        self.initialized.emit()

    @QtCore.Slot()
    def update_window_title(self):
        keys = (
            common.ServerKey,
            common.JobKey,
            common.RootKey,
            common.AssetKey,
            common.TaskKey,
            common.FileKey,
        )
        values = [common.active(k) for k in keys if common.active(k)]
        self.setWindowTitle('/'.join(values))

    @common.debug
    @common.error
    def _init_shortcuts(self):
        connect = functools.partial(
            shortcuts.connect, shortcuts.MainWidgetShortcuts)

        # Adding shortcuts to the MainWidget
        shortcuts.add_shortcuts(self, shortcuts.MainWidgetShortcuts)

        connect(shortcuts.RowIncrease, actions.increase_row_size)
        connect(shortcuts.RowDecrease, actions.decrease_row_size)
        connect(shortcuts.RowReset, actions.reset_row_size)

        connect(shortcuts.ToggleSortOrder, actions.toggle_sort_order)

        connect(shortcuts.ShowBookmarksTab, functools.partial(
            actions.change_tab, common.BookmarkTab))
        connect(shortcuts.ShowAssetsTab, functools.partial(
            actions.change_tab, common.AssetTab))
        connect(shortcuts.ShowFilesTab, actions.toggle_task_view)
        connect(shortcuts.ShowFilesTab, functools.partial(
            actions.change_tab, common.FileTab))
        connect(shortcuts.ShowFavouritesTab, functools.partial(
            actions.change_tab, common.FavouriteTab))

        connect(shortcuts.NextTab, actions.next_tab)
        connect(shortcuts.PreviousTab, actions.previous_tab)

        connect(shortcuts.AddItem, actions.add_item)
        connect(shortcuts.EditItem, actions.edit_item)

        connect(shortcuts.Refresh, actions.refresh)
        connect(shortcuts.AltRefresh, actions.refresh)

        connect(shortcuts.CopyItemPath, actions.copy_selected_path)
        connect(shortcuts.CopyAltItemPath, actions.copy_selected_alt_path)
        connect(shortcuts.RevealItem, actions.reveal_selected)
        connect(shortcuts.RevealAltItem, actions.reveal_url)

        connect(shortcuts.CopyProperties, actions.copy_properties)
        connect(shortcuts.PasteProperties, actions.paste_properties)

        if common.init_mode == common.StandaloneMode:
            connect(shortcuts.Quit, common.uninitialize)
            connect(shortcuts.Minimize, actions.toggle_minimized)
            connect(shortcuts.Maximize, actions.toggle_maximized)
            connect(shortcuts.FullScreen, actions.toggle_fullscreen)
            connect(shortcuts.OpenNewInstance, actions.exec_instance)

        connect(shortcuts.ToggleSearch, common.signals.toggleFilterButton)
        connect(shortcuts.ToggleSequence, common.signals.toggleSequenceButton)
        connect(shortcuts.ToggleArchived, common.signals.toggleArchivedButton)
        connect(shortcuts.ToggleFavourite,
                common.signals.toggleFavouritesButton)
        connect(shortcuts.ToggleActive, actions.toggle_active_item)

        connect(shortcuts.HideInlineButtons,
                common.signals.toggleInlineIcons)

        connect(shortcuts.OpenSlack, actions.show_slack)
        connect(shortcuts.OpenPreferences, actions.show_preferences)
        connect(shortcuts.OpenTodo, actions.show_todos)

        connect(shortcuts.ToggleItemArchived, actions.toggle_archived)
        connect(shortcuts.ToggleItemFavourite, actions.toggle_favourite)

    def _paint_background(self, painter):
        rect = QtCore.QRect(self.rect())
        pen = QtGui.QPen(QtGui.QColor(35, 35, 35, 255))
        pen.setWidth(common.size(common.HeightSeparator))
        painter.setPen(pen)
        painter.setBrush(common.color(common.SeparatorColor).darker(110))
        painter.drawRect(rect)

    def _paint_loading(self, painter):
        font, metrics = common.font_db.primary_font(
            common.size(common.FontSizeMedium))
        rect = QtCore.QRect(self.rect())
        align = QtCore.Qt.AlignCenter
        color = QtGui.QColor(255, 255, 255, 80)

        pixmaprect = QtCore.QRect(rect)
        center = pixmaprect.center()
        s = common.size(common.HeightAsset) * 1.5
        o = common.size(common.WidthMargin)

        pixmaprect.setWidth(s)
        pixmaprect.setHeight(s)
        pixmaprect.moveCenter(center)

        painter.setBrush(QtGui.QColor(0, 0, 0, 20))
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 20))
        painter.setPen(pen)

        painter.drawRoundedRect(
            pixmaprect.marginsAdded(
                QtCore.QMargins(o * 3, o * 3, o * 3, o * 3)),
            o, o)

        pixmap = images.ImageCache.get_rsc_pixmap(
            'icon_bw', None, s)
        painter.setOpacity(0.5)
        painter.drawPixmap(pixmaprect, pixmap, pixmap.rect())
        painter.setOpacity(1.0)

        rect.setTop(pixmaprect.bottom() + (o * 0.5))
        rect.setHeight(metrics.height())
        common.draw_aliased_text(
            painter, font, rect, 'Loading...', align, color)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        self._paint_background(painter)
        if not self.is_initialized:
            self._paint_loading(painter)
        painter.end()

    def sizeHint(self):
        return QtCore.QSize(
            common.size(common.DefaultWidth),
            common.size(common.DefaultHeight)
        )
