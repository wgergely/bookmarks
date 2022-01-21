# -*- coding: utf-8 -*-
"""The publish widget used by Bookmarks to create new PublishedFiles and Version
entities.

Our publish logic creates `Version` and `PublishFile` entites linked against
the current active project and asset and uploads any custom thumbnails set.

"""
import os

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import ui
from .. import database

from .. import images
from ..editor import base
from ..tokens import tokens

from . import shotgun
from . import actions as sg_actions
from . import publish_widgets


instance = None


MOV_FORMATS = (
    'mp4',
    'mov'
)
SEQ_FORMATS = (
    'jpg',
    'png'
)


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
    global instance

    close()
    instance = PublishWidget()
    instance.open()
    return instance


def basename(v):
    return v.strip('.').strip('-').strip('_')


SECTIONS = {
    0: {
        'name': 'Publish File',
        'icon': '',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'Shotgun Project',
                    'key': 'project_entity',
                    'validator': None,
                    'widget': publish_widgets.ProjectEntityEditor,
                    'placeholder': '',
                    'description': 'The current bookmark\'s linked Shotgun Project.',
                    'button': 'Visit',
                },
                1: {
                    'name': 'Shotgun Asset',
                    'key': 'asset_entity',
                    'validator': None,
                    'widget': publish_widgets.AssetEntityEditor,
                    'placeholder': '',
                    'description': 'The current bookmark\'s linked Shotgun Project.',
                    'button': 'Visit',
                },
            },
            1: {
                0: {
                    'name': 'My Task',
                    'key': 'task_entity',
                    'validator': None,
                    'widget': publish_widgets.TaskEditor,
                    'placeholder': '',
                    'description': 'Select a Shotgun Task.',
                    'button': 'Visit',
                },
                1: {
                    'name': 'Publish Status',
                    'key': 'status',
                    'validator': None,
                    'widget': publish_widgets.StatusEditor,
                    'placeholder': '',
                    'description': 'Select a Shotgun Status.',
                },
            },
            2: {
                0: {
                    'name': 'Shotgun Storage',
                    'key': 'storage',
                    'validator': None,
                    'widget': publish_widgets.LocalStorageEditor,
                    'placeholder': '',
                    'description': 'Select a Shotgun Storage.',
                },
                1: {
                    'name': 'Shotgun File Type',
                    'key': 'file_type',
                    'validator': None,
                    'widget': publish_widgets.PublishedFileTypeEditor,
                    'placeholder': '',
                    'description': 'Select a Shotgun Published File Type.',
                },
            },
            3: {
                0: {
                    'name': 'Description',
                    'key': 'description',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Enter a description...',
                    'description': 'The item\'s description.',
                },
            },
            4: {
                0: {
                    'name': None,
                    'key': 'file',
                    'validator': None,
                    'widget': publish_widgets.DropWidget,
                    'no_group': True,
                    'placeholder': 'Drop a file here, or click to select...',
                    'description': 'Drag-and-drop, or click, to add a file to publish to Shotgun.',
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
            SECTIONS,
            None,
            None,
            None,
            asset=None,
            db_table=database.AssetTable,
            buttons=('Publish', 'Cancel'),
            alignment=QtCore.Qt.AlignLeft,
            fallback_thumb='placeholder',
            parent=parent
        )

        self._file = None

        self.init_file_from_selection()

    def _connect_signals(self):
        super()._connect_signals()
        self.file_editor.fileSelected.connect(self.set_path)

    @common.error
    @common.debug
    def init_file_from_selection(self):
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
        file_info = QtCore.QFileInfo(v)

        ext = file_info.suffix()
        if not ext:  # We'll ignore files without extensions
            return

        # Get the last entry of the sequence and check if the file is valid
        if common.is_collapsed(v):
            v = common.get_sequence_endpath(v)
        file_info = QtCore.QFileInfo(v)
        if not file_info.exists():
            raise RuntimeError('Could not find file.')

        # Setting the path and thumbnail. The path is stored in `file_editor`.
        # `self.db_source` # uses this path to return it's value.

        # The name should be a
        self.file_editor.set_path(file_info.filePath())
        self.set_thumbnail_source()
        self.init_db_data()

        self.find_movie()
        self.find_sequence()

    def find_movie(self):
        """Try to find a movie file associated with selected publish file.

        """
        self.version_movie_editor.clear()

        v = self.file_editor.path()
        file_info = QtCore.QFileInfo(v)
        d = file_info.dir().path()
        b0 = file_info.baseName()

        def p(*args):
            return '/'.join(args)

        s = common.get_sequence(file_info.fileName())
        paths = []
        if s:
            b1 = s.group(1) + s.group(3)
            b2 = s.group(1).rstrip('_').rstrip('-') + s.group(3)
            b3 = s.group(1).rstrip('v').rstrip('_').rstrip(
                '-') + s.group(3)  # version notation
            b4 = s.group(1).rstrip('v').rstrip('_').rstrip('-') + \
                s.group(3).strip('_').strip('-')  # version notation

            for x in (b0, b1, b2, b3, b4):
                paths.append(p(d, x))
                for y in (b0, b1, b2, b3, b4):
                    paths.append(p(d, x, y))
        else:
            paths.append(p(d, b0))
            paths.append(p(d, b0, b0))

        for path in paths:
            for ext in MOV_FORMATS:
                _path = path + '.' + ext
                if QtCore.QFileInfo(_path).exists():
                    self.version_movie_editor.setText(_path)
                    return path

        return None

    def find_sequence(self):
        """Find an image sequence associated with the current publish file.

        """
        self.version_sequence_editor.clear()

        v = self.file_editor.path()

        file_info = QtCore.QFileInfo(v)
        d = file_info.dir().path()
        b0 = file_info.dir().dirName()

        def p(*args):
            return '/'.join(args)

        s = common.get_sequence(file_info.fileName())
        paths = []

        if s:
            b1 = s.group(1) + s.group(3)
            b2 = s.group(1).rstrip('_').rstrip('-') + s.group(3)
            b3 = s.group(1).rstrip('v').rstrip('_').rstrip(
                '-') + s.group(3)  # version notation
            b4 = s.group(1).rstrip('v').rstrip('_').rstrip('-') + \
                s.group(3).strip('_').strip('-')  # version notation

            for x in (b0, b1, b2, b3, b4):
                paths.append(p(d, x))
                for y in (b0, b1, b2, b3, b4):
                    paths.append(p(d, x, y))
        else:
            paths.append(p(d))
            paths.append(p(d, b0))
            paths.append(p(d, b0, b0))

        for path in paths:
            if not QtCore.QFileInfo(path).exists():
                continue

            for entry in os.scandir(path):
                if entry.is_dir():
                    continue

                ext = entry.name.split('.')[-1]
                if ext.lower() not in SEQ_FORMATS:
                    continue

                # A match, let's set the sequence path
                if file_info.baseName() in entry.name:
                    # Reading the Shotgun source code, looks like they're expecting
                    # an fprint style sequence notation
                    _file_info = QtCore.QFileInfo(entry.path)
                    seq = common.get_sequence(_file_info.filePath())
                    fprint_path = '{}{}{}.{}'.format(
                        seq.group(1),
                        '%0{}d'.format(len(seq.group(2))),
                        seq.group(3),
                        seq.group(4)
                    )
                    self.version_sequence_editor.setText(fprint_path)
                    return

    def is_scene_file(self):
        """Checks if the selected file is a scene.

        This is used to check if we should publish the scene file in addittion
        to a version.

        """
        if not self.file_editor.path():
            return False
        v = self.file_editor.path()

        config = tokens.get(
            common.active(common.ServerKey),
            common.active(common.JobKey),
            common.active(common.RootKey)
        )
        exts = config.get_extensions(tokens.SceneFormat)
        return QtCore.QFileInfo(v).suffix().lower() in exts

    @property
    def server(self):
        return common.active(common.ServerKey)

    @server.setter
    def server(self, v):
        pass

    @property
    def job(self):
        return common.active(common.JobKey)

    @job.setter
    def job(self, v):
        pass

    @property
    def root(self):
        return common.active(common.RootKey)

    @root.setter
    def root(self, v):
        pass

    @property
    def asset(self):
        return common.active(common.AssetKey)

    @asset.setter
    def asset(self, v):
        pass

    @property
    def task(self):
        return common.active(common.TaskKey)

    def db_source(self):
        p = self.file_editor.path()
        if not p:
            return None
        if common.is_collapsed(p):
            return common.proxy_path(p)
        return p

    def init_data(self):
        self.init_db_data()

    @common.error
    @common.debug
    def save_changes(self):
        """Publishes the file to shotgun.

        """
        if not self.file_editor.path():
            ui.MessageBox(
                'File not selected.',
                'Drag-and-drop a file to the top bar before continuing.'
            ).open()
            return False

        # Get all arguments needed to publish a Version and a PublishFile
        kwargs = self.get_publish_args()

        # Start version publish
        sg_properties = shotgun.ShotgunProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(asset=True):
            raise ValueError('Asset not configured.')

        with shotgun.connection(sg_properties) as sg:
            kwargs['sg'] = sg

            mbox = ui.MessageBox(
                'Checking for existing publish...', no_buttons=True)
            try:
                mbox.open()
                QtWidgets.QApplication.instance().processEvents()
                res = self._verify(**kwargs)
                if not res:
                    return
            except:
                raise
            finally:
                mbox.close()

            mbox = ui.MessageBox('Creating Version...', no_buttons=True)
            try:
                mbox.open()
                QtWidgets.QApplication.instance().processEvents()
                version_entity = self._create_version_entity(**kwargs)
                kwargs['version_entity'] = version_entity
            except:
                raise
            finally:
                mbox.close()

            mbox = ui.MessageBox('Uploading movie...', no_buttons=True)
            try:
                mbox.open()
                QtWidgets.QApplication.instance().processEvents()
                self._upload_movie(**kwargs)
            except:
                raise
            finally:
                mbox.close()

            mbox = ui.MessageBox('Publishing File...', no_buttons=True)
            try:
                mbox.open()
                QtWidgets.QApplication.instance().processEvents()
                published_file_entity = self._create_published_file(**kwargs)
            except:
                raise
            finally:
                mbox.close()

            import pprint
            info = {
                'id': published_file_entity['id'],
                'name': published_file_entity['name'],
                'version_number': published_file_entity['version_number'],
            }

            mbox = ui.MessageBox(
                'Success.',
                '{} was published successfully as:\n\n{}'.format(
                    published_file_entity['code'],
                    pprint.pformat(info, indent=1, depth=3, width=2)
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
                seq.group(1).rstrip('_v').strip('-v').strip('.v').strip(),
                seq.group(3),
                seq.group(4),
            )
            name = QtCore.QFileInfo(name).fileName()

        description = self.description_editor.text()

        project_entity = self.project_entity_editor.currentData(
            role=shotgun.EntityRole)
        asset_entity = self.asset_entity_editor.currentData(
            role=shotgun.EntityRole)

        task_entity = self.task_entity_editor.currentData(
            role=shotgun.EntityRole)
        user_entity = None
        if task_entity:
            # let's extract the user information from the task. If the task has multiple
            # users assigned we'll prompt the user to pick one from a list:
            k = 'task_assignees'
            if k in task_entity and task_entity[k]:
                if len(task_entity[k]) > 1:
                    items = [f['name'] if 'name' in f else f['id']
                             for f in task_entity[k]]
                    item = QtWidgets.QInputDialog.getItems(
                        self,
                        'Select User',
                        'Users:',
                        items,
                        current=0,
                        editable=False
                    )
                    idx = items.index(item)
                    user_entity = task_entity[k][idx]
            else:
                # use the first item, since there's only one user assigned
                user_entity = task_entity[k][0]

        published_file_type_entity = self.file_type_editor.currentData(
            role=shotgun.EntityRole)
        local_storage_entity = self.storage_editor.currentData(
            role=shotgun.EntityRole)
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

    def _verify(self, **kwargs):
        return sg_actions.verify_published_file_version(
            kwargs['sg'],
            kwargs['name'],
            kwargs['version'],
            kwargs['project_entity'],
            kwargs['asset_entity'],
            kwargs['published_file_type_entity'],
        )

    def _upload_movie(self, **kwargs):
        """Upload the specified movie file to link with the Version."""
        if not kwargs['version_movie']:
            return None
        return sg_actions.upload_movie(
            kwargs['sg'],
            kwargs['version_entity'],
            kwargs['version_movie']
        )

    def _create_version_entity(self, **kwargs):
        return sg_actions.create_version(
            kwargs['sg'],
            kwargs['file_name'],
            kwargs['file_path'],
            kwargs['version_movie'],
            kwargs['version_sequence'],
            kwargs['version_cache'],
            kwargs['description'],
            kwargs['project_entity'],
            kwargs['asset_entity'],
            kwargs['task_entity'],
            kwargs['user_entity'],
            kwargs['status_entity'],
        )

    def _create_published_file(self, **kwargs):
        return sg_actions.create_published_file(
            kwargs['sg'],
            kwargs['version_entity'],
            kwargs['name'],
            kwargs['file_name'],
            kwargs['file_path'],
            kwargs['version'],
            kwargs['description'],
            kwargs['project_entity'],
            kwargs['asset_entity'],
            kwargs['user_entity'],
            kwargs['task_entity'],
            kwargs['published_file_type_entity'],
            kwargs['local_storage_entity'],
        )

    @QtCore.Slot()
    @common.error
    @common.debug
    def project_entity_button_clicked(self):
        entity_type = self.project_entity_editor.currentData(shotgun.TypeRole)
        entity_id = self.project_entity_editor.currentData(shotgun.IdRole)
        if not all((entity_type, entity_id)):
            return
        sg_properties = shotgun.ShotgunProperties(
            self.server, self.job, self.root, self.asset)
        sg_properties.init()
        if not sg_properties.verify(connection=True):
            raise ValueError('Bookmark not configured.')

        url = shotgun.ENTITY_URL.format(
            domain=sg_properties.domain,
            entity_type=entity_type,
            entity_id=entity_id
        )
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
            self.server, self.job, self.root, self.asset)
        sg_properties.init()
        if not sg_properties.verify():
            return

        url = shotgun.ENTITY_URL.format(
            domain=sg_properties.domain,
            entity_type=entity_type,
            entity_id=entity_id
        )
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
            self.server, self.job, self.root, self.asset)
        sg_properties.init()
        if not sg_properties.verify():
            return

        url = shotgun.ENTITY_URL.format(
            domain=sg_properties.domain,
            entity_type=entity_type,
            entity_id=entity_id
        )
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
            parent=self,
            caption='Select an image sequence to include',
            dir=_dir,
            filter=images.get_oiio_namefilters()
        )
        if not file_path:
            return
        seq = common.get_sequence(file_path)
        if not seq:
            raise ValueError(
                'The selected file does not seem like an image sequence.')

        v = '{}{}{}.{}'.format(
            seq.group(1),
            '%0{}d'.format(len(seq.group(2))),
            seq.group(3),
            seq.group(4)
        )
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
            parent=self,
            caption='Select a movie to include',
            dir=_dir,
            filter='Movie Files (*.mov *.mp4)',
        )
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
            parent=self,
            caption='Select a cache to include',
            dir=_dir,
        )
        if not file_path:
            return
        self.version_cache_editor.setText(file_path)


if __name__ == '__main__':
    import bookmarks.standalone as standalone
    app = standalone.StandaloneApp([])
    w = PublishWidget()
    w.exec_()
