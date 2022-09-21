# -*- coding: utf-8 -*-
"""Sub-editor widget used by
:class:`bookmarks.bookmark_editor.bookmark_editor_widget.BookmarkEditorWidget`
to add and select jobs a server.

"""
import functools
import os

from PySide2 import QtCore, QtGui, QtWidgets

from .. import actions
from .. import common
from .. import contextmenu
from .. import shortcuts
from .. import templates
from .. import ui
from .. import images
from ..editor import base

SECTIONS = {
    0: {
        'name': 'Add Job',
        'icon': '',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'Name',
                    'key': None,
                    'validator': base.jobnamevalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Name, eg. `MY_NEW_JOB`',
                    'description': 'The job\'s name, eg. `MY_NEW_JOB`.',
                },
            },
            1: {
                0: {
                    'name': 'Template',
                    'key': None,
                    'validator': None,
                    'widget': functools.partial(
                        templates.TemplatesWidget, templates.JobTemplateMode
                    ),
                    'placeholder': None,
                    'description': 'Select a folder template to create this asset.',
                },
            },
        },
    },
}


def get_job_icon(path):
    """Checks the given job folder for the presence of a thumbnail image file.

    """
    for entry in os.scandir(path):
        if 'thumbnail' not in entry.name.lower():
            continue
        pixmap = images.ImageCache.get_pixmap(
            QtCore.QFileInfo(entry.path).filePath(),
            common.thumbnail_size
        )
        if not pixmap or pixmap.isNull():
            continue
        return QtGui.QIcon(pixmap)

    path = common.get_rsc(
        f'{common.GuiResource}/placeholder.{common.thumbnail_format}'
    )
    pixmap = images.ImageCache.get_pixmap(path, common.thumbnail_size)
    return QtGui.QIcon(pixmap)


