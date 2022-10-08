"""Asset items in their simplest sense are file paths made up of ``server``, ``job``, ``root``
and ``asset`` components.

.. code-block:: python

    server, job, root, asset = common.active('asset', args=True)
    asset = f'{server}/{job}/{root}/{asset}'

Bookmarks considers any folder in the root of a bookmark item to be an asset. Note that
we don't have any notion of asset types (like how some pipelines make a distinction
between shots and assets), nor do we understand nested assets by default (like a
``SEQ010/SH010 `` structure).

Asset data is queried by :class:`AssetItemModel`, and displayed by
:class:`AssetItemView`. Any custom logic of how assets are queried should be
implemented in :meth:`AssetItemModel.item_generator`.

Asset items have their own bespoke list of attributes, stored in the bookmark item's
database. See :mod:`bookmarks.database` for more details.

"""
import functools
import os

from PySide2 import QtCore, QtWidgets, QtGui

from . import delegate
from . import models
from . import views
from .. import actions
from .. import common
from .. import contextmenu
from .. import database
from .. import log
from ..threads import threads


def get_display_name(s):
    """Manipulate the given file name to a display friendly name.

    Args:
        s (str): Source asset item file name.

    Returns:
        str: A modified asset item display name.

    """
    return s


class AssetItemViewContextMenu(contextmenu.BaseContextMenu):
    """The context menu associated with :class:`AssetItemView`."""

    @common.debug
    @common.error
    def setup(self):
        """Creates the context menu.

        """
        self.extra_menu()
        self.separator()
        self.show_add_asset_menu()
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


class AssetItemModel(models.ItemModel):
    """The model containing all item information needed to represent assets.
    Used in conjunction with :class:`.AssetItemView`.

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
    @models.initdata
    @common.error
    @common.debug
    def init_data(self):
        """Collects the data needed to populate the asset item model.

        """
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

        for entry in self.item_generator(source):
            if self._interrupt_requested:
                break

            filepath = entry.path.replace('\\', '/')

            if asset_identifier:
                identifier = f'{filepath}/{asset_identifier}'
                if not os.path.isfile(identifier):
                    continue

            # Progress bar
            c += 9
            if not c % nth:
                common.signals.showStatusBarMessage.emit(
                    f'Loading assets ({c} found)...')
                QtWidgets.QApplication.instance().processEvents()

            filename = filepath[len(source) + 1:]
            flags = models.DEFAULT_ITEM_FLAGS

            if filepath in common.favourites:
                flags = flags | common.MarkedAsFavourite

            # Is the item currently active?
            active = common.active('asset')
            if active and active == filename:
                flags = flags | common.MarkedAsActive

            # Beautify the name
            name = get_display_name(filename)
            parent_path_role = p + (filename,)

            sort_by_name_role = models.DEFAULT_SORT_BY_NAME_ROLE.copy()
            for i, n in enumerate(p):
                if i >= 8:
                    break
                sort_by_name_role[i] = n.lower()
            sort_by_name_role[3] = filename.lower()


            idx = len(data)
            if idx >= common.max_list_items:
                break  # Let's limit the maximum number of items we load

            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: name,
                QtCore.Qt.EditRole: filename,
                common.PathRole: filepath,
                QtCore.Qt.SizeHintRole: self.row_size,
                #
                QtCore.Qt.StatusTipRole: filename,
                QtCore.Qt.AccessibleDescriptionRole: filename,
                QtCore.Qt.WhatsThisRole: filename,
                QtCore.Qt.ToolTipRole: filename,
                #
                common.QueueRole: self.queues,
                common.DataTypeRole: t,
                common.ItemTabRole: common.AssetTab,
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: parent_path_role,
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
            common.active('server'),
            common.active('job'),
            common.active('root'),
        )

    def item_generator(self, path):
        """Yields the asset items to be processed by :meth:`init_data`.

        Yields:
            DirEntry: Entry instances of valid asset folders.

        """
        try:
            it = os.scandir(path)
        except OSError as e:
            log.error(e)
            return
            yield

        for entry in it:
            if entry.name.startswith('.'):
                continue
            if not entry.is_dir():
                continue
            yield entry

        # Studio Aka Pipe entries
        from ..studioaka import base
        for entry in base.item_generator(path):
            yield entry

    def save_active(self):
        """Saves the active item.

        """
        index = self.active_index()

        if not index.isValid():
            return
        if not index.data(common.PathRole):
            return
        if not index.data(common.ParentPathRole):
            return

        actions.set_active(
            'asset',
            index.data(common.ParentPathRole)[-1]
        )

    def data_type(self):
        """Model data type.

        """
        return common.FileItem

    def filter_setting_dict_key(self):
        """The custom dictionary key used to save filter settings to the user settings
        file.

        """
        v = [common.active(k) for k in ('server', 'job', 'root')]
        if not all(v):
            return None
        return '/'.join(v)

    def default_row_size(self):
        """Returns the default item size.

        """
        return QtCore.QSize(1, common.size(common.size_asset_row_height))


class AssetItemView(views.ThreadedItemView):
    """The view used to display :class:`.AssetItemModel` item.

    """
    SourceModel = AssetItemModel
    Delegate = delegate.AssetItemViewDelegate
    ContextMenu = AssetItemViewContextMenu

    queues = (threads.AssetInfo, threads.AssetThumbnail)

    def __init__(self, parent=None):
        super().__init__(
            icon='asset',
            parent=parent
        )
        common.signals.assetAdded.connect(
            functools.partial(
                self.show_item,
                role=common.PathRole,
            )
        )
        common.signals.assetAdded.connect(self.start_delayed_queue_timer)
        common.signals.sgAssetsLinked.connect(self.start_delayed_queue_timer)

    def inline_icons_count(self):
        """Inline buttons count.

        """
        if self.width() < common.size(common.size_width) * 0.5:
            return 0
        if self.buttons_hidden():
            return 0
        return 6

    def get_hint_string(self):
        """Returns an informative hint text.

        """
        return 'Right-click and select \'Add Asset\' to add items'

    def mouseReleaseEvent(self, event):
        """Mouse release event handler.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return

        super().mouseReleaseEvent(event)

        cursor_position = self.mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)

        if not index.isValid():
            return
        if index.flags() & common.MarkedAsArchived:
            return

        rectangles = self.itemDelegate().get_rectangles(index)
        archived = index.data(common.FlagsRole) & common.MarkedAsArchived
        if rectangles[delegate.AddAssetRect].contains(cursor_position) and not archived:
            actions.show_add_file(asset=index.data(common.ParentPathRole)[-1])
            return

        if rectangles[delegate.PropertiesRect].contains(cursor_position) and not archived:
            actions.edit_asset(index.data(common.ParentPathRole)[-1])
            return

    def showEvent(self, event):
        """Show event handler.

        """
        source_index = self.model().sourceModel().active_index()
        if source_index.isValid():
            index = self.model().mapFromSource(source_index)
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.ClearAndSelect)
        return super().showEvent(event)
