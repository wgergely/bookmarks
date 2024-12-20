"""The module contains the definition of :class:`FileSaverWidget`, the main widget used
by Bookmarks to create versioned template files.

The suggested save destination will be partially dependent on the extension
specified, the current token config values as well as the active bookmark and asset
items.

See the :mod:`bookmarks.tokens` and :mod:`bookmarks.editor.bookmark_properties` modules
for more information.

.. code-block:: python
    :linenos:

    editor = FileSaverWidget(extension='fbx')


Attributes:
    INACTIVE_KEYS (tuple): A tuple of keys used to mark hidden and disabled editors.


"""
import os

from PySide2 import QtWidgets, QtCore

from . import widgets
from .. import actions, tokens
from .. import common
from .. import database
from .. import log
from .. import ui
from ..editor import base


def close():
    """Close the :class:`FileSaverWidget` widget.

    """
    if common.file_saver_widget is None:
        return
    try:
        common.file_saver_widget.close()
        common.file_saver_widget.deleteLater()
    except:
        pass
    common.file_saver_widget = None


def show(
        extension=None, file=None, create_file=True,
        increment=False
):
    """Show the :class:`FileSaverWidget` widget.

    Args:
        extension (str): Optional file extension. Default is ``None``.
        file (str): Optional, path to an existing file.
        create_file (bool): Optional, when ``True`` the widget will create empty
            placeholder files. Default is ``True``.
        increment (bool): Optional bool. Will increment the version of ``file`` when
            ``True``. Default is ``False``

    """
    close()
    common.file_saver_widget = FileSaverWidget(
        extension=extension,
        file=file,
        create_file=create_file,
        increment=increment,
    )
    common.restore_window_geometry(common.file_saver_widget)
    common.restore_window_state(common.file_saver_widget)
    return common.file_saver_widget


#: Keys we don't associate with local preferences
INACTIVE_KEYS = (
    'file_saver_task',
    'prefix',
    'file_saver_element',
    'version',
    'file_saver_extension',
    'file_saver_user',
    'file_saver_template',
)


