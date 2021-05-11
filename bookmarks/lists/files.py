# -*- coding: utf-8 -*-
"""The view and model used to browse files.

"""
import _scandir
import functools
from PySide2 import QtWidgets, QtCore, QtGui

from .. import contextmenu
from .. import log
from .. import common
from ..threads import threads
from .. import settings
from .. import images
from .. import actions
from .. import datacache
from ..properties import asset_config

from . import base
from . import delegate


FILTER_EXTENSIONS = False


class DropIndicatorWidget(QtWidgets.QWidget):
    """Widgets responsible for drawing an overlay."""

    def __init__(self, parent=None):
        super(DropIndicatorWidget, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        """Paints the indicator area."""
        painter = QtGui.QPainter()
        painter.begin(self)
        pen = QtGui.QPen(common.BLUE)
        pen.setWidth(common.INDICATOR_WIDTH())
        painter.setPen(pen)
        painter.setBrush(common.BLUE)
        painter.setOpacity(0.35)
        painter.drawRect(self.rect())
        painter.setOpacity(1.0)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0],
            self.rect(),
            u'Drop to add bookmark',
            QtCore.Qt.AlignCenter,
            common.BLUE
        )
        painter.end()

    def show(self):
        """Shows and sets the size of the widget."""
        self.setGeometry(self.parent().geometry())
        super(DropIndicatorWidget, self).show()


class ItemDrag(QtGui.QDrag):
    def __init__(self, index, widget):
        super(ItemDrag, self).__init__(widget)

        model = index.model().sourceModel()
        self.setMimeData(model.mimeData([index, ]))

        def get(s, color=common.GREEN):
            return images.ImageCache.get_rsc_pixmap(s, color, common.MARGIN() * images.pixel_ratio)

        # Set drag icon
        self.setDragCursor(get('add_circle'), QtCore.Qt.CopyAction)
        self.setDragCursor(get('file'), QtCore.Qt.MoveAction)
        self.setDragCursor(get('close', color=common.RED),
                           QtCore.Qt.ActionMask)
        self.setDragCursor(get('close', color=common.RED),
                           QtCore.Qt.IgnoreAction)

        # Set pixmap
        source = index.data(QtCore.Qt.StatusTipRole)

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
                size=common.ROW_HEIGHT(),
            )
        elif alt_modifier and shift_modifier:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'folder', common.SECONDARY_TEXT, common.ROW_HEIGHT())
            source = QtCore.QFileInfo(source).dir().path()
        elif alt_modifier:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'file', common.SECONDARY_TEXT, common.ROW_HEIGHT())
            source = common.get_sequence_startpath(source)
        elif shift_modifier:
            source = common.get_sequence_startpath(source) + u', ++'
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'multiples_files', common.SECONDARY_TEXT, common.ROW_HEIGHT())
        else:
            return

        if pixmap and not pixmap.isNull():
            pixmap = DragPixmapFactory.pixmap(pixmap, source)
            self.setPixmap(pixmap)


class DragPixmapFactory(QtWidgets.QWidget):
    """Widget used to define the appearance of an item being dragged."""

    def __init__(self, pixmap, text, parent=None):
        super(DragPixmapFactory, self).__init__(parent=parent)
        self._pixmap = pixmap
        self._text = text

        _, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        self._text_width = metrics.width(text)

        width = self._text_width + common.MARGIN()
        width = common.WIDTH() + common.MARGIN() if width > common.WIDTH() else width

        self.setFixedHeight(common.ROW_HEIGHT())

        longest_edge = max((pixmap.width(), pixmap.height()))
        o = common.INDICATOR_WIDTH()
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
        pixmap = QtGui.QPixmap(w.size() * images.pixel_ratio, )
        pixmap.setDevicePixelRatio(images.pixel_ratio)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        w.render(painter, QtCore.QPoint(), QtGui.QRegion())
        return pixmap

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.DARK_BG)
        painter.setOpacity(0.6)
        painter.drawRoundedRect(self.rect(), 4, 4)
        painter.setOpacity(1.0)

        pixmap_rect = QtCore.QRect(
            0, 0, common.ROW_HEIGHT(), common.ROW_HEIGHT())
        painter.drawPixmap(pixmap_rect, self._pixmap, self._pixmap.rect())

        width = self._text_width + common.INDICATOR_WIDTH()
        width = 640 if width > 640 else width
        rect = QtCore.QRect(
            common.ROW_HEIGHT() + common.INDICATOR_WIDTH(),
            0,
            width,
            self.height()
        )
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0],
            rect,
            self._text,
            QtCore.Qt.AlignCenter,
            common.SELECTED_TEXT
        )
        painter.end()


