"""Editor widget used by :class:`~bookmarks.bookmarker.main.BookmarkerWidget` to add and
select jobs found inside a server.

The module also defines :class:`AddJobWidget`, an editor used to create new jobs inside
a server.

Arguments:
    SECTIONS (dict): UI definitions used by :class:`AddJobWidget`.

"""
import functools
import os

from PySide2 import QtCore, QtGui, QtWidgets

from .. import actions
from .. import common
from .. import contextmenu
from .. import images
from .. import shortcuts
from .. import templates
from .. import ui
from ..editor import base

#: UI layout definition
SECTIONS = {
    0: {
        'name': 'Add Job',
        'icon': '',
        'color': common.color(common.color_dark_background),
        'groups': {
            0: {
                0: {
                    'name': 'Name',
                    'key': None,
                    'validator': base.job_name_validator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Name, e.g. `MY_NEW_JOB`',
                    'description': 'The job\'s name, e.g. `MY_NEW_JOB`.',
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

    path = common.rsc(
        f'{common.GuiResource}/asset_item.{common.thumbnail_format}'
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

        self.jobs = None
        self.setWindowTitle(f'{self.server}: Add Job')

        common.signals.templateExpanded.connect(self.close)
        common.signals.jobAdded.connect(self.close)
        common.signals.serversChanged.connect(self.close)

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        return None

    def init_data(self):
        """Initialize data.

        """
        self.jobs = []
        items = []

        for name, path in self.parent().job_editor.item_generator(self.server,
                                                                  emit_progress=False):
            items.append(name)

        completer = QtWidgets.QCompleter(items, parent=self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_stylesheet(completer.popup())
        self.name_editor.setCompleter(completer)
        self.name_editor.setFocus(QtCore.Qt.MouseFocusReason)

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
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

        return True


class JobContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with :class:`JobItemEditor`.

    """

    def setup(self):
        """Creates the context menu.

        """
        self.add_menu()
        self.separator()
        self.reveal_menu()
        self.separator()
        self.refresh_menu()

    def add_menu(self):
        """Add job item action.

        """
        self.menu['Add Job...'] = {
            'action': self.parent().add,
            'icon': ui.get_icon('add', color=common.color(common.color_green))
        }

    def reveal_menu(self):
        """Reveal job item action.

        """
        self.menu['Reveal...'] = {
            'action': lambda: actions.reveal(
                f'{self.index.data(QtCore.Qt.UserRole)}/.'
            ),
            'icon': ui.get_icon('folder')
        }

    def refresh_menu(self):
        """Refresh job list action.

        """
        self.menu['Refresh'] = {
            'action': self.parent().init_data,
            'icon': ui.get_icon('refresh')
        }


class JobItemEditor(ui.ListViewWidget):
    """Simple list widget used to add and remove servers to/from the local
    common.

    """

    def __init__(self, parent=None):
        super().__init__(
            default_icon='asset',
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
        self.setMinimumWidth(common.size(common.size_width) * 0.2)

        self._connect_signals()
        self._init_shortcuts()

    def _init_shortcuts(self):
        """Initialize shortcuts.

        """
        shortcuts.add_shortcuts(self, shortcuts.BookmarkEditorShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.BookmarkEditorShortcuts
        )
        connect(shortcuts.AddItem, self.add)

    def _connect_signals(self):
        """Connect signals.

        """
        super()._connect_signals()

        self.selectionModel().selectionChanged.connect(
            functools.partial(common.save_selection, self)
        )

        common.signals.bookmarkAdded.connect(self.update_text)
        common.signals.bookmarkRemoved.connect(self.update_text)

        common.signals.jobAdded.connect(self.init_data)
        common.signals.jobAdded.connect(
            lambda v: common.select_index(self, v, role=QtCore.Qt.UserRole)
        )
        common.signals.serversChanged.connect(self.init_data)

    def item_generator(self, source, emit_progress=True):
        """Scans the given source, usually a server, to find job items.

        """
        if emit_progress:
            self.progressUpdate.emit('')

        has_subdir = common.settings.value('settings/jobs_have_clients')
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
                continue

        if emit_progress:
            self.progressUpdate.emit('')

    @QtCore.Slot()
    def init_data(self, *args, **kwargs):
        """Load job item data.

        """
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

            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable
            )

            _name = (
                name.
                replace('_', ' ').
                replace('  ', ' ').
                strip().
                replace('/', '  ｜  ').
                strip().upper()
            )

            item.setData(_name, role=QtCore.Qt.DisplayRole)
            item.setData(path, role=QtCore.Qt.UserRole)
            item.setData(name, role=QtCore.Qt.UserRole + 1)
            item.setData(path, role=QtCore.Qt.StatusTipRole)
            item.setData(path, role=QtCore.Qt.WhatsThisRole)
            item.setData(path, role=QtCore.Qt.ToolTipRole)

            size = QtCore.QSize(0, common.size(common.size_margin) * 2)
            item.setSizeHint(size)

            _icon = get_job_icon(path)
            item.setData(
                _icon if _icon else None,
                role=QtCore.Qt.DecorationRole
            )

            self.addItem(item)

        self.update_text()
        self.progressUpdate.emit('Loading jobs...')

        if selected_name:
            for idx in range(self.model().rowCount()):
                index = self.model().index(idx, 0)
                if index.data(QtCore.Qt.DisplayRole) == selected_name:
                    self.selectionModel().select(
                        index, QtCore.QItemSelectionModel.ClearAndSelect
                    )
                    break

        self.selectionModel().blockSignals(False)

        common.restore_selection(self)
        self.progressUpdate.emit('')

    @QtCore.Slot()
    def update_text(self):
        """Checks each job item to see if they have active bookmark items, and marks
        them visually as active.

        """
        if not self.model():
            return

        active_jobs = set([f['job'] for f in common.bookmarks.values()])
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
                    common.color(common.color_green),
                    role=QtCore.Qt.ForegroundRole
                )
                if suffix not in item.data(QtCore.Qt.DisplayRole):
                    item.setData(
                        f'{item.data(QtCore.Qt.DisplayRole)}{suffix}',
                        role=QtCore.Qt.DisplayRole
                    )
                continue

            item.setData(
                common.color(common.color_text),
                role=QtCore.Qt.ForegroundRole
            )
            name = item.data(QtCore.Qt.DisplayRole).replace(suffix, '')
            item.setData(
                name,
                role=QtCore.Qt.DisplayRole
            )

    @QtCore.Slot()
    def add(self):
        """Opens the widget used to create new job items.

        """
        if not self.window().server():
            return

        widget = AddJobWidget(self.window().server(), parent=self.window())
        widget.open()

    def set_filter(self, v):
        """Set a search filter.

        Args:
            v (str): The search filter.

        """
        self.selectionModel().blockSignals(True)
        self.model().setFilterWildcard(v)
        common.restore_selection(self)
        self.selectionModel().blockSignals(False)

    def keyPressEvent(self, event):
        """Key press event handler.

        """
        if event.key() == QtCore.Qt.Key_Escape:
            self._interrupt_requested = True

    def contextMenuEvent(self, event):
        """Context menu event handler.

        """
        item = self.indexAt(event.pos())
        menu = JobContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()
