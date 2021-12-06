# -*- coding: utf-8 -*-
"""The view and model used to display asset items.

"""
import functools
import os
import re

from PySide2 import QtCore, QtWidgets, QtGui

from . import basemodel
from . import basewidget
from . import delegate
from .. import actions
from .. import common
from .. import contextmenu
from .. import database
from .. import log
from ..threads import threads


def get_display_name(file_name):
    """Transform a source file name to a display name.

    Args:
        file_name (str): Source file name.

    Returns:
        str: Display name.

    """
    return re.sub(r'[_]+', ' ', file_name).strip('_').strip('')


class AssetsWidgetContextMenu(contextmenu.BaseContextMenu):
    """The context menu associated with :class:`AssetsWidget`."""

    @common.debug
    @common.error
    def setup(self):
        self.title()

        self.show_addasset_menu()
        self.add_file_to_asset_menu()

        self.separator()

        self.launcher_menu()

        self.separator()

        self.sg_link_assets_menu()
        self.sg_link_asset_menu()
        self.sg_url_menu()
        self.import_json_menu()

        self.separator()

        self.bookmark_url_menu()
        self.asset_url_menu()
        self.reveal_item_menu()
        self.copy_menu()

        self.separator()

        self.edit_active_bookmark_menu()
        self.edit_selected_asset_menu()
        self.asset_clipboard_menu()
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


class AssetsModel(basemodel.BaseModel):
    """The model containing all item information needed to represent assets.
    Used in conjunction with :class:`.AssetsWidget`.

    """
    queues = (threads.AssetInfo, threads.AssetThumbnail)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        common.signals.sgAssetsLinked.connect(
            lambda: self.blockSignals(True))
        common.signals.sgAssetsLinked.connect(self.reset_data)
        common.signals.sgAssetsLinked.connect(
            lambda: self.blockSignals(False))
        common.signals.sgAssetsLinked.connect(self.sort_data)

    @common.status_bar_message('Loading assets...')
    @basemodel.initdata
    def init_data(self):
        """Collects the data needed to populate the asset model.

        """
        common.settings.load_active_values()

        p = self.source_path()
        k = self.task()
        t = self.data_type()

        if not p or not all(p) or not k or t is None:
            return

        data = common.get_data(p, k, t)
        source = '/'.join(p)

        # Let's get the identifier from the bookmark database
        db = database.get_db(*p)
        asset_identifier = db.value(
            source,
            'identifier',
            database.BookmarkTable
        )

        nth = 1
        c = 0

        for entry in self.item_iterator(source):
            if self._interrupt_requested:
                break

            filepath = entry.path.replace('\\', '/')

            if asset_identifier:
                identifier = filepath + '/' + asset_identifier
                if not os.path.isfile(identifier):
                    continue

            # Progress bar
            c += 9
            if not c % nth:
                common.signals.showStatusBarMessage.emit(
                    f'Loading assets ({c} found)...')
                QtWidgets.QApplication.instance().processEvents()

            filename = entry.name
            flags = basemodel.DEFAULT_ITEM_FLAGS

            if filepath in common.favourites:
                flags = flags | common.MarkedAsFavourite

            # Is the item currently active?
            active = common.active(common.AssetKey)
            if active and active == filename:
                flags = flags | common.MarkedAsActive

            # Beautify the name
            name = get_display_name(filename)

            sort_by_name_role = [0, ] * 8
            for i, n in enumerate(name.split(u'/')):
                if i >= 8:
                    break
                sort_by_name_role[i] = n.lower()

            idx = len(data)
            if idx >= common.max_list_items:
                break  # Let's limit the maximum number of items we load

            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: name,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.row_size(),
                #
                common.QueueRole: self.queues,
                common.DataTypeRole: t,
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: p + (filename,),
                common.DescriptionRole: '',
                common.TodoCountRole: 0,
                common.FileDetailsRole: '',
                common.SequenceRole: None,
                common.FramesRole: [],
                common.StartPathRole: None,
                common.EndPathRole: None,
                #
                common.FileInfoLoaded: False,
                common.ThumbnailLoaded: False,
                #
                common.TypeRole: common.FileItem,
                #
                common.SortByNameRole: sort_by_name_role,
                common.SortByLastModifiedRole: 0,
                common.SortBySizeRole: 0,
                common.SortByTypeRole: name,
                #
                common.IdRole: idx,
                #
                common.ShotgunLinkedRole: False,
            })

        # Explicitly emit `activeChanged` to notify other dependent models
        self.activeChanged.emit(self.active_index())

    def source_path(self):
        """The model's parent folder path.

        Returns:
            tuple: A tuple of path segments.

        """
        return (
            common.active(common.ServerKey),
            common.active(common.JobKey),
            common.active(common.RootKey),
        )

    def item_iterator(self, path):
        """Yields DirEntry instances to be processed in init_data.

        """
        try:
            it = os.scandir(path)
        except OSError as e:
            log.error(e)
            return

        for entry in it:
            if entry.name.startswith('.'):
                continue
            if not entry.is_dir():
                continue
            yield entry

    def save_active(self):
        index = self.active_index()

        if not index.isValid():
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            return
        if not index.data(common.ParentPathRole):
            return

        actions.set_active(
            common.AssetKey,
            index.data(common.ParentPathRole)[-1]
        )

    def data_type(self):
        return common.FileItem

    def user_settings_key(self):
        v = [common.active(k) for k in (common.JobKey, common.RootKey)]
        if not all(v):
            return None
        return '/'.join(v)

    def default_row_size(self):
        return QtCore.QSize(1, common.size(common.HeightAsset))


class AssetsWidget(basewidget.ThreadedBaseWidget):
    """A thread-supported view used to display the contents of :class:`.AssetsModel`."""
    SourceModel = AssetsModel
    Delegate = delegate.AssetsWidgetDelegate
    ContextMenu = AssetsWidgetContextMenu

    queues = (threads.AssetInfo, threads.AssetThumbnail)

    def __init__(self, parent=None):
        super().__init__(
            icon='asset',
            parent=parent
        )
        common.signals.assetAdded.connect(
            functools.partial(
                self.show_item,
                role=QtCore.Qt.StatusTipRole,
            )
        )
        common.signals.assetAdded.connect(self.queue_visible_indexes)
        common.signals.sgAssetsLinked.connect(self.queue_visible_indexes)

    def inline_icons_count(self):
        """The number of icons on the right - hand side."""
        if self.width() < common.size(common.DefaultWidth) * 0.5:
            return 0
        if self.buttons_hidden():
            return 0
        return 6

    def get_hint_string(self):
        return 'No items. Select right-click - Add Asset to add a new asset.'

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return

        super().mouseReleaseEvent(event)

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)

        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        rect = self.visualRect(index)
        rectangles = delegate.get_rectangles(rect, self.inline_icons_count())

        if rectangles[delegate.AddAssetRect].contains(cursor_position):
            actions.show_add_file(asset=index.data(common.ParentPathRole)[-1])
            return

        if rectangles[delegate.PropertiesRect].contains(cursor_position):
            actions.edit_asset(index.data(common.ParentPathRole)[-1])
            return

    def showEvent(self, event):
        source_index = self.model().sourceModel().active_index()
        if source_index.isValid():
            index = self.model().mapFromSource(source_index)
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
        return super().showEvent(event)
