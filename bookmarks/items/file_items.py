# -*- coding: utf-8 -*-
"""The view and model used to display file items.

"""
import functools
import os

from PySide2 import QtWidgets, QtCore, QtGui

from . import delegate
from . import models
from . import views
from .. import actions
from .. import common
from .. import contextmenu
from .. import images
from .. import log
from ..threads import threads
from ..tokens import tokens


def add_path_to_mime(mime, path):
    """Adds the given path to the mime data."""
    common.check_type(path, str)

    path = QtCore.QFileInfo(path).absoluteFilePath()
    mime.setUrls(mime.urls() + [QtCore.QUrl.fromLocalFile(path), ])

    path = QtCore.QDir.toNativeSeparators(path)
    _bytes = QtCore.QByteArray(path.encode('utf-8'))

    mime.setData(
        'application/x-qt-windows-mime;value="FileName"', _bytes
    )
    mime.setData(
        'application/x-qt-windows-mime;value="FileNameW"', _bytes
    )

    return mime


@functools.lru_cache(maxsize=1048576)
def get_path_elements(name, path, _source_path):
    """Utility method used to cache and retrieve path elements.

    """
    path = path.replace('\\', '/')

    ext = name.split('.')[-1]

    # Getting the file's relative root folder
    # This data is used to display the clickable sub-folders relative
    # to the current task folder
    file_root = path[:path.rfind('/')][len(_source_path) + 1:]

    sort_by_name_role = models.DEFAULT_SORT_BY_NAME_ROLE.copy()
    _dir = None
    if file_root:
        # Save the file's parent folder for the file system watcher
        _dir = _source_path + '/' + file_root
        # To sort by folders correctly, we populate a fixed length
        # list with the sub-folders and file names. Sorting is case-insensitive.
        _file_root = file_root.lower().split('/')
        for idx in range(len(_file_root)):
            sort_by_name_role[idx] = _file_root[idx]
            if idx == 6:
                break
    sort_by_name_role[7] = name.lower()

    return path, ext, file_root, _dir, sort_by_name_role


@functools.lru_cache(maxsize=4194304)
def get_sequence_elements(filepath):
    try:
        seq = common.get_sequence(filepath)
    except RuntimeError:
        seq = None

    sequence_path = None
    if seq:
        sequence_path = seq.group(1) + common.SEQPROXY + \
                        seq.group(3) + '.' + seq.group(4)
    return seq, sequence_path


