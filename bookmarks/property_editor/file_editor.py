# -*- coding: utf-8 -*-
"""The module contains the definition of `FileBasePropertyEditor`, the main
widget used by Bookmarks to create versioned template files.

The suggested save destination will be partially dependent on the extension
selected, the current asset config values as well as the active bookmark and
asset items.

File Name
---------

    The final file name is generated from a filename template. The editor
    widgets defined in `file_editor_widgets.py` are used to edit the values
    needed to expand the tokens of in the selected file name template.

    See the `asset_config.py` and `bookmark_editor.py` modules for
    more information.


Example
-------

    .. code-block:: python

            editor = FileBasePropertyEditor(
                server,
                job,
                root,
                asset=asset,
                extension='fbx'
            ).open()

"""
import re
import os
import _scandir

from PySide2 import QtWidgets, QtGui, QtCore

from .. import ui
from .. import common
from .. import database
from .. import actions

from . import base
from . import file_editor_widgets
from ..asset_config import asset_config


instance = None


def close():
    global instance
    if instance is None:
        return
    try:
        instance.close()
        instance.deleteLater()
    except:
        pass
    instance = None


def show(server, job, root, asset, extension=None, file=None, create_file=True, increment=False):
    global instance

    close()
    instance = FileBasePropertyEditor(
        server,
        job,
        root,
        asset,
        extension=extension,
        file=file,
        create_file=create_file,
        increment=increment,
    )
    instance.open()
    return instance


SETTING_KEYS = (
    'task',
    'element',
    # 'version',
    'extension',
    'user',
    'template'
)

INACTIVE_KEYS = (
    'bookmark',
    'asset',
    'task',
    'prefix',
    'element',
    'version',
    'extension',
    'user',
    'template',
)


SECTIONS = {
    0: {
        'name': 'Save File',
        'icon': '',
        'color': common.DARK_BG,
        'groups': {
            0: {
                0: {
                    'name': 'Bookmark',
                    'key': 'bookmark',
                    'validator': None,
                    'widget': file_editor_widgets.BookmarkComboBox,
                    'placeholder': None,
                    'description': 'The current bookmark item.',
                },
                1: {
                    'name': 'Asset',
                    'key': 'asset',
                    'validator': None,
                    'widget': file_editor_widgets.AssetComboBox,
                    'placeholder': None,
                    'description': 'The current asset item.',
                },
                2: {
                    'name': 'Task',
                    'key': 'task',
                    'validator': None,
                    'widget': file_editor_widgets.TaskComboBox,
                    'placeholder': None,
                    'description': 'The current task item.',
                    'button': 'Pick'
                },
            },
            1: {
                0: {
                    'name': 'Description',
                    'key': 'description',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'A short description, eg. \'Compositing files\'',
                    'description': 'A short description of the file\'s contents.\nIndicate significant changes and notes here.',
                },
            },
            2: {
                0: {
                    'name': 'Prefix',
                    'key': 'prefix',
                    'validator': base.textvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Prefix not yet set!',
                    'description': 'A short prefix used to identify the job eg.\'MYB\'.',
                    'button': 'Edit'
                },
                1: {
                    'name': 'Element',
                    'key': 'element',
                    'validator': base.textvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'The element being saved, eg. \'CastleInterior\'',
                    'description': 'The name of the element being saved. Eg., \'ForegroundTower\', or \'BackgroundElements\'',
                },
                2: {
                    'name': 'Version',
                    'key': 'version',
                    'validator': base.versionvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'A version number, eg. \'v001\'',
                    'description': 'A version number with, or without, a preceeding \'v\'. Eg. \'v001\'.',
                    'button': '+',
                    'button2': '-',
                },
                3: {
                    'name': 'User',
                    'key': 'user',
                    'validator': base.textvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Your name, eg. \'JohnDoe\'',
                    'description': 'The name of the current user, eg. \'JohnDoe\', or \'JD\'',
                },
                4: {
                    'name': 'Format',
                    'key': 'extension',
                    'validator': None,
                    'widget': file_editor_widgets.ExtensionComboBox,
                    'placeholder': 'File extension, eg. \'exr\'',
                    'description': 'A file extension, without the leading dot. Eg. \'ma\'',
                },
            },
            3: {
                0: {
                    'name': 'Template',
                    'key': 'template',
                    'validator': base.textvalidator,
                    'widget': file_editor_widgets.TemplateComboBox,
                    'placeholder': 'Custom prefix, eg. \'MYB\'',
                    'description': 'A short name of the bookmark (or job) used when saving files.\n\nEg. \'MYB_sh0010_anim_v001.ma\' where \'MYB\' is the prefix specified here.',
                    'button': 'Edit'
                },
            },
            4: {
                0: {
                    'name': ' ',
                    'key': 'filename',
                    'validator': None,
                    'widget': QtWidgets.QLabel,
                    # 'widget': ui.LineEdit,
                    'placeholder': 'Invalid file name...',
                    'description': 'The file name, based on the current template.',
                    'button': 'Reveal'
                },
            },
        },
    },
}


