# -*- coding: utf-8 -*-
"""The widget, model and context menu needed for listing bookmarks stored
in `local_settings`.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from .. import common
from ..threads import threads
from .. import contextmenu
from .. import settings
from .. import actions
from .. import datacache

from . import base
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

        self.set_generate_thumbnails_menu()
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
        common.signals.bookmarksChanged.connect(
            lambda: self.blockSignals(True))
        common.signals.bookmarksChanged.connect(self.__resetdata__)
        common.signals.bookmarksChanged.connect(
            lambda: self.blockSignals(False))
        common.signals.bookmarksChanged.connect(self.beginResetModel)
        common.signals.bookmarksChanged.connect(self.endResetModel)

    @common.status_bar_message(u'Loading Bookmarks...')
    @base.initdata
    @common.error
    @common.debug
    def __initdata__(self):
        """Collects the data needed to populate the bookmarks model.

        """

        p = self.parent_path()
        _k = self.task()
        t = self.data_type()
        data = datacache.get_data(p, _k, t)

        for k, v in self.item_generator():
            if not all(v.values()):
                continue
            if not len(v.values()) >= 3:
                raise ValueError(u'Invalid bookmark value.')

            server = v[settings.ServerKey]
            job = v[settings.JobKey]
            root = v[settings.RootKey]

            file_info = QtCore.QFileInfo(k)
            exists = file_info.exists()

            # We'll mark the item archived if the saved bookmark does not refer
            # to an existing file
            if exists:
                flags = DEFAULT_ITEM_FLAGS
            else:
                flags = DEFAULT_ITEM_FLAGS | common.MarkedAsArchived

            filepath = file_info.filePath()

            # Item flags. Active and favourite flags will be only set if the
            # bookmark exist
            if all((
                server == settings.active(settings.ServerKey),
                job == settings.active(settings.JobKey),
                root == settings.active(settings.RootKey)
            )) and exists:
                flags = flags | common.MarkedAsActive

            if filepath in common.FAVOURITES_SET and exists:
                flags = flags | common.MarkedAsFavourite

            text = u'{}  |  {}'.format(
                job,
                root
            )

            idx = len(data)
            if idx >= common.MAXITEMS:
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
                common.DescriptionRole: u'',
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
        for item in common.BOOKMARKS.iteritems():
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
        actions.set_active(settings.ServerKey, server)
        actions.set_active(settings.JobKey, job)
        actions.set_active(settings.RootKey, root)

    def parent_path(self):
        return (u'bookmarks',)

    def data_type(self):
        return common.FileItem

    def default_row_size(self):
        return QtCore.QSize(1, common.BOOKMARK_ROW_HEIGHT())

    def local_settings_key(self):
        return settings.BookmarksKey


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

        self.bookmarks_to_remove = []

        self.remove_bookmark_timer = common.Timer(parent=self)
        self.remove_bookmark_timer.setSingleShot(True)
        self.remove_bookmark_timer.setInterval(10)
        self.remove_bookmark_timer.timeout.connect(
            self.remove_queued_bookmarks)

    @QtCore.Slot()
    def remove_queued_bookmarks(self):
        """This slot is called by the `remove_bookmark_timer`'s timeout signal
        and is used to remove bookmark items from the list.

        We're using a timer mechanism, because otherwise a model refresh would
        be triggered a mouseReleaseEvent, causing an app crash.

        """
        if self.multi_toggle_pos:
            self.remove_bookmark_timer.start(
                self.remove_bookmark_timer.interval())
            return

        for bookmark in [f for f in self.bookmarks_to_remove]:
            actions.remove_bookmark(*bookmark)
            del self.bookmarks_to_remove[self.bookmarks_to_remove.index(
                bookmark)]

        self.model().sourceModel().blockSignals(True)
        self.model().sourceModel().__resetdata__()
        self.model().sourceModel().blockSignals(False)

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            return

        if index.flags() & common.MarkedAsArchived:
            super(BookmarksWidget, self).toggle_item_flag(
                index,
                common.MarkedAsArchived,
                state=False,
            )
            self.update(index)
            self.reset_multitoggle()
            return

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(
            rect, self.inline_icons_count())

        super(BookmarksWidget, self).mouseReleaseEvent(event)

        if not index.isValid():
            return
        if not index.data(common.ParentPathRole):
            return

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

    def toggle_item_flag(self, index, flag, state=None, commit_now=True):
        """Overrides the base behaviour because bookmark items cannot be archived.

        """
        if flag == common.MarkedAsArchived:
            if hasattr(index.model(), 'sourceModel'):
                index = self.model().mapToSource(index)

            # Set flags
            idx = index.row()
            data = index.model().model_data()
            data[idx][common.FlagsRole] = data[idx][common.FlagsRole] | common.MarkedAsArchived
            self.update(index)

            # Do nothing else for now, instead, queue the bookmark item for
            # later processing. The queued items will be removed when the user
            # releases the mouse button and finishes the multi-toggle
            # operation.
            self.bookmarks_to_remove.append(index.data(common.ParentPathRole))
            self.remove_bookmark_timer.start()
            return

        # Call the base behaviour for all other flags
        super(BookmarksWidget, self).toggle_item_flag(
            index, flag, state=state, commit_now=commit_now)

    def get_hint_string(self):
        return u'No bookmarks have been added yet. Select Right-Click - Add Bookmark... to add new items.'
