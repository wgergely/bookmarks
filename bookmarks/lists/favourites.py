# -*- coding: utf-8 -*-
"""Classes responsible for viewing and editing items marked as favourites.

"""
import functools
import os

from PySide2 import QtCore

from . import basemodel
from . import delegate
from . import files
from .. import actions
from .. import common
from .. import contextmenu
from ..threads import threads


def _check_sequence(path):
    # Checking if the dropped item is sequence and if so, is does it have
    # more than one member
    seq = common.get_sequence(path)
    if not seq:
        return path

    # Let's see if we can find more than one member
    file_info = QtCore.QFileInfo(path)
    frames = 0
    for entry in os.scandir(file_info.dir().path()):
        p = entry.path.replace('\\', '/')
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

    def __init__(self, *args, **kwargs):
        super(FavouritesModel, self).__init__(*args, **kwargs)

        self.reset_timer = common.Timer(parent=self)
        self.reset_timer.setInterval(10)
        self.reset_timer.setSingleShot(True)

        self.reset_timer.timeout.connect(
            functools.partial(self.reset_data, force=True)
        )
        common.signals.favouritesChanged.connect(self.queued_model_reset)

    @QtCore.Slot()
    def queued_model_reset(self):
        """Starts/reset the timer responsible for reloading the list of
        favourite items.

        """
        self.reset_timer.start(self.reset_timer.interval())

    @common.error
    @common.status_bar_message('Loading My Files...')
    @basemodel.initdata
    def init_data(self):
        __p = self.source_path()
        __k = self.task()
        t = common.FileItem
        data = common.get_data(__p, __k, t)

        SEQUENCE_DATA = common.DataDict()

        nth = 1
        c = 0
        for entry, source_paths in self.item_generator():
            if self._interrupt_requested:
                break

            if len(source_paths) == 3:
                p = source_paths[0:3]
            elif len(source_paths) == 4:
                p = source_paths[0:4]

            if len(source_paths) <= 4:
                k = 'default'
            else:
                k = source_paths[4]

            _source_path = '/'.join(source_paths)
            filename = entry.name
            filepath, ext, file_root, _dir, sort_by_name_role = files.get_path_elements(
                filename,
                entry.path,
                _source_path
            )
            flags = basemodel.DEFAULT_ITEM_FLAGS
            seq, sequence_path = files.get_sequence_elements(filepath)

            if (seq and (sequence_path in common.favourites or filepath in common.favourites)) or (
                    filepath in common.favourites):
                flags = flags | common.MarkedAsFavourite

            parent_path_role = source_paths

            if '.' not in filename:
                for idx in range(6):
                    sort_by_name_role[idx] = 'zzzz'

            # Let's limit the maximum number of items we load
            idx = len(data)
            if idx >= common.max_list_items:
                break

            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.SizeHintRole: self.row_size,
                #
                common.QueueRole: self.queues,
                common.DataTypeRole: t,
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
            })

            # If the file in question is a sequence, we will also save a reference
            # to it in the sequence data dict
            if seq:
                # If the sequence has not yet been added to our dictionary
                # of sequences we add it here
                if sequence_path not in SEQUENCE_DATA:  # ... and create it if it doesn't exist
                    sequence_name = sequence_path.split('/')[-1]
                    flags = basemodel.DEFAULT_ITEM_FLAGS

                    if sequence_path in common.favourites:
                        flags = flags | common.MarkedAsFavourite

                    sort_by_name_role = list(sort_by_name_role)
                    sort_by_name_role[7] = sequence_name.lower()

                    SEQUENCE_DATA[sequence_path] = common.DataDict({
                        QtCore.Qt.DisplayRole: sequence_name,
                        QtCore.Qt.EditRole: sequence_name,
                        QtCore.Qt.StatusTipRole: sequence_path,
                        QtCore.Qt.SizeHintRole: self.row_size,
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
                        common.SortBySizeRole: 0,  # Initializing with null-size,
                        common.SortByTypeRole: ext,
                        #
                        common.IdRole: 0,
                        #
                        common.ShotgunLinkedRole: False,
                    })

                SEQUENCE_DATA[sequence_path][common.FramesRole].append(seq.group(2))
                SEQUENCE_DATA[sequence_path][common.EntryRole].append(entry)
            else:
                # Copy the existing file item
                SEQUENCE_DATA[filepath] = common.DataDict(data[idx])
                SEQUENCE_DATA[filepath][common.IdRole] = -1

        # Cast the sequence data back onto the model
        t = common.SequenceItem
        data = common.get_data(__p, __k, t)

        # Casting the sequence data back onto the model
        for idx, v in enumerate(SEQUENCE_DATA.values()):
            if idx >= common.max_list_items:
                break  # Let's limit the maximum number of items we load

            if len(v[common.FramesRole]) == 1:
                # A sequence with only one element is not a sequence
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
                v[QtCore.Qt.StatusTipRole] = filepath
                v[common.TypeRole] = common.FileItem
                v[common.SortByLastModifiedRole] = 0

                flags = basemodel.DEFAULT_ITEM_FLAGS
                if filepath in common.favourites:
                    flags = flags | common.MarkedAsFavourite

                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem

            data[idx] = v
            data[idx][common.IdRole] = idx
            data[idx][common.DataTypeRole] = common.SequenceItem

    def source_path(self):
        """The model's parent folder path segments.

        Returns:
            tuple: A tuple of path segments.

        """
        return common.pseudo_local_bookmark()

    def item_generator(self):
        """We're using the saved keys to find and return the DirEntries
        corresponding to the saved favourites.

        """
        entries = []

        for k in common.favourites:
            file_info = QtCore.QFileInfo(k)
            _path = file_info.path()

            if not QtCore.QFileInfo(_path).exists():
                continue

            source_paths = tuple(f for f in common.favourites[k] if f and f is not 'default')
            for entry in os.scandir(_path):
                path = entry.path.replace('\\', '/')
                if path == k:
                    entries.append((entry, source_paths))
                    continue
                _k = common.proxy_path(path)
                if k == _k:
                    entries.append((entry, source_paths))

        for args in entries:
            yield args

    def task(self):
        return 'favourites'

    def user_settings_key(self):
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

    def toggle_item_flag(self, index, flag, state=None, commit_now=True):
        if flag != common.MarkedAsFavourite:
            return

        super(FavouritesWidget, self).toggle_item_flag(
            index,
            flag,
            state=False,
            commit_now=commit_now
        )

    def dragEnterEvent(self, event):
        if event.source() == self:
            return

        if event.mimeData().hasUrls():
            self.drop_indicator_widget.show()
            return event.accept()
        self.drop_indicator_widget.hide()

    def dragLeaveEvent(self, event):
        self.drop_indicator_widget.hide()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        """Event responsible for adding the dropped file to the favourites."""
        self.drop_indicator_widget.hide()

        if event.source() == self:
            return  # Won't allow dropping an item from itself

        mime = event.mimeData()
        if not mime.hasUrls():
            return

        event.accept()

        for url in mime.urls():
            file_info = QtCore.QFileInfo(url.toLocalFile())

            # Import favourites file
            if file_info.suffix() == common.favorite_file_ext:
                actions.import_favourites(source=file_info.filePath())
                continue

            source = _check_sequence(file_info.filePath())

            # Skip files saved already
            if source in common.favourites:
                continue

            # Add the dropped file with dummy server/job/root values
            actions.add_favourite(
                common.pseudo_local_bookmark(),
                source,
            )

    def get_hint_string(self):
        model = self.model().sourceModel()
        if not model.rowCount():
            return 'You didn\'t save any items yet.'
