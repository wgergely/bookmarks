"""Bookmark items at their core are simple file paths made up of a ``server``, ``job``
and ``root`` components. We usually store them in the following form:

.. code-block:: python

    {
        '//path/to/my/server/my_job/my_shots': {
            'server': '//path_to_my/server',
            'job': 'my_job',
            'root': 'my_shots'
        }
    }


:class:`BookmarkItemModel` is responsible for loading saved bookmark items and
:class:`BookmarkItemView` for displaying them. See
:meth:`BookmarkItemModel.item_generator` for how the model finds saved bookmark items.

Properties like description, frame-range, frame-rate, or ShotGrid linkage are stored in
sqlite3 databases located at each bookmark item's root folder. See
:mod:`bookmarks.database` more details.

Throughout the app, data interfaces usually require a bookmark item, commonly as
separate server, job, root arguments. See :func:`~bookmarks.common.settings.active` to
see how active path components can be queried.

Hint:
    The term "active" refers to items the user has activated, e.g. double-clicked. When
    an item is activated all path components that make up that item will
    become active.

    .. code-block:: python

        server = common.active('server')
        job = common.active('job')
        root = common.active('root')

        # Or...

        server, job, root = common.active('root', args=True)



Model items store their path segments using the
:attr:`~bookmarks.common.ParentPathRole` role. E.g.:

.. code-block:: python

    # ...in case of a QtCore.QModelIndex item:
    server, job, root = index.data(common.ParentPathRole)[0:3]


"""
import os

from PySide2 import QtGui, QtCore

from . import delegate
from . import models
from . import views
from .. import actions
from .. import common
from .. import contextmenu
from ..threads import threads

#: Default item flags used by the item model.
DEFAULT_ITEM_FLAGS = models.DEFAULT_ITEM_FLAGS | QtCore.Qt.ItemIsDropEnabled


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
        self.extra_menu()
        self.bookmark_editor_menu()
        self.separator()
        self.launcher_menu()
        self.separator()
        self.sg_link_bookmark_menu()
        self.sg_url_menu()
        self.separator()
        self.bookmark_url_menu()
        self.asset_url_menu()
        self.reveal_item_menu()
        self.copy_menu()
        self.separator()
        self.add_asset_to_bookmark_menu()
        self.edit_selected_bookmark_menu()
        self.bookmark_clipboard_menu()
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


