import functools
import os
import weakref

from PySide2 import QtWidgets, QtCore

from . import base
from ... import common, log, tokens
from ...threads import threads


def _add_path_to_mime(mime, path):
    """Utility function adds a path to the mime data.

    """
    path = QtCore.QFileInfo(path).absoluteFilePath()
    mime.setUrls(mime.urls() + [QtCore.QUrl.fromLocalFile(path), ])

    path = QtCore.QDir.toNativeSeparators(path)
    _bytes = QtCore.QByteArray(path.encode('utf-8'))

    if common.get_platform() == common.PlatformWindows:
        mime.setData(
            'application/x-qt-windows-mime;value="FileName"', _bytes
        )
        mime.setData(
            'application/x-qt-windows-mime;value="FileNameW"', _bytes
        )

    return mime


@functools.lru_cache(maxsize=4194304)
def get_sequence_elements(filepath):
    """Cache-backed utility function to retrieve the sequence elements from the given file path.

    Args:
        filepath (str): A file path.

    Returns:
        tuple: (seq, sequence_path) where seq is the regex match object or None,
               and sequence_path is the proxy sequence path or None.
    """
    try:
        seq = common.get_sequence(filepath)
    except RuntimeError:
        seq = None

    sequence_path = None
    if seq:
        try:
            # Ensure seq has the expected number of groups
            if len(seq.groups()) >= 4:
                sequence_path = seq.group(1) + common.SEQPROXY + seq.group(3) + '.' + seq.group(4)
            else:
                # seq does not have the expected groups
                seq = None
                sequence_path = None
        except IndexError:
            # seq groups are not accessible
            seq = None
            sequence_path = None
    return seq, sequence_path


