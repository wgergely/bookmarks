# -*- coding: utf-8 -*-
"""Bookmarks's main widget.

This is where the UI is assembled and signals & slots are connected.

"""
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from . import common
from . import images
from . import settings
from .threads import threads
from . import topbar
from . import shortcuts
from . import actions
from . import statusbar

from .lists import base
from .lists import assets
from .lists import bookmarks
from .lists import favourites
from .lists import files
from .lists import tasks


_instance = None


def init():
    global _instance
    _instance = MainWidget()
    _instance.initialize()
    return _instance


def instance():
    if _instance is None:
        raise RuntimeError('MainWidget is not initialized.')
    if not isinstance(_instance, MainWidget):
        raise TypeError('Wrong widget type.')
    return _instance


class MainWidget(QtWidgets.QWidget):
    """Bookmark's main widget.

    The widget is made up of a top bar, a stacked widget, and a status bar. The
    stacked widget contains the Bookmark-, Asset-, File- and Favourite widgets.

    """
    initialized = QtCore.Signal()
    connectExtraSignals = QtCore.Signal()

    def __init__(self, parent=None):
        global _instance
        if _instance is not None:
            raise RuntimeError(
                '{} cannot be initialised more than once.'.format(self.__class__.__name__))
        _instance = self

        super(MainWidget, self).__init__(parent=parent)

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon', None, common.ASSET_ROW_HEIGHT())
        self.setWindowIcon(QtGui.QIcon(pixmap))

        self._contextMenu = None
        self._initialized = False
        self.shortcuts = []

        self.stackedwidget = None
        self.bookmarkswidget = None
        self.topbar = None
        self.assetswidget = None
        self.fileswidget = None
        self.taskswidget = None
        self.favouriteswidget = None
        self.statusbar = None
        self.init_progress = u'Loading...'

    @common.debug
    @common.error
    def _create_ui(self):
        o = 0
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )

        self.stackedwidget = base.StackedWidget(parent=self)
        self.bookmarkswidget = bookmarks.BookmarksWidget(parent=self)
        self.assetswidget = assets.AssetsWidget(parent=self)
        self.fileswidget = files.FilesWidget(parent=self)
        self.taskswidget = tasks.TaskFolderWidget(parent=self.fileswidget)
        self.taskswidget.setHidden(True)
        self.favouriteswidget = favourites.FavouritesWidget(parent=self)

        self.stackedwidget.addWidget(self.bookmarkswidget)
        self.stackedwidget.addWidget(self.assetswidget)
        self.stackedwidget.addWidget(self.fileswidget)
        self.stackedwidget.addWidget(self.favouriteswidget)

        # Setting the tab now before we do any more initialisation
        idx = settings.instance().value(
            settings.UIStateSection,
            settings.CurrentList
        )
        idx = common.BookmarkTab if idx is None or False else idx
        idx = common.BookmarkTab if idx < common.BookmarkTab else idx
        idx = common.FavouriteTab if idx > common.FavouriteTab else idx
        self.stackedwidget._setCurrentIndex(idx)

        self.topbar = topbar.ListControlWidget(parent=self)
        self.statusbar = statusbar.StatusBar(parent=self)

        self.layout().addWidget(self.topbar)
        self.layout().addWidget(self.stackedwidget)
        self.layout().addWidget(self.statusbar)

    @common.debug
    @common.error
    def _connect_signals(self):
        """This is where the bulk of the model, view and control widget
        signals and slots are connected.

        """
        b = self.bookmarkswidget
        a = self.assetswidget
        f = self.fileswidget
        lc = self.topbar
        l = self.taskswidget

        # Bookmark -> Asset
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().modelDataResetRequested)
        # Asset -> File
        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().modelDataResetRequested)

        # * -> Listcontrol
        f.model().sourceModel().modelDataResetRequested.connect(
            l.model().sourceModel().modelDataResetRequested)
        f.model().sourceModel().taskFolderChanged.connect(
            l.model().sourceModel().check_task)

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
        self.taskswidget.connect_signals()

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
        """Load all model and user data.

        """
        if self._initialized:
            return

        self._init_shortcuts()
        self._create_ui()
        self._connect_signals()
        self.connectExtraSignals.emit()

        # Load active paths from the local settings
        settings.instance().verify_active()

        # Update the window title to display the current active paths
        for n in xrange(3):
            model = self.stackedwidget.widget(n).model().sourceModel()
            model.activeChanged.connect(self.update_window_title)
            model.modelReset.connect(self.update_window_title)

        # Load saved flter values from local settings
        b = self.bookmarkswidget.model()
        b.filterTextChanged.emit(b.filter_text())
        a = self.assetswidget.model()
        a.filterTextChanged.emit(a.filter_text())
        f = self.fileswidget.model()
        f.filterTextChanged.emit(f.filter_text())
        ff = self.favouriteswidget.model()
        ff.filterTextChanged.emit(ff.filter_text())

        # Load and apply filter flags stored in the local settings
        for flag in (common.MarkedAsActive, common.MarkedAsArchived, common.MarkedAsFavourite):
            b.filterFlagChanged.emit(flag, b.filter_flag(flag))
            a.filterFlagChanged.emit(flag, a.filter_flag(flag))
            f.filterFlagChanged.emit(flag, f.filter_flag(flag))
            ff.filterFlagChanged.emit(flag, ff.filter_flag(flag))

        # Start non-model linked worker threads
        _threads = []
        thread = threads.get_thread(threads.QueuedDatabaseTransaction)
        thread.start()
        _threads.append(thread)
        thread = threads.get_thread(threads.QueuedShotgunQuery)
        thread.start()
        _threads.append(thread)

        # Wait for all threads to spin up before continuing
        n = 0.0
        import time
        while not all([f.isRunning() for f in _threads]):
            n += 0.1
            time.sleep(0.1)
            if n > 2.0:
                break

        # Initialize the bookmarks model. This will initialise the
        # connected models asset, task and file models.
        self.bookmarkswidget.model().sourceModel().modelDataResetRequested.emit()

        # Let's load our favourite items
        common.signals.favouritesChanged.emit()
        
        # We're done, let other componenets know, we have finished initializing
        # the base widget
        self._initialized = True
        self.initialized.emit()

    def update_window_title(self):
        keys = (
            settings.ServerKey,
            settings.JobKey,
            settings.RootKey,
            settings.AssetKey,
            settings.TaskKey,
            settings.FileKey,
        )
        values = [settings.active(k) for k in keys if settings.active(k)]
        self.setWindowTitle(u'/'.join(values))

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

        if common.STANDALONE:
            connect(shortcuts.Quit, actions.quit)
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

    def widget(self):
        return self.stackedwidget.currentWidget()

    def index(self):
        if not self.widget().selectionModel().hasSelection():
            return QtCore.QModelIndex()
        index = self.widget().selectionModel().currentIndex()
        if not index.isValid():
            return QtCore.QModelIndex()
        return index

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
        pen.setWidth(common.ROW_SEPARATOR())
        painter.setPen(pen)
        painter.setBrush(common.SEPARATOR.darker(110))
        painter.drawRect(rect)

    def _paint_loading(self, painter):
        font, metrics = common.font_db.primary_font(
            common.MEDIUM_FONT_SIZE())
        rect = QtCore.QRect(self.rect())
        align = QtCore.Qt.AlignCenter
        color = QtGui.QColor(255, 255, 255, 80)

        pixmaprect = QtCore.QRect(rect)
        center = pixmaprect.center()
        s = common.ASSET_ROW_HEIGHT() * 1.5
        o = common.MARGIN()

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
            u'icon_bw', None, s)
        painter.setOpacity(0.5)
        painter.drawPixmap(pixmaprect, pixmap, pixmap.rect())
        painter.setOpacity(1.0)

        rect.setTop(pixmaprect.bottom() + (o * 0.5))
        rect.setHeight(metrics.height())
        common.draw_aliased_text(
            painter, font, rect, self.init_progress, align, color)

    def sizeHint(self):
        """The widget's default size."""
        return QtCore.QSize(common.WIDTH(), common.HEIGHT())