class FileBasePropertyEditor(base.BasePropertyEditor):
    """The main widget used to create template files.

    """

    def __init__(self, server, job, root, asset, extension=None, file=None, create_file=True, increment=False, parent=None):
        super().__init__(
            SECTIONS,
            server,
            job,
            root,
            asset=asset,
            alignment=QtCore.Qt.AlignLeft,
            fallback_thumb='file',
            db_table=database.AssetTable,
            parent=parent
        )

        self._file = None

        self._increment = increment
        self._create_file = create_file
        self._extension = extension
        self._filelist = {}

        self._file_path = None

        self.update_timer = common.Timer(parent=self)
        self.update_timer.setInterval(10)
        self.update_timer.setSingleShot(False)
        self.update_timer.timeout.connect(self.verify_unique)

        if file is not None:
            self.set_file(file)
            return

        self.update_timer.timeout.connect(self.set_name)
        self.update_timer.timeout.connect(self.set_thumbnail_source)

        # if settings.ACTIVE[settings.TaskKey] is not None:
        #     self.add_task(settings.ACTIVE[settings.TaskKey])

    def file_path(self):
        return self._file_path

    def set_file(self, file):
        self._file = file

        self.version_editor.setText('')

        if not common.is_collapsed(file):
            seq = common.get_sequence(file)
            if seq:
                # Set the version string based on the current file
                v = seq.group(2)
                self.version_editor.setText(v)

                # Increment the version
                file_info = QtCore.QFileInfo(file)
                name = file_info.fileName()

                # Te file exists and we requested an incremented version number
                if self._increment and file_info.exists():
                    v = self.increment_version(
                        v, self.parent_folder(), name, max, 1)
                    self.version_editor.setText(v)
                    file = seq.group(1) + v + seq.group(3) + \
                        '.' + seq.group(4)
            else:
                self.version_editor.setText('')

        else:
            # The item is collapsed
            file = common.proxy_path(file)

        self._file = file

        self.thumbnail_editor.source = file
        self.thumbnail_editor.update()

        for k in INACTIVE_KEYS:
            if not hasattr(self, k + '_editor'):
                continue
            editor = getattr(self, k + '_editor')
            editor.parent().setDisabled(True)
            editor.parent().parent().setHidden(True)

        self.filename_editor.setText(QtCore.QFileInfo(file).fileName())

    def _connect_signals(self):
        super(FileBasePropertyEditor, self)._connect_signals()
        self._connect_settings_save_signals(SETTING_KEYS)

    def name(self):
        return self.filename_editor.text()

    @QtCore.Slot()
    def set_name(self):
        """Slot connected to the update timer used to preview the current
        file name.

        """
        bookmark = '/'.join((self.server, self.job, self.root))
        asset_root = '/'.join((self.server, self.job, self.root, self.asset))

        template = self.template_editor.currentData(QtCore.Qt.UserRole)
        config = asset_config.get(self.server, self.job, self.root)

        def _strip(s):
            return (
                s.
                strip('-').
                strip('_').
                strip().
                replace('__', '_').
                replace('_.', '.')
            )

        def _get(k):
            if not hasattr(self, k + '_editor'):
                return ''
            editor = getattr(self, k + '_editor')
            if hasattr(editor, 'currentText'):
                v = editor.currentText()
            elif hasattr(editor, 'text'):
                v = editor.text()
            else:
                v = ''

            return _strip(v)

        # Get generic shot and sequence numbers from the current asset name
        match = re.match(
            r'.*(?:SQ|SEQ|SEQUENCE)([0-9]+).*',
            self.parent_folder(),
            re.IGNORECASE
        )
        seq = match.group(1) if match else '###'
        match = re.match(
            r'.*(?:SH|SHOT)([0-9]+).*',
            self.parent_folder(),
            re.IGNORECASE
        )
        shot = match.group(1) if match else '###'

        v = config.expand_tokens(
            template,
            asset_root=asset_root,
            bookmark=bookmark,
            asset=_get('asset'),
            user=_get('user'),
            version=_get('version').lower(),
            task=_get('task'),
            mode=_get('task'),
            element=_get('element'),
            seq=seq,
            shot=shot,
            sequence=seq,
            project=self.job,
            ext=_get('extension').lower()
        )
        v = _strip(v)
        v = v.replace(
            '{invalid_token}', '<span style="color:{}">{{invalid_token}}</span>'.format(common.rgb(common.RED)))

        self.filename_editor.setText(v)

    @QtCore.Slot()
    def verify_unique(self):
        """Checks if the proposed file name exists already, and if does,
        makes the output file name red.

        """
        if self.db_source() not in self._filelist:
            file_info = QtCore.QFileInfo(self.db_source())
            self._filelist[self.db_source()] = file_info.exists()

        if self._filelist[self.db_source()]:
            self.filename_editor.setStyleSheet(
                'color:{};'.format(common.rgb(common.RED)))
        else:
            self.filename_editor.setStyleSheet(
                'color:{};'.format(common.rgb(common.GREEN)))

    def parent_folder(self):
        """The folder where the new file is about to be saved.

        """
        if self._file:
            return QtCore.QFileInfo(self._file).dir().path()

        folder = self.task_editor.currentData(QtCore.Qt.UserRole)
        if not folder:
            return None
        return '/'.join((self.server, self.job, self.root, self.asset, folder))

    def db_source(self):
        """The final file path."""
        if self._file:
            if common.is_collapsed(self._file):
                return common.proxy_path(self._file)
            return self._file

        if not self.parent_folder():
            return None
        return self.parent_folder() + '/' + self.name()

    @common.error
    @common.debug
    def init_data(self):
        """Initialises values of each editor.

        Some values are retrieved by the context the widget was called in, and
        some are loaded from the user settings if the user saved a custom value
        previously.

        """
        if all((self.server, self.job, self.root)):
            bookmark = '/'.join((self.server, self.job, self.root))
            self.bookmark_editor.setCurrentText(bookmark)
        if self.asset:
            self.asset_editor.setCurrentText(self.asset)

        self.user_editor.blockSignals(True)
        if self._file is not None:
            self.user_editor.setText('-')
        else:
            self.user_editor.setText(common.get_username())
        self.user_editor.blockSignals(False)

        # Load previously set values from the user settings file
        if self._file is None:
            self.load_saved_user_settings(SETTING_KEYS)

        # Prefix
        self.prefix_editor.setReadOnly(True)
        if self._file is None:
            db = database.get_db(self.server, self.job, self.root)
            prefix = db.value(
                db.source(),
                'prefix',
                table=database.BookmarkTable
            )
            if prefix:
                self.prefix_editor.setText(prefix)

        if self._extension and self._file is None:
            self.extension_editor.setCurrentText(self._extension.upper())
            self.extension_editor.setDisabled(True)

            self.task_editor.blockSignals(True)
            self.update_tasks(self._extension)
            self.task_editor.blockSignals(False)

            if self.task_editor.findText(self._extension.upper()) > 0:
                self.task_editor.blockSignals(True)
                self.task_editor.setCurrentText(self._extension.upper())
                self.task_editor.blockSignals(False)

        # Description
        if self._file is not None:
            db = database.get_db(self.server, self.job, self.root)
            v = db.value(
                self.db_source(),
                'description',
                table=database.AssetTable
            )
            v = v if v else ''
            self.description_editor.setText(v)
            self.description_editor.setFocus()
            return

        # Increment the version if the source already exists
        self.set_name()

        # Set a default the version string if not set previously
        if not self.version_editor.text():
            self.version_editor.setText('v001')

        # Increment the version by one if the file already exists
        if QtCore.QFileInfo(self.db_source()).exists():
            v = self.version_editor.text()
            v = self.increment_version(
                v, self.parent_folder(), self.name(), max, 1)
            self.version_editor.setText(v)

        self.update_timer.start()

    @QtCore.Slot(str)
    def update_tasks(self, ext):
        """Update the available task folder options based on the given file extension.

        """
        ext = ext.lower()
        config = asset_config.get(self.server, self.job, self.root)

        if ext in config.get_extensions(asset_config.CacheFormat):
            self.task_editor.set_mode(file_editor_widgets.CacheMode)
        elif ext in config.get_extensions(asset_config.SceneFormat):
            self.task_editor.set_mode(file_editor_widgets.SceneMode)
        else:
            self.task_editor.set_mode(file_editor_widgets.NoMode)

    def exec_(self):
        result = super(FileBasePropertyEditor, self).exec_()
        if result == QtWidgets.QDialog.Rejected:
            return QtWidgets.QDialog.Rejected
        if result == QtWidgets.QDialog.Accepted:
            return self._file_path
        return None

    @common.error
    @common.debug
    def save_changes(self):
        """Creates a new empty file or updates and existing item.

        """
        self.create_file()
        self.save_changed_data_to_db()
        self.thumbnail_editor.save_image()
        self.thumbnailUpdated.emit(self.db_source())
        self.itemUpdated.emit(self.db_source())
        self._file_path = self.db_source()
        return True

    def create_file(self):
        """Creates a new file on the disk.

        """
        if not self._create_file:
            return

        if not self.parent_folder():
            raise RuntimeError('Invalid parent folder')

        _dir = self.parent_folder()

        name = self.name()
        if not name or not _dir or '{invalid_token}' in name:
            raise RuntimeError('Invalid token in output name')

        _dir = QtCore.QDir(_dir)
        if not _dir.mkpath('.'):
            raise RuntimeError('Could name create folder.')

        file_info = QtCore.QFileInfo(self.db_source())
        if file_info.exists():
            raise RuntimeError(
                '{} already exists. Try incrementing the version number.'.format(name))

        path = file_info.absoluteFilePath()
        open(os.path.normpath(path), 'a').close()
        self.itemCreated.emit(path)

    @QtCore.Slot()
    def task_button_clicked(self):
        """Lets the user select a custom save destination.

        The selection has to be inside the currently seleted asset, otherwise
        will be rejected. If the folder is not part of the current available
        options, it will be added as a new option.

        """
        source = '/'.join((self.server, self.job, self.root, self.asset))
        _dir = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption='Select a folder...',
            dir=source,
            options=QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks | QtWidgets.QFileDialog.DontUseCustomDirectoryIcons
        )
        if not _dir:
            return

        if source not in _dir:
            ui.ErrorBox(
                'Invalid selection',
                'Make sure to select a folder inside the current asset.'
            ).open()
            return

        relative_path = _dir.replace(source, '').strip('/')
        self.add_task(relative_path)

    def add_task(self, relative_path):
        """Adds a task folder to the folder editor.

        """
        for n in range(self.task_editor.count()):
            v = self.task_editor.itemData(n, role=QtCore.Qt.UserRole)
            if v == relative_path:
                self.task_editor.setCurrentIndex(n)
                return

        self.task_editor.model().add_item(relative_path)
        self.task_editor.blockSignals(True)
        self.task_editor.setCurrentIndex(self.task_editor.count() - 1)
        self.task_editor.blockSignals(False)

    @QtCore.Slot()
    def filename_button_clicked(self):
        """Used to reveal the parent folder in the file explorer.

        """
        if self._file is not None:
            actions.reveal(self._file)
            return

        if not self.parent_folder():
            return

        _dir = QtCore.QDir(self.parent_folder())

        if not _dir.exists():
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setWindowTitle('Folder does not yet exist')
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setText('Destination folder does not exist.')
            mbox.setInformativeText(
                'The destination folder does not yet exist. Do you want to create it now?')
            button = mbox.addButton(
                'Create folder', QtWidgets.QMessageBox.AcceptRole)
            mbox.setDefaultButton(button)
            mbox.addButton('Cancel', QtWidgets.QMessageBox.RejectRole)

            if mbox.exec_() == QtWidgets.QMessageBox.RejectRole:
                return
            if not _dir.mkpath('.'):
                ui.ErrorBox(
                    'Could not create destination folder.').open()
                return

        actions.reveal(_dir.path())

    @QtCore.Slot()
    def prefix_button_clicked(self):
        editor = file_editor_widgets.PrefixEditor(parent=self)
        editor.open()

    @QtCore.Slot()
    def version_button_clicked(self):
        """Increments the version number by one.

        """
        v = self.version_editor.text()
        v = self.increment_version(
            v, self.parent_folder(), self.name(), max, 1)
        self.version_editor.setText(v)

    @QtCore.Slot()
    def version_button2_clicked(self):
        """Decrements the version number by one.

        """
        v = self.version_editor.text()
        v = self.increment_version(
            v, self.parent_folder(), self.name(), min, -1)
        self.version_editor.setText(v)

    def increment_version(self, v, dir, name, func, increment):
        """Increments the version number by one or to the smallest/largest
        available version number based on existing files found in the
        destination folder.

        """
        if not v:
            v = 'v001'

        prefix = 'v' if v.startswith('v') else ''
        padding = len(v.replace('v', ''))
        try:
            n = int(v.replace('v', ''))
        except:
            return 'v001'

        if not dir:
            return 'v001'
        _dir = QtCore.QDir(dir)

        if not _dir.exists():
            # We can freely increment the version number as there won't be any conflicts
            n += increment
            if n < 0:
                n = 0
            if n > 999:
                n = 999
            return '{}{}'.format(prefix, '{}'.format(n).zfill(padding))

        # Let's scan the destination directory for existing versions to make
        # sure we're only suggesting valid versions
        if v not in name:
            return 'v001'
        idx = name.index(v)

        _arr = []
        for entry in _scandir.scandir(_dir.path()):
            if len(name) != len(entry.name):
                continue
            if name[:idx] != entry.name[:idx]:
                continue

            _v = entry.name[idx:idx + len(v)]
            _prefix = 'v' if _v.startswith('v') else ''
            _padding = len(_v.replace('v', ''))
            try:
                _n = int(_v.replace('v', ''))
            except ValueError:
                continue
            _arr.append(_n)

        if not _arr:
            n += increment
            if n < 0:
                n = 0
            if n > 999:
                n = 999
            return '{}{}'.format(prefix, '{}'.format(n).zfill(padding))

        _n = func(_arr)
        _n += increment

        if func is max and _n <= n:
            _n = n + increment
        if func is min and _n >= n:
            _n = n + increment
        if _n < 0:
            _n = 0
        if _n > 999:
            _n = 999

        return '{}{}'.format(_prefix, '{}'.format(_n).zfill(_padding))
