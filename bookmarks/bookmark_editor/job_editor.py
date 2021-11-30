# -*- coding: utf-8 -*-
"""Sub-editor widget used by the Bookmark Editor to add and select jobs on on a
server.

"""
import functools
from PySide2 import QtCore, QtGui, QtWidgets
import _scandir

from .. import common
from .. import ui
from .. import images
from .. import contextmenu
from .. import shortcuts
from .. import actions

from .. templates import templates
from .. property_editor import base


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
                    'validator': base.namevalidator,
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
                        templates.TemplatesWidget, templates.JobTemplateMode),
                    'placeholder': None,
                    'description': 'Select a folder template to create this asset.',
                },
            },
        },
    },
}


def get_job_thumbnail(path):
    """Checks the given job folder for the presence of a thumbnail image file.

    """
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return QtGui.QPixmap()

    for entry in _scandir.scandir(file_info.absoluteFilePath()):
        if entry.is_dir():
            continue

        if 'thumbnail' not in entry.name.lower():
            continue

        pixmap = QtGui.QPixmap(entry.path)
        if pixmap.isNull():
            continue
        return pixmap

    return QtGui.QPixmap()


class AddJobWidget(base.BasePropertyEditor):
    """A custom `BasePropertyEditor` used to add new jobs on a server.

    """
    buttons = ('Create', 'Cancel')

    def __init__(self, server, parent=None):
        super().__init__(
            SECTIONS,
            server,
            None,
            None,
            asset=None,
            db_table=None,
            fallback_thumb='folder_sm',
            buttons=self.buttons,
            hide_thumbnail_editor=True,
            parent=parent
        )

        self.setWindowTitle('{}: Add Job'.format(self.server))
        self.setFixedHeight(common.size(common.DefaultHeight) * 0.66)

    def init_data(self):
        items = []
        for entry in _scandir.scandir(self.server):
            if not entry.is_dir():
                continue
            items.append(entry.name)

        completer = QtWidgets.QCompleter(items, parent=self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_custom_stylesheet(completer.popup())
        self.name_editor.setCompleter(completer)

    @common.error
    @common.debug
    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            return super(base.BasePropertyEditor, self).done(result)  # pylint: disable=E1003

        if not self.name_editor.text():
            raise ValueError('Must enter a name to create a job.')

        # Create template and signal
        name = self.name_editor.text()
        self.template_editor.template_list_widget.create(name, self.server)
        path = f'{self.server}/{name}'

        if not QtCore.QFileInfo(path).exists():
            raise RuntimeError('Unknown error, could not find the new job.')

        path += f'/thumbnail.{common.thumbnail_format}'
        self.thumbnail_editor.save_image(destination=path)

        ui.MessageBox(f'{name} was successfully created.').open()

        return super(base.BasePropertyEditor, self).done(result)  # pylint: disable=E1003


class JobContextMenu(contextmenu.BaseContextMenu):
    """Custom context menu used to control the list of saved servers.

    """

    def setup(self):
        self.add_menu()
        self.separator()
        if isinstance(self.index, QtWidgets.QListWidgetItem) and self.index.flags() & QtCore.Qt.ItemIsEnabled:
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
            'action': lambda: actions.reveal(self.index.data(QtCore.Qt.UserRole) + '/.'),
            'icon': ui.get_icon('folder')
        }

    def add_refresh_menu(self):
        self.menu['Refresh'] = {
            'action': (
                functools.partial(self.parent().init_data, reset=False),
                self.parent().restore_current
            ),
            'icon': ui.get_icon('refresh')
        }


