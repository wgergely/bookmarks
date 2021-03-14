# -*- coding: utf-8 -*-
"""Classes responsible for viewing and editing items marked as favourites.

"""
import _scandir

from PySide2 import QtWidgets, QtCore, QtGui


from .. import log
from .. import common
from ..threads import threads
from .. import settings
from .. import contextmenu
from .. import actions

from . import delegate
from . import files
from . import base


def _check_sequence(path):
    # Checking if the dropped item is sequence and if so, is does it have
    # more than one member
    seq = common.get_sequence(path)
    if not seq:
        return path

    # Let's see if we can find more than one members
    file_info = QtCore.QFileInfo(path)
    frames = 0
    for entry in _scandir.scandir(file_info.dir().path()):
        p = entry.path.replace(u'\\', u'/')
        if seq.group(1) in p and seq.group(3) in p:
            frames += 1
        if frames >= 2:
            break

    if frames > 1:
        return common.proxy_path(path)

    return path


class FavouritesWidgetContextMenu(contextmenu.BaseContextMenu):
    @common.error
    @common.debug
    def setup(self):
        self.control_favourites_menu()
        if self.index.isValid():
            self.remove_favourite_menu()
        self.separator()
        self.reveal_item_menu()
        self.copy_menu()
        self.separator()
        self.sort_menu()
        self.collapse_sequence_menu()
        self.separator()
        self.refresh_menu()


class FavouritesModel(files.FilesModel):
    """The model responsible for displaying the saved favourites."""
    queues = (threads.FavouriteInfo, threads.FavouriteThumbnail)

    @common.error
    @common.status_bar_message(u'Loading My Files...')
    @base.initdata
    def __initdata__(self):
        def dflags():
            """The default flags to apply to the item."""
            return (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable)

        k = self.task()
        t = self.data_type()
        data = self.INTERNAL_MODEL_DATA[k][t]

        SEQUENCE_DATA = common.DataDict()

        nth = 1
        c = 0
        for entry, parent_paths in self._entry_iterator():
            _parent_path = u'/'.join(parent_paths)

            if self._interrupt_requested:
                break

            filename = entry.name

            # Skipping common hidden files
            if filename[0] == u'.':
                continue
            if u'thumbs.db' in filename:
                continue

            filepath = entry.path.replace(u'\\', u'/')

            # Progress bar
            c += 1
            if not c % nth:
                common.signals.showStatusBarMessage.emit(
                    u'Loading files (found ' + unicode(c) + u' items)...')
                QtWidgets.QApplication.instance().processEvents()

            # Getting the fileroot
            fileroot = filepath.replace(_parent_path, u'').strip('/')
            fileroot = u'/'.join(fileroot.split(u'/')[:-1])

            # To sort by subfolders correctly, we'll have to populate a list
            # with all subfolders and file names. The list must be of fixed
            # length and we'll do case insensitive comparisons:
            sort_by_name_role = [0, 0, 0, 0, 0, 0, 0, 0]
            if fileroot:
                _fileroot = fileroot.lower().split(u'/')
                for idx in xrange(len(_fileroot)):
                    sort_by_name_role[idx] = _fileroot[idx]
                    if idx == 6:
                        break
            sort_by_name_role[7] = filename.lower()

            try:
                seq = common.get_sequence(filepath)
            except RuntimeError:
                log.error(u'"' + filename + u'" named incorrectly. Skipping.')
                continue

            flags = dflags()

            if seq:
                seqpath = seq.group(1) + common.SEQPROXY + \
                    seq.group(3) + u'.' + seq.group(4)
            if (seq and (seqpath in common.FAVOURITES_SET or filepath in common.FAVOURITES_SET)) or (filepath in common.FAVOURITES_SET):
                flags = flags | common.MarkedAsFavourite

            # Let's limit the maximum number of items we load
            idx = len(data)
            if idx >= common.MAXITEMS:
                break

            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: parent_paths[1] + u'|' + filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.SizeHintRole: self._row_size,
                #
                common.QueueRole: self.queues,
                common.DataTypeRole: t,
                #
                common.EntryRole: [entry, ],
                common.FlagsRole: flags,
                common.ParentPathRole: parent_paths,
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
                    flags = dflags()

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
                        common.ParentPathRole: parent_paths,
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
                        common.SortByNameRole: sort_by_name_role,
                        common.SortByLastModifiedRole: 0,
                        common.SortBySizeRole: 0,  # Initializing with null-size
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
        data = self.INTERNAL_MODEL_DATA[k][t]

        # Casting the sequence data back onto the model
        for idx, v in enumerate(SEQUENCE_DATA.itervalues()):
            if idx >= common.MAXITEMS:
                break  # Let's limit the maximum number of items we load

            if len(v[common.FramesRole]) == 1:
                # A sequence with only one element is not a sequence
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

                flags = dflags()
                if filepath in common.FAVOURITES_SET:
                    flags = flags | common.MarkedAsFavourite

                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem

            data[idx] = v
            data[idx][common.IdRole] = idx
            data[idx][common.DataTypeRole] = common.SequenceItem

    def _entry_iterator(self):
        """We're using the saved keys to find and return the DirEntries
        corresponding to the saved favourites.

        """
        entries = []

        for k in common.FAVOURITES_SET:
            file_info = QtCore.QFileInfo(k)
            _path = file_info.path()

            if not QtCore.QFileInfo(_path).exists():
                continue

            parent_paths = common.FAVOURITES[k]
            for entry in _scandir.scandir(_path):
                path = entry.path.replace(u'\\', u'/')
                if path == k:
                    entries.append((entry, parent_paths))
                    continue
                _k = common.proxy_path(path)
                if k == _k:
                    entries.append((entry, parent_paths))

        for args in entries:
            yield args

    def task(self):
        return u'favourites'

    def local_settings_key(self):
        return self.task()


