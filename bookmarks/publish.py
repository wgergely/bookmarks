"""This modules defines the widget and methods needed for a simple publish flow.

This currently entails



"""
import functools
import json
import os
import time

import bookmarks_openimageio

try:
    from PySide6 import QtWidgets, QtGui, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore

from . import actions
from . import common
from . import database
from . import images
from . import log
from . import ui
from .editor import base
from .external import ffmpeg
from .tokens import tokens


def close():
    """Closes the :class:`PublishWidget` editor.

    """
    if common.publish_widget is None:
        return
    try:
        common.publish_widget.close()
        common.publish_widget.deleteLater()
    except:
        pass
    common.publish_widget = None


def show(index):
    """Shows the :class:`PublishWidget` editor.

    """
    close()
    if common.publish_widget is None:
        common.publish_widget = PublishWidget(index)

    common.restore_window_geometry(common.publish_widget)
    common.restore_window_state(common.publish_widget)
    return common.publish_widget


def _strip(s):
    return (s.strip('-').strip('_').strip().replace('__', '_').replace('_.', '.'))


def get_payload(kwargs, destination):
    """Get the payload for the publish process.

    Args:
        kwargs (dict): A list of keyword arguments.
        destination (str): The destination path.

    Returns:
        dict: The payload information used to publish the item.

    """
    if 'entries' not in kwargs or not kwargs['entries']:
        raise ValueError('No file entry found to publish!')

    v = {
        'type': None,
        'format': None,
        'files': {},
        'kwargs': kwargs,
        'timestamp': time.strftime('%d/%m/%Y %H:%M:%S'),
        'user': common.get_username(),
    }

    # Get format type
    config = tokens.get(*common.active('root', args=True))
    vals = tokens.DEFAULT_TOKEN_CONFIG[tokens.FileFormatConfig].values()
    flags = [v['flag'] for v in vals]
    for flag in flags:
        extensions = [f.lower() for f in config.get_extensions(flag)]
        if kwargs['ext'].lower() in extensions:
            v['format'] = flag
            break

    if len(kwargs['entries']) > 1 and kwargs['is_collapsed']:
        v['type'] = common.SequenceItem

        destination = destination.split('.')
        destination.pop(-1)
        destination = '.'.join(destination)

        for entry in kwargs['entries']:
            path = entry.path.replace('\\', '/')
            seq = common.get_sequence(path)

            if not seq:
                raise ValueError('Error occurred when extracting sequence.')

            if not QtCore.QFileInfo(path).exists():
                raise RuntimeError('A sequence item does not exist.')

            v['files'][path] = f'{destination}.{int(seq.group(2))}.{kwargs["ext"]}'

    elif len(kwargs['entries']) == 1:
        v['type'] = common.FileItem

        source = kwargs['entries'][0].path.replace('\\', '/')
        if not QtCore.QFileInfo(source).exists():
            raise RuntimeError('Source does not exist.')
        v['files'][source] = destination
    else:
        raise RuntimeError('Could not publish item.')

    return v


class TemplateModel(ui.AbstractListModel):
    """Model used to list all available publish templates from the active bookmark item's token configuration.

    """

    def init_data(self):
        """Initializes data.

        """
        args = common.active('root', args=True)
        if not all(args):
            return

        config = tokens.get(*args)
        data = config.data()
        if not isinstance(data, dict):
            return

        template = common.settings.value('publish/template')
        for v in data[tokens.PublishConfig].values():
            if 'name' not in v:
                print(f'Warning: Invalid publish template: {v}')
                continue
            if 'value' not in v:
                print(f'Warning: Invalid publish template: {v}')
                continue
            if 'description' not in v:
                print(f'Warning: Invalid publish template: {v}')
                continue

            if template == v['name']:
                pixmap = images.rsc_pixmap(
                    'check', common.color(common.color_green), common.size(common.size_margin) * 2
                )
            else:
                pixmap = images.rsc_pixmap(
                    'file', common.color(common.color_separator), common.size(common.size_margin) * 2
                )
            icon = QtGui.QIcon(pixmap)

            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: v['name'],
                QtCore.Qt.DecorationRole: icon,
                QtCore.Qt.SizeHintRole: self.row_size,
                QtCore.Qt.StatusTipRole: v['description'],
                QtCore.Qt.AccessibleDescriptionRole: v['description'],
                QtCore.Qt.WhatsThisRole: v['description'],
                QtCore.Qt.ToolTipRole: v['description'],
                QtCore.Qt.UserRole: v['value'],
            }


