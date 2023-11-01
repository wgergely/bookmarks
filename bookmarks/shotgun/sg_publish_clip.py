"""The publishing widget used by Bookmarks to create new PublishedFiles and Version
entities on ShotGrid.

The publish logic creates `Version` and `PublishFile` entities linked against
the current active project and asset and uploads any custom thumbnails set.

"""
import re
import time

from PySide2 import QtCore, QtGui, QtWidgets

from . import actions as sg_actions
from . import publish_widgets
from . import shotgun
from .. import common
from .. import database
from .. import ui
from ..editor import base

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


def show(formats=('mp4', 'mov')):
    # Set credentials if not already set
    if not all((common.settings.value('sg_auth/login'), common.settings.value('sg_auth/password'))):
        publish_widgets.Credentials().exec_()
        if not all(
                (common.settings.value('sg_auth/login'), common.settings.value('sg_auth/password'))
        ):
            return

    close()
    instance = PublishWidget(formats=formats)
    instance.open()
    return instance


def basename(v):
    return v.strip('.-_')


class PublishWidget(base.BasePropertyEditor):

    #: UI layout definition
    sections = {
        0: {
            'name': 'Publish File',
            'icon': '',
            'color': common.color(common.color_dark_background),
            'groups': {
                0: {
                    0: {
                        'name': None,
                        'key': 'file',
                        'validator': None,
                        'widget': publish_widgets.DropWidget,
                        'no_group': True,
                        'placeholder': 'Drop a file here, or click to select...',
                        'description': 'Drag-and-drop, or click, to add a file to publish to ShotGrid.',
                    },
                    1: {
                        'name': 'Description',
                        'key': 'description',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'Enter a description...',
                        'description': 'The item\'s description.',
                    },
                },
                1: {
                    0: {
                        'name': 'ShotGrid Project',
                        'key': 'project_entity',
                        'validator': None,
                        'widget': publish_widgets.ProjectEntityEditor,
                        'placeholder': '',
                        'description': 'The current bookmark\'s linked ShotGrid Project.',
                        'button': 'Visit',
                    },
                    1: {
                        'name': 'ShotGrid Asset',
                        'key': 'asset_entity',
                        'validator': None,
                        'widget': publish_widgets.AssetEntityEditor,
                        'placeholder': '',
                        'description': 'The current bookmark\'s linked ShotGrid Project.',
                        'button': 'Visit',
                    },
                    2: {
                        'name': 'Login',
                        'key': 'sg_auth/login',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': '',
                        'description': 'Your ShotGrid login name',
                    },
                    3: {
                        'name': 'Password',
                        'key': 'sg_auth/password',
                        'validator': None,
                        'protect': True,
                        'widget': ui.LineEdit,
                        'placeholder': '',
                        'description': 'Your ShotGrid password',
                    },
                },
                2: {
                    0: {
                        'name': 'My Task',
                        'key': 'task_entity',
                        'validator': None,
                        'widget': publish_widgets.TaskEditor,
                        'placeholder': '',
                        'description': 'Select a ShotGrid Task.',
                        'button': 'Visit',
                        'button2': 'Pick',
                    },
                },
                3: {
                    0: {
                        'name': 'ShotGrid Storage',
                        'key': 'storage',
                        'validator': None,
                        'widget': publish_widgets.LocalStorageEditor,
                        'placeholder': '',
                        'description': 'Select a ShotGrid Storage.',
                    },
                    1: {
                        'name': 'ShotGrid File Type',
                        'key': 'file_type',
                        'validator': None,
                        'widget': publish_widgets.PublishedFileTypeEditor,
                        'placeholder': '',
                        'description': 'Select a ShotGrid Published File Type.',
                    },
                },
            },
        },
    }

    def __init__(self, formats=('mp4', 'mov'), parent=None):
        super().__init__(
            None, None, None, asset=None, db_table=database.AssetTable,
            buttons=('Publish', 'Cancel'), alignment=QtCore.Qt.AlignLeft, fallback_thumb='placeholder',
            parent=parent
        )

        self.setWindowTitle('Publish Clip to ShotGrid')

        self.formats = formats
        self._file = None

    def _connect_signals(self):
        super()._connect_signals()

        self._connect_settings_save_signals(common.SECTIONS['shotgrid_publish'])
        self.file_editor.fileSelected.connect(self.set_path)

    @common.error
    @common.debug
    def init_path(self):
        """If the files tab has any valid selection, we'll use it to
        set the file path.

        """
        if common.main_widget is None or not common.main_widget.is_initialized:
            raise RuntimeError('Main widget is not initialized.')

        index = common.selected_index(common.FileTab)
        if not index.isValid():
            raise RuntimeError('No valid selection found.')

        v = index.data(common.PathRole)
        if not v:
            raise RuntimeError('Invalid selection')

        file_info = QtCore.QFileInfo(v)
        ext = file_info.suffix()
        if not ext or ext.lower() not in self.formats:
            self.setDisabled(True)
            raise RuntimeError(f'Unsupported format for this publish: {ext}\n'
                               f'Expected: {", ".join(self.formats)}')

        self.set_path(v)

    @common.error
    @common.debug
    def set_path(self, v):
        """Sets the path of the file to publish.

        Args:
            v (str): Path to a file.

        """
        if not v:
            raise RuntimeError('No path provided.')

        # Get the last entry of the sequence and check if the file is valid
        is_collapsed = common.is_collapsed(v)

        if is_collapsed:
            file_info = QtCore.QFileInfo(common.get_sequence_end_path(v))
            if not file_info.exists():
                raise RuntimeError(f'Could not find file: {file_info.fileName()}')
        else:
            file_info = QtCore.QFileInfo(v)
            if not file_info.exists():
                raise RuntimeError(f'Could not find file: {file_info.fileName()}')

        # Setting the path and thumbnail. The path is stored in `file_editor`.
        # `self.db_source` uses this path to return its value.
        self.file_editor.set_path(file_info.filePath())
        self.thumbnail_editor.update()

        self.init_db_data()

    @property
    def server(self):
        return common.active('server')

    @server.setter
    def server(self, v):
        pass

    @property
    def job(self):
        return common.active('job')

    @job.setter
    def job(self, v):
        pass

    @property
    def root(self):
        return common.active('root')

    @root.setter
    def root(self, v):
        pass

    @property
    def asset(self):
        return common.active('asset')

    @asset.setter
    def asset(self, v):
        pass

    @property
    def task(self):
        """The model's associated task.

        """
        return common.active('task')

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        p = self.file_editor.path()
        if not p:
            return None
        if common.is_collapsed(p):
            return common.proxy_path(p)
        return p

    def init_data(self):
        """Initializes data.

        """
        self.init_path()
        self.init_db_data()

        for k in ('sg_auth', 'shotgrid_publish'):
            self.load_saved_user_settings(common.SECTIONS[k])
            self._connect_settings_save_signals(common.SECTIONS[k])

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        if not self.file_editor.path():
            common.show_message(
                'File not selected.',
                body='Drag-and-drop a file to the top bar before continuing.',
                message_type='error'
            )
            return False

        # Get all arguments needed to publish a Version and a PublishFile
        data = self.get_publish_args()

        # Start version publish
        sg_properties = shotgun.SGProperties(active=True, auth_as_user=True)
        sg_properties.init()
        if not sg_properties.verify(asset=True):
            raise ValueError('Asset not configured.')

        errors = []

        with sg_properties.connection() as sg:
            try:

                common.show_message(
                    'Publishing Version',
                    body='Please wait while the file is being published.',
                    message_type=None,
                    buttons=[],
                    disable_animation=True,
                    parent=self
                )

                existing_version = sg.find_one(
                    'Version', [['code', 'is', data['name']]]
                )

                if existing_version:
                    raise RuntimeError(
                        f'A Version with the name {data["name"]} and version number'
                        f'{data["version"]} already exists.'
                    )

                user_entity = sg.find_one(
                    'HumanUser', [['login', 'is', sg_properties.login]]
                )
                if not user_entity:
                    raise RuntimeError(
                        f'Could not find user {sg_properties.login}.'
                    )

                # Publish steps for creating the Cut, CutInfo and Version entities
                # Get the entity type
                if 'task_entity' in data and data['task_entity']:
                    entity = data['task_entity']
                elif 'asset_entity' in data and data['asset_entity']:
                    entity = data['asset_entity']
                else:
                    raise RuntimeError('No asset or task entity found to associate with the publish.')

                version_data = {
                    'project': data['project_entity'],
                    'code': data['name'],
                    'description': data['description'],
                    'entity': entity,
                    'user': user_entity
                }
                version = sg.create('Version', version_data)

            except Exception as e:
                common.close_message()
                raise RuntimeError(f"Failed to create Version:\n{e}")

            try:
                common.show_message(
                    'Publishing Cut',
                    body='Please wait while the file is being published.',
                    message_type=None,
                    buttons=[],
                    disable_animation=True,
                    parent=self
                )

                cut_data = {
                    'project': data['project_entity'],
                    'entity': entity,
                    'description': data['description'],
                    'version': version
                }
                cut = sg.create('Cut', cut_data)
            except Exception as e:
                cut = None
                errors.append(e)

            try:
                common.show_message(
                    'Publishing Cut Item',
                    body='Please wait while the file is being published.',
                    message_type=None,
                    buttons=[],
                    disable_animation=True,
                    parent=self
                )

                cut_item_data = {
                    'project': data['project_entity'],
                    'cut': cut,
                    'version': version,
                    'sg_cut_in': data['cut_in'],
                    'sg_cut_out': data['cut_out'],
                    'sg_edit_in': data['edit_in'],
                    'sg_edit_out': data['edit_out']
                }
                cut_item = sg.create('CutItem', cut_item_data)
            except Exception as e:
                cut_item = None
                errors.append(e)

            # Publish step for copying local files to their destinations
            try:
                common.show_message(
                    'Publishing Published File',
                    body='Please wait while the file is being published.',
                    message_type=None,
                    buttons=[],
                    disable_animation=True,
                    parent=self
                )

                published_file_data = {
                    'project': data['project_entity'],
                    'code': data['name'],
                    'description': data['description'],
                    'entity': data['asset_entity'],
                    'version': version,
                    'published_file_type': data['published_file_type_entity'],
                    'path': {
                        'local_path': data['file_path']
                    },
                }
                published_file = sg.create('PublishedFile', published_file_data)

                # After creating all PublishedFile entities, update the Version to link them
                sg.update(
                    'Version',
                    version['id'],
                    {
                        'published_files': [
                            {
                                'type': 'PublishedFile',
                                'id': published_file['id']
                            },
                        ],
                        'sg_path_to_movie': published_file['path']['local_path']
                    }
                )
            except Exception as e:
                errors.append(e)

            try:
                common.show_message(
                    'Uploading video file',
                    body='Please wait while the file is being published.',
                    message_type=None,
                    buttons=[],
                    disable_animation=True,
                    parent=self
                )

                # Upload the actual file to ShotGrid
                sg.upload("Version", version['id'], data['file_path'], field_name='sg_uploaded_movie')
            except Exception as e:
                errors.append(e)

        # Update the task's status
        try:
            if data['task_entity']:
                sg.update(
                    'Task', data['task_entity']['id'], {
                        'sg_edit_status': 'tim'
                    }
                )
        except Exception as e:
            errors.append(e)

        common.close_message()

        self.annotate_local_file(data)

        errs = '\n\n'.join([str(e) for e in errors])
        body = f'Publish successful.\n{len(errors)} errors occurred:\n\n{errs}' if errors else 'Publish successful.'
        common.show_message(
            'Publish finished.',
            body=body,
            message_type='success',
            parent=common.main_widget
        )

    def annotate_local_file(self, data):
        # Stamp the file
        # Get the source's description from the database
        db = database.get(*common.active('root', args=True))
        description = db.value(data['file_path'], 'description', database.AssetTable)
        description = description if description else ''

        if '#sg_published' not in description:
            description += f' #sg_published'
        db.set_value(data['file_path'], 'description', description, database.AssetTable)

        # Add a note to the database
        note = (
            f'Publish Log (ShotGrid)'
            f'\nName: {data["name"]}'
            f'\nDescription: {data["description"]}'
            f'\nTime: {time.strftime("%d/%m/%Y %H:%M:%S")}'
            f'\nUser: {common.get_username()}'
        )
        notes = db.value(data['file_path'], 'notes', database.AssetTable)
        notes = notes if notes else {}
        notes[len(notes)] = {
            'title': 'Publish Log (ShotGrid)',
            'body': note,
            'extra_data': {
                'created_by': common.get_username(),
                'created_at': time.strftime('%d/%m/%Y %H:%M:%S'),
                'fold': False,
            }
        }
        db.set_value(data['file_path'], 'notes', notes, database.AssetTable)

    def get_publish_args(self):
        """Get all necessary arguments for publishing.

        """
        data = {}

        def get_publish_name():
            return QtCore.QFileInfo(self.file_editor.path()).completeBaseName()

        def get_version_number():
            # Extract version number from file name. The version number must be a 'v' prefixed
            # number, followed by a number:
            file_name = QtCore.QFileInfo(self.file_editor.path()).filePath()
            match = re.match(r'.*(v[0-9]+.*?)', file_name)
            if not match:
                raise ValueError('Could not extract version number from file name.')
            v = int(match.group(1).strip('.-_v '))
            return v

        def get_task_assignees():
            task_entity = self.task_entity_editor.currentData(role=shotgun.EntityRole)
            k = 'task_assignees'
            if task_entity and k in task_entity and task_entity[k]:
                task_entity[k]
            return []

        def get_thumbnail():
            if not self.thumbnail_editor.image() or self.thumbnail_editor.image().isNull():
                return None

            temp_image_path = f'{common.temp_path()}/temp_sg_thumbnail.{common.thumbnail_format}'
            if QtCore.QFileInfo(temp_image_path).exists():
                if not QtCore.QFile.remove(temp_image_path):
                    print('Could not remove temp image file.')
                    return None

            self.thumbnail_editor.image().save(temp_image_path)
            if not QtCore.QFileInfo(temp_image_path).exists():
                print('Could not save temp image file.')
                return None

            return temp_image_path

        def get_cut_info():
            v = {}
            d = {
                'cut_in': 1,
                'cut_out': 100,
                'edit_in': 1,
                'edit_out': 100
            }
            db = database.get(*common.active('root', args=True))
            with db.connection():
                for k in ('cut_in', 'cut_out', 'edit_in', 'edit_out'):
                    _v = db.value(common.active('asset', path=True), k, database.AssetTable)
                    _v = _v if _v is not None else d[k]
                    v[k] = _v
            return v

        data['name'] = get_publish_name()
        data['file_name'] = QtCore.QFileInfo(self.file_editor.path()).fileName()
        data['file_path'] = self.file_editor.path()
        data['version'] = get_version_number()
        data['description'] = self.description_editor.text()
        data['project_entity'] = self.project_entity_editor.currentData(role=shotgun.EntityRole)
        data['asset_entity'] = self.asset_entity_editor.currentData(role=shotgun.EntityRole)
        data['task_assignees'] = get_task_assignees()
        data['task_entity'] = self.task_entity_editor.currentData(role=shotgun.EntityRole)
        data['published_file_type_entity'] = self.file_type_editor.currentData(role=shotgun.EntityRole)
        data['local_storage_entity'] = self.storage_editor.currentData(role=shotgun.EntityRole)
        data['thumbnail'] = get_thumbnail()
        data.update(get_cut_info())

        # Verify Data
        if not data['name'] or not data['file_name'] or not data['file_path']:
            raise ValueError('File not specified.')

        if not data['version']:
            raise ValueError('Version not specified.')

        if not data['project_entity']:
            raise ValueError('Project not specified.')

        if not data['asset_entity']:
            raise ValueError('Asset not specified.')

        if not data['task_entity']:
            raise ValueError('Task not specified.')

        return data

    @QtCore.Slot()
    @common.error
    @common.debug
    def project_entity_button_clicked(self):
        entity_type = self.project_entity_editor.currentData(shotgun.TypeRole)
        entity_id = self.project_entity_editor.currentData(shotgun.IdRole)

        if not all((entity_type, entity_id)):

            return
        sg_properties = shotgun.SGProperties(active=True, auth_as_user=True)
        sg_properties.init()

        if not sg_properties.verify(connection=True):
            raise ValueError('Bookmark not configured.')

        url = shotgun.ENTITY_URL.format(domain=sg_properties.domain, entity_type=entity_type, entity_id=entity_id)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    @QtCore.Slot()
    @common.error
    @common.debug
    def asset_entity_button_clicked(self):
        entity_type = self.asset_entity_editor.currentData(shotgun.TypeRole)
        entity_id = self.asset_entity_editor.currentData(shotgun.IdRole)

        if not all((entity_type, entity_id)):
            return

        sg_properties = shotgun.SGProperties(active=True, auth_as_user=True)
        sg_properties.init()
        if not sg_properties.verify():
            return

        url = shotgun.ENTITY_URL.format(domain=sg_properties.domain, entity_type=entity_type, entity_id=entity_id)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    @QtCore.Slot()
    @common.error
    @common.debug
    def task_entity_button_clicked(self):
        entity_type = self.task_entity_editor.currentData(shotgun.TypeRole)
        entity_id = self.task_entity_editor.currentData(shotgun.IdRole)

        if not all((entity_type, entity_id)):
            return

        sg_properties = shotgun.SGProperties(active=True, auth_as_user=True)
        sg_properties.init()
        if not sg_properties.verify():
            return

        url = shotgun.ENTITY_URL.format(domain=sg_properties.domain, entity_type=entity_type, entity_id=entity_id)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    @common.error
    @common.debug
    def task_entity_button2_clicked(self):
        sg_actions.show_task_picker()