class DropIndicatorWidget(QtWidgets.QWidget):
    """Widgets responsible for drawing an overlay."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        """Paints the indicator area."""
        painter = QtGui.QPainter()
        painter.begin(self)
        pen = QtGui.QPen(common.color(common.BlueColor))
        pen.setWidth(common.size(common.WidthIndicator))
        painter.setPen(pen)
        painter.setBrush(common.color(common.BlueColor))
        painter.setOpacity(0.35)
        painter.drawRect(self.rect())
        painter.setOpacity(1.0)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.size(common.FontSizeMedium))[0],
            self.rect(),
            'Drop to add bookmark',
            QtCore.Qt.AlignCenter,
            common.color(common.BlueColor)
        )
        painter.end()

    def show(self):
        """Shows and sets the size of the widget."""
        self.setGeometry(self.parent().geometry())
        super().show()


class ItemDrag(QtGui.QDrag):
    """A utility class used to start a drag operation.
    
    """

    def __init__(self, index, widget):
        super(ItemDrag, self).__init__(widget)

        model = index.model().sourceModel()
        self.setMimeData(model.mimeData([index, ]))

        def get(s, color=common.color(common.GreenColor)):
            return images.ImageCache.get_rsc_pixmap(
                s, color,
                common.size(
                    common.WidthMargin
                ) * common.pixel_ratio
            )

        # Set drag icon
        self.setDragCursor(get('add_circle'), QtCore.Qt.CopyAction)
        self.setDragCursor(get('file'), QtCore.Qt.MoveAction)
        self.setDragCursor(
            get('close', color=common.color(common.RedColor)),
            QtCore.Qt.ActionMask
        )
        self.setDragCursor(
            get('close', color=common.color(common.RedColor)),
            QtCore.Qt.IgnoreAction
        )

        # Set pixmap
        source = index.data(common.PathRole)

        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier

        if no_modifier:
            source = common.get_sequence_endpath(source)
            pixmap, _ = images.get_thumbnail(
                index.data(common.ParentPathRole)[0],
                index.data(common.ParentPathRole)[1],
                index.data(common.ParentPathRole)[2],
                source,
                size=common.size(common.HeightRow),
            )
        elif alt_modifier and shift_modifier:
            pixmap = images.ImageCache.get_rsc_pixmap(
                'folder', common.color(common.TextSecondaryColor),
                common.size(common.HeightRow)
            )
            source = QtCore.QFileInfo(source).dir().path()
        elif alt_modifier:
            pixmap = images.ImageCache.get_rsc_pixmap(
                'file', common.color(common.TextSecondaryColor),
                common.size(common.HeightRow)
            )
            source = common.get_sequence_startpath(source)
        elif shift_modifier:
            source = common.get_sequence_startpath(source) + ', ++'
            pixmap = images.ImageCache.get_rsc_pixmap(
                'multiples_files', common.color(common.TextSecondaryColor),
                common.size(common.HeightRow)
            )
        else:
            return

        if pixmap and not pixmap.isNull():
            pixmap = DragPixmapFactory.pixmap(pixmap, source)
            self.setPixmap(pixmap)


class DragPixmapFactory(QtWidgets.QWidget):
    """Widget used to define the appearance of an item being dragged."""

    def __init__(self, pixmap, text, parent=None):
        super().__init__(parent=parent)
        self._pixmap = pixmap
        self._text = text

        _, metrics = common.font_db.primary_font(
            common.size(common.FontSizeMedium)
        )
        self._text_width = metrics.horizontalAdvance(text)

        width = self._text_width + common.size(common.WidthMargin)
        width = common.size(common.DefaultWidth) + common.size(
            common.WidthMargin
        ) if width > common.size(common.DefaultWidth) else width

        self.setFixedHeight(common.size(common.HeightRow))

        longest_edge = max((pixmap.width(), pixmap.height()))
        o = common.size(common.WidthIndicator)
        self.setFixedWidth(
            longest_edge + (o * 2) + width
        )

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.adjustSize()

    @classmethod
    def pixmap(cls, pixmap, text):
        """Returns the widget as a rendered pixmap."""
        w = cls(pixmap, text)
        pixmap = QtGui.QPixmap(w.size() * common.pixel_ratio, )
        pixmap.setDevicePixelRatio(common.pixel_ratio)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        w.render(painter, QtCore.QPoint(), QtGui.QRegion())
        return pixmap

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.BackgroundDarkColor))
        painter.setOpacity(0.6)
        painter.drawRoundedRect(self.rect(), 4, 4)
        painter.setOpacity(1.0)

        pixmap_rect = QtCore.QRect(
            0, 0, common.size(common.HeightRow), common.size(common.HeightRow)
        )
        painter.drawPixmap(pixmap_rect, self._pixmap, self._pixmap.rect())

        width = self._text_width + common.size(common.WidthIndicator)
        width = 640 if width > 640 else width
        rect = QtCore.QRect(
            common.size(common.HeightRow) + common.size(common.WidthIndicator),
            0,
            width,
            self.height()
        )
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.size(common.FontSizeMedium))[0],
            rect,
            self._text,
            QtCore.Qt.AlignCenter,
            common.color(common.TextSelectedColor)
        )
        painter.end()


class FilesWidgetContextMenu(contextmenu.BaseContextMenu):
    @common.error
    @common.debug
    def setup(self):
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.extra_menu()
        self.task_folder_toggle_menu()
        self.separator()
        self.launcher_menu()
        self.separator()
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.sg_publish_menu()
            self.sg_rv_menu()
        self.sg_url_menu()
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.convert_menu()
        self.add_file_menu()
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.delete_selected_files_menu()
        self.separator()
        self.bookmark_url_menu()
        self.asset_url_menu()
        self.reveal_item_menu()
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.copy_menu()
        self.separator()
        self.edit_active_bookmark_menu()
        self.edit_active_asset_menu()
        self.notes_menu()
        if self.index.flags() & QtCore.Qt.ItemIsEnabled:
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


class FilesModel(models.BaseModel):
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

    Note:

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
        p = self.source_path()
        k = self.task()
        t = common.FileItem

        if not p or not all(p) or not k or t is None:
            return False

        data = common.get_data(p, k, t)
        if not data:
            return False

        return data.refresh_needed

    def set_refresh_needed(self, v):
        p = self.source_path()
        k = self.task()
        t = common.FileItem

        if not p or not all(p) or not k or t is None:
            return

        data = common.get_data(p, k, t)
        if not data:
            return

        data.refresh_needed = v

    @common.status_bar_message('Loading Files...')
    @models.initdata
    @common.error
    @common.debug
    def init_data(self):
        """The method is responsible for getting the bare-bones file items by
        running a file-iterator stemming from ``self.source_path()``.

        Additional information, like description, item flags or thumbnails are
        fetched by thread workers.

        The method will iterate through all items returned by
        ``self.item_generator()`` and will gather information for both individual
        ``FileItems`` and collapsed ``SequenceItems`` (switch between the two
        datasets using the ``dataTypeChanged`` signal with the desired data
        type).

        """
        common.settings.load_active_values()

        p = self.source_path()
        k = self.task()
        t = common.FileItem

        if not p or not all(p) or not k or t is None:
            return

        _dirs = []
        data = common.get_data(p, k, t)

        SEQUENCE_DATA = common.DataDict()  # temporary dict for temp data

        # Reset file system watcher
        _source_path = '/'.join(p + (k,))
        if not QtCore.QFileInfo(_source_path).exists():
            return
        _dirs.append(_source_path)

        # Let's get the token config instance to check what extensions are
        # currently allowed to be displayed in the task folder
        config = tokens.get(*p[0:3])
        is_valid_task = config.check_task(k)
        if is_valid_task:
            valid_extensions = config.get_task_extensions(k)
        else:
            valid_extensions = config.get_extensions(tokens.AllFormat)

        disable_filter = self.disable_filter()

        nth = 987
        c = 0

        for entry in self.item_generator(_source_path):
            if self._interrupt_requested:
                break

            # Skipping directories
            if entry.is_dir():
                continue

            filename = entry.name

            # Skip items without file extension
            if '.' not in filename:
                continue

            # Skipping common hidden files
            if filename[0] == '.':
                continue

            if 'thumbs.db' in filename:
                continue

            # These values will always resolve to be the same, and therefore we
            # can use a cache to retrieve them
            filepath, ext, file_root, _dir, sort_by_name_role = get_path_elements(
                filename,
                entry.path,
                _source_path
            )
            _dirs.append(_dir)

            # We'll check against the current file extension against the allowed
            # extensions. If the task folder is not defined in the token config,
            # we'll allow all extensions
            if not disable_filter and ext not in valid_extensions:
                continue

            # Progress bar
            c += 1
            if not c % nth:
                common.signals.showStatusBarMessage.emit(
                    'Loading files (found ' + str(c) + ' items)...'
                )
                QtWidgets.QApplication.instance().processEvents()

            flags = models.DEFAULT_ITEM_FLAGS
            seq, sequence_path = get_sequence_elements(filepath)

            if (seq and (
                    sequence_path in common.favourites or filepath in
                    common.favourites)) or (
                    filepath in common.favourites):
                flags = flags | common.MarkedAsFavourite

            parent_path_role = p + (k, file_root)

            idx = len(data)
            if idx >= common.max_list_items:
                break  # Let's limit the maximum number of items we load

            data[idx] = common.DataDict(
                {
                    QtCore.Qt.DisplayRole: filename,
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
                    common.DataTypeRole: common.FileItem,
                    #
                    common.EntryRole: [entry, ],
                    common.FlagsRole: flags,
                    common.ParentPathRole: parent_path_role,
                    common.DescriptionRole: '',
                    common.TodoCountRole: 0,
                    common.FileDetailsRole: '',
                    common.SequenceRole: seq,
                    common.FramesRole: [],
                    common.FileInfoLoaded: False,
                    common.StartPathRole: None,
                    common.EndPathRole: None,
                    #
                    common.ThumbnailLoaded: False,
                    #
                    common.TypeRole: common.FileItem,
                    #
                    common.SortByNameRole: sort_by_name_role,
                    common.SortByLastModifiedRole: 0,
                    common.SortBySizeRole: 0,
                    common.SortByTypeRole: ext,
                    #
                    common.IdRole: idx,  # non-mutable
                    #
                    common.ShotgunLinkedRole: False,
                }
            )

            # If the file in question is a sequence, we will also save a reference
            # to it in the sequence data dict
            if seq:
                # If the sequence has not yet been added to our dictionary
                # of sequences we add it here
                if sequence_path not in SEQUENCE_DATA:  # create if it doesn't exist
                    sequence_name = sequence_path.split('/')[-1]
                    flags = models.DEFAULT_ITEM_FLAGS

                    if sequence_path in common.favourites:
                        flags = flags | common.MarkedAsFavourite

                    sort_by_name_role = list(sort_by_name_role)
                    sort_by_name_role[7] = sequence_name.lower()

                    SEQUENCE_DATA[sequence_path] = common.DataDict(
                        {
                            QtCore.Qt.DisplayRole: sequence_name,
                            QtCore.Qt.EditRole: sequence_name,
                            common.PathRole: sequence_path,
                            QtCore.Qt.SizeHintRole: self.row_size,
                            #
                            QtCore.Qt.StatusTipRole: sequence_name,
                            QtCore.Qt.AccessibleDescriptionRole: sequence_name,
                            QtCore.Qt.WhatsThisRole: sequence_name,
                            QtCore.Qt.ToolTipRole: sequence_name,
                            #
                            common.QueueRole: self.queues,
                            #
                            common.EntryRole: [],
                            common.FlagsRole: flags,
                            common.ParentPathRole: parent_path_role,
                            common.DescriptionRole: '',
                            common.TodoCountRole: 0,
                            common.FileDetailsRole: '',
                            common.SequenceRole: seq,
                            common.FramesRole: [],
                            common.FileInfoLoaded: False,
                            common.StartPathRole: None,
                            common.EndPathRole: None,
                            #
                            common.ThumbnailLoaded: False,
                            #
                            common.TypeRole: common.SequenceItem,
                            #
                            common.SortByNameRole: sort_by_name_role,
                            common.SortByLastModifiedRole: 0,
                            common.SortBySizeRole: 0,  # Initializing with null-size
                            common.SortByTypeRole: ext,
                            #
                            common.IdRole: 0,
                            #
                            common.ShotgunLinkedRole: False,
                        }
                    )

                SEQUENCE_DATA[sequence_path][common.FramesRole].append(seq.group(2))
                SEQUENCE_DATA[sequence_path][common.EntryRole].append(entry)
            else:
                # Copy the existing file item
                SEQUENCE_DATA[filepath] = common.DataDict(data[idx])
                SEQUENCE_DATA[filepath][common.IdRole] = -1

        # Cast the sequence data back onto the model
        t = common.SequenceItem
        data = common.get_data(p, k, t)

        for idx, v in enumerate(SEQUENCE_DATA.values()):
            if idx >= common.max_list_items:
                break  # Let's limit the maximum number of items we load

            # A sequence with only one element is not a sequence far as
            # we're concerned
            if len(v[common.FramesRole]) == 1:
                _seq = v[common.SequenceRole]
                filepath = (
                        _seq.group(1) +
                        v[common.FramesRole][0] +
                        _seq.group(3) +
                        '.' + _seq.group(4)
                )
                filename = filepath.split('/')[-1]
                v[QtCore.Qt.DisplayRole] = filename
                v[QtCore.Qt.EditRole] = filename
                v[common.PathRole] = filepath
                v[common.TypeRole] = common.FileItem
                v[common.SortByLastModifiedRole] = 0

                flags = models.DEFAULT_ITEM_FLAGS
                if filepath in common.favourites:
                    flags = flags | common.MarkedAsFavourite

                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem

            data[idx] = v
            data[idx][common.IdRole] = idx
            data[idx][common.DataTypeRole] = common.SequenceItem

        common.clear_watchdirs(common.FileItemMonitor)
        common.set_watchdirs(common.FileItemMonitor, list(set(_dirs)))
        self.set_refresh_needed(False)

    def disable_filter(self):
        """Overrides the token config and disables file filters."""
        return False

    def source_path(self):
        """The model's parent folder path segments.

        Returns:
            tuple: A tuple of path segments.

        """
        return (
            common.active('server'),
            common.active('job'),
            common.active('root'),
            common.active('asset')
        )

    def item_generator(self, path):
        """Recursive iterator for retrieving files from all sub-folders.

        """
        try:
            it = os.scandir(path)
        except OSError as e:
            log.error(e)
            return

        for entry in it:
            if entry.is_dir():
                for _entry in self.item_generator(entry.path):
                    yield _entry
            else:
                yield entry

    def save_active(self):
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
                   common.get_sequence_endpath(file_info.fileName())

        actions.set_active('file', filepath)

    def task(self):
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

    def filter_setting_dict_key(self):
        if common.active('task') is None:
            return None

        keys = (
            'server',
            'job',
            'root',
            'asset',
            'task',
        )
        v = [common.active(k) for k in keys]
        if not all(v):
            return None

        return '/'.join(v)

    def mimeData(self, indexes):
        """The data necessary for supporting drag and drop operations are
        constructed here.

        There is ambiguity in the absence of any good documentation I could find
        regarding what mime types have to be defined exactly for fully
        supporting drag and drop on all platforms.

        Note:
            On Windows, ``application/x-qt-windows-mime;value="FileName"`` and
            ``application/x-qt-windows-mime;value="FileNameW"`` types seems to be
            necessary, but on macOS a simple uri list seem to suffice.

        """
        mime = QtCore.QMimeData()
        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier

        for index in indexes:
            if not index.isValid():
                continue
            path = index.data(common.PathRole)

            if no_modifier:
                path = common.get_sequence_endpath(path)
                add_path_to_mime(mime, path)
            elif alt_modifier and shift_modifier:
                path = QtCore.QFileInfo(path).dir().path()
                add_path_to_mime(mime, path)
            elif alt_modifier:
                path = common.get_sequence_startpath(path)
                add_path_to_mime(mime, path)
            elif shift_modifier:
                paths = common.get_sequence_paths(index)
                for path in paths:
                    add_path_to_mime(mime, path)
        return mime


class FilesWidget(views.ThreadedBaseWidget):
    """The view used to display the contents of a ``FilesModel`` instance.

    """
    SourceModel = FilesModel
    Delegate = delegate.FilesWidgetDelegate
    ContextMenu = FilesWidgetContextMenu

    queues = (threads.FileInfo, threads.FileThumbnail)

    def __init__(self, icon='file', parent=None):
        super(FilesWidget, self).__init__(
            icon=icon,
            parent=parent
        )
        self.drop_indicator_widget = DropIndicatorWidget(parent=self)
        self.drop_indicator_widget.hide()

        self.drag_source_index = QtCore.QModelIndex()
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)

        common.signals.fileAdded.connect(self.show_item)

    def inline_icons_count(self):
        if self.buttons_hidden():
            return 0
        return 3

    def action_on_enter_key(self):
        index = common.get_selected_index(self)
        if not index.isValid():
            self.activate(index)

    def startDrag(self, supported_actions):
        index = common.get_selected_index(self)
        if not index.isValid():
            return
        if not index.data(common.PathRole):
            return
        if not index.data(common.ParentPathRole):
            return

        self.drag_source_index = index
        self.update(index)

        drag = ItemDrag(index, self)
        common.main_widget.topbar_widget.slack_drop_area_widget.setHidden(False)
        QtCore.QTimer.singleShot(1, self.viewport().update)
        drag.exec_(supported_actions)
        common.main_widget.topbar_widget.slack_drop_area_widget.setHidden(True)

        self.drag_source_index = QtCore.QModelIndex()

    def get_hint_string(self):
        model = self.model().sourceModel()
        k = model.task()
        if not k:
            return 'Click the File tab to select a folder'
        return f'No files found in "{k}"'

    @common.error
    @common.debug
    @QtCore.Slot(str)
    def show_item(self, v, role=QtCore.Qt.DisplayRole, update=True, limit=10000):
        """This slot is called by the `itemAdded` signal.

        For instance, when new file is added we'll use this method to reveal it
        in the files tab.

        """
        proxy = self.model()
        model = proxy.sourceModel()
        k = model.task()

        if not all(model.source_path()):
            return
        source_path = '/'.join(model.source_path())

        # We probably saved outside the asset, we won't be showing the
        # file...
        if source_path not in v:
            return

        # Show files tab
        actions.change_tab(common.FileTab)

        # Change task folder
        task = v.replace(source_path, '').strip('/').split('/', maxsplit=1)[0]
        if k != task:
            common.signals.taskFolderChanged.emit(task)

        data = model.model_data()
        t = model.data_type()
        if t == common.SequenceItem:
            v = common.proxy_path(v)

        # Refresh the model if
        if len(data) < limit:
            model.reset_data(force=True)

        # Delay the selection to let the model process events
        QtCore.QTimer.singleShot(
            300, functools.partial(
                self.select_item, v, role=common.PathRole
            )
        )
