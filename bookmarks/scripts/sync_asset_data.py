"""This experimental module allows you to sync data to between ShotGrid and the local asset items.

We can supply a source asset data file, a task mapping file and a template to create folders on the server.
The source asset data file is a JSON file that contains a dictionary of asset data. Each asset is identified by
a key that is the asset name. The values are key/value pairs that correspond to the bookmark item database columns.

For example, the following data would sync with an asset named ``010_0010`` with a description and thumbnail:

.. code-block:: python

    data = {
        '010_0010`: {
            'description': 'A description of the asset',
            'thumbnail': 'path/to/thumbnail.jpg',
            'cut_in': 1001,
            'cut_out': 2000,
            'edit_in': 1001,
            'edit_out': 2000,
            ...
    }

The task mapping file is a JSON file that contains a dictionary of task mapping data. Each entity is made up of a list
of tasks path templates relative to the asset root directory, for example:

.. code-block:: python

    data = {
        'Asset': (
            '{asset}/work/maya/lighting',
            '{asset}/work/maya/animation',
            '{asset}/work/maya/modeling',
        },
        'Shot': (
            '{asset}/work/maya/animation',
            '{asset}/work/maya/lighting',
            '{asset}/work/maya/compositing',
        }
    }

"""
import functools
import json
import os
import shutil
import time
import zipfile

from PySide2 import QtWidgets, QtCore

from .. import actions
from .. import common
from .. import database
from .. import templates
from .. import ui
from ..editor import base
from ..shotgun import shotgun

instance = None


def close():
    """Closes the :class:`PreferenceEditor` widget.

    """
    global instance
    if instance is None:
        return
    try:
        instance.close()
        instance.deleteLater()
    except:
        pass
    instance = None


def show():
    """Shows the :class:`PreferenceEditor` widget.

    """
    close()
    global instance
    instance = SyncWidget()
    common.restore_window_geometry(instance)
    common.restore_window_state(instance)
    return instance


def sg_get_tasks(sg, entity):
    """
    Find all tasks linked to an entity in ShotGrid.

    Args:
        sg (Shotgun): The Shotgun instance.
        entity (dict): The entity to which the tasks are linked.

    Returns:
        list: The tasks found in ShotGrid.
    """
    # Find all tasks linked to the entity
    filters = [['entity', 'is', entity]]
    # Specify the fields to return
    fields = ['id', 'content', 'entity', 'step']
    return sg.find('Task', filters, fields)


SHOT_REGEX = r'.*_([0-9]{3})_([0-9]{4})'


