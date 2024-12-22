import functools

from PySide2 import QtWidgets, QtCore

from . import threadedview
from ..model import asset as assetmodel
from ..delegate.asset import AssetItemViewDelegate
from ... import common, contextmenu
from ...threads import threads


class AssetItemViewContextMenu(contextmenu.BaseContextMenu):
    """The context menu associated with :class:`AssetItemView`."""

    @common.debug
    @common.error
    def setup(self):
        """Creates the context menu.

        """
        self.scripts_menu()
        self.separator()
        self.show_add_asset_menu()
        self.add_file_to_asset_menu()
        self.separator()
        self.edit_links_menu()
        self.separator()
        self.launcher_menu()
        self.separator()
        self.sg_url_menu()
        self.sg_link_assets_menu()
        self.sg_link_asset_menu()
        self.separator()
        self.asset_progress_menu()
        self.separator()
        self.bookmark_url_menu()
        self.asset_url_menu()
        self.reveal_item_menu()
        self.copy_menu()
        self.separator()
        self.import_export_properties_menu()
        self.separator()
        self.edit_active_bookmark_menu()
        self.edit_selected_asset_menu()
        self.notes_menu()
        self.toggle_item_flags_menu()
        self.separator()
        self.row_size_menu()
        self.sort_menu()
        self.list_filter_menu()
        self.refresh_menu()
        self.separator()
        self.preferences_menu()
        self.separator()
        self.window_menu()
        self.quit_menu()


class AssetItemView(threadedview.ThreadedItemView):
    Delegate = AssetItemViewDelegate
    ContextMenu = AssetItemViewContextMenu

    queues = (threads.AssetInfo, threads.AssetThumbnail)

    def __init__(self, parent=None):
        super().__init__(
            icon='asset',
            parent=parent
        )

    def _connect_signals(self):
        super()._connect_signals()

        common.signals.assetAdded.connect(
            functools.partial(
                self.show_item,
                role=common.PathRole,
            )
        )
        common.signals.assetAdded.connect(self.start_delayed_queue_timer)
        common.signals.sgAssetsLinked.connect(self.start_delayed_queue_timer)

    def get_source_model(self):
        return assetmodel.AssetItemModel(parent=self)

    def init_model(self, *args, **kwargs):
        super().init_model(*args, **kwargs)

        model = self.model().sourceModel()
        model.modelReset.connect(self.init_progress_hidden)

        self.init_progress_columns()
        self.init_progress_hidden()

    def init_progress_columns(self):
        """Tweaks the horizontal header.

        """
        self.resized.connect(self.adapt_horizontal_header)

        self.horizontalHeader().setHidden(False)
        self.horizontalHeader().setMinimumSectionSize(common.Size.Section())

        for idx in range(self.model().columnCount()):
            if idx < 4:
                continue
            self.horizontalHeader().setSectionResizeMode(
                idx, QtWidgets.QHeaderView.Fixed
            )

    @QtCore.Slot()
    def adapt_horizontal_header(self, *args, **kwargs):
        """Slot connected to the resized signal is used to hide the progress columns when
        the window size is small.

        """
        min_width = common.Size.DefaultWidth(1.66)

        hidden = self.progress_hidden()
        hidden = True if self.width() < min_width else hidden

        self.horizontalHeader().setHidden(hidden)
        for n in range(self.model().columnCount()):
            if n < 4:
                continue
            self.horizontalHeader().setSectionHidden(n, hidden)

    def get_hint_string(self):
        """Returns an informative hint text.

        """
        return 'Right-click and select \'Add Asset\' to add items'

    def showEvent(self, event):
        """Show event handler.

        """
        source_index = self.model().sourceModel().active_index()
        if source_index.isValid():
            index = self.model().mapFromSource(source_index)
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect
            )
        return super().showEvent(event)

    def mouseReleaseEvent(self, event):
        cursor_position = event.pos()
        index = self.indexAt(cursor_position)
        if not index.isValid():
            return super().mouseReleaseEvent(event)

        if index.column() < 4:
            return super().mouseReleaseEvent(event)

        self.edit(index)

    @common.error
    @common.debug
    def init_progress_hidden(self):
        """Restore the previous state of the inline icon buttons.

        """
        model = self.model().sourceModel()
        v = model.get_filter_setting('filters/progress')
        v = False if not v else v
        self._progress_hidden = v

        self.adapt_horizontal_header()

    def progress_hidden(self):
        return self._progress_hidden

    def set_progress_hidden(self, val):
        """Sets the visibility of the progress tracker columns.

        """
        self.model().sourceModel().set_filter_setting('filters/progress', val)
        self._progress_hidden = val
        self.adapt_horizontal_header()
