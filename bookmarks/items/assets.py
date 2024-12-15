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
from .. import common
from .. import contextmenu
from .. import database
from .. import log
from .. import progress
from .. import tokens
from ..links.lib import LinksAPI
from ..threads import threads


@common.error
@common.debug
def asset_item_generator(path, interrupt_requested=False):
    """
    Generates asset items from a specified directory.

    This generator function scans a given directory for asset folders,
    checks their validity, and yields the paths of valid asset items.
    It can be interrupted by setting the `interrupt_requested` flag to True.
    Additionally, it scans for link files within each asset folder and yields
    their paths if they exist.

    Args:
        path (str): The path to the directory containing asset folders.
        interrupt_requested (bool): If True, the generator stops yielding items.

    Yields:
        tuple: A tuple containing the absolute path of the asset item and the links file,
               or None if no links are found.
    """
    path = os.path.abspath(os.path.normpath(path)).replace('\\', '/')

    try:
        with os.scandir(path) as it:
            for entry in it:
                if interrupt_requested:
                    return

                if entry.name.startswith('.') or not entry.is_dir(follow_symlinks=False):
                    continue

                if not os.access(entry.path, os.R_OK):
                    continue

                asset_root = os.path.abspath(os.path.normpath(entry.path)).replace('\\', '/')

                try:
                    common_path = os.path.commonpath([path, asset_root])
                except ValueError:
                    log.error(__name__,
                              f'Asset {asset_root} is on a different drive than the source path {path}. Skipping.')
                    common_path = None

                if common_path != path:
                    log.error(__name__,
                        f'Asset {asset_root} is outside the source path {path}. Please verify if this is intentional')

                api = LinksAPI(asset_root)
                links = api.get(force=True)

                if links:
                    for rel_path in links:
                        abs_path = os.path.abspath(os.path.normpath(f'{asset_root}/{rel_path}')).replace('\\', '/')
                        if os.path.exists(abs_path):
                            yield abs_path, api.links_file
                else:
                    yield asset_root, None
    except OSError as e:
        log.error(__name__, e)
        return


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

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4 + len(progress.STAGES)

    def headerData(self, column, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Vertical:
            return super().headerData(column, orientation, role=role)

        if orientation == QtCore.Qt.Horizontal and column >= 4:
            if role == QtCore.Qt.DisplayRole:
                return progress.STAGES[column - 4]['name']

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        # The first four columns are the default columns
        if index.column() < 4:
            return super().data(index, role=role)

        # The rest of the columns are the progress tracker columns
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            p = self.parent_path()
            k = self.task()
            t = common.FileItem
            data = common.get_data(p, k, t)
            v = data[index.row()][common.AssetProgressRole]
            if not v:
                return None
            return v[index.column() - 4]['value']

    def flags(self, index):
        """Overrides the flag behavior to turn off drag when the alt modifier isn't pressed.

        """
        # The first four columns are the default columns
        if index.column() < 4:
            flags = super().flags(index)
        # The rest of the columns are the progress tracker columns
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
        """Collects the data needed to populate the asset item model."""
        p = self.parent_path()
        k = self.task()
        t = self.data_type()

        if not p or not all(p) or not k or t is None:
            return

        # Convert the source to the absolute and normalized path
        source = os.path.abspath(os.path.normpath('/'.join(p))).replace('\\', '/')

        data = common.get_data(p, k, t)

        # Cache commonly used values upfront
        db = database.get(*p)
        display_token = db.value(source, 'asset_display_token', database.BookmarkTable)
        prefix = db.value(source, 'prefix', database.BookmarkTable)

        nth = 27
        c = 0

        # Cache active asset and favorites for faster lookup
        active = common.active('asset')
        favourites = common.favourites

        for filepath, links_file in asset_item_generator(source, self._interrupt_requested):
            if self._interrupt_requested:
                break

            c += 1
            if c % nth == 0:
                common.signals.showStatusBarMessage.emit(f'Loading assets ({c} found)...')
                QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

            # Convert the path to the absolute and normalized path
            filepath = os.path.abspath(os.path.normpath(filepath)).replace('\\', '/')

            # Check if the path is within the source
            try:
                common_path = os.path.commonpath([source, filepath])
            except ValueError:
                common_path = None

            if common_path != source:
                log.error(__name__,
                    f'Asset {filepath} is outside the source path {source}. Please verify if this is intentional.')

            # Compute the relative path
            relative_path = os.path.relpath(filepath, source).replace('\\', '/')
            # Ensure relative_path does not contain '../' or './'
            if '..' in relative_path or relative_path.startswith('.'):
                # Use the base name of the path
                filename = os.path.basename(filepath)
            else:
                filename = relative_path

            # Remove any leading './' from filename
            if filename.startswith('./'):
                filename = filename[2:]

            # Set flags efficiently
            flags = models.DEFAULT_ITEM_FLAGS
            if filepath in favourites:
                flags |= common.MarkedAsFavourite
            if active == filename:
                flags |= common.MarkedAsActive

            # Prepare display name based on bookmark token, only if valid
            display_name = filename
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

            # Optimize role setup by pre-caching and limiting length
            parent_path_role = tuple(p + (filename,))
            sort_by_name_role = models.DEFAULT_SORT_BY_NAME_ROLE.copy()
            for idx, segment in enumerate(re.split(r'[\\/|]', filename)):
                if idx >= len(sort_by_name_role):
                    break
                sort_by_name_role[idx] = segment.lower().strip().strip('.').strip('_').strip('/')

            # Limit the number of items loaded for performance
            idx = len(data)
            if idx >= common.max_list_items:
                break

            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: display_name,
                common.FilterTextRole: display_name,
                QtCore.Qt.EditRole: filename,
                common.PathRole: filepath,
                QtCore.Qt.SizeHintRole: self.row_size,
                common.AssetLinkRole: links_file,
                QtCore.Qt.StatusTipRole: filename,
                QtCore.Qt.AccessibleDescriptionRole: filename,
                QtCore.Qt.WhatsThisRole: filename,
                QtCore.Qt.ToolTipRole: filename,
                common.QueueRole: self.queues,
                common.DataTypeRole: t,
                common.DataDictRole: weakref.ref(data),
                common.ItemTabRole: common.AssetTab,
                common.EntryRole: [],
                common.FlagsRole: flags,
                common.ParentPathRole: parent_path_role,
                common.DescriptionRole: '',
                common.NoteCountRole: 0,
                common.AssetCountRole: 0,
                common.FileDetailsRole: '',
                common.SequenceRole: None,
                common.FramesRole: [],
                common.StartPathRole: None,
                common.EndPathRole: None,
                common.FileInfoLoaded: False,
                common.ThumbnailLoaded: False,
                common.SortByNameRole: sort_by_name_role,
                common.SortByLastModifiedRole: 0,
                common.SortBySizeRole: 0,
                common.SortByTypeRole: display_name,
                common.IdRole: idx,
                common.SGLinkedRole: False,
                common.AssetProgressRole: copy.deepcopy(progress.STAGES),
            })

        # Emit `activeChanged` once, only at the end for efficiency
        self.activeChanged.emit(self.active_index())

    def parent_path(self):
        """The model's parent folder path.

        Returns:
            tuple: A tuple of path segments.

        """
        return (
            common.active('server'),
            common.active('job'),
            common.active('root'),
        )

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
