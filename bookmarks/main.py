"""Bookmarks' main widget.

:class:`.MainWidget` consist of :class:`~bookmarks.topbar.topbar.TopBarWidget`,
:class:`~bookmarks.statusbar.StatusBar`,
and :class:`~bookmarks.items.views.ListsWidget`. The latter is the container
for the three main list item widgets:
:class:`~bookmarks.items.bookmark_items.BookmarkItemView`,
:class:`~bookmarks.items.asset_items.AssetItemView` and
:class:`~bookmarks.items.file_items.FileItemView`.

You can always access the main widget from the :mod:`~bookmarks.common` module directly:

.. code-block:: python
    :linenos:

    from bookmarks import common
    common.main_widget.show()



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
from .items import assets
from .items import bookmarks
from .items import favourites
from .items import files
from .items import views
from .topbar import topbar


def init():
    """Creates the :class:`MainWidget` instance.

    """
    if common.init_mode == common.Mode.Standalone:
        raise RuntimeError("Cannot be initialized in `StandaloneMode`.")

    if isinstance(common.main_widget, MainWidget):
        raise RuntimeError("MainWidget already exists.")

    common.main_widget = MainWidget()


class MainWidget(QtWidgets.QWidget):
    """Bookmark's main widget when initialized in :attr:`~bookmarks.common.Mode.Embedded`.
    See also :class:`bookmarks.standalone.BookmarksAppWindow`, a subclass used
    as the main widget when run in :attr:`~bookmarks.common.Mode.Standalone`.

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
        self.topbar_widget = None
        self.statusbar = None

        self.bookmarks_widget = None
        self.assets_widget = None
        self.files_widget = None
        self.favourites_widget = None

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

        # Main stacked widget used to navigate items
        self.stacked_widget = views.ListsWidget(parent=self)

        # Item views
        self.bookmarks_widget = bookmarks.BookmarkItemView(parent=self)
        self.assets_widget = assets.AssetItemView(parent=self)
        self.files_widget = files.FileItemView(parent=self)
        self.favourites_widget = favourites.FavouriteItemView(parent=self)

        # Add items to stacked widget
        self.stacked_widget.addWidget(self.bookmarks_widget)
        self.stacked_widget.addWidget(self.assets_widget)
        self.stacked_widget.addWidget(self.files_widget)
        self.stacked_widget.addWidget(self.favourites_widget)

        # Top and bottom bars
        self.topbar_widget = topbar.TopBarWidget(parent=self)
        self.statusbar = statusbar.StatusBar(parent=self)

        self.layout().addWidget(self.topbar_widget, 0)
        self.layout().addWidget(self.stacked_widget, 1)
        self.layout().addWidget(self.statusbar, 0)

    def _init_current_tab(self):
        """Sets our current tab based on the current user settings.

        We can't use model indexes when this method is called as the list models
        themselves are still shutdownd resulting in
        `self.stacked_widget.setCurrentIndex()` returning an incorrect tab.

        """
        idx = common.settings.value('selection/current_tab')
        idx = common.BookmarkTab if idx is None or idx is False else idx
        idx = idx if idx >= common.BookmarkTab else common.BookmarkTab

        root = common.active_paths[common.ActiveMode.Synchronized]['root']
        asset = common.active_paths[common.ActiveMode.Synchronized]['asset']

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
        super(views.ListsWidget, self.stacked_widget).setCurrentIndex(idx)

    @common.debug
    @common.error
    def _connect_signals(self):
        """This is where the bulk of the model, view and control widget
        signals and slots are connected.

        """
        b = self.bookmarks_widget
        a = self.assets_widget
        f = self.files_widget

        # Make sure the active values are correctly set
        self.aboutToInitialize.connect(common.init_active)

        # Bookmark -> Asset
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().reset_data
        )
        # Asset -> File
        a.model().sourceModel().activeChanged.connect(
            actions.activate_scenes_task_folder
        )
        a.model().sourceModel().activeChanged.connect(
            f.model().sourceModel().reset_data
        )

        # Stacked widget navigation
        b.activated.connect(
            lambda: common.signals.tabChanged.emit(common.AssetTab)
        )
        a.activated.connect(
            lambda: common.signals.tabChanged.emit(common.FileTab)
        )


        common.signals.tabChanged.connect(common.signals.updateTopBarButtons)

        # Standard activation signals
        b.activated.connect(
            lambda x: common.signals.bookmarkItemActivated.emit(
                *x.data(common.ParentPathRole)[0:3]
            )
        )
        a.activated.connect(
            lambda x: common.signals.assetItemActivated.emit(
                *x.data(common.ParentPathRole)[0:4]
            )
        )
        f.activated.connect(
            lambda x: common.signals.fileItemActivated.emit(
                *x.data(common.ParentPathRole)[0:5]
            )
        )

        # Load bookmark items upon initialization
        self.initialized.connect(b.model().sourceModel().reset_data)

    @QtCore.Slot()
    @common.error
    @common.debug
    def initialize(self):
        """The widget will be in ``shutdownd`` state after creation.
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
        QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

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

        for flag in (
                common.MarkedAsActive,
                common.MarkedAsArchived,
                common.MarkedAsFavourite
        ):
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
        """Slot used to update the window title.

        """
        values = [common.active(k) for k in common.SECTIONS['active'] if common.active(k)]
        self.setWindowTitle('/'.join(values))

    @common.debug
    @common.error
    def _init_shortcuts(self):
        connect = functools.partial(
            shortcuts.connect, shortcuts.MainWidgetShortcuts
        )

        # Adding shortcuts to the MainWidget
        shortcuts.add_shortcuts(self, shortcuts.MainWidgetShortcuts)

        connect(shortcuts.RowIncrease, actions.increase_row_size)
        connect(shortcuts.RowDecrease, actions.decrease_row_size)
        connect(shortcuts.RowReset, actions.reset_row_size)

        connect(shortcuts.ToggleSortOrder, actions.toggle_sort_order)

        connect(
            shortcuts.ShowBookmarksTab, functools.partial(
                actions.change_tab, common.BookmarkTab
            )
        )
        connect(
            shortcuts.ShowAssetsTab, functools.partial(
                actions.change_tab, common.AssetTab
            )
        )
        connect(
            shortcuts.ShowFilesTab, functools.partial(
                actions.change_tab, common.FileTab
            )
        )
        connect(
            shortcuts.ShowFavouritesTab, functools.partial(
                actions.change_tab, common.FavouriteTab
            )
        )

        connect(shortcuts.NextTab, actions.next_tab)
        connect(shortcuts.PreviousTab, actions.previous_tab)

        connect(shortcuts.AddItem, actions.add_item)
        connect(shortcuts.EditItemProperties, actions.edit_item_properties)

        connect(shortcuts.Refresh, actions.refresh)
        connect(shortcuts.AltRefresh, actions.refresh)

        connect(shortcuts.ApplicationLauncher, actions.pick_launcher_item)

        connect(shortcuts.CopyItemPath, actions.copy_selected_path)
        connect(shortcuts.CopyAltItemPath, actions.copy_selected_alt_path)
        connect(shortcuts.RevealItem, actions.reveal_selected)
        connect(shortcuts.RevealAltItem, actions.reveal_url)

        connect(shortcuts.CopyProperties, actions.copy_properties)
        connect(shortcuts.PasteProperties, actions.paste_properties)

        if common.init_mode == common.Mode.Standalone:
            connect(shortcuts.Quit, common.shutdown)
            connect(shortcuts.Minimize, actions.toggle_minimized)
            connect(shortcuts.Maximize, actions.toggle_maximized)
            connect(shortcuts.FullScreen, actions.toggle_full_screen)
            connect(shortcuts.OpenNewInstance, actions.exec_instance)

        connect(shortcuts.ToggleSearch, common.signals.toggleFilterButton)
        connect(shortcuts.ToggleSequence, common.signals.toggleSequenceButton)
        connect(shortcuts.ToggleArchived, common.signals.toggleArchivedButton)
        connect(
            shortcuts.ToggleFavourite,
            common.signals.toggleFavouritesButton
        )
        connect(shortcuts.ToggleActive, actions.toggle_active_item)

        connect(
            shortcuts.HideInlineButtons,
            common.signals.toggleInlineIcons
        )

        connect(shortcuts.OpenPreferences, actions.show_preferences)
        connect(shortcuts.OpenTodo, actions.show_notes)

        connect(shortcuts.ToggleItemArchived, actions.toggle_archived)
        connect(shortcuts.ToggleItemFavourite, actions.toggle_favourite)

        connect(shortcuts.PushToRV, actions.push_to_rv)
        connect(shortcuts.PushToRVFullScreen, actions.push_to_rv_full_screen)
        connect(shortcuts.EditAssetLinks, actions.edit_asset_links)

    def _paint_background(self, painter):
        rect = QtCore.QRect(self.rect())
        pen = QtGui.QPen(QtGui.QColor(35, 35, 35, 255))
        pen.setWidth(common.Size.Separator())
        painter.setPen(pen)
        painter.setBrush(common.Color.VeryDarkBackground().darker(110))
        painter.drawRect(rect)

    def _paint_loading(self, painter):
        font, metrics = common.Font.MediumFont(common.Size.MediumText())
        rect = QtCore.QRect(self.rect())
        align = QtCore.Qt.AlignCenter
        color = QtGui.QColor(255, 255, 255, 80)

        pixmaprect = QtCore.QRect(rect)
        center = pixmaprect.center()
        s = common.Size.RowHeight(3.0)
        o = common.Size.Margin()

        pixmaprect.setWidth(s)
        pixmaprect.setHeight(s)
        pixmaprect.moveCenter(center)

        painter.setBrush(QtGui.QColor(0, 0, 0, 20))
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 20))
        painter.setPen(pen)

        painter.drawRoundedRect(
            pixmaprect.marginsAdded(
                QtCore.QMargins(o * 3, o * 3, o * 3, o * 3)
            ),
            o, o
        )

        pixmap = images.rsc_pixmap(
            'icon_bw', None, s
        )
        painter.setOpacity(0.5)
        painter.drawPixmap(pixmaprect, pixmap, pixmap.rect())
        painter.setOpacity(1.0)

        rect.setTop(pixmaprect.bottom() + (o * 0.5))
        rect.setHeight(metrics.height())
        common.draw_aliased_text(
            painter, font, rect, 'Loading...', align, color
        )

    def paintEvent(self, event):
        """Event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        self._paint_background(painter)
        if not self.is_initialized:
            self._paint_loading(painter)
        painter.end()

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight()
        )