class FileItemModel(base.ItemModel):
    """Model used to list files in an asset.

    The model will load files from one task folder at any given time. The current
    task folder can be retrieved by :meth:`task()`. Switching tasks is done via
    emitting the :attr:`taskFolderChanged` signals.

    The model will load the found files into two separate data sets, one listing
    files individually, the other groups them into sequences. See
    :mod:`bookmarks.common.sequences` for the rules that determine how sequence
    items are identified.

    Switching between `FileItems` and `SequenceItems` is done by emitting the
    :attr:`dataTypeChanged` signal.

    .. note:

        The model won't necessarily load all files it encounters. If the parent
        bookmark item has a valid token config set, certain file extension might be
        excluded. See the :mod:`bookmarks.tokens.tokens` for details.

    """
    queues = (threads.FileInfo, threads.FileThumbnail)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.dataTypeChanged.connect(self.set_data_type)
        self.dataTypeChanged.connect(common.signals.updateTopBarButtons)

    def refresh_needed(self):
        """Returns the refresh states of the current model data set.

        """
        p = self.parent_path()
        k = self.task()
        t = common.FileItem

        if not p or not all(p) or not k or t is None:
            return False

        data = common.get_data(p, k, t)
        if not data:
            return False

        return data.refresh_needed

    def set_refresh_needed(self, v):
        """Sets the refresh status of the current model data set.

        """
        p = self.parent_path()
        k = self.task()
        t = common.FileItem

        if not p or not all(p) or not k or t is None:
            return

        for t in (common.FileItem, common.SequenceItem):
            data = common.get_data(p, k, t)
            if not data:
                continue
            data.refresh_needed = v

    def item_generator(self, path):
        """Recursive iterator for retrieving files from all task subfolders."""
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if self._interrupt_requested:
                        return
                    if entry.is_file():
                        yield entry
                    elif entry.is_dir(follow_symlinks=False):
                        yield from self.item_generator(entry.path)
        except OSError as e:
            log.error(__name__, f"Error scanning {path}: {e}")

    @common.status_bar_message('Loading Files...')
    @base.initdata
    @common.error
    @common.debug
    def init_data(self):
        """Collects file data for both individual files and sequences."""
        p = self.parent_path()
        k = self.task()
        t = common.FileItem

        if not p or not all(p) or not k or t is None:
            return

        # Initialize data structures
        data = common.get_data(p, k, t)
        sequence_data = common.DataDict()  # Temporary dictionary for sequence data

        # Prepare source path as absolute and normalized path
        source_path = common.normalize_path('/'.join(p + (k,)))
        if not os.path.exists(source_path):
            return

        # Initialize variables
        watcher = common.get_watcher(common.FileTab)
        watcher.reset()
        watch_paths = {source_path, }
        favourites = common.favourites
        disable_filter = self.disable_filter()

        # Get valid extensions
        config = tokens.get(*p[0:3])
        valid_extensions = (
            config.get_task_extensions(k) if config.check_task(k) else config.get_extensions(tokens.AllFormat)
        )

        # Cache commonly used values
        parent_path_prefix = tuple(p + (k,))
        row_size = self.row_size
        queues = self.queues

        # Progress bar variables
        nth = 987
        c = 0

        # Iterate over files using optimized item_generator
        for entry in self.item_generator(source_path):
            if self._interrupt_requested:
                break

            # Early filtering
            if not entry.is_file():
                continue

            filename = entry.name

            # Skip hidden and system files
            if filename.startswith('.') or filename.lower() == 'thumbs.db':
                continue

            # Get file extension
            ext = os.path.splitext(filename)[1][1:].lower()
            if not ext:
                continue

            # Filter by valid extensions
            if not disable_filter and ext not in valid_extensions:
                continue

            # Prepare file paths
            filepath = common.normalize_path(entry.path)

            # Check if filepath is within source_path
            try:
                common_path = os.path.commonpath([source_path, filepath]).replace('\\', '/')
            except ValueError:
                # Paths are on different drives on Windows
                common_path = None

            if common_path != source_path:
                log.error(__name__,
                          f'File {filepath} is outside the source path {source_path}. Verify if this is intentional.')

            # Compute relative path from task folder to file without relative denominators
            relative_path = os.path.relpath(filepath, source_path).replace('\\', '/')
            # Ensure relative_path does not contain '../' or './'
            if '..' in relative_path or relative_path.startswith('.'):
                # Path goes outside the source directory; use absolute path or handle accordingly
                display_path = os.path.basename(filepath)  # Fallback to filename
            else:
                display_path = relative_path

            file_root = os.path.splitext(filename)[0]
            sort_by_name_role = [name.lower() for name in p[:8]] + [display_path.lower()]

            # Update progress bar
            c += 1
            if c % nth == 0:
                common.signals.showStatusBarMessage.emit(f'Loading files (found {c} items)...')
                QtWidgets.QApplication.instance().processEvents(
                    QtCore.QEventLoop.ExcludeUserInputEvents
                )

            # Set flags
            flags = base.DEFAULT_ITEM_FLAGS
            if filepath in favourites:
                flags |= common.MarkedAsFavourite

            # Add file to data (FileItem model) regardless of sequence
            idx = len(data)
            if idx >= common.max_list_items:
                break  # Limit the number of items loaded

            file_data_dict = common.DataDict({
                QtCore.Qt.DisplayRole: display_path,
                common.FilterTextRole: f"{display_path}\n{filename}",
                QtCore.Qt.EditRole: filename,
                common.PathRole: filepath,
                QtCore.Qt.SizeHintRole: row_size,
                QtCore.Qt.StatusTipRole: display_path,
                QtCore.Qt.AccessibleDescriptionRole: display_path,
                QtCore.Qt.WhatsThisRole: display_path,
                QtCore.Qt.ToolTipRole: display_path,
                common.QueueRole: queues,
                common.DataTypeRole: common.FileItem,
                common.DataDictRole: weakref.ref(data),
                common.ItemTabRole: common.FileTab,
                common.EntryRole: [entry],
                common.FlagsRole: flags,
                common.ParentPathRole: parent_path_prefix + tuple(relative_path.split('/')[:-1]),
                common.DescriptionRole: '',
                common.NoteCountRole: 0,
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
                common.SortByTypeRole: ext,
                common.IdRole: idx,
                common.SGLinkedRole: False,
            })

            # Add file to data (FileItem model)
            data[idx] = file_data_dict

            # Get sequence information
            seq_match = get_sequence_elements(filepath)  # Use the full filepath here
            seq = None  # Initialize seq
            if seq_match and len(seq_match) == 2:
                seq, sequence_path = seq_match
                if seq and sequence_path:
                    # Now proceed with sequence processing
                    sequence_path = common.normalize_path(sequence_path)

                    # Check if sequence_path is within source_path
                    try:
                        seq_common_path = os.path.commonpath([source_path, sequence_path]).replace('\\', '/')
                    except ValueError:
                        seq_common_path = None

                    if seq_common_path != source_path:
                        log.error(__name__,
                                  f'Sequence {sequence_path} is outside the source path {source_path}. Verify if this is intentional.')
                        seq = None  # Treat as an individual file
                    else:
                        # Compute the relative path for the sequence
                        sequence_relative_path = os.path.relpath(sequence_path, source_path).replace('\\', '/')
                        if '..' in sequence_relative_path or sequence_relative_path.startswith('.'):
                            sequence_name = os.path.basename(sequence_path)
                        else:
                            sequence_name = sequence_relative_path

                        sort_by_name_role_seq = [name.lower() for name in p[:8]] + [sequence_name.lower()]

                        # Initialize sequence data if not already present
                        if sequence_path not in sequence_data:
                            seq_flags = base.DEFAULT_ITEM_FLAGS
                            if sequence_path in favourites:
                                seq_flags |= common.MarkedAsFavourite

                            sequence_data[sequence_path] = common.DataDict({
                                QtCore.Qt.DisplayRole: sequence_name,
                                common.FilterTextRole: sequence_name,
                                QtCore.Qt.EditRole: os.path.basename(sequence_path),
                                common.PathRole: sequence_path,
                                QtCore.Qt.SizeHintRole: row_size,
                                QtCore.Qt.StatusTipRole: sequence_name,
                                QtCore.Qt.AccessibleDescriptionRole: sequence_name,
                                QtCore.Qt.WhatsThisRole: sequence_name,
                                QtCore.Qt.ToolTipRole: sequence_name,
                                common.QueueRole: queues,
                                common.DataTypeRole: common.SequenceItem,
                                common.DataDictRole: None,  # Will be set later
                                common.ItemTabRole: common.FileTab,
                                common.EntryRole: [],
                                common.FlagsRole: seq_flags,
                                common.ParentPathRole: parent_path_prefix + tuple(
                                    sequence_relative_path.split('/')[:-1]),
                                common.DescriptionRole: '',
                                common.NoteCountRole: 0,
                                common.FileDetailsRole: '',
                                common.SequenceRole: seq,
                                common.FramesRole: [],
                                common.StartPathRole: None,
                                common.EndPathRole: None,
                                common.FileInfoLoaded: False,
                                common.ThumbnailLoaded: False,
                                common.SortByNameRole: sort_by_name_role_seq,
                                common.SortByLastModifiedRole: 0,
                                common.SortBySizeRole: 0,
                                common.SortByTypeRole: ext,
                                common.IdRole: 0,  # Will be updated later
                                common.SGLinkedRole: False,
                            })

                        # Append frame and entry to sequence data
                        sequence_data[sequence_path][common.FramesRole].append(seq.group(2))
                        sequence_data[sequence_path][common.EntryRole].append(entry)
                else:
                    seq = None  # Treat as individual file
            else:
                seq = None  # Treat as individual file

        # Process sequence data
        sequence_items = common.get_data(p, k, common.SequenceItem)
        for idx, (seq_path, seq_data) in enumerate(sequence_data.items()):
            if idx >= common.max_list_items:
                break  # Limit the number of items loaded

            frames = seq_data.get(common.FramesRole, [])
            if len(frames) == 1:
                # Sequence with a single frame; treat as individual file
                _seq = seq_data[common.SequenceRole]
                if _seq and len(_seq.groups()) >= 4:
                    frame = frames[0]
                    filepath = common.normalize_path(f"{_seq.group(1)}{frame}{_seq.group(3)}.{_seq.group(4)}")

                    # Compute relative path
                    relative_path = os.path.relpath(filepath, source_path).replace('\\', '/')
                    if '..' in relative_path or relative_path.startswith('.'):
                        display_path = os.path.basename(filepath)
                    else:
                        display_path = relative_path

                    filename = os.path.basename(filepath)
                    seq_data.update({
                        QtCore.Qt.DisplayRole: display_path,
                        common.FilterTextRole: f"{display_path}\n{filename}",
                        QtCore.Qt.EditRole: filename,
                        common.PathRole: filepath,
                        common.DataTypeRole: common.FileItem,
                        common.SortByLastModifiedRole: 0,
                        common.FlagsRole: base.DEFAULT_ITEM_FLAGS | (
                            common.MarkedAsFavourite if filepath in favourites else 0
                        ),
                        common.SequenceRole: None,
                        common.FramesRole: [],
                    })

                    # Add to sequence_items (SequenceItem model)
                    seq_data[common.DataDictRole] = weakref.ref(sequence_items)
                    seq_data[common.IdRole] = idx
                    sequence_items[idx] = seq_data
                else:
                    # Invalid sequence; treat as individual file
                    seq_data[common.DataTypeRole] = common.FileItem
                    seq_data[common.DataDictRole] = weakref.ref(sequence_items)
                    seq_data[common.IdRole] = idx
                    sequence_items[idx] = seq_data
            else:
                # Sequence with multiple frames
                seq_relative_path = os.path.relpath(seq_path, source_path).replace('\\', '/')
                if '..' in seq_relative_path or seq_relative_path.startswith('.'):
                    seq_display_name = os.path.basename(seq_path)
                else:
                    seq_display_name = seq_relative_path

                seq_data[QtCore.Qt.DisplayRole] = seq_display_name
                seq_data[common.FilterTextRole] = seq_display_name
                seq_data[common.SortByNameRole][-1] = seq_display_name.lower()
                seq_data[common.DataDictRole] = weakref.ref(sequence_items)
                seq_data[common.IdRole] = idx
                sequence_items[idx] = seq_data

        # Update file system watcher
        watcher.add_directories(sorted(watch_paths))

        # Mark refresh as not needed
        common.get_data(p, k, common.FileItem).refresh_needed = False
        common.get_data(p, k, common.SequenceItem).refresh_needed = False

    def disable_filter(self):
        """Overrides the token config and disables file filters."""
        return False

    def parent_path(self):
        """The model's parent folder path segments.

        Returns:
            tuple: A tuple of path segments.

        """
        return common.active('asset', args=True) or ()

    def save_active(self):
        """Saves the current active item.

        """
        index = self.active_index()

        if not index.isValid():
            return
        if not index.data(common.PathRole):
            return
        if not index.data(common.ParentPathRole):
            return

        parent_role = index.data(common.ParentPathRole)
        if len(parent_role) < 5:
            return

        file_info = QtCore.QFileInfo(index.data(common.PathRole))
        filepath = parent_role[5] + '/' + \
                   common.get_sequence_end_path(file_info.fileName())

        common.set_active('file', filepath)

    def task(self):
        """The model's associated task.

        """
        return common.active('task')

    @common.error
    def data_type(self):
        """Data type refers to the internal data set exposed to the model.

        We have two types implemented: A `FileItem` type and a `SequenceItem`
        type. The latter is used to display image sequences as single
        collapsed items.

        The type can be toggled with the `dataTypeChanged` signal.

        """
        task = self.task()
        if not task:
            return common.FileItem

        if task not in self._datatype:
            val = self.get_filter_setting('filters/collapsed')
            val = common.SequenceItem if val not in (
                common.FileItem, common.SequenceItem) else val
            self._datatype[task] = val

        return self._datatype[task]

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def set_data_type(self, val):
        """Set the model's data type.

        The model can serv items as collapsed sequence items, or as standard,
        individual file items. When the data type is set to ``common.SequenceItem``
        file sequences will be collapsed into a single sequence item. When the data
        type is ``common.FileItem`` each item will be displayed individually.

        In practice only :class:`FileItemModel` implements collapsed
        ``common.SequenceItem`` items.

        Args:
            val (int): A data type, one of ``common.FileItem``, ``common.SequenceItem``.

        """
        if val not in (common.FileItem, common.SequenceItem):
            raise ValueError(f'{val} is not a valid `data_type`.')

        task = self.task()
        if not task:
            task = common.FileItem

        if task not in self._datatype:
            self._datatype[task] = val

        # We don't have to do anything as the type is already the to `val`
        if self._datatype[task] == val:
            return

        # Set the data type to the user settings file
        self.set_filter_setting('filters/collapsed', val)

        self.beginResetModel()
        self._datatype[task] = val
        self.endResetModel()

    def filter_setting_key(self):
        """The custom dictionary key used to save filter settings to the user settings
        file.

        """
        return common.active('task', path=True)

    def _can_drop_properties(self, mime, action, row, column, parent=QtCore.QModelIndex()):
        return False

    def mimeData(self, indexes):
        """The data necessary for supporting drag and drop operations are
        constructed here.

        There is ambiguity in the absence of any good documentation I could find
        regarding what mime types have to be defined exactly for fully
        supporting drag and drop on all platforms.

        .. note:
            On Windows, ``application/x-qt-windows-mime;value="FileName"`` and
            ``application/x-qt-windows-mime;value="FileNameW"`` types seems to be
            necessary, but on macOS a simple uri list seem to suffice.

        """
        mime = super().mimeData(indexes)

        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier

        for index in indexes:
            if not index.isValid():
                continue
            path = index.data(common.PathRole)

            if no_modifier:
                path = common.get_sequence_end_path(path)
                _add_path_to_mime(mime, path)
            elif alt_modifier and shift_modifier:
                path = QtCore.QFileInfo(path).dir().path()
                _add_path_to_mime(mime, path)
            elif alt_modifier:
                path = common.get_sequence_start_path(path)
                _add_path_to_mime(mime, path)
            elif shift_modifier:
                paths = common.get_sequence_paths(index)
                for path in paths:
                    _add_path_to_mime(mime, path)
        return mime