class FavouritesWidget(files.FilesWidget):
    """The widget responsible for showing all the items marked as favourites."""
    SourceModel = FavouritesModel
    Delegate = delegate.FavouritesWidgetDelegate
    ContextMenu = FavouritesWidgetContextMenu

    queues = (threads.FavouriteInfo, threads.FavouriteThumbnail)

    def __init__(self, icon='favourite', parent=None):
        super(FavouritesWidget, self).__init__(
            icon=icon,
            parent=parent
        )
        self.reset_timer = common.Timer(parent=self)
        self.reset_timer.setInterval(100)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(
            self.model().sourceModel().modelDataResetRequested)
        common.signals.favouritesChanged.connect(self.queued_model_reset)

    def queued_model_reset(self):
        self.reset_timer.start(self.reset_timer.interval())

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons."""
        return True

    def inline_icons_count(self):
        return 3

    def toggle_item_flag(self, index, flag, state=None, commit_now=False):
        super(FavouritesWidget, self).toggle_item_flag(
            index, common.MarkedAsFavourite, state=False, commit_now=commit_now)
        self.reset_timer.start()

    def dragEnterEvent(self, event):
        if event.source() == self:
            return

        if event.mimeData().hasUrls():
            self.indicatorwidget.show()
            return event.accept()
        self.indicatorwidget.hide()

    def dragLeaveEvent(self, event):
        self.indicatorwidget.hide()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        """Event responsible for adding the dropped file to the favourites."""
        self.indicatorwidget.hide()

        if event.source() == self:
            return  # Won't allow dropping an item from itself

        mime = event.mimeData()
        if not mime.hasUrls():
            return

        event.accept()

        for url in mime.urls():
            file_info = QtCore.QFileInfo(url.toLocalFile())

            # Import favourite archive
            if file_info.suffix() == common.FAVOURITE_FILE_FORMAT:
                actions.import_favourites(source=file_info.filePath())
                continue

            k = _check_sequence(file_info.filePath())
            common.FAVOURITES[k] = common.local_parent_paths()

        common.FAVOURITES_SET = set(common.FAVOURITES)
        settings.instance().set_favourites(common.FAVOURITES)

    def get_hint_string(self):
        model = self.model().sourceModel()
        if not model.rowCount():
            return u'You didn\'t add any files yet.'