class TemplateComboBox(QtWidgets.QComboBox):
    """Publish template picker.

    The editor will list all relevant templates stored in the bookmark item database's token configuration.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.setModel(TemplateModel())


class PublishWidget(base.BasePropertyEditor):
    """Publishes a footage.

    """
    #: UI layout definition
    sections = {
        0: {
            'name': 'Publish File',
            'icon': 'icon',
            'color': common.color(common.color_green),
            'groups': {
                0: {
                    0: {
                        'name': 'Source',
                        'key': 'source',
                        'validator': None,
                        'widget': functools.partial(
                            ui.PaintedLabel,
                            '',
                            color=common.color(common.color_selected_text)
                        ),
                        'placeholder': '',
                        'description': 'Source file path',
                    },
                    1: {
                        'name': 'Destination',
                        'key': 'destination',
                        'validator': None,
                        'widget': functools.partial(
                            ui.PaintedLabel,
                            '',
                            color=common.color(common.color_green)
                        ),
                        'placeholder': '',
                        'description': 'The publish\'s destination path',
                    },
                },
            },
        },
        1: {
            'name': 'Template',
            'icon': None,
            'color': None,
            'groups': {
                0: {
                    0: {
                        'name': 'Publish Template',
                        'key': 'publish/template',
                        'validator': None,
                        'widget': TemplateComboBox,
                        'placeholder': None,
                        'description': 'Select a publish template',
                        'help': 'Select a publish template from the list. The templates can be customized in the '
                                'bookmark item\'s property editor.',
                    },
                },
                1: {
                    0: {
                        'name': 'Description',
                        'key': 'description',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'Enter a short description here...',
                        'description': 'A short description of this file '
                                       'publish.\nIndicate significant changes and '
                                       'notes here.',
                    },
                    1: {
                        'name': 'Specify Element',
                        'key': 'element',
                        'validator': base.text_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'The element being published, e.g. \'CastleInterior\'',
                        'description': 'The name of the element being published. E.g., '
                                       '\'ForegroundTower\', or \'BackgroundElements\'',
                    },
                },
            },
        },
        2: {
            'name': 'Options',
            'icon': None,
            'color': common.color(common.color_dark_background),
            'groups': {
                0: {
                    0: {
                        'name': 'Archive existing files',
                        'key': 'publish/archive_existing',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': None,
                        'description': 'Enable will archive all existing files in the destination folder.',
                    },
                },
                1: {
                    0: {
                        'name': 'Copy publish path',
                        'key': 'publish/copy_path',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': None,
                        'description': 'Copy the publish path to the clipboard after finish.',
                    },
                    1: {
                        'name': 'Reveal files',
                        'key': 'publish/reveal',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': None,
                        'description': 'Reveal the published files in the explorer.',
                    },
                },
            },
        },
    }

    def __init__(self, index, parent=None):
        super().__init__(
            common.active('server'), common.active('job'), common.active('root'), db_table=database.AssetTable,
            buttons=(
                'Publish', 'Cancel'), parent=parent
        )
        self._index = index
        self.progress_widget = None

        self.update_timer = common.Timer(parent=self)
        self.update_timer.setInterval(100)
        self.update_timer.setSingleShot(False)

        self.update_timer.timeout.connect(self.update_expanded_template)

        self._connect_settings_save_signals(common.SECTIONS['publish'])

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.source_editor.clicked.connect(self.source_editor_clicked)
        self.destination_editor.clicked.connect(self.destination_editor_clicked)

    @QtCore.Slot()
    def source_editor_clicked(self):
        """Slot -> Called when the source item label is clicked."""
        v = self.source_editor.text()
        if not v:
            return
        v = common.get_sequence_start_path(v)
        file_info = QtCore.QFileInfo(v)
        if not file_info.exists():
            common.show_message(
                'Warning',
                f'Publish source file does not exist:\n\n{v}'
            )
            return

        actions.reveal(v)

    @QtCore.Slot()
    def destination_editor_clicked(self):
        """Slot -> Called when the destination item label is clicked."""
        text = self.destination_editor.text()
        if not text:
            return

        file_info = QtCore.QFileInfo(text)
        _dir = file_info.dir()
        if not _dir.exists():
            common.show_message(
                'Publish directory does not exist',
                f'Publish has not yet been created:\n\n{_dir.path()}'
            )
            return

        actions.reveal(_dir.path())

    def init_progress_bar(self):
        """Initializes the progress bar.

        """
        self.progress_widget = QtWidgets.QProgressDialog(parent=self)
        self.progress_widget.setFixedWidth(common.size(common.size_width))
        self.progress_widget.setLabelText('Publishing, please wait...')
        self.progress_widget.setWindowTitle('Publish')
        self.progress_widget.close()

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        v = self._index.data(common.PathRole)
        if common.is_collapsed(v):
            return common.proxy_path(v)
        return self._index.data(common.PathRole)

    @common.error
    @common.debug
    def init_data(self):
        """Initializes data.

        """
        if not self._index.isValid():
            raise ValueError('Invalid index value.')

        self.load_saved_user_settings(common.SECTIONS['publish'])

        self.init_db_data()
        self.init_thumbnail()
        self.set_source_text()
        self.init_progress_bar()

    def init_thumbnail(self):
        """Load the item's current thumbnail.

        """
        if not self._index.isValid():
            raise ValueError('Invalid index value.')

        server, job, root = self._index.data(common.ParentPathRole)[0:3]
        source = images.get_thumbnail(
            server, job, root, self._index.data(common.PathRole), get_path=True
        )
        if QtCore.QFileInfo(source).exists():
            self.thumbnail_editor.process_image(source)

    def set_source_text(self):
        """Set source item label.

        """
        self.source_editor.setText(self._index.data(common.PathRole))

    @QtCore.Slot()
    def update_expanded_template(self):
        """Slot used update the source and destination editors.

        """
        kwargs = self.get_publish_kwargs()

        if not kwargs['publish_template']:
            return tokens.invalid_token

        config = tokens.get(kwargs['server'], kwargs['job'], kwargs['root'])
        v = config.expand_tokens(
            kwargs['publish_template'], **kwargs
        )

        r = common.rgb(common.color_red)
        v = v.replace(
            tokens.invalid_token, f'<span style="color:{r}">{tokens.invalid_token}</span>'
        )
        v = v.replace(
            '###', f'<span style="color:{common.rgb(common.color_red)}">###</span>'
        )

        self.destination_editor.setText(v)

    def get_publish_kwargs(self, **_kwargs):
        """Get the list of properties needed to publish the item.

        Args:
            _kwargs (dict): Dictionary of properties overrides.

        Returns:
            dict: Dictionary of properties.

        """
        kwargs = {}
        if not self._index.isValid():
            raise ValueError('Invalid index value.')

        args = common.active('task', args=True)
        if not all(args) or len(args) < 5:
            raise ValueError('Invalid active value.')

        # init
        config = tokens.get(*common.active('root', args=True))
        kwargs.update(config.get_tokens(asset=common.active('asset')))

        # Item info
        kwargs['source'] = self._index.data(common.PathRole)
        kwargs['type'] = self._index.data(common.DataTypeRole)
        kwargs['entries'] = self._index.data(common.EntryRole)
        kwargs['is_collapsed'] = common.is_collapsed(kwargs['source'])
        kwargs['ext'] = QtCore.QFileInfo(kwargs['source']).suffix()

        kwargs['shot'], kwargs['sequence'] = common.get_sequence_and_shot(
            self._index.data(common.PathRole)
        )
        kwargs['sh'] = kwargs['shot']
        kwargs['sq'] = kwargs['sequence']
        kwargs['seq'] = kwargs['sequence']

        kwargs['element'] = self.element_editor.text()
        kwargs['element'] = kwargs['element'] if kwargs['element'] else 'main'

        # Widget state
        kwargs['publish_template'] = self.publish_template_editor.currentData()
        kwargs['description'] = self.description_editor.text()
        kwargs['publish_copy_path'] = self.publish_copy_path_editor.isChecked()
        kwargs['publish_reveal'] = self.publish_reveal_editor.isChecked()

        # Overrides
        kwargs.update(_kwargs)
        return kwargs

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        kwargs = self.get_publish_kwargs()
        if 'publish_template' not in kwargs or not kwargs['publish_template']:
            raise ValueError('Publish template not set.')

        destination = self.destination_editor.text()
        if not destination:
            raise ValueError('Destination not set.')
        if tokens.invalid_token in destination:
            raise ValueError(
                'Invalid token in destination. '
                'Try selecting another publish template.'
            )

        try:
            payload = get_payload(kwargs, destination)

            config = tokens.get(*common.active('root', args=True))

            flag = (tokens.SceneFormat | tokens.ImageFormat | tokens.MovieFormat | tokens.AudioFormat |
                    tokens.CacheFormat)
            exts = config.get_extensions(flag, force=True)

            if kwargs['ext'] not in exts:
                raise RuntimeError(
                    f'"{kwargs["ext"]}" is not a valid publish format.\n'
                    f'Only following formats are accepted:\n{", ".join(exts)}'
                )

            self.prepare_publish(destination, payload=payload)
            self.copy_payload_files(payload=payload)
            self.save_thumbnail(destination, payload=payload)

            # TODO: We can't implement this without more user control!
            # jpegs = self.make_jpegs(payload=payload)
            # self.make_videos(destination, jpegs, payload=payload)

            self.write_manifest(destination, payload=payload)
            self.post_publish(destination, kwargs)
            return True
        except:
            raise
        finally:
            self.progress_widget.close()

    def save_thumbnail(self, destination, payload=None):
        """Saves the current thumbnail to the `publish` folder.

        """
        _dir = QtCore.QFileInfo(destination).dir()
        temp = f'{_dir.path()}/temp.{common.thumbnail_format}'
        dest = f'{_dir.path()}/thumbnail.{common.thumbnail_format}'

        self.thumbnail_editor.save_image(destination=temp)

        if QtCore.QFileInfo(temp).exists():
            res = bookmarks_openimageio.convert_image(
                temp, dest, size=int(common.thumbnail_size)
            )
            if not res:
                print(f'Error: Could not convert {temp}')
            QtCore.QFile(temp).remove()

        payload['thumbnail'] = dest

    def prepare_publish(self, destination, payload=None):
        """Prepare the destination directory for publishing.

        """
        if not common.settings.value('publish/archive_existing', False):
            return

        self.progress_widget.setLabelText('Preparing publish...')
        self.progress_widget.setMinimum(0)
        self.progress_widget.setMaximum(2)
        self.progress_widget.setRange(0, 2)
        self.progress_widget.open()

        file_info = QtCore.QFileInfo(destination)
        _dir = file_info.dir()

        if not QtCore.QFileInfo(f'{_dir.path()}').exists() and not _dir.mkpath('.'):
            raise OSError('Failed to create publish directory.')

        if (not QtCore.QFileInfo(f'{_dir.path()}/.archive').exists() and not _dir.mkpath('./.archive')):
            raise OSError('Failed to create .archive directory.')

        s = time.strftime('.archive_%Y-%m-%d-%H%M%S')
        f = QtCore.QFileInfo(f'{_dir.path()}/.archive/{s}')

        self.progress_widget.setValue(1)

        for entry in os.scandir(_dir.path()):
            if entry.name.startswith('.') and entry.is_dir():
                continue

            if not f.exists():
                _dir.mkpath(f'./.archive/{s}')

            file_info = QtCore.QFileInfo(entry.path)
            if not QtCore.QFile(file_info.filePath()).rename(
                    f'{_dir.path()}/.archive/{s}/{file_info.fileName()}'
            ):
                log.error(f'Could not remove {file_info.filePath()}')

        log.success('Previous publish archived successfully.')

    def copy_payload_files(self, payload=None):
        """Copy files based on the given payload.

        Args:
            payload (dict): Payload data.

        """
        self.progress_widget.setLabelText('Copying files...')
        self.progress_widget.setMinimum(0)
        self.progress_widget.setMaximum(len(payload['files']))
        self.progress_widget.setRange(0, len(payload['files']))
        self.progress_widget.open()
        n = 0

        for source, destination in payload['files'].items():
            n += 1
            self.progress_widget.setValue(n)

            if not QtCore.QFile(source).copy(destination):
                raise RuntimeError(f'Could not copy {source} to {destination}.')

        log.success('Files copied successfully.')

    def make_jpegs(self, payload):
        """Convert the source image files to a jpeg sequence.

        Args:
            payload (dict): The payload data used to publish the item.

        Returns:
            list: A list of file paths of the created jpeg files, or `None`.

        """
        if payload['format'] != tokens.ImageFormat:
            return None

        self.progress_widget.setLabelText('Making jpeg previews...')
        self.progress_widget.setMinimum(0)
        self.progress_widget.setMaximum(len(payload['files']))
        self.progress_widget.setRange(0, len(payload['files']))
        self.progress_widget.open()

        files = []

        n = 0
        for source, destination in payload['files'].items():
            n += 1
            self.progress_widget.setValue(n)
            file_info = QtCore.QFileInfo(destination)
            _dir = file_info.dir()

            buf = images.ImageCache.get_buf(destination)
            if not buf:
                continue

            if not QtCore.QFileInfo(f'{_dir.path()}/jpg').exists():
                if not _dir.mkpath('./jpg'):
                    return None

            folder = file_info.dir().path()
            name = file_info.completeBaseName()

            f = f'{folder}/jpg/{name}.jpg'
            files.append(f)
            buf.write(f)

            images.ImageCache.flush(destination)
            images.ImageCache.flush(f)

        payload['jpgs'] = files

        log.success('Jpegs created successfully.')
        return files

    def make_videos(self, destination, jpegs, payload=None):
        """Create videos from the source images.

        Args:
            destination (str): Publish destination path.
            jpegs (list): A list of file paths of previously created jpeg images.
            payload (dict): Optional. A dictionary of payload data.

        """
        if payload['format'] != tokens.ImageFormat:
            return
        if payload['type'] != common.SequenceItem:
            return
        if not payload['kwargs']['entries'] or len(payload['kwargs']['entries']) < 10:
            return

        if not jpegs:
            return

        file_info = QtCore.QFileInfo(destination)
        _dir = file_info.dir()

        if not QtCore.QFileInfo(f'{_dir.path()}/video').exists() and not _dir.mkpath(
                './video'
        ):
            raise RuntimeError(f'"{_dir.path()}/video" does not exist')

        asset = payload['kwargs']['asset']
        if payload['kwargs']['sequence'] and payload['kwargs']['shot']:
            asset = f"{payload['kwargs']['sequence']}_{payload['kwargs']['shot']}"

        payload['videos'] = []

        o = f'{_dir.path()}/video/{file_info.completeBaseName()}.' \
            f'{ffmpeg.PRESETS[ffmpeg.H264HQ]["output_extension"]}'

        ffmpeg.convert(
            jpegs[0],
            ffmpeg.PRESETS[ffmpeg.H264HQ]['preset'], server=payload['kwargs']['server'], job=payload['kwargs'][
                'job'], root=payload['kwargs']['root'], asset=asset, task=payload['kwargs']['task'], size=(
                None, None), timecode=False, output_path=o
        )
        payload['videos'].append(o)

        o = f'{_dir.path()}/video/{file_info.completeBaseName()}_TC.' \
            f'{ffmpeg.PRESETS[ffmpeg.H264HQ]["output_extension"]}'

        ffmpeg.convert(
            jpegs[0],
            ffmpeg.PRESETS[ffmpeg.H264HQ]['preset'], server=payload['kwargs']['server'], job=payload['kwargs'][
                'job'], root=payload['kwargs']['root'], asset=asset, task=payload['kwargs']['task'], size=(
                1920, 1080), timecode=True, output_path=o
        )
        payload['videos'].append(o)

        try:
            o = f'{_dir.path()}/video/{file_info.completeBaseName()}.' \
                f'{ffmpeg.PRESETS[ffmpeg.DNxHD90]["output_extension"]}'

            ffmpeg.convert(
                jpegs[0],
                ffmpeg.PRESETS[ffmpeg.DNxHD90]['preset'], server=payload['kwargs']['server'], job=payload['kwargs'][
                    'job'], root=payload['kwargs']['root'], asset=asset, task=payload['kwargs'][
                    'task'], timecode=True, output_path=o
            )
            payload['videos'].append(o)
        except:
            log.error('Could not convert DNxHD video.')

        log.success('Videos converted successfully.')

    def write_manifest(self, destination, payload=None):
        """Write an informative manifest file with information about this publish.

        Args:
            destination (str): Publish destination path.
            payload (dict, optional): Optional. Dictionary of payload data.

        """
        payload['description'] = payload['kwargs']['description']
        del payload['kwargs']

        file_info = QtCore.QFileInfo(destination)
        s = f'{file_info.dir().path()}/publish.json'
        with open(s, 'w') as f:
            json.dump(payload, f, sort_keys=True, indent=4)

    def post_publish(self, destination, kwargs):
        """Post publish actions.

        Args:
            destination (str): Publish destination path.
            kwargs (dict, optional): Optional. Dictionary of payload data.

        """
        log.success('Publish done.')
        common.show_message('Publish finished.', message_type='success')

        if kwargs['publish_reveal']:
            actions.reveal(QtCore.QFileInfo(destination).dir().path())
        if kwargs['publish_copy_path']:
            actions.copy_path(destination)

        # Get the source's description from the database
        index = self._index
        if not index.isValid():
            return

        path = index.data(common.PathRole)
        if kwargs['is_collapsed']:
            path = common.proxy_path(path)

        db = database.get(*common.active('root', args=True))
        description = db.value(path, 'description', database.AssetTable)
        description = description if description else ''

        if '#published' not in description:
            description += f' #published'
        db.set_value(path, 'description', description, database.AssetTable)

        # Add a note to the database
        note = (
            f'\nTime: {time.strftime("%d/%m/%Y %H:%M:%S")}'
            f'\nUser: {common.get_username()}'
            f'\nDestination:\n{QtCore.QFileInfo(destination).dir().path()}'
        )
        notes = db.value(path, 'notes', database.AssetTable)
        notes = notes if notes else {}
        notes[len(notes)] = {
            'title': 'Publish Log (server)',
            'body': note,
            'extra_data': {
                'created_by': common.get_username(),
                'created_at': time.strftime('%d/%m/%Y %H:%M:%S'),
                'fold': False,
            }
        }
        db.set_value(path, 'notes', notes, database.AssetTable)

    def showEvent(self, event):
        """Called when the widget is shown.

        Args:
            event (QtCore.QEvent): The event that triggered this slot.

        """
        super().showEvent(event)
        self.update_timer.start()

    def hideEvent(self, event):
        """Called when the widget is hidden.

        Args:
            event (QtCore.QEvent): The event that triggered this slot.

        """
        super().hideEvent(event)
        self.update_timer.stop()

    def closeEvent(self, event):
        """Called when the widget is closed.

        Args:
            event (QtCore.QEvent): The event that triggered this slot.

        """
        super().closeEvent(event)
        self.update_timer.stop()
        close()