class AssetTypeComboBox(QtWidgets.QComboBox):
    """Editor used to pick a ui scale value.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        size = QtCore.QSize(1, common.Size.RowHeight(0.8))

        self.blockSignals(True)
        for n in ('Asset', 'Shot'):
            self.addItem(n)

            self.setItemData(
                self.count() - 1, n, role=QtCore.Qt.UserRole
            )
            self.setItemData(
                self.count() - 1, size, role=QtCore.Qt.SizeHintRole
            )
        self.blockSignals(False)


SETTINGS_SECTIONS = {
    'sg_sync': (
        'sg_sync/auth_as_user', 'sg_sync/create_folders', 'sg_sync/sync_data_to_shotgrid',
        'sg_sync/sync_data_to_bookmarks',
        'sg_sync/asset_data', 'sg_sync/task_mapping', 'sg_sync/asset_template',),
    'sg_auth': ('sg_auth/login', 'sg_auth/password',)
}


class SyncWidget(base.BasePropertyEditor):

    #: UI layout
    sections = {
        0: {
            'name': 'Options',
            'icon': 'icon',
            'color': common.Color.Green(),
            'groups': {
                0: {
                    0: {
                        'name': None,
                        'key': None,
                        'validator': None,
                        'widget': None,
                        'placeholder': None,
                        'description': None,
                        'help': 'This module allows you to sync data to between ShotGrid and the local asset items.'
                    },
                    1: {
                        'name': 'Asset Type',
                        'key': None,
                        'validator': None,
                        'widget': AssetTypeComboBox,
                        'placeholder': '',
                        'description': 'The type of asset to sync.',
                        'help': 'The type of asset to sync. This will determine the Shotgun entity types to sync and '
                                'how the source asset data is processed.'
                    },
                    2: {
                        'name': 'Authenticate SG as User',
                        'key': 'sg_sync/auth_as_user',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': '',
                        'description': 'Authenticate as the current user on ShotGrid.',
                        'help': 'Authenticate as the current user on ShotGrid.'
                    },
                    3: {
                        'name': 'Create Asset Folders',
                        'key': 'sg_sync/create_folders',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': None,
                        'description': 'Create missing folders.',
                        'help': 'Creates missing asset folders on the server based on the current '
                                'ShotGrid Asset and Shots entities.'
                    },
                    4: {
                        'name': 'Sync Data to ShotGrid',
                        'key': 'sg_sync/sync_data_to_shotgrid',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': None,
                        'description': 'Upload the source asset data to ShotGrid.',
                        'help': 'Upload the source asset data to ShotGrid. '
                                'E.g. edit and cut data for the Shot items.'
                    },
                    5: {
                        'name': 'Sync Data to Bookmarks',
                        'key': 'sg_sync/sync_data_to_bookmarks',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': None,
                        'description': 'Apply properties to the bookmark asset items.',
                        'help': 'Apply properties to the bookmark asset items. '
                                'E.g. edit and cut data for the Shot items.'
                    },
                },
            },
        },
        1: {
            'name': 'Source Data',
            'icon': 'file',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': 'Input Asset Data',
                        'key': 'sg_sync/asset_data',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'button': 'Pick',
                        'placeholder': 'path/to/asset_data.json',
                        'description': 'Path to a previously exported edit data json file.',
                        'help': 'Path to a source data file used to update ShotGrid entities and asset items. '
                                'The file should contain a dictionary with asset names as keys and a dictionary with '
                                'asset '
                                'data as values matching bookmark database columns: '
                                '\n'
                                '\n'
                                '{'
                                '\n'
                                '    "SEQ010_SH0010": {'
                                '\n'
                                '        "description": "My awesome SEQ010_SH0010",'
                                '\n'
                                '        "cut_in": 1001,'
                                '\n'
                                '        "cut_out": 1100,'
                                '\n'
                                '        "thumbnail": "path/to/thumbnail.jpg",'
                                '    }'
                                '\n'
                                '}',
                    },
                    1: {
                        'name': 'SG Task Mapping',
                        'key': 'sg_sync/task_mapping',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'button': 'Pick',
                        'placeholder': 'path/to/task_mapping.json',
                        'description': 'Path to a task mapping json file.',
                        'help': 'Path to a source config file used to map SG tasks to the server. '
                                'The file should contain a dictionary with asset types as keys and a dictionary with '
                                'task '
                                'relative task paths. Make sure the task names correspond with the task names on '
                                'ShotGrid: '
                                '\n'
                                '\n'
                                '{'
                                '\n'
                                '    "Shot": ('
                                '\n'
                                '        "{asset}/3DANI/work/maya/anim,"'
                                '\n'
                                '        "{asset}/LAY/work/maya/layout,"'
                                '\n'
                                '    ),'
                                '\n'
                                '   "Asset": ('
                                '\n'
                                '        "{asset}/3DANI/work/maya/modeling",'
                                '\n'
                                '        "{asset}/3DANI/work/maya/rigging"'
                                '\n'
                                '    )'
                                '\n'
                                '}',
                    },
                },
            },
        },
        2: {
            'name': 'Asset Template',
            'icon': 'folder',
            'color': common.Color.DarkBackground(),
            'groups': {
                1: {
                    0: {
                        'name': 'Asset Template',
                        'key': 'sg_sync/asset_template',
                        'validator': None,
                        'widget': functools.partial(
                            templates.TemplatesWidget, templates.AssetTemplateMode
                        ),
                        'placeholder': None,
                        'description': 'The asset template used to create missing assets on the server.',
                        'help': 'The asset template used to create missing assets on the server.',
                    },
                },
            },
        },
        3: {
            'name': 'ShotGrid',
            'icon': 'sg',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': 'Domain',
                        'key': 'sg_domain',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'Domain, for example, https://mystudio.shotgunstudio.com',
                        'description': 'The domain, including http:// or https://, '
                                       'used by shotgun. for example, '
                                       '\'https://mystudio.shotgunstudio.com\'',
                    },
                },
                1: {
                    0: {
                        'name': 'Script Name',
                        'key': 'sg_scriptname',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'my-sg-script',
                        'description': 'A name of a ShotGrid Script.',
                    },
                    1: {
                        'name': 'API Key',
                        'key': 'sg_api_key',
                        'validator': None,
                        'protect': True,
                        'widget': ui.LineEdit,
                        'placeholder': 'abcdefghijklmno3bqr*1',
                        'description': 'A ShotGrid Script API Key, '
                                       'for example, \'abcdefghijklmno3bqr*1\'.\n\nA valid '
                                       'script has to be set up for your organisation '
                                       'for Bookmarks to be able to connect to '
                                       'ShotGrid. Consult the ShotGrid documentation for '
                                       'details on how to set this up.',
                        'help': 'Make sure ShotGrid has a valid API Script set up. This '
                                'can be done from the ShotGrid Admin - Scripts option.',
                    },
                },
                2: {
                    0: {
                        'name': 'Login',
                        'key': 'sg_auth/login',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': '',
                        'description': 'Your ShotGrid login name',
                    },
                    1: {
                        'name': 'Password',
                        'key': 'sg_auth/password',
                        'validator': None,
                        'protect': True,
                        'widget': ui.LineEdit,
                        'placeholder': '',
                        'description': 'Your ShotGrid password',
                    },
                },
            },
        },
    }

    def __init__(self, parent=None):
        super().__init__(
            common.active('server'), common.active('job'), common.active('root'),
            db_table=database.BookmarkTable, fallback_thumb='sg', parent=parent
        )

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        return common.active('root', path=True)

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        if not common.active('root', args=True):
            common.show_message(
                'A bookmark item must be active before continuing.', message_type='error', )
            return False

        if common.show_message(
                'Are you sure you want to continue?',
                body='We will sync the source asset data to ShotGrid, create missing folders on the server and update '
                     'bookmark items', message_type=None, buttons=[common.YesButton, common.NoButton],
                modal=True, ) == QtWidgets.QDialog.Rejected:
            return False

        if not self.asset_type_editor.currentText():
            common.show_message(
                'No asset type selected.', 'Please select an asset type to continue.', message_type='error', )
            return False

        if (
                self.sg_sync_create_folders_editor.isChecked() and not
        self.sg_sync_asset_template_editor.current_template_path()):
            common.show_message(
                'No asset template selected.', 'Please select an asset template to continue.', message_type='error', )
            return False

        if not self.sg_sync_asset_data_editor.text():
            common.show_message(
                'No asset data selected.', 'Please select an asset data file to continue.', message_type='error', )
            return False

        if not self.sg_sync_task_mapping_editor.text():
            common.show_message(
                'No task mapping selected.', 'Please select a task mapping file to continue.', message_type='error', )
            return False

        self.save_changed_data_to_db()

        if os.path.isfile(f'{self.sg_sync_asset_data_editor.text()}'):
            asset_data = json.load(open(f'{self.sg_sync_asset_data_editor.text()}', 'r'))
        else:
            common.show_message(
                'Asset data file not found.', body='Please select a valid asset data file to continue.',
                message_type='error', )
            return False

        if os.path.isfile(f'{self.sg_sync_asset_data_editor.text()}'):
            task_mapping = json.load(open(f'{self.sg_sync_task_mapping_editor.text()}', 'r'))
        else:
            common.show_message(
                'Task mapping file not found.', body='Please select a valid task mapping file to continue.',
                message_type='error', )
            return False

        asset_template_path = self.sg_sync_asset_template_editor.current_template_path()
        if not os.path.isfile(asset_template_path):
            common.show_message(
                'Workspace template file not found.', body='Please select a valid workspace template file to continue.',
                message_type='error', )
            return False

        db = database.get(*common.active('root', args=True))
        prefix = db.value(db.source(), 'prefix', database.BookmarkTable)
        if not prefix:
            common.show_message(
                'No prefix set', body='Please set a prefix for the active bookmark item to continue.',
                message_type='error', )
            return

        # Init Shotgun
        sgproperties = shotgun.SGProperties(
            active=True, auth_as_user=self.sg_sync_auth_as_user_editor.isChecked()
        )
        sgproperties.init()

        if not sgproperties.verify(connection=True):
            common.show_message(
                'ShotGrid connection failed.', message_type='error', )
            return False

        if not sgproperties.verify(bookmark=True):
            common.show_message(
                'Active bookmark item is not configured to use ShotGrid.', message_type='error', )
            return False

        with sgproperties.connection() as sg:
            try:
                self.process_entities(
                    sg, sgproperties, self.asset_type_editor.currentText(), prefix, asset_data, task_mapping,
                    asset_template_path
                )
            finally:
                common.close_message()

    @common.error
    @common.debug
    def init_data(self, *args, **kwargs):
        """Initializes data.

        """
        self.init_db_data()
        self.thumbnail_editor.setDisabled(True)
        for k in SETTINGS_SECTIONS:
            self.load_saved_user_settings(SETTINGS_SECTIONS[k])
            self._connect_settings_save_signals(SETTINGS_SECTIONS[k])

        # Guess asset type
        if 'asset' in self.db_source().lower():
            self.asset_type_editor.setCurrentText('Asset')
        elif 'shot' in self.db_source().lower():
            self.asset_type_editor.setCurrentText('Shot')
        elif 'sequence' in self.db_source().lower():
            self.asset_type_editor.setCurrentText('Shot')
        else:
            self.asset_type_editor.setCurrentIndex(-1)

    @common.error
    @common.debug
    def sg_sync_asset_data_button_clicked(self):
        """Opens a file dialog to select a json file.

        """
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select a json file', '', 'Json Files (*.json)'
        )[0]
        if not file_path:
            return
        self.sg_sync_asset_data_editor.setText(file_path)

    @common.error
    @common.debug
    def sg_sync_task_mapping_button_clicked(self):
        """Opens a file dialog to select a json file.

        """
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select a json file', '', 'Json Files (*.json)'
        )[0]
        if not file_path:
            return
        self.sg_sync_task_mapping_editor.setText(file_path)

    def patch_asset(self, template_path, destination):
        """
        Check if a destination directory exists and creates it if it doesn't.
        It also extracts a zip file to this directory.

        Args:
            destination (str): The destination directory.

        """
        # Check if destination directory exists, if not create it
        if not os.path.exists(destination):
            print(f'{destination} does not exist, creating.')
            os.makedirs(destination)

        # Open the zip file
        with zipfile.ZipFile(template_path, 'r') as zip_ref:
            for file in zip_ref.namelist():
                file_path_after_zip = os.path.join(destination, file)
                if not os.path.exists(file_path_after_zip):
                    zip_ref.extract(file, destination)
                    print(f'Creating {file_path_after_zip}')

    def process_entities(
            self, sg, sgproperties, source_entity_type, prefix, asset_data, task_mapping, asset_template_path, ):
        common.check_type(asset_data, dict)
        common.check_type(task_mapping, dict)
        common.check_type(source_entity_type, str)
        common.check_type(prefix, str)

        common.show_message(
            'Processing entities',
            body='This may take a while, please wait...',
            message_type=None,
            buttons=[],
            disable_animation=True,
        )

        if not asset_data:
            raise RuntimeError('No asset data found!')

        if not task_mapping:
            raise RuntimeError('No task mapping found!')

        if source_entity_type not in task_mapping:
            raise RuntimeError(f'No task mapping found for "{source_entity_type}"\n\n:{task_mapping}')

        project_entity = sg.find_one(
            'Project', [['id', 'is', sgproperties.bookmark_id], ], )
        if not project_entity:
            raise RuntimeError('Could not find the ShotGrid project!')

        schema = sg.schema_field_read(source_entity_type)

        # Get all ShotGrid entities matching the source type
        if source_entity_type == 'Shot':
            entities = sg.find(
                source_entity_type, [['project', 'is', project_entity], ['code', 'contains', prefix]],
                ['id', 'code', 'type', 'description', 'sg_cut_in', 'sg_cut_out']
            )
        elif source_entity_type == 'Asset':
            entities = sg.find(
                source_entity_type, [['project', 'is', project_entity], ],
                ['id', 'code', 'type', 'description', 'sg_asset_type']
            )
        else:
            raise RuntimeError('Unknown entity type')

        if not entities:
            common.show_message(
                f'No {source_entity_type} found for {project_entity["name"]}.', message_type='error', modal=True, )

        links = {}
        items_data = {}

        bookmark_root = common.active('root', path=True)

        if '_' in prefix:
            _prefix = prefix.split('_')[1]
        else:
            _prefix = prefix

        # Get all ShotGrid entities
        for n, entity in enumerate(entities):
            common.message_widget.title_label.setText(f'Processing {entity["code"]} ({n + 1} of {len(entities)})')
            QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

            if source_entity_type == 'Shot':
                seq, shot = common.get_sequence_and_shot(entity['code'])

                if not all([seq, shot]):
                    print(f'Skipping {entity["code"]}')
                    continue

                root = f'{bookmark_root}/{_prefix}_{seq}'
                k = f'{_prefix}_{seq}'
                print(f'Found candidate: {entity["code"]} -> {root}')

            elif source_entity_type == 'Asset':
                if 'sg_asset_type' not in entity:
                    print(f'Asset {entity["code"]} has no asset type!')
                    continue

                root = f'{bookmark_root}/{entity["sg_asset_type"]}'
                k = entity['sg_asset_type']
                print(f'Found candidate: {entity["code"]} -> {root}')
            else:
                raise RuntimeError(f'Unknown entity type: {source_entity_type}')

            if not QtCore.QFileInfo(root).exists():
                raise RuntimeError(f'Root directory does not exist: {root}')

            if k not in links:
                links[k] = []

            # Get all tasks associated with the entity
            task_entities = sg.find(
                'Task', [['entity', 'is', entity]], ['id', 'content', 'entity', 'step']
            )
            if not task_entities:
                print(f'No tasks found for {entity["code"]}, skipping.')
                continue

            # Match source asset data with the ShotGrid entity using their names
            asset_data_item = [f for f in asset_data if f['name'].lower() in entity['code'].lower()]

            if len(asset_data_item) > 1:
                print(f'Multiple asset data items found for {entity["code"]}, skipping: {", ".join(asset_data_item)}')
                continue

            if not asset_data_item:
                print(f'No asset data item found for {entity["code"]}, skipping.')
            else:
                asset_data_item = asset_data_item[0]

            thumbnail_path = None

            if self.sg_sync_sync_data_to_shotgrid_editor.isChecked():

                update_data = {}

                if asset_data_item and 'cut_in' in asset_data_item and 'sg_cut_in' in schema:
                    update_data['sg_cut_in'] = int(asset_data_item['cut_in'])
                else:
                    print(f'Skipping invalid field: cut_in')

                if asset_data_item and 'cut_out' in asset_data_item and 'sg_cut_out' in schema:
                    update_data['sg_cut_out'] = int(asset_data_item['cut_out'])
                else:
                    print(f'Skipping invalid field: cut_out')

                if asset_data_item and 'description' in asset_data_item and 'description' in schema:
                    update_data['description'] = asset_data_item['description']
                else:
                    print(f'Skipping invalid field: description')

                if update_data:
                    common.message_widget.body_label.setText(f'Updating ShotGrid entity...')
                    QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

                    sg.update(
                        'Shot', entity['id'], update_data, )

                    print(f'Updated {entity["code"]} with {update_data}')

                # Check the parent folder for a thumbnail
                _dir = QtCore.QFileInfo(self.sg_sync_asset_data_editor.text()).dir().path()
                thumbnail_path = f'{_dir}/{entity["code"]}.png'
                if QtCore.QFileInfo(thumbnail_path).exists():
                    print(f'Uploading thumbnail for {entity["code"]}')

                    common.message_widget.body_label.setText(f'Uploading ShotGrid thumbnail...')
                    QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

                    sg.upload_thumbnail('Shot', entity['id'], thumbnail_path)

            # Collect all relative paths for all work items
            for task_path in task_mapping[source_entity_type]:
                if '{asset}' not in task_path:
                    raise RuntimeError(f'Invalid task path: {task_path}. Template must contain {{asset}}.')

                task_path = task_path.format(asset=entity['code'])
                links[k].append(task_path)

                # Prepare asset data
                items_data[task_path] = {}
                items_data[task_path]['thumbnail'] = thumbnail_path
                items_data[task_path]['name'] = entity['code']
                items_data[task_path]['sg_id'] = int(entity['id'])
                items_data[task_path]['sg_name'] = entity['code']
                items_data[task_path]['sg_type'] = entity['type']

                if asset_data_item and 'cut_in' in asset_data_item:
                    items_data[task_path]['cut_in'] = int(asset_data_item['cut_in'])

                if asset_data_item and 'cut_out' in asset_data_item:
                    items_data[task_path]['cut_out'] = int(asset_data_item['cut_out'])

                if asset_data_item and 'cut_in' in asset_data_item and 'cut_out' in asset_data_item:
                    items_data[task_path]['cut_duration'] = int(asset_data_item['cut_out']) - int(
                        asset_data_item['cut_in']
                    ) + 1

                if asset_data_item and 'edit_in' in asset_data_item:
                    items_data[task_path]['edit_in'] = int(asset_data_item['edit_in'])

                if asset_data_item and 'edit_out' in asset_data_item:
                    items_data[task_path]['edit_out'] = int(asset_data_item['edit_out'])

                if asset_data_item and 'edit_in' in asset_data_item and 'edit_out' in asset_data_item:
                    items_data[task_path]['edit_duration'] = int(asset_data_item['edit_out']) - int(
                        asset_data_item['edit_in']
                    ) + 1

                if asset_data_item and 'description' in asset_data_item:
                    items_data[task_path]['description'] = asset_data_item['description']

                common.message_widget.body_label.setText(f'Finding tasks...')
                QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

                # Find the associated task entity
                for task_entity in task_entities:
                    if task_entity['content'].lower() in task_path.lower():
                        items_data[task_path]['sg_task_name'] = task_entity['content']
                        items_data[task_path]['sg_task_id'] = task_entity['id']
                        print(f'Found matching task: {task_entity["content"]}')

                # Create any missing files and folders inside the Maya work folders
                if self.sg_sync_create_folders_editor.isChecked():
                    common.message_widget.body_label.setText(f'Making folders...')
                    QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

                    print(f'Patching {root}/{task_path}')
                    self.patch_asset(asset_template_path, f'{root}/{task_path}')

                    # Check if the audio file exists
                    audio_file_path = f"{bookmark_root}/{entity['code']}.wav"

                    if os.path.exists(audio_file_path):
                        print(f'Copying audio file {entity["code"]}.wav to {root}/{task_path}/audio/'
                              f'{entity["code"]}.wav')
                        task_audio_dir = os.path.join(f'{root}', task_path, 'audio')
                        destination_audio_path = os.path.join(task_audio_dir, f"{entity['code']}.wav")

                        # Create 'audio' folder if it doesn't exist
                        if not os.path.exists(task_audio_dir):
                            os.makedirs(task_audio_dir)

                        # Copy the audio file
                        shutil.copy2(audio_file_path, destination_audio_path)

        # Update the .link files for Bookmarks
        if self.sg_sync_sync_data_to_bookmarks_editor.isChecked():
            common.message_widget.title_label.setText(f'Adding asset links...')
            common.message_widget.body_label.setText('')
            QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

            for k in links:
                if not os.path.isdir(f'{bookmark_root}/{k}'):
                    continue
                p = f'{bookmark_root}/{k}/.links'
                print(f'Saving links to {p}:\n{sorted(links[k])}')
                with open(p, 'w') as f:
                    f.write(f'[links]\nasset={",".join(sorted(links[k]))}')

            # Save data to json file in the source same source folder as the asset data
            file_info = QtCore.QFileInfo(self.sg_sync_asset_data_editor.text())
            json_path = f'{file_info.dir().path()}/{file_info.baseName()}_{source_entity_type.lower()}_properties.json'

            print(f'Saving asset data to {json_path}')
            with open(json_path, 'w') as f:
                json.dump(items_data, f, ensure_ascii=False, indent=4)

            if not file_info.exists():
                raise RuntimeError(f'Failed to save asset data to {json_path}')

            # Reset the filters
            common.message_widget.title_label.setText(f'Updating asset items...')
            QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

            common.model(common.AssetTab).set_filter_text('')
            # Refresh model
            actions.refresh(common.AssetTab)

            # Wait for the model to refresh
            common.message_widget.body_label.setText(f'Waiting for refresh...')
            QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

            model = common.source_model(common.AssetTab)
            p = model.source_path()
            k = model.task()
            t = model.data_type()

            if not p or not all(p) or not k or t is None:
                raise RuntimeError(f'Failed to get valid path, task, and data type from model: {p}, {k}, {t}')

            data = common.get_data(p, k, t)

            max_sleep = 15
            _time_slept = 0
            _increment = 0.1
            while not data.loaded:
                QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
                if _time_slept >= max_sleep:
                    break
                _time_slept += _increment
                time.sleep(_increment)

            if not data.loaded:
                raise RuntimeError(f'Failed to load data: {p}, {k}, {t}')

            # Load properties
            actions.import_json_asset_properties(path=json_path, prompt=False)

        common.close_message()
        common.show_message('Sync Complete', message_type='success')


def run():
    w = SyncWidget()
    w.show()


if __name__ == '__main__':
    run()
