# -*- coding: utf-8 -*-
"""The widget, model and context menu needed for listing bookmarks stored
in `local_settings`.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from .. import common
from ..threads import threads
from .. import contextmenu

from .. import actions

from . import basemodel
from . import basewidget
from . import delegate


DEFAULT_ITEM_FLAGS = base.DEFAULT_ITEM_FLAGS | QtCore.Qt.ItemIsDropEnabled


class BookmarksWidgetContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with the BookmarksWidget.

    Methods:
        refresh: Refreshes the collector and repopulates the widget.

    """

    @common.debug
    @common.error
    def setup(self):
        self.title()

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


class BookmarksModel(base.BaseModel):
    """The model used store the data necessary to display bookmarks.

    """
    queues = (threads.BookmarkInfo, threads.BookmarkThumbnail)

    def __init__(self, parent=None):
        super(BookmarksModel, self).__init__(parent=parent)
        common.signals.bookmarkAdded.connect(
            lambda: self.blockSignals(True))
        common.signals.bookmarkAdded.connect(self.__resetdata__)
        common.signals.bookmarkAdded.connect(
            lambda: self.blockSignals(False))
        common.signals.bookmarkAdded.connect(self.beginResetModel)
        common.signals.bookmarkAdded.connect(self.endResetModel)

        common.signals.bookmarkRemoved.connect(
            lambda: self.blockSignals(True))
        common.signals.bookmarkRemoved.connect(self.__resetdata__)
        common.signals.bookmarkRemoved.connect(
            lambda: self.blockSignals(False))
        common.signals.bookmarkRemoved.connect(self.beginResetModel)
        common.signals.bookmarkRemoved.connect(self.endResetModel)

    @common.status_bar_message('Loading Bookmarks...')
    @base.initdata
    @common.error
    @common.debug
    def __initdata__(self):
        """Collects the data needed to populate the bookmarks model.

        """
        p = self.parent_path()
        _k = self.task()
        t = self.data_type()
        data = common.get_data(p, _k, t)

        for k, v in self.item_generator():
            if not all(v.values()):
                continue
            if not len(v.values()) >= 3:
                raise ValueError('Invalid bookmark value.')

            server = v[common.ServerKey]
            job = v[common.JobKey]
            root = v[common.RootKey]

            file_info = QtCore.QFileInfo(k)
            exists = file_info.exists()

            # We'll mark the item archived if the saved bookmark does not refer
            # to an existing file
            if exists:
                flags = DEFAULT_ITEM_FLAGS
            else:
                flags = DEFAULT_ITEM_FLAGS | common.MarkedAsArchived

            if k in common.static_bookmarks:
                flags = flags | common.MarkedAsPersistent

            filepath = file_info.filePath()

            # Item flags. Active and favourite flags will be only set if the
            # bookmark exist
            if all((
                server == common.active(common.ServerKey),
                job == common.active(common.JobKey),
                root == common.active(common.RootKey)
            )) and exists:
                flags = flags | common.MarkedAsActive

            if filepath in common.favourites and exists:
                flags = flags | common.MarkedAsFavourite

            text = '{}  |  {}'.format(
                job,
                root
            )

            idx = len(data)
            if idx >= common.max_list_items:
                break  # Let's limit the maximum number of items we load

            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: text,
                QtCore.Qt.EditRole: text,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.row_size(),
                #
                common.QueueRole: self.queues,
                common.DataTypeRole: t,
                #
                common.EntryRole: [],
                common.FlagsRole: flags,
                common.ParentPathRole: (server, job, root),
                common.DescriptionRole: '',
                common.TodoCountRole: 0,
                common.AssetCountRole: 0,
                common.FileDetailsRole: None,
                common.SequenceRole: None,
                common.EntryRole: [],
                common.FileInfoLoaded: False,
                common.StartpathRole: None,
                common.EndpathRole: None,
                #
                common.ThumbnailLoaded: False,
                #
                common.TypeRole: common.FileItem,
                #
                common.SortByNameRole: text.lower(),
                common.SortByLastModifiedRole: file_info.lastModified().toMSecsSinceEpoch(),
                common.SortBySizeRole: file_info.size(),
                common.SortByTypeRole: text,
                #
                common.IdRole: idx,
                #
                common.ShotgunLinkedRole: False,
            })

            if not exists:
                continue

        self.activeChanged.emit(self.active_index())

    def item_generator(self):
        for item in common.bookmarks.items():
            yield item

    def save_active(self):
        index = self.active_index()

        if not index.isValid():
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            return
        if not index.data(common.ParentPathRole):
            return

        server, job, root = index.data(common.ParentPathRole)
        actions.set_active(common.ServerKey, server)
        actions.set_active(common.JobKey, job)
        actions.set_active(common.RootKey, root)

    def parent_path(self):
        return ('bookmarks',)

    def data_type(self):
        return common.FileItem

    def default_row_size(self):
        return QtCore.QSize(1, common.size(common.HeightBookmark))

    def local_settings_key(self):
        return common.BookmarksKey


class BookmarksWidget(base.ThreadedBaseWidget):
    """The view used to display the contents of a ``BookmarksModel`` instance."""
    SourceModel = BookmarksModel
    Delegate = delegate.BookmarksWidgetDelegate
    ContextMenu = BookmarksWidgetContextMenu

    queues = (threads.BookmarkInfo, threads.BookmarkThumbnail)

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(
            icon='bookmark',
            parent=parent
        )

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return

        super(BookmarksWidget, self).mouseReleaseEvent(event)

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)

        if not index.isValid():
            return
        if not index.data(common.ParentPathRole):
            return

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(
            rect, self.inline_icons_count())

        server, job, root = index.data(common.ParentPathRole)[0:3]
        if rectangles[delegate.AddAssetRect].contains(cursor_position):
            actions.show_add_asset(server=server, job=job, root=root)
            return

        if rectangles[delegate.PropertiesRect].contains(cursor_position):
            actions.edit_bookmark(server=server, job=job, root=root)
            return

    def inline_icons_count(self):
        """The number of row-icons an item has."""
        if self.buttons_hidden():
            return 0
        return 6

    def get_hint_string(self):
        return 'No items. Select right-click - Edit Bookmarks to add new bookmarks.'
