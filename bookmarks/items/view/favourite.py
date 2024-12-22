from PySide2 import QtCore, QtWidgets

from ... import common, contextmenu
from . import file as fileview
from ..model import favourite as favouritemodel
from ..delegate import favourite as delegate
from ...threads import threads


class FavouriteItemViewContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with :class:`FavouriteItemView`.

    """

    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
        self.scripts_menu()
        self.separator()
        self.control_favourites_menu()
        if self.index.isValid():
            self.remove_favourite_menu()
        self.separator()
        self.reveal_item_menu()
        self.copy_menu()
        self.separator()
        self.collapse_sequence_menu()
        self.separator()
        self.row_size_menu()
        self.sort_menu()
        self.list_filter_menu()
        self.separator()
        self.refresh_menu()
        self.separator()
        self.preferences_menu()
        self.separator()
        self.window_menu()
        self.quit_menu()


class FavouriteItemView(fileview.FileItemView):
    """The widget responsible for showing all the items marked as favourites.

    """
    Delegate = delegate.FavouriteItemViewDelegate
    ContextMenu = FavouriteItemViewContextMenu

    queues = (threads.FavouriteInfo, threads.FavouriteThumbnail)

    def __init__(self, icon='favourite', parent=None):
        super().__init__(
            icon=icon,
            parent=parent
        )

        self.reset_timer = common.Timer(parent=self)
        self.reset_timer.setInterval(50)
        self.reset_timer.setSingleShot(True)

        self.reset_timer.timeout.connect(self.execute_queued_reset)

        common.signals.favouritesChanged.connect(self.queue_model_reset)

    def get_source_model(self):
        return favouritemodel.FavouriteItemModel(parent=self)

    @QtCore.Slot()
    def execute_queued_reset(self):
        """Make sure to only reset the model when the mouse is no longer pressed.

        """
        if QtWidgets.QApplication.instance().mouseButtons() != QtCore.Qt.NoButton:
            self.queue_model_reset()
            return
        if self.multi_toggle_items:
            self.queue_model_reset()
            return
        model = self.model().sourceModel()
        model.reset_data(force=True)

    @QtCore.Slot()
    def queue_model_reset(self):
        """Starts/reset the timer responsible for reloading the list of
        favourite items.

        """
        self.reset_timer.start(self.reset_timer.interval())

    def get_hint_string(self):
        """Returns an informative hint text.

        """
        model = self.model().sourceModel()
        if not model.rowCount():
            return 'No favourites yet'