class FilesWidgetContextMenu(contextmenu.BaseContextMenu):
    @common.error
    @common.debug
    def setup(self):
        self.window_menu()

        self.separator()

        self.task_toggles_menu()

        self.separator()

        self.sg_publish_menu()
        self.sg_rv_menu()
        self.sg_url_menu()

        self.convert_menu()

        self.title()

        self.add_file_menu()

        self.separator()

        self.bookmark_url_menu()
        self.asset_url_menu()
        self.reveal_item_menu()
        self.copy_menu()

        self.separator()

        self.edit_active_bookmark_menu()
        self.edit_active_asset_menu()
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

        self.quit_menu()


class FilesModel(base.BaseModel):
    """Model used to list files in an asset.

    The root of the asset folder is never read, instead, each asset is expected
    to contain a series of subfolders - referred to here as `task folders`.

    The model will load files from one task folder at any given time. The
    current task folder can be retrieved using `self.task()`. Switching
    the task folders is done via the `taskFolderChanged.emit('my_task')`
    signal.

    Files & Sequences
    -----------------
    The model will load the found files into two separate data sets, one
    listing files individually, the other collects files into file sequences
    if they have an incremental number element.

    Switching between the `FileItems` and `SequenceItems` is done by emitting
    the `dataTypeChanged.emit(FileItem)` signal.

    File Format Filtering
    ---------------------

    If the current task folder has a curresponding configuration in the current
    bookmark's asset config, we can determine which file formats should be
    allowed to display in the folder.
    See the `asset_config.py` module for details.

    """
    queues = (threads.FileInfo, threads.FileThumbnail)

    def __init__(self, parent=None):
        super(FilesModel, self).__init__(parent=parent)

        self._refresh_needed = False
        self._watcher = QtCore.QFileSystemWatcher(parent=self)
        self._watcher.directoryChanged.connect(self.dir_changed)

        self.taskFolderChanged.connect(self.set_task)
        self.dataTypeChanged.connect(self.set_data_type)
        self.dataTypeChanged.connect(common.signals.updateButtons)

    def refresh_needed(self):
        return self._refresh_needed

    def set_refresh_needed(self, v):
        self._refresh_needed = v

    def watcher(self):
        """The file system monitor used to check for file changes."""
        return self._watcher

    def clear_watchdirs(self):
        self.set_refresh_needed(False)
        v = self._watcher.directories()
        if not v:
            return
        self._watcher.removePaths(v)

    def set_watchdirs(self, v):
        self._watcher.addPaths(v[0:128])

    @QtCore.Slot(unicode)
    def dir_changed(self, path):
        """Slot called when a watched directory changes.

        """
        p = self.parent_path()
        k = self.task()
        if not k:
            return
        t = common.FileItem
        data = datacache.get_data(p, k, t)

        # If the dataset is small we can safely reload the model
        if len(data) < 1999:
            self.__resetdata__(force=True)

        # Otherwise, we won't reload but indicate that the model needs
        # refreshing
        self.set_refresh_needed(True)

    @common.status_bar_message(u'Loading Files...')
    @base.initdata
    def __initdata__(self):
        """The method is responsible for getting the bare-bones file items by
        running a file-iterator stemming from ``self.parent_path()``.

        Additional information, like description, item flags or thumbnails are
        fetched by thread workers.

        The method will iterate through all items returned by
        ``self.item_iterator()`` and will gather information for both individual
        ``FileItems`` and collapsed ``SequenceItems`` (switch between the two
        datasets using the ``dataTypeChanged`` signal with the desired data
        type).

        """
        p = self.parent_path()
        k = self.task()
        if not k:
            return
        t = common.FileItem
        data = datacache.get_data(p, k, t)

        SEQUENCE_DATA = common.DataDict()  # temporary dict for temp data

        # Reset file system watcher
        self.clear_watchdirs()
        WATCHDIRS = []

        _parent_path = u'/'.join(p + (k,))
        if not QtCore.QFileInfo(_parent_path).exists():
            return

        # Let' get the asset config instance to check what extensions are
        # currently allowed to be displayed in the task folder
        config = asset_config.get(*p[0:3])
        is_valid_task = config.check_task(k)
        if is_valid_task:
            valid_extensions = config.get_task_extensions(k)
        else:
            valid_extensions = None
        disable_filter = self.disable_filter()

        nth = 987
        c = 0

        for entry in self.item_iterator(_parent_path):
            if self._interrupt_requested:
                break

            # Skipping directories
            if entry.is_dir():
                continue
            filename = entry.name

            # Skipping common hidden files
            if filename[0] == u'.':
                continue
            if u'thumbs.db' in filename:
                continue

            filepath = entry.path.replace(u'\\', u'/')

            # Skip items without file extension
            if u'.' not in filename:
                continue

            ext = filename.split(u'.')[-1]

            # We'll check against the current file extension against the allowed
            # extensions. If the task folder is not defined in the asset config,
            # we'll allow all extensions
            if not disable_filter and is_valid_task and ext not in valid_extensions:
                continue

            # Progress bar
            c += 1
            if not c % nth:
                common.signals.showStatusBarMessage.emit(
                    u'Loading files (found ' + unicode(c) + u' items)...')
                QtWidgets.QApplication.instance().processEvents()

            # Getting the file's relative root folder
            # This data is used to display the clickable subfolders relative
            # to the current task folder
            fileroot = filepath.replace(_parent_path, u'').strip(u'/')
            fileroot = u'/'.join(fileroot.split(u'/')[:-1])

            # Save the file's parent folder for the file system watcher
            WATCHDIRS.append(_parent_path + u'/' + fileroot)

            # To sort by subfolders correctly, we'll a populate a fixed length
            # list with the subfolders and file names. Sorting is do case
            # insensitive:
            sort_by_name_role = [0, 0, 0, 0, 0, 0, 0, 0]
            if fileroot:
                _fileroot = fileroot.lower().split(u'/')
                for idx in xrange(len(_fileroot)):
                    sort_by_name_role[idx] = _fileroot[idx]
                    if idx == 6:
                        break
            sort_by_name_role[7] = filename.lower()

            # If the file is named using our sequence denominators,
            # we can't use and must skip it
            try:
                seq = common.get_sequence(filepath)
            except RuntimeError:
                log.error(u'"' + filename + u'" named incorrectly. Skipping.')
                continue

            flags = base.DEFAULT_ITEM_FLAGS

            if seq:
                seqpath = seq.group(1) + common.SEQPROXY + \
                    seq.group(3) + u'.' + seq.group(4)
            if (seq and (seqpath in common.FAVOURITES_SET or filepath in common.FAVOURITES_SET)) or (filepath in common.FAVOURITES_SET):
                flags = flags | common.MarkedAsFavourite

            parent_path_role = p + (k, fileroot)

            idx = len(data)

            if idx >= common.MAXITEMS:
                break  # Let's limit the maximum number of items we load

            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.SizeHintRole: self._row_size,
                #
                common.QueueRole: self.queues,
                common.DataTypeRole: common.FileItem,
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: parent_path_role,
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: u'',
                common.SequenceRole: seq,
                common.FramesRole: [],
                common.FileInfoLoaded: False,
                common.StartpathRole: None,
                common.EndpathRole: None,
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
            })

            # If the file in question is a sequence, we will also save a reference
            # to it in the sequence data dict
            if seq:
                # If the sequence has not yet been added to our dictionary
                # of seqeunces we add it here
                if seqpath not in SEQUENCE_DATA:  # ... and create it if it doesn't exist
                    seqname = seqpath.split(u'/')[-1]
                    flags = base.DEFAULT_ITEM_FLAGS

                    if seqpath in common.FAVOURITES_SET:
                        flags = flags | common.MarkedAsFavourite

                    sort_by_name_role = list(sort_by_name_role)
                    sort_by_name_role[7] = seqname.lower()

                    SEQUENCE_DATA[seqpath] = common.DataDict({
                        QtCore.Qt.DisplayRole: seqname,
                        QtCore.Qt.EditRole: seqname,
                        QtCore.Qt.StatusTipRole: seqpath,
                        QtCore.Qt.SizeHintRole: self._row_size,
                        #
                        common.QueueRole: self.queues,
                        #
                        common.EntryRole: [],
                        common.FlagsRole: flags,
                        common.ParentPathRole: parent_path_role,
                        common.DescriptionRole: u'',
                        common.TodoCountRole: 0,
                        common.FileDetailsRole: u'',
                        common.SequenceRole: seq,
                        common.FramesRole: [],
                        common.FileInfoLoaded: False,
                        common.StartpathRole: None,
                        common.EndpathRole: None,
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
                    })

                SEQUENCE_DATA[seqpath][common.FramesRole].append(seq.group(2))
                SEQUENCE_DATA[seqpath][common.EntryRole].append(entry)
            else:
                # Copy the existing file item
                SEQUENCE_DATA[filepath] = common.DataDict(data[idx])
                SEQUENCE_DATA[filepath][common.IdRole] = -1

        # Cast the sequence data back onto the model
        t = common.SequenceItem
        data = datacache.get_data(p, k, t)

        for idx, v in enumerate(SEQUENCE_DATA.itervalues()):
            if idx >= common.MAXITEMS:
                break  # Let's limit the maximum number of items we load

            # A sequence with only one element is not a sequencemas far as
            # we're concerned
            if len(v[common.FramesRole]) == 1:
                _seq = v[common.SequenceRole]
                filepath = (
                    _seq.group(1) +
                    v[common.FramesRole][0] +
                    _seq.group(3) +
                    u'.' + _seq.group(4)
                )
                filename = filepath.split(u'/')[-1]
                v[QtCore.Qt.DisplayRole] = filename
                v[QtCore.Qt.EditRole] = filename
                v[QtCore.Qt.StatusTipRole] = filepath
                v[common.TypeRole] = common.FileItem
                v[common.SortByLastModifiedRole] = 0

                flags = base.DEFAULT_ITEM_FLAGS
                if filepath in common.FAVOURITES_SET:
                    flags = flags | common.MarkedAsFavourite

                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem

            data[idx] = v
            data[idx][common.IdRole] = idx
            data[idx][common.DataTypeRole] = common.SequenceItem

        self.set_watchdirs(list(set(WATCHDIRS)))
        self.set_refresh_needed(False)
        
    def disable_filter(self):
        """Overrides the asset config and disables file filters."""
        return False

    def parent_path(self):
        """The model's parent folder path segments.

        Returns:
            tuple: A tuple of path segments.

        """
        return (
            settings.active(settings.ServerKey),
            settings.active(settings.JobKey),
            settings.active(settings.RootKey),
            settings.active(settings.AssetKey)
        )

    def item_iterator(self, path):
        """Recursive iterator for retrieving files from all subfolders.

        """
        for entry in _scandir.scandir(path):
            if entry.is_dir():
                for _entry in self.item_iterator(entry.path):
                    yield _entry
            else:
                yield entry

    def save_active(self):
        index = self.active_index()

        if not index.isValid():
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            return
        if not index.data(common.ParentPathRole):
            return

        parent_role = index.data(common.ParentPathRole)
        if len(parent_role) < 5:
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        filepath = parent_role[5] + u'/' + \
            common.get_sequence_endpath(file_info.fileName())

        actions.set_active(settings.FileKey, filepath)

    def task(self):
        return settings.active(settings.TaskKey)

    @QtCore.Slot(unicode)
    def set_task(self, val):
        """Slot used to set the model's task folder.

        The active task folder is stored in `settings` and
        can be retried using `self.task()`.

        """
        p = self.parent_path()
        k = self.task()

        if k == val:
            return

        k = val
        actions.set_active(settings.TaskKey, val)
        self.__resetdata__()

    @common.debug
    @common.error
    def data_type(self):
        """Data type refers to the internal data set exposed to the model.

        We have two types implemented: A `FileItem` type and a `SequenceItem`
        type. The latter is used to display image sequences as single
        collapsed items.

        The type can be toggled with the `dataTypeChanged` signal.

        """
        task = self.task()

        if task not in self._datatype:
            key = u'{}/{}'.format(
                self.__class__.__name__,
                task
            )
            val = self.get_local_setting(
                settings.CurrentDataType,
                key=key,
                section=settings.UIStateSection
            )
            val = common.SequenceItem if val not in (
                common.FileItem, common.SequenceItem) else val
            self._datatype[task] = val

        return self._datatype[task]

    @common.debug
    @common.error
    @QtCore.Slot(int)
    def set_data_type(self, val):
        if val not in (common.FileItem, common.SequenceItem):
            s = u'Invalid data type value.'
            raise TypeError(s)

        task = self.task()
        if task not in self._datatype:
            self._datatype[task] = val

        # We don't have to do anything as the type is already the to `val`
        if self._datatype[task] == val:
            return

        # Set the data type to the local settings file
        key = u'{}/{}'.format(
            self.__class__.__name__,
            self.task()
        )
        self.set_local_setting(
            settings.CurrentDataType,
            val,
            key=key,
            section=settings.UIStateSection
        )

        self.beginResetModel()
        self._datatype[task] = val
        self.endResetModel()

    def local_settings_key(self):
        if settings.active(settings.TaskKey) is None:
            return None

        keys = (
            settings.JobKey,
            settings.RootKey,
            settings.AssetKey,
            settings.TaskKey,
        )
        v = [settings.active(k) for k in keys]
        if not all(v):
            return None

        return u'/'.join(v)

    def mimeData(self, indexes):
        """The data necessary for supporting drag and drop operations are
        constructed here.

        There is ambiguity in the absence of any good documentation I could find
        regarding what mime types have to be defined exactly for fully
        supporting drag and drop on all platforms.

        Note:
            On windows, ``application/x-qt-windows-mime;value="FileName"`` and
            ``application/x-qt-windows-mime;value="FileNameW"`` types seems to be
            necessary, but on MacOS a simple uri list seem to suffice.

        """
        def add_path_to_mime(mime, path):
            """Adds the given path to the mime data."""
            if not isinstance(path, unicode):
                s = u'Expected <type \'unicode\'>, got {}'.format(type(str))
                log.error(s)
                raise TypeError(s)

            path = QtCore.QFileInfo(path).absoluteFilePath()
            mime.setUrls(mime.urls() + [QtCore.QUrl.fromLocalFile(path), ])

            path = QtCore.QDir.toNativeSeparators(path).encode('utf-8')
            _bytes = QtCore.QByteArray(path)
            mime.setData(
                u'application/x-qt-windows-mime;value="FileName"', _bytes)
            mime.setData(
                u'application/x-qt-windows-mime;value="FileNameW"', _bytes)

            return mime

        mime = QtCore.QMimeData()
        modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        no_modifier = modifiers == QtCore.Qt.NoModifier
        alt_modifier = modifiers & QtCore.Qt.AltModifier
        shift_modifier = modifiers & QtCore.Qt.ShiftModifier

        for index in indexes:
            if not index.isValid():
                continue
            path = index.data(QtCore.Qt.StatusTipRole)

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


