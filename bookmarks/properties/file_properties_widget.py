# -*- coding: utf-8 -*-
"""The module contains the definition of `FilePropertiesWidget`, the main
widget used by Bookmarks to add template files.

The suggested save destination will be partially dependent on the extension
selected, the current asset config values as well as the active bookmark and
asset items.

File Name
---------

    The editor widgets defined in `file_properties.widget.py` are used to edit
    values needed to expand the tokens of in the file name
    templates. See the `asset_config.py` and `bookmark_properties_widget.py`
    modules for more information.


Example
-------

    .. code-block:: python

            editor = FilePropertiesWidget(
                server,
                job,
                root,
                asset=asset,
                extension=u'fbx'
            ).open()

"""
import re
import os
import functools
import _scandir

from PySide2 import QtWidgets, QtGui, QtCore

from .. import ui
from .. import common
from .. import settings
from .. import bookmark_db
from .. import log
from .. import actions

from . import base
from . import asset_config
from . import file_properties_widgets


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
    instance = FilePropertiesWidget(
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


LOCAL_KEYS = (
    u'folder',
    u'element',
    u'version',
    u'extension',
    u'user',
    u'template'
)

INACTIVE_KEYS = (
    u'bookmark',
    u'asset',
    u'folder',
    u'prefix',
    u'element',
    u'version',
    u'extension',
    u'user',
    u'template',
)


SECTIONS = {
    0: {
        'name': u'Save File',
        'icon': u'',
        'color': common.DARK_BG,
        'groups': {
            0: {
                0: {
                    'name': u'Bookmark',
                    'key': u'bookmark',
                    'validator': None,
                    'widget': file_properties_widgets.BookmarkComboBox,
                    'placeholder': None,
                    'description': u'The job\'s name, eg. \'MY_NEW_JOB\'.',
                },
                1: {
                    'name': u'Asset',
                    'key': u'asset',
                    'validator': None,
                    'widget': file_properties_widgets.AssetComboBox,
                    'placeholder': None,
                    'description': u'The job\'s name, eg. \'MY_NEW_JOB\'.',
                },
                2: {
                    'name': u'Task',
                    'key': u'folder',
                    'validator': None,
                    'widget': file_properties_widgets.TaskComboBox,
                    'placeholder': None,
                    'description': u'The job\'s name, eg. \'MY_NEW_JOB\'.',
                    'button': 'Pick'
                },
            },
            1: {
                0: {
                    'name': u'Description',
                    'key': 'description',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': u'A short description, eg. \'My animation re-take\'',
                    'description': u'A short description of the file\'s contents.\nIndicate significant changes and notes here.',
                },
            },
            2: {
                0: {
                    'name': u'Prefix',
                    'key': 'prefix',
                    'validator': base.textvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': u'Prefix not yet set!',
                    'description': u'A short prefix used to identify the job eg.\'MYB\'.',
                    'button': u'Edit'
                },
                1: {
                    'name': u'Element',
                    'key': 'element',
                    'validator': base.textvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': u'Element being saved, eg. \'Tower\'',
                    'description': u'The name of the element being saved. Eg., \'ForegroundTower\', or \'Precomp\'',
                },
                2: {
                    'name': u'Version',
                    'key': 'version',
                    'validator': base.versionvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': u'A version number, eg. \'v001\'',
                    'description': u'A version number with, or without, a preceeding \'v\'. Eg. \'v001\'.',
                    'button': u'+',
                    'button2': u'-',
                },
                3: {
                    'name': u'User',
                    'key': 'user',
                    'validator': base.textvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': u'Your name, eg. \'JohnDoe\'',
                    'description': u'The name of the current user, eg. \'JohnDoe\', or \'JD\'',
                },
                4: {
                    'name': u'Format',
                    'key': 'extension',
                    'validator': None,
                    'widget': file_properties_widgets.ExtensionComboBox,
                    'placeholder': u'File extension, eg. \'exr\'',
                    'description': u'A file extension, without the leading dot. Eg. \'ma\'',
                },
            },
            3: {
                0: {
                    'name': u'Template',
                    'key': 'template',
                    'validator': base.textvalidator,
                    'widget': file_properties_widgets.TemplateComboBox,
                    'placeholder': u'Custom prefix, eg. \'MYB\'',
                    'description': u'A short name of the bookmark (or job) used when saving files.\n\nEg. \'MYB_sh0010_anim_v001.ma\' where \'MYB\' is the prefix specified here.',
                    'button': u'Edit'
                },
            },
            4: {
                0: {
                    'name': u' ',
                    'key': u'filename',
                    'validator': None,
                    'widget': QtWidgets.QLabel,
                    # 'widget': ui.LineEdit,
                    'placeholder': u'Invalid file name...',
                    'description': u'The file name, based on the current template.',
                    'button': 'Reveal'
                },
            },
        },
    },
}


class FilePropertiesWidget(base.PropertiesWidget):
    """The widget used to create file name template compliant files.

    """

    def __init__(self, server, job, root, asset, extension=None, file=None, create_file=True, increment=False, parent=None):
        super(FilePropertiesWidget, self).__init__(
            SECTIONS,
            server,
            job,
            root,
            asset=asset,
            alignment=QtCore.Qt.AlignLeft,
            fallback_thumb=u'file_sm',
            db_table=bookmark_db.AssetTable,
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

        if settings.ACTIVE[settings.TaskKey] is not None:
            self.add_task(settings.ACTIVE[settings.TaskKey])

    def file_path(self):
        return self._file_path

    def set_file(self, file):
        self._file = file

        self.version_editor.setText(u'')

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
                        u'.' + seq.group(4)
            else:
                self.version_editor.setText(u'')

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

    def _connect(self, k):
        if not hasattr(self, k + '_editor'):
            return
        editor = getattr(self, k + '_editor')
        if hasattr(editor, 'currentTextChanged'):
            signal = getattr(editor, 'currentTextChanged')
        elif hasattr(editor, 'textChanged'):
            signal = getattr(editor, 'textChanged')
        else:
            return
        signal.connect(functools.partial(self.save_local_value, k))

    def _connect_signals(self):
        super(FilePropertiesWidget, self)._connect_signals()

        for k in LOCAL_KEYS:
            self._connect(k)

    def name(self):
        return self.filename_editor.text()

    @QtCore.Slot()
    def set_name(self):
        """Slot connected to the update timer used to preview the current
        file name.

        """
        bookmark = u'/'.join((self.server, self.job, self.root))
        asset_root = u'/'.join((self.server, self.job, self.root, self.asset))

        template = self.template_editor.currentData(QtCore.Qt.UserRole)
        config = asset_config.get(self.server, self.job, self.root)

        def _strip(s):
            return (
                s.
                strip(u'-').
                strip(u'_').
                strip().
                replace(u'__', u'_').
                replace(u'_.', u'.')
            )

        def _get(k):
            if not hasattr(self, k + '_editor'):
                return u''
            editor = getattr(self, k + '_editor')
            if hasattr(editor, 'currentText'):
                v = editor.currentText()
            elif hasattr(editor, 'text'):
                v = editor.text()
            else:
                v = u''

            return _strip(v)

        # Get generic shot and sequence numbers from the current asset name
        match = re.match(
            ur'.*(?:SQ|SEQ|SEQUENCE)([0-9]+).*',
            self.parent_folder(),
            re.IGNORECASE
        )
        seq = match.group(1) if match else u'###'
        match = re.match(
            ur'.*(?:SH|SHOT)([0-9]+).*',
            self.parent_folder(),
            re.IGNORECASE
        )
        shot = match.group(1) if match else u'###'

        v = config.expand_tokens(
            template,
            asset_root=asset_root,
            bookmark=bookmark,
            asset=_get('asset'),
            user=_get('user'),
            version=_get('version').lower(),
            task=_get('folder'),
            mode=_get('folder'),
            element=_get('element'),
            seq=seq,
            shot=shot,
            sequence=seq,
            project=self.job,
            ext=_get('extension').lower()
        )
        v = _strip(v)
        v = v.replace(
            u'{invalid_token}', u'<span style="color:{}">{{invalid_token}}</span>'.format(common.rgb(common.RED)))

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
                u'color:{};'.format(common.rgb(common.RED)))
        else:
            self.filename_editor.setStyleSheet(
                u'color:{};'.format(common.rgb(common.GREEN)))

    def parent_folder(self):
        """The folder where the new file is about to be saved.

        """
        if self._file:
            return QtCore.QFileInfo(self._file).dir().path()

        folder = self.folder_editor.currentData(QtCore.Qt.UserRole)
        if not folder:
            return None
        return u'/'.join((self.server, self.job, self.root, self.asset, folder))

    def db_source(self):
        """The final file path."""
        if self._file:
            if common.is_collapsed(self._file):
                return common.proxy_path(self._file)
            return self._file

        if not self.parent_folder():
            return None
        return self.parent_folder() + u'/' + self.name()

    def _set_local_value(self, k):
        v = settings.instance().value(
            settings.CurrentUserPicksSection,
            k
        )
        if not isinstance(v, unicode):
            return
        if not v:
            return
        if not hasattr(self, k + '_editor'):
            return
        editor = getattr(self, k + '_editor')
        if hasattr(editor, 'setCurrentText'):
            editor.blockSignals(True)
            editor.setCurrentText(v)
            editor.blockSignals(False)
        elif hasattr(editor, u'setText'):
            editor.blockSignals(True)
            editor.setText(v)
            editor.blockSignals(False)
        else:
            return

    @common.error
    @common.debug
    def init_data(self):
        """Initialises the default values of each editor.

        Some values are retrieved by the context the widget was called, and some
        are loaded from `local_settings` if the user has set a custom value
        previously.

        """
        if all((self.server, self.job, self.root)):
            bookmark = u'/'.join((self.server, self.job, self.root))
            self.bookmark_editor.setCurrentText(bookmark)
        if self.asset:
            self.asset_editor.setCurrentText(self.asset)

        self.user_editor.blockSignals(True)
        if self._file is not None:
            self.user_editor.setText(u'-')
        else:
            self.user_editor.setText(common.get_username())
        self.user_editor.blockSignals(False)

        if self._file is None:
            for k in LOCAL_KEYS:
                self._set_local_value(k)

        # Prefix
        self.prefix_editor.setReadOnly(True)
        if self._file is None:
            with bookmark_db.transactions(self.server, self.job, self.root) as db:
                prefix = db.value(
                    db.source(),
                    u'prefix',
                    table=bookmark_db.BookmarkTable
                )
            if prefix:
                self.prefix_editor.setText(prefix)

        if self._extension and self._file is None:
            self.extension_editor.setCurrentText(self._extension.upper())
            self.extension_editor.setDisabled(True)
            self.update_tasks(self._extension)

            if self.folder_editor.findText(self._extension.upper()) > 0:
                self.folder_editor.blockSignals(True)
                self.folder_editor.setCurrentText(self._extension.upper())
                self.folder_editor.blockSignals(False)

        # Description
        if self._file is not None:
            with bookmark_db.transactions(self.server, self.job, self.root) as db:
                v = db.value(
                    self.db_source(),
                    u'description',
                    table=bookmark_db.AssetTable
                )
            v = v if v else u''
            self.description_editor.setText(v)
            self.description_editor.setFocus()
            return

        # Increment the version if the source already exists
        self.set_name()

        # Set the version string
        # We'll increment the version by one if the file already exists
        if not self.version_editor.text():
            self.version_editor.setText(u'v001')
        if QtCore.QFileInfo(self.db_source()).exists():
            v = self.version_editor.text()
            v = self.increment_version(
                v, self.parent_folder(), self.name(), max, 1)
            self.version_editor.setText(v)

        self.update_timer.start()

    @QtCore.Slot(unicode)
    def update_tasks(self, ext):
        """Update the available task folder options based on the given file extension."""
        ext = ext.lower()
        config = asset_config.get(self.server, self.job, self.root)
        if ext in config.get_extensions(asset_config.CacheFormat):
            self.folder_editor.set_mode(file_properties_widgets.CacheMode)
        elif ext in config.get_extensions(asset_config.SceneFormat):
            self.folder_editor.set_mode(file_properties_widgets.SceneMode)
        else:
            self.folder_editor.set_mode(file_properties_widgets.NoMode)

    def exec_(self):
        result = super(FilePropertiesWidget, self).exec_()
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
        self._save_db_data()
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
        if not name or not _dir or u'{invalid_token}' in name:
            raise RuntimeError('Invalid token in output name')

        _dir = QtCore.QDir(_dir)
        if not _dir.mkpath(u'.'):
            raise RuntimeError('Could name create folder.')

        file_info = QtCore.QFileInfo(self.db_source())
        if file_info.exists():
            raise RuntimeError(
                u'{} already exists. Try incrementing the version number.'.format(name))

        path = file_info.absoluteFilePath()
        open(os.path.normpath(path), 'a').close()
        self.itemCreated.emit(path)

    def save_local_value(self, key, value):
        settings.instance().setValue(
            settings.CurrentUserPicksSection,
            key,
            value
        )

    @QtCore.Slot()
    def folder_button_clicked(self):
        """Lets the user select a custom save destination.

        The selection has to be inside the currently seleted asset, otherwise
        will be rejected. If the folder is not part of the current available
        options, it will be added as a new option.

        """
        source = u'/'.join((self.server, self.job, self.root, self.asset))
        _dir = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption=u'Select a folder...',
            dir=source,
            options=QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks | QtWidgets.QFileDialog.DontUseCustomDirectoryIcons
        )
        if not _dir:
            return

        if source not in _dir:
            ui.ErrorBox(
                u'Invalid selection',
                u'Make sure to select a folder inside the current asset.'
            ).open()
            return

        relative_path = _dir.replace(source, u'').strip(u'/')
        self.add_task(relative_path)

    def add_task(self, relative_path):
        """Adds a task folder to the folder editor.

        """
        for n in xrange(self.folder_editor.count()):
            v = self.folder_editor.itemData(n, role=QtCore.Qt.UserRole)
            if v == relative_path:
                self.folder_editor.setCurrentIndex(n)
                return

        self.folder_editor.model().add_item(relative_path)
        self.folder_editor.blockSignals(True)
        self.folder_editor.setCurrentIndex(self.folder_editor.count() - 1)
        self.folder_editor.blockSignals(False)

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
            mbox.setWindowTitle(u'Folder does not yet exist')
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setText(u'Destination folder does not exist.')
            mbox.setInformativeText(
                u'The destination folder does not yet exist. Do you want to create it now?')
            button = mbox.addButton(
                u'Create folder', QtWidgets.QMessageBox.AcceptRole)
            mbox.setDefaultButton(button)
            mbox.addButton(u'Cancel', QtWidgets.QMessageBox.RejectRole)

            if mbox.exec_() == QtWidgets.QMessageBox.RejectRole:
                return
            if not _dir.mkpath(u'.'):
                ui.ErrorBox(
                    u'Could not create destination folder.').open()
                return

        actions.reveal(_dir.path())

    @QtCore.Slot()
    def prefix_button_clicked(self):
        editor = file_properties_widgets.PrefixEditor(parent=self)
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

        prefix = u'v' if v.startswith(u'v') else u''
        padding = len(v.replace(u'v', u''))
        try:
            n = int(v.replace(u'v', u''))
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
            return u'{}{}'.format(prefix, u'{}'.format(n).zfill(padding))

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
            _prefix = u'v' if _v.startswith(u'v') else u''
            _padding = len(_v.replace(u'v', u''))
            try:
                _n = int(_v.replace(u'v', u''))
            except ValueError:
                continue
            _arr.append(_n)

        if not _arr:
            n += increment
            if n < 0:
                n = 0
            if n > 999:
                n = 999
            return u'{}{}'.format(prefix, u'{}'.format(n).zfill(padding))

        _n = func(_arr)
        _n += increment

        if func == max and _n <= n:
            _n = n + increment
        if func == min and _n >= n:
            _n = n + increment
        if _n < 0:
            _n = 0
        if _n > 999:
            _n = 999

        return u'{}{}'.format(_prefix, u'{}'.format(_n).zfill(_padding))
