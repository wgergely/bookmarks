"""The publishing widget used by Bookmarks to create new PublishedFiles and Version
entities on ShotGrid.

Our publishing logic creates `Version` and `PublishFile` entities linked against
the current active project and asset and uploads any custom thumbnails set.

"""
import os

from PySide2 import QtCore, QtGui, QtWidgets

from . import actions as sg_actions
from . import publish_widgets
from . import shotgun
from .. import common
from .. import database
from .. import images
from .. import log
from .. import ui
from ..editor import base

instance = None

#: Valid movie formats
MOVIE_FORMATS = ('mp4', 'mov')

#: Valid sequence formats
IMAGE_FORMATS = ('jpg', 'png')


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


def show():
    # Set credentials if not already set
    if not all((common.settings.value('shotgrid_publish/login'), common.settings.value('shotgrid_publish/password'))):
        publish_widgets.Credentials().exec_()
        if not all(
                (common.settings.value('shotgrid_publish/login'), common.settings.value('shotgrid_publish/password'))
        ):
            return

    close()
    instance = PublishWidget()
    instance.open()
    return instance


def basename(v):
    return v.strip('.').strip('-').strip('_')


#: UI layout definition
SECTIONS = {
    0: {
        'name': 'Publish File',
        'icon': '',
        'color': common.color(common.color_dark_background),
        'groups': {
            0: {
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
            },
            1: {
                0: {
                    'name': 'Login',
                    'key': 'shotgrid_publish_login',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': '',
                    'description': 'Your ShotGrid login name',
                },
                1: {
                    'name': 'Password',
                    'key': 'shotgrid_publish_password',
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
                },
                1: {
                    'name': 'Publish Status',
                    'key': 'status',
                    'validator': None,
                    'widget': publish_widgets.StatusEditor,
                    'placeholder': '',
                    'description': 'Select a ShotGrid Status.',
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
            4: {
                0: {
                    'name': 'Description',
                    'key': 'description',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Enter a description...',
                    'description': 'The item\'s description.',
                },
            },
            5: {
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
                    'name': 'Image Sequence',
                    'key': 'version_sequence',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Enter a path to your image sequence',
                    'description': 'Enter the path to the first image of an image sequence.',
                    'button': 'Pick',
                },
                2: {
                    'name': 'Movie File',
                    'key': 'version_movie',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Enter a path to your movie',
                    'description': 'Path to an *.mp4 movie file to upload as a reviewable version.',
                    'button': 'Pick',
                },
                3: {
                    'name': 'Cache File',
                    'key': 'version_cache',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Enter a path to your geometry cache',
                    'description': 'Path to a File Cache to publish.',
                    'button': 'Pick',
                },
            },
        },
    },
}


class PublishWidget(base.BasePropertyEditor):
    def __init__(self, parent=None):
        super().__init__(
            SECTIONS, None, None, None, asset=None, db_table=database.AssetTable,
            buttons=('Publish', 'Cancel'), alignment=QtCore.Qt.AlignLeft, fallback_thumb='placeholder',
            parent=parent
        )

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
            return

        widget = common.widget(common.FileTab)
        index = common.get_selected_index(widget)
        if not index.isValid():
            return

        v = index.data(common.PathRole)
        if not v:
            return

        self.set_path(v)

    @common.error
    @common.debug
    def set_path(self, v):
        """Sets the path of the file to publish.

        Args:
            v (str): Path to a file.

        """
        if not v:
            return

        file_info = QtCore.QFileInfo(v)
        ext = file_info.suffix()
        if not ext:
            raise RuntimeError(f'File has no extension: {v}')

        # Get the last entry of the sequence and check if the file is valid
        is_collapsed = common.is_collapsed(v)
        if is_collapsed:
            file_info = QtCore.QFileInfo(common.get_sequence_start_path(v))
            if not file_info.exists():
                raise RuntimeError(f'Could not find file: {common.get_sequence_start_path(v)}')

        # Setting the path and thumbnail. The path is stored in `file_editor`.
        # `self.db_source` uses this path to return its value.
        self.file_editor.set_path(file_info.filePath())
        self.thumbnail_editor.update()
        self.init_db_data()

        # Input is an image sequence
        fstyle_sequence = ''
        mov_path = ''
        mov_tc_path = ''

        # If the input is a valid image sequence, check if there is a movie
        if is_collapsed and ext.lower() in IMAGE_FORMATS:
            seq = common.get_sequence(common.get_sequence_start_path(v))
            if seq:
                fstyle_sequence = f'{is_collapsed.group(1)}{f"%0{len(seq.group(2))}d"}{is_collapsed.group(3)}'
                log.success(f'Image sequence detected: {fstyle_sequence}')

                for _ext in MOVIE_FORMATS:
                    _mov_path = f'{seq.group(1).strip("._- ")}{seq.group(3)}.{_ext}'

                    if QtCore.QFileInfo(_mov_path).exists():
                        mov_path = _mov_path
                        log.success(f'Movie detected:  {mov_path}')

                    _mov_path = f'{seq.group(1).strip("._- ")}{seq.group(3)}_tc.{_ext}'
                    if QtCore.QFileInfo(_mov_path).exists():
                        mov_tc_path = _mov_path
                        log.success(f'Movie (TC) detected:  {mov_tc_path}')

        # If the input is a movie check for image sequence and TC
        elif not is_collapsed and ext.lower() in MOVIE_FORMATS:
            mov_path = file_info.filePath()
            log.success(f'Movie detected:  {mov_path}')

            mov_tc_path = f'{file_info.path()}/{file_info.baseName()}_tc.{file_info.suffix()}'
            if QtCore.QFileInfo(mov_tc_path).exists():
                log.success(f'Movie (TC) detected:  {mov_tc_path}')

            # Check if there is an image sequence
            for entry in os.scandir(file_info.path()):
                if (
                        entry.is_file() and entry.name.startswith(file_info.baseName()) and
                        entry.name.split('.')[-1].lower() in IMAGE_FORMATS
                ):
                    print(entry.path)
                    seq = common.get_sequence(entry.path.replace('\\', '/'))
                    if seq:
                        fstyle_sequence = f'{seq.group(1)}{f"%0{len(seq.group(2))}d"}{seq.group(3)}.{seq.group(4)}'
                        log.success(f'Image sequence detected: {fstyle_sequence}')
                        break

        # Prefer TC over non-TC
        mov_path = mov_tc_path if mov_tc_path else mov_path
        self.version_sequence_editor.setText(fstyle_sequence)
        self.version_movie_editor.setText(mov_path)

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
        self.load_saved_user_settings(common.SECTIONS['shotgrid_publish'])

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        if not self.file_editor.path():
            ui.MessageBox('File not selected.', 'Drag-and-drop a file to the top bar before continuing.').open()
            return False

        # Get all arguments needed to publish a Version and a PublishFile
        kwargs = self.get_publish_args()

        # Start version publish
        sg_properties = shotgun.ShotgunProperties(
            active=True,
            login=common.settings.value('shotgrid_publish/login'),
            password=common.settings.value('shotgrid_publish/password')
        )
        sg_properties.init()
        if not sg_properties.verify(asset=True):
            raise ValueError('Asset not configured.')

        with shotgun.connection(sg_properties) as sg:
            kwargs['sg'] = sg

            print (
                f'ShotGrid properties:\n'
                f'domain: {sg_properties.domain}\n'
                f'script: {sg_properties.script}\n'
                f'key: {sg_properties.key}\n'
                f'login: {sg_properties.login}\n'
                f'password: {sg_properties.password}'
            )

            mbox = ui.MessageBox('Creating Version...', no_buttons=True)
            mbox.open()
            QtWidgets.QApplication.instance().processEvents()

            try:
                version_entity = sg_actions.create_version(
                    kwargs['sg'], kwargs['file_name'], kwargs['file_path'],
                    kwargs['version_movie'], kwargs['version_sequence'], kwargs['version_cache'],
                    kwargs['description'],
                    kwargs['project_entity'], kwargs['asset_entity'], kwargs['task_entity'],
                    kwargs['user_entity'],
                    kwargs['status_entity'], )
                kwargs['version_entity'] = version_entity
            finally:
                mbox.close()

            mbox = ui.MessageBox('Uploading movie...', no_buttons=True)
            mbox.open()
            QtWidgets.QApplication.instance().processEvents()
            try:
                self._upload_movie(**kwargs)
            finally:
                mbox.close()

            mbox = ui.MessageBox('Publishing File...', no_buttons=True)
            mbox.open()
            QtWidgets.QApplication.instance().processEvents()
            try:
                published_file_entity = self._create_published_file(**kwargs)
            finally:
                mbox.close()

            info = {
                'id': published_file_entity['id'],
                'name': published_file_entity['name'],
                'version_number': published_file_entity['version_number'],
            }

            import pprint
            mbox = ui.MessageBox(
                'Success.',
                '{} was published successfully as:\n\n{}'.format(
                    published_file_entity['code'],
                    pprint.pformat(
                        info, indent=1,
                        depth=3,
                        width=2
                    )
                )
            ).open()

            return True

    def get_publish_args(self):
        """Get all necessary arguments for publishing.

        """
        # Code
        file_name = QtCore.QFileInfo(self.file_editor.path()).fileName()
        file_path = self.file_editor.path()

        # Remove the version from the file name
        name = file_name
        version = 0
        seq = common.get_sequence(file_path)
        if seq:
            version = int(seq.group(2))
            name = '{}{}.{}'.format(
                seq.group(1).rstrip('_v').rstrip('-v').rstrip('.v').rstrip(' v').strip(),
                seq.group(3), seq.group(4), )
            name = QtCore.QFileInfo(name).fileName()

        description = self.description_editor.text()

        project_entity = self.project_entity_editor.currentData(role=shotgun.EntityRole)
        asset_entity = self.asset_entity_editor.currentData(role=shotgun.EntityRole)

        task_entity = self.task_entity_editor.currentData(role=shotgun.EntityRole)
        # let's extract the user information from the task. If the task has multiple
        # users assigned we'll prompt the user to pick one from a list:
        k = 'task_assignees'
        if task_entity and k in task_entity and task_entity[k]:
            if len(task_entity[k]) > 1:
                items = [f['name'] if 'name' in f else f['id'] for f in task_entity[k]]
                item = QtWidgets.QInputDialog.getItems(
                    self, 'Select User', 'Users:', items, current=0,
                    editable=False
                )
                idx = items.index(item)
                user_entity = task_entity[k][idx]
            else:
                user_entity = task_entity[k][0]
        else:
            user_entity = None

        published_file_type_entity = self.file_type_editor.currentData(role=shotgun.EntityRole)
        local_storage_entity = self.storage_editor.currentData(role=shotgun.EntityRole)
        status_entity = self.status_editor.currentData(role=shotgun.EntityRole)

        version_sequence = self.version_sequence_editor.text()
        version_movie = self.version_movie_editor.text()
        version_cache = self.version_cache_editor.text()

        return {
            'name': name,
            'file_name': file_name,
            'file_path': file_path,
            'version': version,
            'description': description,
            'project_entity': project_entity,
            'asset_entity': asset_entity,
            'user_entity': user_entity,
            'task_entity': task_entity,
            'status_entity': status_entity,
            'published_file_type_entity': published_file_type_entity,
            'local_storage_entity': local_storage_entity,
            'version_sequence': version_sequence,
            'version_movie': version_movie,
            'version_cache': version_cache,
        }

    def _upload_movie(self, **kwargs):
        """Upload the specified movie file to link with the Version."""
        if not kwargs['version_movie']:
            return None
        return sg_actions.upload_movie(kwargs['sg'], kwargs['version_entity'], kwargs['version_movie'])

    def _create_published_file(self, **kwargs):
        return sg_actions.create_published_file(
            kwargs['sg'], kwargs['version_entity'], kwargs['name'],
            kwargs['file_name'], kwargs['file_path'], kwargs['version'],
            kwargs['description'],
            kwargs['project_entity'], kwargs['asset_entity'], kwargs['user_entity'],
            kwargs['task_entity'],
            kwargs['published_file_type_entity'], kwargs['local_storage_entity'], )

    @QtCore.Slot()
    @common.error
    @common.debug
    def project_entity_button_clicked(self):
        entity_type = self.project_entity_editor.currentData(shotgun.TypeRole)
        entity_id = self.project_entity_editor.currentData(shotgun.IdRole)

        if not all((entity_type, entity_id)):

            return
        sg_properties = shotgun.ShotgunProperties(
            active=True,
            login=common.settings.value('shotgrid_publish/login'),
            password=common.settings.value('shotgrid_publish/password')
        )
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

        sg_properties = shotgun.ShotgunProperties(
            active=True,
            login=common.settings.value('shotgrid_publish/login'),
            password=common.settings.value('shotgrid_publish/password')
        )
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

        sg_properties = shotgun.ShotgunProperties(
            active=True,
            login=common.settings.value('shotgrid_publish/login'),
            password=common.settings.value('shotgrid_publish/password')
        )
        sg_properties.init()
        if not sg_properties.verify():
            return

        url = shotgun.ENTITY_URL.format(domain=sg_properties.domain, entity_type=entity_type, entity_id=entity_id)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    @QtCore.Slot()
    @common.error
    @common.debug
    def version_sequence_button_clicked(self):
        args = (self.server, self.job, self.root, self.asset)
        if all(args):
            _dir = '/'.join(args)
        args = (self.server, self.job, self.root, self.asset, self.task)
        if all(args):
            _dir = '/'.join(args)

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption='Select an image sequence to include',
            dir=_dir, filter=images.get_oiio_namefilters()
        )
        if not file_path:
            return
        seq = common.get_sequence(file_path)
        if not seq:
            raise ValueError('The selected file does not seem like an image sequence.')

        v = '{}{}{}.{}'.format(seq.group(1), '%0{}d'.format(len(seq.group(2))), seq.group(3), seq.group(4))
        self.version_sequence_editor.setText(v)

    @QtCore.Slot()
    @common.error
    @common.debug
    def version_movie_button_clicked(self):
        args = (self.server, self.job, self.root, self.asset)
        if all(args):
            _dir = '/'.join(args)
        args = (self.server, self.job, self.root, self.asset, self.task)
        if all(args):
            _dir = '/'.join(args)

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption='Select a movie to include', dir=_dir,
            filter='Movie Files (*.mov *.mp4)', )
        if not file_path:
            return
        self.version_movie_editor.setText(file_path)

    @QtCore.Slot()
    @common.error
    @common.debug
    def version_cache_button_clicked(self):
        args = (self.server, self.job, self.root, self.asset)
        if all(args):
            _dir = '/'.join(args)
        args = (self.server, self.job, self.root, self.asset, self.task)
        if all(args):
            _dir = '/'.join(args)

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption='Select a cache to include',
            dir=_dir, )
        if not file_path:
            return
        self.version_cache_editor.setText(file_path)