class FilesWidget(base.ThreadedBaseWidget):
    """The view used to display the contents of a ``FilesModel`` instance.

    """
    SourceModel = FilesModel
    Delegate = delegate.FilesWidgetDelegate
    ContextMenu = FilesWidgetContextMenu

    queues = (threads.FileInfo, threads.FileThumbnail)

    def __init__(self, icon='files', parent=None):
        super(FilesWidget, self).__init__(
            icon=icon,
            parent=parent
        )
        self.indicatorwidget = DropIndicatorWidget(parent=self)
        self.indicatorwidget.hide()

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
        self.activate(self.selectionModel().currentIndex())

    def startDrag(self, supported_actions):
        index = self.selectionModel().currentIndex()

        if not index.isValid():
            return
        if not index.data(QtCore.Qt.StatusTipRole):
            return
        if not index.data(common.ParentPathRole):
            return

        self.drag_source_index = index
        self.update(index)

        drag = ItemDrag(index, self)
        drag.exec_(supported_actions)

        self.drag_source_index = QtCore.QModelIndex()

    def get_hint_string(self):
        model = self.model().sourceModel()
        k = model.task()
        if not k:
            return u'Click the File tab to select a folder.'
        return u'No files found in {}.'.format(k)

    @QtCore.Slot(unicode)
    @QtCore.Slot(int)
    @QtCore.Slot(object)
    def update_model_value(self, source, role, v):
        model = self.model().sourceModel()
        data = model.model_data()
        for idx in xrange(model.rowCount()):
            if source != common.proxy_path(data[idx][QtCore.Qt.StatusTipRole]):
                continue
            data[idx][role] = v
            self.update_row(idx)
            break

    @common.error
    @common.debug
    @QtCore.Slot(unicode)
    def show_item(self, v, role=QtCore.Qt.DisplayRole, update=True, limit=10000):
        """This slot is called by the `itemAdded` signal.

        For instance, whena new file is added, we'll use this method to reveal it
        in the files tab.

        """
        proxy = self.model()
        model = proxy.sourceModel()
        k = model.task()

        if not all(model.parent_path()):
            return
        parent_path = u'/'.join(model.parent_path())

        # We probably saved outside the asset, we won't be showing the
        # file...
        if parent_path not in v:
            return

        # Show files tab
        actions.change_tab(common.FileTab)

        # Change task folder
        task = v.replace(parent_path, u'').strip(u'/').split(u'/')[0]
        if k != task:
            model.set_task(task)

        data = model.model_data()
        t = model.data_type()
        if t == common.SequenceItem:
            v = common.proxy_path(v)

        # Refresh the model if
        if len(data) < limit:
            model.__resetdata__(force=True)

        # Delay the selection to let the model process events
        QtCore.QTimer.singleShot(300, functools.partial(
            self.select_item, v, role=QtCore.Qt.StatusTipRole))