class JobListWidget(ui.ListWidget):
    """Simple list widget used to add and remove servers to/from the local
    common.

    Signals:
        jobChanged(server, job):    Emitted when the current job selection changedes.

    """
    jobChanged = QtCore.Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(
            default_message='No jobs found.',
            parent=parent
        )

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
            shortcuts.connect, shortcuts.BookmarkEditorShortcuts)
        connect(shortcuts.AddItem, self.add)

    def _connect_signals(self):
        super()._connect_signals()

        self.selectionModel().selectionChanged.connect(self.save_current)
        self.selectionModel().selectionChanged.connect(self.emit_job_changed)

        common.signals.bookmarkAdded.connect(self.update_status)
        common.signals.bookmarkRemoved.connect(self.update_status)

        common.signals.templateExpanded.connect(lambda: self.init_data(reset=False))
        common.signals.templateExpanded.connect(
            lambda x: self.restore_current(name=QtCore.QFileInfo(x).fileName())
        )

    @QtCore.Slot()
    def update_status(self):
        """Checks each job to see if they have bookmarks added to the current bookmarks.
        If so, we'll mark the item with a checkmark.

        """
        if not self.model():
            return

        jobs = [f[common.JobKey] for f in common.bookmarks.values()]

        for n in range(self.model().rowCount()):
            item = self.item(n)
            if item.data(QtCore.Qt.DisplayRole) in jobs:
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                item.setData(QtCore.Qt.CheckStateRole, QtCore.Qt.Checked)
                return
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsUserCheckable)
            item.setData(QtCore.Qt.CheckStateRole, None)

    @QtCore.Slot(QtCore.QItemSelection)
    @QtCore.Slot(QtCore.QItemSelection)
    def emit_job_changed(self, current, previous):
        index = next((f for f in current.indexes()), QtCore.QModelIndex())
        if not index.isValid():
            self.jobChanged.emit(None, None)
            return
        self.jobChanged.emit(
            self.server,
            index.data(QtCore.Qt.DisplayRole)
        )

    @QtCore.Slot()
    def add(self):
        """Open the widget used to add a new job to the server.

        """
        if not self.server:
            return

        widget = AddJobWidget(self.server, parent=self.window())
        common.signals.templateExpanded.connect(widget.close)
        widget.open()

    @staticmethod
    @QtCore.Slot()
    def save_current(current, previous):
        index = next((f for f in current.indexes()), QtCore.QModelIndex())
        if not index.isValid():
            return
        common.settings.setValue(
            common.UIStateSection,
            common.BookmarkEditorJobKey,
            index.data(QtCore.Qt.DisplayRole)
        )

    @QtCore.Slot()
    def restore_current(self, name=None):
        if name:
            v = name
        else:
            v = common.settings.value(
                common.UIStateSection,
                common.BookmarkEditorJobKey
            )
        if not v:
            return

        for n in range(self.count()):
            if not v == self.item(n).text():
                continue
            index = self.indexFromItem(self.item(n))
            self.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            self.scrollToItem(
                self.item(n), QtWidgets.QAbstractItemView.EnsureVisible)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = JobContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    @QtCore.Slot(str)
    def server_changed(self, server):
        if server is None:
            self.jobChanged.emit(None, None)
            return

        if server == self.server:
            return

        self.server = server
        self.init_data()
        self.restore_current()

    @QtCore.Slot()
    def init_data(self, reset=True):
        if reset:
            self.jobChanged.emit(None, None)

        self.blockSignals(True)
        self.clear()

        if not self.server or not QtCore.QFileInfo(self.server).exists():
            self.blockSignals(False)
            return

        for entry in _scandir.scandir(self.server):
            if not entry.is_dir():
                continue
            file_info = QtCore.QFileInfo(entry.path)
            if file_info.isHidden():
                continue

            item = QtWidgets.QListWidgetItem()
            item.setData(
                QtCore.Qt.DisplayRole,
                entry.name
            )
            item.setData(
                QtCore.Qt.UserRole,
                QtCore.QFileInfo(entry.path).absoluteFilePath()
            )

            size = QtCore.QSize(
                0,
                common.size(common.WidthMargin) * 2
            )
            item.setSizeHint(size)
            self.validate_item(item)
            self.insertItem(self.count(), item)

        self.blockSignals(False)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def validate_item(self, item, emit=False):
        self.blockSignals(True)

        pixmap = get_job_thumbnail(item.data(QtCore.Qt.UserRole))
        if pixmap.isNull():
            pixmap = images.ImageCache.get_rsc_pixmap(
                'icon', common.color(common.BackgroundDarkColor), common.size(common.HeightRow) * 0.8)
            pixmap_selected = images.ImageCache.get_rsc_pixmap(
                'icon', common.color(common.TextSelectedColor), common.size(common.HeightRow) * 0.8)
            pixmap_disabled = images.ImageCache.get_rsc_pixmap(
                'close', common.color(common.RedColor), common.size(common.HeightRow) * 0.8)
        else:
            pixmap_selected = pixmap
            pixmap_disabled = pixmap

        icon = QtGui.QIcon()

        # Let's explicitly check read access by trying to get the
        # files inside the folder
        is_valid = False
        try:
            next(_scandir.scandir(item.data(QtCore.Qt.UserRole)))
            is_valid = True
        except StopIteration:
            is_valid = True
        except OSError:
            is_valid = False

        file_info = QtCore.QFileInfo(item.data(QtCore.Qt.UserRole))
        if (
            file_info.exists() and
            file_info.isReadable() and
            file_info.isWritable() and
            is_valid
        ):
            icon.addPixmap(pixmap, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable
            )
            r = True
        else:
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            item.setFlags(
                QtCore.Qt.NoItemFlags
            )
            r = False

        item.setData(QtCore.Qt.DecorationRole, icon)
        self.blockSignals(False)

        if emit and r:
            index = self.indexFromItem(item)
            self.selectionModel().emitSelectionChanged(
                QtCore.QItemSelection(index, index),
                QtCore.QItemSelection()
            )

        return r