class BookmarkItemModel(models.ItemModel):
    """The model used store the data necessary to display bookmark item.

    """
    queues = (threads.BookmarkInfo, threads.BookmarkThumbnail)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        common.signals.bookmarkAdded.connect(
            lambda _: self.reset_data(force=True, emit_active=False))
        common.signals.bookmarkRemoved.connect(
            lambda _: self.reset_data(force=True, emit_active=False))

    @common.status_bar_message('Loading Bookmarks...')
    @models.initdata
    @common.error
    @common.debug
    def init_data(self):
        """Collects the data needed to populate the bookmark item model.

        """
        p = self.source_path()
        _k = self.task()
        t = self.data_type()

        if not p or not all(p) or not _k or t is None:
            return

        data = common.get_data(p, _k, t)

        for k, v in self.item_generator():
            common.check_type(v, dict)

            if not all(v.values()):
                continue
            if not len(v.values()) >= 3:
                continue

            server = v['server']
            job = v['job']
            root = v['root']

            file_info = QtCore.QFileInfo(k)
            exists = file_info.exists()

            # We'll mark the item archived if the saved bookmark does not refer
            # to an existing file
            if exists:
                flags = DEFAULT_ITEM_FLAGS
            else:
                flags = DEFAULT_ITEM_FLAGS | common.MarkedAsArchived

            if k in common.default_bookmarks:
                flags = flags | common.MarkedAsDefault

            filepath = file_info.filePath()

            # Item flags. Active and favourite flags will be only set if the
            # bookmark exist
            if all((
                    server == common.active('server'),
                    job == common.active('job'),
                    root == common.active('root')
            )) and exists:
                flags = flags | common.MarkedAsActive

            if filepath in common.favourites and exists:
                flags = flags | common.MarkedAsFavourite

            parent_path_role = (server, job, root)

            idx = len(data)
            if idx >= common.max_list_items:
                break  # Let's limit the maximum number of items we load

            # Find the entry
            for entry in os.scandir(file_info.dir().path()):
                if entry.name == file_info.baseName():
                    break

            sort_by_name_role = models.DEFAULT_SORT_BY_NAME_ROLE.copy()
            for i, n in enumerate(parent_path_role):
                if i >= 8:
                    break
                sort_by_name_role[i] = n.lower()

            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: root,
                QtCore.Qt.EditRole: root,
                common.PathRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.row_size,
                #
                common.QueueRole: self.queues,
                common.DataTypeRole: t,
                common.ItemTabRole: common.BookmarkTab,
                #
                common.FlagsRole: flags,
                common.ParentPathRole: parent_path_role,
                common.DescriptionRole: '',
                common.TodoCountRole: 0,
                common.AssetCountRole: 0,
                common.FileDetailsRole: None,
                common.SequenceRole: None,
                common.EntryRole: [entry, ],
                common.FileInfoLoaded: False,
                common.StartPathRole: None,
                common.EndPathRole: None,
                #
                common.ThumbnailLoaded: False,
                #
                common.TypeRole: common.FileItem,
                #
                common.SortByNameRole: sort_by_name_role,
                common.SortByLastModifiedRole: file_info.lastModified().toMSecsSinceEpoch(),
                common.SortBySizeRole: file_info.size(),
                common.SortByTypeRole: sort_by_name_role,
                #
                common.IdRole: idx,
                #
                common.ShotgunLinkedRole: False,
                common.SlackLinkedRole: False
            })

            if not exists:
                continue

        self.activeChanged.emit(self.active_index())

    def item_generator(self):
        """Returns the items to be processed by :meth:`init_data`.

        """
        for item in common.bookmarks.items():
            yield item

    def save_active(self):
        """Save the active bookmark item.

        """
        index = self.active_index()

        if not index.isValid():
            return
        if not index.data(common.PathRole):
            return
        if not index.data(common.ParentPathRole):
            return

        server, job, root = index.data(common.ParentPathRole)
        actions.set_active('server', server)
        actions.set_active('job', job)
        actions.set_active('root', root)

    def source_path(self):
        """The bookmark list's source paths.

        There's no file source for bookmark items, so we're returning some arbitrary
        names.

        """
        return 'bookmarks',

    def data_type(self):
        """The data type of the model.

        """
        return common.FileItem

    def default_row_size(self):
        """Returns the default item size.

        """
        return QtCore.QSize(1, common.size(common.size_bookmark_row_height))

    def filter_setting_dict_key(self):
        """The custom dictionary key used to save filter settings to the user settings
        file.

        """
        return 'bookmarks'


class BookmarkItemView(views.ThreadedItemView):
    """The view used to display bookmark item.

    See :class:`BookmarkItemModel`.

    """
    SourceModel = BookmarkItemModel
    Delegate = delegate.BookmarkItemViewDelegate
    ContextMenu = BookmarkItemViewContextMenu

    queues = (threads.BookmarkInfo, threads.BookmarkThumbnail)

    def __init__(self, parent=None):
        super().__init__(
            icon='bookmark',
            parent=parent
        )

    def add_item_action(self, index):
        """Action to execute when the add item icon is clicked."""
        server, job, root = index.data(common.ParentPathRole)[0:3]
        actions.show_add_asset(server=server, job=job, root=root)

    def edit_item_action(self, index):
        """Action to execute when the edit item icon is clicked."""
        server, job, root = index.data(common.ParentPathRole)[0:3]
        actions.edit_bookmark(server=server, job=job, root=root)

    def inline_icons_count(self):
        """Inline buttons count.

        """
        if self.buttons_hidden():
            return 0
        return 6

    def get_hint_string(self):
        """Returns an informative hint text.

        """
        return 'Right-click and select \'Manage Bookmark Items\' to add items'