def increment_version(v, dir, name, func, increment):
    """Increments a version number considering existing versions in a directory.

    This function can either increment the version number by a specified amount or to
    the smallest/largest available version number based on existing files found in the
    destination folder.

    Args:
        v (str): Initial version string, for example, 'v001'. If None, it defaults to 'v001'.
        dir (str): Path to the directory where versions should be checked.
        name (str): The name of the file or directory whose version should be incremented.
        func (function): Python built-in function min or max. Determines whether to increment
                         to the smallest (min) or largest (max) version number in the directory.
        increment (int): The amount by which the version number should be incremented.

    Returns:
        str: The incremented version string, for example, 'v002'. If the version cannot be incremented
             (due to a problem with the provided values), the function will return 'v001'.

    Raises:
        ValueError: If the initial version string can't be converted to an integer.
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
        # We can freely increment the version number, as there won't be any conflicts
        n += increment
        if n < 0:
            n = 0
        if n > 999:
            n = 999
        return f'{prefix}{"{}".format(n).zfill(padding)}'

    # Let's scan the destination directory for existing versions to make
    # sure we're only suggesting valid versions
    if v not in name:
        return 'v001'
    idx = name.index(v)

    _arr = []
    with os.scandir(_dir.path()) as it:
        for entry in it:
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


class FileSaverWidget(base.BasePropertyEditor):
    """The main widget used to create template files.

    """
    #: UI layout definition
    sections = {
        0: {
            'name': 'Save File',
            'icon': 'file',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': 'Template',
                        'key': 'file_saver/template',
                        'validator': base.text_validator,
                        'widget': widgets.TemplateComboBox,
                        'placeholder': 'A customizable template name',
                        'description': 'The name of the template to use. These can'
                                       'be customized in the bookmark properties.',
                    },
                    1: {
                        'name': 'Task',
                        'key': 'file_saver/task',
                        'validator': None,
                        'widget': widgets.TaskComboBox,
                        'placeholder': None,
                        'description': 'The current task item.',
                        'button': 'Pick'
                    },
                    2: {
                        'name': 'Format',
                        'key': 'file_saver/extension',
                        'validator': None,
                        'widget': widgets.FormatComboBox,
                        'placeholder': 'File extension, for example, \'exr\'',
                        'description': 'A file extension, without the leading dot. for example'
                                       ' \'ma\'',
                    },
                },
                1: {
                    0: {
                        'name': 'Description',
                        'key': 'description',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'A short description, for example, \'Compositing files\'',
                        'description': 'A short description of the file\'s '
                                       'contents.\nIndicate significant changes and '
                                       'notes here.',
                    },
                    1: {
                        'name': 'Element',
                        'key': 'file_saver/element',
                        'validator': base.text_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'The element being saved, for example, \'CastleInterior\'',
                        'description': 'The name of the element being saved. for example, '
                                       '\'ForegroundTower\', or \'BackgroundElements\'',
                    },
                    2: {
                        'name': 'Version',
                        'key': 'version',
                        'validator': base.version_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'A version number, for example, \'v001\'',
                        'description': 'A version number with, or without, '
                                       'a preceding \'v\'. for example, \'v001\'.',
                        'button': '+',
                        'button2': '-',
                    },
                    3: {
                        'name': 'User',
                        'key': 'file_saver/user',
                        'validator': base.text_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Your name, for example, \'JohnDoe\'',
                        'description': 'The name of the current user, for example, \'JohnDoe\','
                                       ' or \'JD\'',
                    },
                },
                2: {
                    0: {
                        'name': None,
                        'key': 'filename',
                        'validator': None,
                        'widget': widgets.FileNameInfo,
                        'placeholder': 'Invalid file name...',
                        'description': 'The file name, based on the current template.',
                        'button': 'Reveal'
                    },
                },
            },
        },
    }

    def __init__(
            self, extension=None, file=None,
            create_file=True, increment=False, parent=None
    ):
        super().__init__(
            common.active('server'),
            common.active('job'),
            common.active('root'),
            asset=common.active('asset'),
            alignment=QtCore.Qt.AlignLeft,
            fallback_thumb='file',
            db_table=database.AssetTable,
            parent=parent,
            section_buttons=False
        )

        self._file = None

        self._increment = increment
        self._create_file = create_file
        self._extension = extension
        self._filelist = {}

        self._file_path = None

        self.update_timer = common.Timer(parent=self)
        self.update_timer.setInterval(100)
        self.update_timer.setSingleShot(False)
        self.update_timer.timeout.connect(self.verify_unique)

        self.filename_editor.setStyleSheet(
            f'color:{common.Color.Green(qss=True)};font-size:{int(common.Size.MediumText(apply_scale=False))}px;qproperty-alignment: '
            f'AlignCenter;'
        )

        if file is not None:
            self.set_file(file)
            return

        self.update_timer.timeout.connect(self.update_expanded_template)
        self.update_timer.timeout.connect(self.thumbnail_editor.update)

    def file_path(self):
        """File path.

        """
        return self._file_path

    def set_file(self, file):
        """Set the given file as the current file.

        Args:
            file (str): Path to a file.

        """
        if not file:
            raise RuntimeError('Invalid file path: {}'.format(file))

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
                    v = increment_version(
                        v, self.parent_folder(), name, max, 1
                    )
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
            if not hasattr(self, f'{k}_editor'):
                continue
            editor = getattr(self, f'{k}_editor')
            editor.parent().setDisabled(True)
            editor.parent().parent().setHidden(True)

        self.filename_editor.setText(QtCore.QFileInfo(file).fileName())

    def _connect_signals(self):
        super()._connect_signals()
        self._connect_settings_save_signals(common.SECTIONS['file_saver'])

    def name(self):
        """Returns the current name.

        """
        return self.filename_editor.text()

    @QtCore.Slot()
    def update_expanded_template(self):
        """Slot connected to the update timer used to preview the current
        file name.

        """
        template = self.file_saver_template_editor.currentData(QtCore.Qt.UserRole)
        config = tokens.get(*common.active('root', args=True))

        if not self.parent_folder():
            return tokens.invalid_token

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
            if not hasattr(self, f'{k}_editor'):
                log.error(f'Could not find {k}_editor')
                return ''
            editor = getattr(self, f'{k}_editor')
            if hasattr(editor, 'currentData'):
                v = editor.currentData(QtCore.Qt.UserRole)
            elif hasattr(editor, 'currentText'):
                v = editor.currentText()
            elif hasattr(editor, 'text'):
                v = editor.text()
            else:
                v = ''

            return _strip(v)

        # Get generic shot and sequence numbers from the current asset name
        seq, shot = common.get_sequence_and_shot(self.parent_folder())

        task = _get('file_saver_task')
        if '/' in task:
            task = task.split('/')[-1]

        v = common.parser.format(
            template,
            user=_get('file_saver_user'),
            version=_get('version').lower(),
            task=task,
            element=_get('file_saver_element') if _get('file_saver_element') else 'main',
            sh=shot,
            shot=shot,
            sq=seq,
            seq=seq,
            sequence=seq,
            ext=_get('file_saver_extension').lower()
        )
        v = _strip(v)
        r = common.Color.Red(qss=True)
        v = v.replace(
            tokens.invalid_token,
            f'<span style="color:{r}">{tokens.invalid_token}</span>'
        )

        v = v.replace(
            '###',
            f'<span style="color:{common.Color.Red(qss=True)}">###</span>'
        )

        self.filename_editor.setText(v)

    @QtCore.Slot()
    def verify_unique(self):
        """Checks if the proposed file name exists already, and if it does,
        makes the output file name red.

        """
        if self.db_source() not in self._filelist:
            file_info = QtCore.QFileInfo(self.db_source())
            self._filelist[self.db_source()] = file_info.exists()

        if self._filelist[self.db_source()]:
            self.filename_editor.setStyleSheet(
                f'color:{common.Color.Red(qss=True)};font-size:'
                f'{int(common.Size.MediumText(apply_scale=False))}px;qproperty-alignment: AlignCenter;'
            )
        else:
            self.filename_editor.setStyleSheet(
                f'color:{common.Color.Green(qss=True)};font-size:'
                f'{int(common.Size.MediumText(apply_scale=False))}px;qproperty-alignment: AlignCenter;'
            )

    def parent_folder(self):
        """The folder where the new file is about to be saved.

        """
        if self._file:
            return QtCore.QFileInfo(self._file).dir().path()

        folder = self.file_saver_task_editor.currentData(QtCore.Qt.UserRole)
        if not folder:
            return None

        return f'{common.active("asset", path=True)}/{folder}'

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        if self._file:
            if common.is_collapsed(self._file):
                return common.proxy_path(self._file)
            return self._file

        if not self.parent_folder():
            return None
        return f'{self.parent_folder()}/{self.name()}'

    @common.error
    @common.debug
    def init_data(self):
        """Initialises values of each editor.

        Some values are retrieved by the context the widget was called in, and
        some are loaded from the user settings if the user saved a custom value
        previously.

        """
        self.file_saver_user_editor.blockSignals(True)
        if self._file is not None:
            self.file_saver_user_editor.setText('-')
        else:
            self.file_saver_user_editor.setText(common.get_username())
        self.file_saver_user_editor.blockSignals(False)

        # Load previously set values from the user settings file
        if self._file is None:
            self.load_saved_user_settings(common.SECTIONS['file_saver'])

        if self._extension and self._file is None:
            if self.file_saver_extension_editor.findText(self._extension) > 0:
                self.file_saver_extension_editor.setCurrentText(self._extension)
                self.file_saver_extension_editor.setDisabled(True)

            self.file_saver_task_editor.blockSignals(True)
            self.update_tasks(self._extension)
            self.file_saver_task_editor.blockSignals(False)

            if self.file_saver_task_editor.findText(self._extension.upper()) > 0:
                self.file_saver_task_editor.blockSignals(True)
                self.file_saver_task_editor.setCurrentText(self._extension.upper())
                self.file_saver_task_editor.blockSignals(False)

        # Description
        if self._file is not None:
            db = database.get(*common.active('root', args=True))
            v = db.value(
                self.db_source(),
                'description',
                database.AssetTable
            )
            v = v if v else ''
            self.description_editor.setText(v)
            self.description_editor.setFocus()
            return

        # Increment the version if the source already exists
        self.update_expanded_template()

        # Set a default the version string if not set previously
        if not self.version_editor.text():
            self.version_editor.setText('v001')

        # Increment the version by one if the file already exists
        if QtCore.QFileInfo(self.db_source()).exists():
            v = self.version_editor.text()
            v = increment_version(
                v, self.parent_folder(), self.name(), max, 1
            )
            self.version_editor.setText(v)

        self.update_timer.start()

    @QtCore.Slot(str)
    def update_tasks(self, ext):
        """Update the available task folder options based on the given file
        extension.

        """
        ext = ext.lower()
        config = tokens.get(*common.active('root', args=True))

        if ext in config.get_extensions(tokens.CacheFormat):
            self.file_saver_task_editor.set_mode(widgets.CacheMode)
        elif ext in config.get_extensions(tokens.SceneFormat):
            self.file_saver_task_editor.set_mode(widgets.SceneMode)
        else:
            self.file_saver_task_editor.set_mode(widgets.NoMode)

    def exec_(self):
        """Customized exec function.

        """
        result = super().exec_()
        if result == QtWidgets.QDialog.Rejected:
            return QtWidgets.QDialog.Rejected
        if result == QtWidgets.QDialog.Accepted:
            return self._file_path
        return None

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        name = self.name()
        if not name or tokens.invalid_token in name or '###' in name:
            raise RuntimeError('Invalid token in output name')

        self.create_file()
        self.save_changed_data_to_db()
        self.thumbnail_editor.save_image()
        self.thumbnailUpdated.emit(self.db_source())
        self._file_path = self.db_source()

        log.info(f'File saved to {self._file_path} successfully')

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
        if not name or not _dir or tokens.invalid_token in name or '###' in name:
            raise RuntimeError('Invalid token in output name')

        _dir = QtCore.QDir(_dir)
        if not _dir.mkpath('.'):
            raise RuntimeError('Could name create folder.')

        file_info = QtCore.QFileInfo(self.db_source())
        if file_info.exists():
            raise RuntimeError(
                f'{name} already exists. Try incrementing the version number.'
            )

        path = file_info.absoluteFilePath()
        open(os.path.normpath(path), 'a').close()
        self.itemCreated.emit(path)

    @QtCore.Slot()
    def file_saver_task_button_clicked(self):
        """Lets the user select a custom save destination.

        The selection has to be inside the currently selected asset, otherwise
        will be rejected. If the folder is not part of the current available
        options, it will be added as a new option.

        """
        source = common.active('asset', path=True)
        _dir = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption='Select a folder...',
            dir=source,
            options=QtWidgets.QFileDialog.ShowDirsOnly |
                    QtWidgets.QFileDialog.DontResolveSymlinks |
                    QtWidgets.QFileDialog.DontUseCustomDirectoryIcons
        )
        if not _dir:
            return

        if source not in _dir or source == _dir:
            common.show_message(
                'Invalid selection',
                body=f'{_dir} must be inside the current asset.',
                message_type='error'
            )
            return

        relative_path = _dir.replace(source, '').strip('/')
        if not relative_path:
            raise RuntimeError('Invalid folder selection.')

        self.add_task(relative_path)

    def add_task(self, relative_path):
        """Adds a task folder to the folder editor.

        """
        k = 'file_saver/task'
        k = f'{k.replace("/", "_")}_editor'

        if not hasattr(self, k):
            return

        editor = getattr(self, k)

        for n in range(editor.count()):
            v = editor.itemData(n, role=QtCore.Qt.UserRole)
            if v == relative_path:
                editor.setCurrentIndex(n)
                return

        editor.model().add_item(relative_path)
        editor.blockSignals(True)
        editor.setCurrentIndex(editor.count() - 1)
        editor.blockSignals(False)

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
            if common.show_message(
                    f'Folder does not yet exist',
                    body='The destination folder does not yet exist. Do you want to create it now?',
                    buttons=[common.YesButton, common.NoButton],
                    modal=True,
            ) == QtWidgets.QDialog.Rejected:
                return
            if not _dir.mkpath('.'):
                common.show_message(
                    'Could not create destination folder',
                    message_type='error'
                )
                return

        actions.reveal(_dir.path())

    @QtCore.Slot()
    def version_button_clicked(self):
        """Increments the version number by one.

        """
        v = self.version_editor.text()
        v = increment_version(
            v, self.parent_folder(), self.name(), max, 1
        )
        self.version_editor.setText(v)

    @QtCore.Slot()
    def version_button2_clicked(self):
        """Decrements the version number by one.

        """
        v = self.version_editor.text()
        v = increment_version(
            v, self.parent_folder(), self.name(), min, -1
        )
        self.version_editor.setText(v)
