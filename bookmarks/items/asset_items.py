"""Asset items in their simplest sense are file paths made up of ``server``, ``job``, ``root``
and ``asset`` components.

.. code-block:: python
    :linenos:

    server, job, root, asset = common.active('asset', args=True)
    asset = f'{server}/{job}/{root}/{asset}'

The app considers folders found in the root of a bookmark item assets.
We don't have any notion of asset types (like how some pipelines make a distinction
between shots and assets), nor do we understand nested assets by default (like a
``SEQ010/SH010`` structure).

Asset data is queried by :class:`AssetItemModel`, and displayed by
:class:`AssetItemView`. Any custom logic of how assets are queried should be
implemented in :meth:`AssetItemModel.item_generator`.

Asset items have their own bespoke list of attributes, stored in the bookmark item's
database. See :mod:`bookmarks.database` for more details.

"""
import copy
import functools
import os
import re
import weakref

from PySide2 import QtCore, QtWidgets

from . import delegate
from . import models
from . import views
from .. import actions, tokens
from .. import common
from .. import contextmenu
from .. import database
from .. import log
from .. import progress
from ..links.lib import LinksAPI
from ..threads import threads


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


class AssetItemModel(models.ItemModel):
    """The model containing all item information needed to represent assets.
    Used in conjunction with :class:`.AssetItemView`.

    """
    queues = (threads.AssetInfo, threads.AssetThumbnail)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        common.signals.sgAssetsLinked.connect(
            lambda: self.blockSignals(True)
        )
        common.signals.sgAssetsLinked.connect(self.reset_data)
        common.signals.sgAssetsLinked.connect(
            lambda: self.blockSignals(False)
        )
        common.signals.sgAssetsLinked.connect(self.sort_data)

    def columnCount(self, index):
        return 1 + len(progress.STAGES)

    def headerData(self, column, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Vertical:
            return super().headerData(column, orientation, role=role)

        if orientation == QtCore.Qt.Horizontal and column > 0:
            if role == QtCore.Qt.DisplayRole:
                return progress.STAGES[column - 1]['name']

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        if index.column() == 0:
            return super().data(index, role=role)

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            p = self.source_path()
            k = self.task()
            t = common.FileItem
            data = common.get_data(p, k, t)
            v = data[index.row()][common.AssetProgressRole]
            if not v:
                return None
            return v[index.column() - 1]['value']

    def flags(self, index):
        """Overrides the flag behaviour to disable drag if the alt modifier is not pressed.

        """
        if index.column() == 0:
            flags = super().flags(index)
        else:
            flags = (
                    QtCore.Qt.ItemIsEnabled |
                    QtCore.Qt.ItemIsSelectable |
                    QtCore.Qt.ItemIsEditable
            )

        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        alt_modifier = modifiers & QtCore.Qt.AltModifier

        if not alt_modifier:
            flags &= ~QtCore.Qt.ItemIsDragEnabled
        return flags

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
        db = database.get(*p)

        # ...and the display token
        display_token = db.value(
            source,
            'asset_display_token',
            database.BookmarkTable
        )
        prefix = db.value(
            source,
            'prefix',
            database.BookmarkTable
        )

        nth = 17
        c = 0

        for filepath in self.item_generator(source):
            if self._interrupt_requested:
                break

            # Progress bar
            c += 1
            if not c % nth:
                common.signals.showStatusBarMessage.emit(
                    f'Loading assets ({c} found)...'
                )
                QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

            if '..' in filepath:
                _filepath = re.sub(r'\.\.[/]?', '', filepath).rstrip('/')
                dir_name = os.path.abspath(filepath).replace('\\', '/').split('/')[-1]
                filename = f'{_filepath[len(source) + 1:]}/{dir_name}'
            else:
                filename = filepath[len(source) + 1:]
            flags = models.DEFAULT_ITEM_FLAGS

            if filepath in common.favourites:
                flags = flags | common.MarkedAsFavourite

            # Is the item currently active?
            active = common.active('asset')
            if active and active == filename:
                flags = flags | common.MarkedAsActive

            display_name = filename

            # Set the display name based on the bookmark item's configuration value
            if display_token:
                seq, shot = common.get_sequence_and_shot(filepath)
                _display_name = common.parser.format(
                    display_token,
                    server=p[0],
                    job=p[1],
                    root=p[2],
                    asset=filename,
                    sq=seq,
                    seq=seq,
                    sequence=seq if seq else '',
                    sh=shot if shot else '',
                    shot=shot if shot else '',
                    prefix=prefix
                )
                if tokens.invalid_token not in _display_name:
                    display_name = _display_name

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

            data[idx] = common.DataDict(
                {
                    QtCore.Qt.DisplayRole: display_name,
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
                    common.DataDictRole: weakref.ref(data),
                    common.ItemTabRole: common.AssetTab,
                    #
                    common.EntryRole: [],
                    common.FlagsRole: flags,
                    common.ParentPathRole: parent_path_role,
                    common.DescriptionRole: '',
                    common.NoteCountRole: 0,
                    common.FileDetailsRole: '',
                    common.SequenceRole: None,
                    common.FramesRole: [],
                    common.StartPathRole: None,
                    common.EndPathRole: None,
                    #
                    common.FileInfoLoaded: False,
                    common.ThumbnailLoaded: False,
                    #
                    common.SortByNameRole: sort_by_name_role,
                    common.SortByLastModifiedRole: 0,
                    common.SortBySizeRole: 0,
                    common.SortByTypeRole: display_name,
                    #
                    common.IdRole: idx,
                    #
                    common.SGLinkedRole: False,
                    #
                    common.AssetProgressRole: copy.deepcopy(progress.STAGES),
                }
            )

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

        Args:
            path (string): The path to a directory containing asset folders.

        Yields:
            DirEntry: Entry instances of valid asset folders.

        """
        try:
            it = os.scandir(path)
        except OSError as e:
            log.error(e)
            return

        # Iterate over the directories in the root item folder
        for entry in it:
            if self._interrupt_requested:
                return

            if entry.name.startswith('.'):
                continue
            if not entry.is_dir():
                continue
            if not os.access(entry.path, os.R_OK):
                continue

            asset_root = f'{path}/{entry.name}'.replace('\\', '/')

            # Check if the root item has links
            api = LinksAPI(asset_root)
            links = api.get(force=True)

            for rel_path in links:
                abs_path = f'{asset_root}/{rel_path}'.replace('\\', '/')
                if not os.path.exists(abs_path):
                    continue
                yield abs_path

            # If no links were found, yield the root item
            if not links:
                yield entry.path.replace('\\', '/')

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

        common.set_active(
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
        return QtCore.QSize(1, common.Size.RowHeight())


class AssetItemView(views.ThreadedItemView):
    """The view used to display :class:`.AssetItemModel` item.

    """
    Delegate = delegate.AssetItemViewDelegate
    ContextMenu = AssetItemViewContextMenu

    queues = (threads.AssetInfo, threads.AssetThumbnail)

    def __init__(self, parent=None):
        super().__init__(
            icon='asset',
            parent=parent
        )

        self._progress_hidden = False

        common.signals.assetAdded.connect(
            functools.partial(
                self.show_item,
                role=common.PathRole,
            )
        )
        common.signals.assetAdded.connect(self.start_delayed_queue_timer)
        common.signals.sgAssetsLinked.connect(self.start_delayed_queue_timer)

    def get_source_model(self):
        return AssetItemModel(parent=self)

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
            if idx == 0:
                self.horizontalHeader().setSectionResizeMode(
                    idx, QtWidgets.QHeaderView.Stretch
                )
            else:
                self.horizontalHeader().setSectionResizeMode(
                    idx, QtWidgets.QHeaderView.Fixed
                )
                self.setItemDelegateForColumn(idx, progress.ProgressDelegate(parent=self))

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
            if n == 0:
                continue
            self.horizontalHeader().setSectionHidden(n, hidden)
        self.horizontalHeader().resizeSections()

    def inline_icons_count(self):
        """Inline buttons count.

        """
        if self.columnWidth(0) < common.Size.DefaultWidth(0.66):
            return 0
        if self.buttons_hidden():
            return 0
        return 6

    def get_hint_string(self):
        """Returns an informative hint text.

        """
        return 'Right-click and select \'Add Asset\' to add items'

    def add_item_action(self, index):
        """Action to execute when the add item icon is clicked."""
        self.activate(index)

        from .. import tokens
        d = tokens.get_folder(tokens.SceneFolder)
        if QtCore.QFileInfo(f'{common.active("asset", path=True)}/{d}').exists():
            common.signals.taskFolderChanged.emit(d)
        actions.show_add_file()

    def edit_item_action(self, index):
        """Action to execute when the edit item icon is clicked."""
        actions.edit_asset(index.data(common.ParentPathRole)[-1])

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
        cursor_position = self.viewport().mapFromGlobal(common.cursor.pos())
        index = self.indexAt(cursor_position)
        if not index.isValid():
            return super().mouseReleaseEvent(event)

        if index.column() == 0:
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
