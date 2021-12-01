# -*- coding: utf-8 -*-
"""Bookmarks's main widget.

This is where the UI is assembled and signals & slots are connected.

"""
import time
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from . import images

from . threads import threads
from . import topbar
from . import shortcuts
from . import actions
from . import statusbar

from . lists import basewidget
from . lists import assets
from . lists import bookmarks
from . lists import favourites
from . lists import files
from . lists import tasks


def init():
    if common.init_mode == common.StandaloneMode:
        raise RuntimeError("Cannot be initialized in `StandaloneMode`.")

    if isinstance(common.main_widget, MainWidget):
        raise RuntimeError("MainWidget already exists.")

    common.main_widget = MainWidget()


class MainWidget(QtWidgets.QWidget):
    """Bookmark's main widget when initialized as `EmbeddedMode`.

    The widget is made up of topbar, a stacked widget, and a status bar. The
    stacked widget contains the Bookmark-, Asset-, File- and Favourite widgets.

    """
    aboutToInitialize = QtCore.Signal()
    initialized = QtCore.Signal()

    def __init__(self, parent=None):
        if isinstance(common.main_widget, self.__class__):
            raise RuntimeError(f'{self.__class__.__name__} already exists.')

        super().__init__(parent=parent)

        self._initialized = False
        self.init_progress = 'Loading...'
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

        self.stacked_widget = basewidget.TabsWidget(parent=self)
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
        # Setting the tab now before we do any more initialisation
        idx = common.settings.value(
            common.UIStateSection,
            common.CurrentList
        )
        idx = common.BookmarkTab if idx is None or idx is False else idx
        idx = common.BookmarkTab if idx < common.BookmarkTab else idx
        idx = common.FavouriteTab if idx > common.FavouriteTab else idx
        super(basewidget.TabsWidget, self.stacked_widget).setCurrentIndex(idx)

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

        # Bookmark -> Asset
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().reset_data)
        # Asset -> File
        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().reset_data)
        #####################################################
        # Stacked widget navigation
        b.activated.connect(
            lambda: common.signals.tabChanged.emit(common.AssetTab))
        a.activated.connect(
            lambda: common.signals.tabChanged.emit(common.FileTab))
        a.activated.connect(l.model().sourceModel().check_task)

        ########################################################################
        b.model().sourceModel().activeChanged.connect(lc.slack_button.check_token)
        #####################################################
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

    @QtCore.Slot()
    @common.error
    @common.debug
    def initialize(self):
        """When the widget is first constructed it won't be initialized until
        this method is called.

        """
        if self._initialized:
            return

        self._init_shortcuts()
        self._create_ui()
        self._init_current_tab()
        self._connect_signals()
        self.aboutToInitialize.emit()

        # Start non-model linked worker threads
        _threads = []
        thread = threads.get_thread(threads.QueuedDatabaseTransaction)
        thread.start()
        _threads.append(thread)
        thread = threads.get_thread(threads.QueuedShotgunQuery)
        thread.start()
        _threads.append(thread)

        # Update the window title to display the current active paths
        for n in range(3):
            model = self.stacked_widget.widget(n).model().sourceModel()
            model.activeChanged.connect(self.update_window_title)
            model.modelReset.connect(self.update_window_title)

        # Load saved flter values from user settings
        b = self.bookmarks_widget.model()
        b.filterTextChanged.emit(b.filter_text())
        a = self.assets_widget.model()
        a.filterTextChanged.emit(a.filter_text())
        f = self.files_widget.model()
        f.filterTextChanged.emit(f.filter_text())
        ff = self.favourites_widget.model()
        ff.filterTextChanged.emit(ff.filter_text())

        # Load and apply filter flags stored in the user settings
        for flag in (common.MarkedAsActive, common.MarkedAsArchived, common.MarkedAsFavourite):
            b.filterFlagChanged.emit(flag, b.filter_flag(flag))
            a.filterFlagChanged.emit(flag, a.filter_flag(flag))
            f.filterFlagChanged.emit(flag, f.filter_flag(flag))
            ff.filterFlagChanged.emit(flag, ff.filter_flag(flag))

        # Wait for all threads to spin up before continuing
        n = 0.0
        while not all(f.isRunning() for f in _threads):
            n += 0.1
            time.sleep(0.1)
            if n > 2.0:
                break

        # Initialize the bookmarks model. This will initialise the
        # connected models asset, task and file models.
        self.bookmarks_widget.model().sourceModel().reset_data()

        # Let's load our favourite items
        common.signals.favouritesChanged.emit()

        # We're done, let other componenets know, we have finished initializing
        # the base widget
        self._initialized = True
        self.initialized.emit()

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

        connect(shortcuts.ToggleGenerateThumbnails,
                common.signals.toggleMakeThumbnailsButton)
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

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        self._paint_background(painter)
        if not self._initialized:
            self._paint_loading(painter)
        painter.end()

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
            painter, font, rect, self.init_progress, align, color)

    def sizeHint(self):
        return QtCore.QSize(
            common.size(common.DefaultWidth),
            common.size(common.DefaultHeight)
        )
