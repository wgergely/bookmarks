from . import threadedview
from .. import delegate
from ..model.bookmark import BookmarkItemModel
from ... import common, contextmenu
from ...threads import threads


class BookmarkItemViewContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with the BookmarkItemView.

    Methods:
        refresh: Refreshes the collector and repopulates the widget.

    """

    @common.debug
    @common.error
    def setup(self):
        """Creates the context menu.

        """
        self.scripts_menu()
        self.separator()
        self.bookmark_editor_menu()
        self.add_asset_to_bookmark_menu()
        self.separator()
        self.launcher_menu()
        self.separator()
        self.sg_url_menu()
        self.sg_link_bookmark_menu()
        self.separator()
        self.bookmark_url_menu()
        self.asset_url_menu()
        self.reveal_item_menu()
        self.copy_menu()
        self.separator()
        self.import_export_properties_menu()
        self.separator()
        self.edit_selected_bookmark_menu()
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


class BookmarkItemView(threadedview.ThreadedItemView):
    """The view used to display bookmark item.

    See :class:`BookmarkItemModel`.

    """
    Delegate = delegate.BookmarkItemViewDelegate
    ContextMenu = BookmarkItemViewContextMenu

    queues = (threads.BookmarkInfo, threads.BookmarkThumbnail)

    def get_source_model(self):
        return BookmarkItemModel(parent=self)

    def __init__(self, parent=None):
        super().__init__(
            icon='bookmark',
            parent=parent
        )

    def get_hint_string(self):
        """Returns an informative hint text.

        """
        return 'Right-click and select \'Edit Jobs\' to add bookmark items'
