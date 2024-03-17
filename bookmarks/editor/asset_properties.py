""":class:`.AssetPropertyEditor` is used to create new assets and edit existing asset
item properties.

"""
import functools
import re

try:
    from PySide6 import QtWidgets, QtGui, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore

from . import base
from . import base_widgets
from .. import common
from .. import database
from .. import log
from .. import templates
from .. import ui
from ..shotgun import actions as sg_actions
from ..shotgun import shotgun


def close():
    """Closes the :class:`AssetPropertyEditor` editor.

    """
    if common.asset_property_editor is None:
        return
    try:
        common.asset_property_editor.close()
        common.asset_property_editor.deleteLater()
    except:
        pass
    common.asset_property_editor = None


def show(server, job, root, asset=None):
    """Show the :class:`AssetPropertyEditor` window.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.
        asset (str, optional): Asset name. Default: `None`.

    """
    close()
    common.asset_property_editor = AssetPropertyEditor(
        server,
        job,
        root,
        asset=asset
    )
    common.restore_window_geometry(common.asset_property_editor)
    common.restore_window_state(common.asset_property_editor)
    return common.asset_property_editor


class AssetPropertyEditor(base.BasePropertyEditor):
    """Property editor widget used to edit asset item properties.

    The class is a customized :class:`bookmarks.editor.base.BasePropertyEditor`,
    and implements asset creation on top of existing features.

    """

    #: UI layout definition
    sections = {
        0: {
            'name': 'Settings',
            'icon': '',
            'color': common.color(common.color_dark_background),
            'groups': {
                0: {
                    0: {
                        'name': 'Name',
                        'key': None,
                        'validator': base.job_name_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Enter name, e.g. \'SH0010\'',
                        'description': 'The asset\'s name, e.g. \'SH0010\'',
                    },
                    1: {
                        'name': 'Description',
                        'key': 'description',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'A description, e.g. \'My first shot\'',
                        'description': 'A short description of the asset, e.g. \'My '
                                       'first shot.\'.',
                    },
                },
                1: {
                    0: {
                        'name': 'Template',
                        'key': None,
                        'validator': None,
                        'widget': functools.partial(
                            templates.TemplatesWidget,
                            templates.AssetTemplateMode
                        ),
                        'placeholder': None,
                        'description': 'Select a folder template to create this asset.',
                        'help': 'Select a folder template to create this asset. Templates are simple zip files that '
                                'contain a folder structure and a set of files. The template can contain a `.link` '
                                'file '
                                'which will be used to read nested assets inside the template. This can be useful if an'
                                'asset is made up of multiple tasks, e.g. a shot asset may contain a `lighting` and '
                                '`anim`'
                                'tasks.',
                    },
                },
            },
        },
        1: {
            'name': 'ShotGrid Entity',
            'icon': 'sg',
            'color': None,
            'groups': {
                0: {
                    0: {
                        'name': 'ShotGrid Link',
                        'key': 'link',
                        'validator': None,
                        'widget': None,
                        'placeholder': None,
                        'description': 'Link item with a ShotGrid Entity',
                        'button': 'Link with ShotGrid Entity',
                    },
                    1: {
                        'name': 'ShotGrid Type',
                        'key': 'shotgun_type',
                        'validator': base.int_validator,
                        'widget': base_widgets.SGAssetTypesWidget,
                        'placeholder': None,
                        'description': 'Select the item\'s ShotGrid type',
                    },
                    2: {
                        'name': 'ShotGrid Id',
                        'key': 'shotgun_id',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid entity id, e.g. \'123\'',
                        'description': 'The ShotGrid entity id this item is associated '
                                       'with. e.g. \'123\'.',
                    },
                    3: {
                        'name': 'ShotGrid Name',
                        'key': 'shotgun_name',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid entity name, e.g. \'MyAsset\'',
                        'description': 'The ShotGrid entity name. The name usually corresponds to the "code" field'
                                       'in ShotGrid.',
                    },
                },
                1: {
                    0: {
                        'name': 'Task Id',
                        'key': 'sg_task_id',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid task id, e.g. \'123\'',
                        'description': 'If the asset is associated with a ShotGrid task, the task entity id can be '
                                       'entered here. e.g. \'123\'.',
                    },
                    1: {
                        'name': 'Task Name',
                        'key': 'sg_task_name',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid task name, e.g. \'rigging\'',
                        'description': 'If the asset is associated with a ShotGrid task, the task name can be entered '
                                       'here. e.g. \'rigging\'.',
                    },
                },
            }
        },
        2: {
            'name': 'Settings',
            'icon': 'bookmark',
            'color': common.color(common.color_dark_background),
            'groups': {
                0: {
                    0: {
                        'name': 'Cut In',
                        'key': 'cut_in',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'In frame, e.g. \'1150\'',
                        'description': 'The frame this asset starts at, e.g. \'1150\'.',
                    },
                    1: {
                        'name': 'Cut Out',
                        'key': 'cut_out',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Out frame, e.g. \'1575\'',
                        'description': 'The frame this asset ends at, e.g. \'1575\'.',
                    },
                    2: {
                        'name': 'Cut Duration',
                        'key': 'cut_duration',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Duration in frames, e.g. \'425\'',
                        'description': 'The asset\'s duration in frames, e.g. \'425\'.',
                    },
                },
                1: {
                    0: {
                        'name': 'Edit In',
                        'key': 'edit_in',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'In frame, e.g. \'1150\'',
                        'description': 'The frame this asset starts at, e.g. \'1150\'.',
                    },
                    1: {
                        'name': 'Edit Out',
                        'key': 'edit_out',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Out frame, e.g. \'1575\'',
                        'description': 'The frame this asset ends at, e.g. \'1575\'.',
                    },
                },
                2: {
                    0: {
                        'name': 'Asset frame-rate',
                        'key': 'asset_framerate',
                        'validator': base.float_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Frame-rate, e.g. \'23.976\'',
                        'description': 'The frame-rate of the asset, e.g. '
                                       '\'25.0\'',
                    },
                    1: {
                        'name': 'Asset width',
                        'key': 'asset_width',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Width in pixels',
                        'description': 'The asset\'s output width in pixels, e.g. \'1920\''
                    },
                    2: {
                        'name': 'Asset height',
                        'key': 'asset_height',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Height in pixels',
                        'description': 'The asset\'s output height in pixels, e.g. \'1080\''
                    },
                },
            },
        },
        3: {
            'name': 'Links',
            'icon': '',
            'color': common.color(common.color_dark_background),
            'groups': {
                0: {
                    0: {
                        'name': 'Link #1',
                        'key': 'url1',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'https://my.custom-url.com',
                        'description': 'A custom url of the bookmarks, '
                                       'e.g. https://sheets.google.com/123',
                        'button': 'Visit',
                    },
                    1: {
                        'name': 'Link #2',
                        'key': 'url2',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'https://my.custom-url.com',
                        'description': 'A custom url of the bookmarks, '
                                       'e.g. https://sheets.google.com/123',
                        'button': 'Visit',
                    }
                }
            }
        }
    }

    def __init__(self, server, job, root, asset=None, parent=None):
        if asset:
            buttons = ('Save', 'Cancel')
        else:
            buttons = ('Add Asset', 'Cancel')

        super().__init__(
            server,
            job,
            root,
            asset=asset,
            db_table=database.AssetTable,
            fallback_thumb='thumb_asset0',
            buttons=buttons,
            parent=parent
        )

        if asset:
            # When `asset` is set, the template_editor is no longer used, so
            # we can hide it:
            self.name_editor.setText(asset)
            self.name_editor.setDisabled(True)
            self.template_editor.parent().parent().setHidden(True)
            self.setWindowTitle('/'.join((server, job, root, asset)))
        else:
            self.setWindowTitle(f'{server}/{job}/{root}: Create Asset')
            self.name_editor.setFocus()

    def _connect_signals(self):
        super()._connect_signals()
        self.thumbnailUpdated.connect(common.signals.thumbnailUpdated)
        self.itemCreated.connect(self.create_link_file)
        self.itemCreated.connect(common.signals.assetAdded)

    def create_link_file(self, path):
        """Creates a link file for nested assets.

        Args:
            path (str): Path to the newly created asset.

        """
        if not path:
            return

        path = path.replace('\\', '/')

        bookmark = '/'.join((self.server, self.job, self.root))
        asset = path.replace(bookmark, '').strip('/')

        # Nothing to do if the asset is not nested
        if '/' not in asset:
            return

        root = '/'.join(
            (
                self.server,
                self.job,
                self.root,
                asset.split('/')[0]
            )
        )
        rel = '/'.join(asset.split('/')[1:])
        if not common.add_link(root, rel, section='links/asset'):
            log.error('Could not add link')

    def name(self):
        """Returns the name of the asset.

        """
        name = self.name_editor.text()
        name = self.asset if self.asset else name
        return name if name else None

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        if not self.name():
            return '/'.join(
                (
                    self.server,
                    self.job,
                    self.root,
                )
            )
        return '/'.join(
            (
                self.server,
                self.job,
                self.root,
                self.name()
            )
        )

    def init_data(self):
        """Initializes data.

        """
        self.init_db_data()
        self._set_completer()
        self._disable_shotgun()

    def init_db_data(self):
        super().init_db_data()

        # Asset frame-rate, width and height overrides
        db = database.get(self.server, self.job, self.root)
        for k in ('asset_framerate', 'asset_width', 'asset_height'):
            # Skip items that don't have editors
            if not hasattr(self, f'{k}_editor'):
                raise RuntimeError(f'No editor for {k}!')

            v = db.value(self.db_source(), k, database.AssetTable)
            # If the value is not set, we'll use the bookmark item's value instead as a
            # placeholder for the text editor
            if not v:
                source = f'{self.server}/{self.job}/{self.root}'
                _v = db.value(source, k.replace('asset_', ''), database.BookmarkTable)
                if _v is None:
                    continue
                getattr(self, f'{k}_editor').setPlaceholderText(f'{_v}')

    def _disable_shotgun(self):
        sg_properties = shotgun.SGProperties(
            self.server,
            self.job,
            self.root,
            self.name()
        )
        sg_properties.init()

        if not sg_properties.verify(bookmark=True):
            self.shotgun_type_editor.parent().parent().parent().setDisabled(True)

    def _set_completer(self):
        """Add the current list of assets to the name editor's completer.

        """
        items = []

        model = common.source_model(common.AssetTab)
        data = model.model_data()
        for idx in data:
            if data[idx][common.FlagsRole] & common.MarkedAsArchived:
                continue
            v = data[idx][common.ParentPathRole][-1]
            items.append(v)

            match = re.search(r'[0-9]+$', v)
            if match:
                pad = len(match.group(0))
                num = int(match.group(0))
                span = match.span()
                _v1 = str(num + 1).zfill(pad)
                _v2 = str(num + 10).zfill(pad)
                v1 = v[0:span[0]] + _v1 + v[span[1]:-1]
                v2 = v[0:span[0]] + _v2 + v[span[1]:-1]
                items.append(v1)
                items.append(v2)

        items = sorted(set(items), reverse=True)
        completer = QtWidgets.QCompleter(items, parent=self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_stylesheet(completer.popup())
        self.name_editor.setCompleter(completer)

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        # When the asset is not set, we'll create one based on the name set
        if not self.asset:
            self.create_asset()

        self.save_changed_data_to_db()
        self.thumbnail_editor.save_image()
        self.thumbnailUpdated.emit(self.db_source())
        return True

    def shotgun_properties(self):
        """Returns the currently stored ShotGrid properties.

        Returns:
            An initialized :class:`~bookmarks.shotgun.SGProperties` instance.

        """
        sg_properties = shotgun.SGProperties(
            self.server,
            self.job,
            self.root,
            self.name()
        )
        sg_properties.init()

        sg_properties.asset_type = self.shotgun_type_editor.currentText()
        _id = self.shotgun_id_editor.text()
        _id = int(_id) if _id else None
        sg_properties.asset_id = _id
        sg_properties.asset_name = self.shotgun_name_editor.text()

        return sg_properties

    def create_asset(self):
        """Creates a new asset based on the current name and template selections.

        """
        name = self.name()
        editor = self.template_editor.template_list_widget

        if not name:
            raise RuntimeError('Must enter a name to create asset.')

        file_info = QtCore.QFileInfo(f'{self.server}/{self.job}/{self.root}/{name}')
        if not file_info.exists() and not file_info.dir().mkpath('.'):
            raise RuntimeError(f'Could not create {file_info.dir().path()}')

        editor.create(
            file_info.fileName(),
            file_info.dir().absolutePath()
        )

        if not file_info.exists():
            raise RuntimeError('Failed to create asset.')

        self.create_link_file(file_info.absoluteFilePath())
        self.itemCreated.emit(file_info.absoluteFilePath())

    @common.error
    @QtCore.Slot()
    def link_button_clicked(self):
        """Slot connected to the link button.

        """
        if not self.shotgun_type_editor.currentText():
            common.show_message('Select an entity type before continuing', message_type='error')
            return

        sg_actions.link_asset_entity(
            self.server,
            self.job,
            self.root,
            self.name(),
            self.shotgun_type_editor.currentText()
        )