class AddJobWidget(base.BasePropertyEditor):
    """A custom `BasePropertyEditor` used to add new jobs on a server.

    """
    buttons = ('Create Job', 'Cancel')

    def __init__(self, server, parent=None):
        super().__init__(
            SECTIONS,
            server,
            None,
            None,
            asset=None,
            db_table=None,
            buttons=self.buttons,
            parent=parent
        )

        self.setWindowTitle(f'{self.server}: Add Job')
        self.setFixedHeight(common.size(common.DefaultHeight) * 0.66)

        common.signals.templateExpanded.connect(self.close)
        common.signals.jobAdded.connect(self.close)

    def init_data(self):
        items = []

        for name, path in self.parent().job_editor.item_generator(self.server, emit_progress=False):
            items.append(name)

        completer = QtWidgets.QCompleter(items, parent=self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_stylesheet(completer.popup())
        self.name_editor.setCompleter(completer)
        self.name_editor.setFocus(QtCore.Qt.MouseFocusReason)

    @common.error
    @common.debug
    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            return super(base.BasePropertyEditor, self).done(
                result
            )  # pylint: disable=E1003

        if not self.name_editor.text():
            raise ValueError('Must enter a name to create a job.')

        root = self.server

        name = self.name_editor.text()
        if not name:
            raise ValueError('Must enter a name to create job')
        name = name.replace('\\', '/')

        if '/' in name:
            _name = name.split('/')[-1]
            _root = name[:-len(_name) - 1]
            name = _name
            root = f'{self.server}/{_root}'

            if not QtCore.QFileInfo(root).exists():
                if not QtCore.QDir(root).mkpath('.'):
                    raise RuntimeError('Error creating folders.')

        # Create template and signal
        self.template_editor.template_list_widget.create(name, root)
        path = f'{root}/{name}'

        if not QtCore.QFileInfo(path).exists():
            raise RuntimeError('Could not find the added job.')

        try:
            path += f'/thumbnail.{common.thumbnail_format}'
            self.thumbnail_editor.save_image(destination=path)
        except:
            pass

        common.signals.jobAdded.emit(path)
        ui.MessageBox(f'{name} was successfully created.').open()

        return super().done(result)


class JobContextMenu(contextmenu.BaseContextMenu):
    """Custom context menu used to control the list of saved servers.

    """

    def setup(self):
        self.add_menu()
        self.separator()
        self.reveal_menu()
        self.separator()
        self.refresh_menu()

    def add_menu(self):
        self.menu['Add Job...'] = {
            'action': self.parent().add,
            'icon': ui.get_icon('add', color=common.color(common.GreenColor))
        }

    def reveal_menu(self):
        self.menu['Reveal...'] = {
            'action': lambda: actions.reveal(
                self.index.data(QtCore.Qt.UserRole) + '/.'
            ),
            'icon': ui.get_icon('folder')
        }

    def refresh_menu(self):
        self.menu['Refresh'] = {
            'action': self.parent().init_data,
            'icon': ui.get_icon('refresh')
        }


class JobListWidget(ui.ListViewWidget):
    """Simple list widget used to add and remove servers to/from the local
    common.

    """

    def __init__(self, parent=None):
        super().__init__(
            default_message='No jobs found.',
            parent=parent
        )

        self._interrupt_requested = False

        self.setWindowTitle('Job Editor')
        self.setObjectName('JobEditor')

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.setMinimumWidth(common.size(common.DefaultWidth) * 0.2)

        self._connect_signals()
        self.init_shortcuts()

    def init_shortcuts(self):
        shortcuts.add_shortcuts(self, shortcuts.BookmarkEditorShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.BookmarkEditorShortcuts
        )
        connect(shortcuts.AddItem, self.add)

    def _connect_signals(self):
        super()._connect_signals()

        self.selectionModel().selectionChanged.connect(
            functools.partial(
                common.save_selection,
                self,
                common.BookmarkEditorJobKey
            )
        )

        common.signals.bookmarkAdded.connect(self.update_text)
        common.signals.bookmarkRemoved.connect(self.update_text)

        common.signals.jobAdded.connect(self.init_data)
        common.signals.jobAdded.connect(
            lambda v: common.select_index(self, v, role=QtCore.Qt.UserRole)
        )

    def item_generator(self, source, emit_progress=True):
        if emit_progress:
            self.progressUpdate.emit('')

        has_subdir = common.settings.value(
            common.SettingsSection, common.JobsHaveSubdirs
        )
        has_subdir = QtCore.Qt.Unchecked if has_subdir is None else \
            QtCore.Qt.CheckState(
                has_subdir
            )
        has_subdir = has_subdir == QtCore.Qt.Checked

        for client_entry in os.scandir(source):
            if self._interrupt_requested:
                if emit_progress:
                    self.progressUpdate.emit('')
                return

            if not client_entry.is_dir():
                continue

            file_info = QtCore.QFileInfo(client_entry.path)
            if emit_progress:
                self.progressUpdate.emit(f'Scanning:  {file_info.filePath()}')

            if file_info.isHidden():
                continue
            if not file_info.isReadable():
                continue
            try:
                next(os.scandir(file_info.filePath()))
            except:
                continue

            if not has_subdir:
                yield client_entry.name, file_info.filePath()
                continue

            for job_entry in os.scandir(client_entry.path):
                if self._interrupt_requested:
                    if emit_progress:
                        self.progressUpdate.emit('')
                    return

                if not job_entry.is_dir():
                    continue

                file_info = QtCore.QFileInfo(job_entry.path)
                if emit_progress:
                    self.progressUpdate.emit(f'Scanning:  {file_info.filePath()}')

                if file_info.isHidden():
                    continue
                if not file_info.isReadable():
                    continue
                try:
                    next(os.scandir(file_info.filePath()))
                except:
                    continue
                yield f'{client_entry.name}/{job_entry.name}', file_info.filePath()

        if emit_progress:
            self.progressUpdate.emit('')

    @QtCore.Slot()
    def init_data(self, *args, **kwargs):
        selected_index = common.get_selected_index(self)
        selected_name = selected_index.data(
            QtCore.Qt.DisplayRole
        ) if selected_index.isValid() else None

        self.selectionModel().blockSignals(True)

        self.model().sourceModel().clear()
        self._interrupt_requested = False

        if (
                not self.window().server() or
                not QtCore.QFileInfo(self.window().server()).exists()
        ):
            self.selectionModel().blockSignals(False)
            return

        for name, path in self.item_generator(self.window().server()):
            item = QtGui.QStandardItem()

            _name = (
                name.
                    replace('_', ' ').
                    replace('  ', ' ').
                    strip().
                    replace('/', '  |  ').
                    strip().upper()
            )

            item.setData(_name, role=QtCore.Qt.DisplayRole)
            item.setData(path, role=QtCore.Qt.UserRole)
            item.setData(name, role=QtCore.Qt.UserRole + 1)

            size = QtCore.QSize(0, common.size(common.WidthMargin) * 2)
            item.setSizeHint(size)

            _icon = get_job_icon(path)
            item.setData(
                _icon if _icon else None,
                role=QtCore.Qt.DecorationRole
            )

            self.addItem(item)

        self.update_text()
        self.progressUpdate.emit('Loading bookmarks...')

        if selected_name:
            for idx in range(self.model().rowCount()):
                index = self.model().index(idx, 0)
                if index.data(QtCore.Qt.DisplayRole) == selected_name:
                    self.selectionModel().select(
                        index, QtCore.QItemSelectionModel.ClearAndSelect
                    )
                    break

        self.selectionModel().blockSignals(False)

        common.restore_selection(self, common.BookmarkEditorJobKey)
        self.progressUpdate.emit('')

    @QtCore.Slot()
    def update_text(self):
        """Checks each job to see if they have active bookmark items, and marks them
        visually as active.

        """
        if not self.model():
            return

        active_jobs = set([f[common.JobKey] for f in common.bookmarks.values()])
        suffix = ' (Active)'

        for n in range(self.model().rowCount()):
            index = self.model().index(n, 0)
            if not index.isValid():
                continue
            source_index = self.model().mapToSource(index)
            if not source_index.isValid():
                continue
            item = self.model().sourceModel().itemFromIndex(source_index)
            if not item:
                continue

            if item.data(QtCore.Qt.UserRole + 1) in active_jobs:
                item.setData(
                    common.color(common.GreenColor),
                    role=QtCore.Qt.ForegroundRole
                )
                if suffix not in item.data(QtCore.Qt.DisplayRole):
                    item.setData(
                        f'{item.data(QtCore.Qt.DisplayRole)}{suffix}',
                        role=QtCore.Qt.DisplayRole
                    )
                continue

            item.setData(
                common.color(common.TextColor),
                role=QtCore.Qt.ForegroundRole
            )
            name = item.data(QtCore.Qt.DisplayRole).replace(suffix, '')
            item.setData(
                name,
                role=QtCore.Qt.DisplayRole
            )

    @QtCore.Slot()
    def add(self):
        """Open the widget used to add a new job to the server.

        """
        if not self.window().server():
            return

        widget = AddJobWidget(self.window().server(), parent=self.window())
        widget.open()

    def set_filter(self, v):
        self.selectionModel().blockSignals(True)
        self.model().setFilterWildcard(v)
        common.restore_selection(self, common.BookmarkEditorJobKey)
        self.selectionModel().blockSignals(False)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self._interrupt_requested = True

    def contextMenuEvent(self, event):
        item = self.indexAt(event.pos())
        menu = JobContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()
