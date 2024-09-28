""":class:`.AssetPropertyEditor` is used to create new assets and edit existing asset
item properties.

"""
import functools
import re

from PySide2 import QtWidgets, QtCore

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
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': 'Name',
                        'key': None,
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'Enter name, for example, \'SH0010\'',
                        'description': 'The asset\'s name, for example, \'SH0010\'',
                    },
                    1: {
                        'name': 'Description',
                        'key': 'description',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'A description, for example, \'My first shot\'',
                        'description': 'A short description of the asset, for example, \'My '
                                       'first shot.\'.',
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
                        'key': 'sg_type',
                        'validator': base.int_validator,
                        'widget': base_widgets.SGAssetTypesWidget,
                        'placeholder': None,
                        'description': 'Select the item\'s ShotGrid type',
                    },
                    2: {
                        'name': 'ShotGrid Id',
                        'key': 'sg_id',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid entity id, for example, \'123\'',
                        'description': 'The ShotGrid entity id this item is associated '
                                       'with. for example, \'123\'.',
                    },
                    3: {
                        'name': 'ShotGrid Name',
                        'key': 'sg_name',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid entity name, for example, \'MyAsset\'',
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
                        'placeholder': 'ShotGrid task id, for example, \'123\'',
                        'description': 'If the asset is associated with a ShotGrid task, the task entity id can be '
                                       'entered here. for example, \'123\'.',
                    },
                    1: {
                        'name': 'Task Name',
                        'key': 'sg_task_name',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid task name, for example, \'rigging\'',
                        'description': 'If the asset is associated with a ShotGrid task, the task name can be entered '
                                       'here. for example, \'rigging\'.',
                    },
                },
            }
        },
        2: {
            'name': 'Settings',
            'icon': 'bookmark',
            'color': common.Color.DarkBackground(),
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
            'name': 'Urls',
            'icon': '',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': 'Urls #1',
                        'key': 'url1',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'https://my.custom-url.com',
                        'description': 'A custom url of the bookmarks, '
                                       'e.g. https://sheets.google.com/123',
                        'button': 'Visit',
                    },
                    1: {
                        'name': 'Urls #2',
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

    def __init__(self, server, job, root, asset, parent=None):
        buttons = ('Save', 'Cancel')

        super().__init__(
            server,
            job,
            root,
            asset,
            db_table=database.AssetTable,
            fallback_thumb='thumb_asset0',
            buttons=buttons,
            parent=parent
        )

        self.name_editor.setText(asset)
        self.name_editor.setDisabled(True)
        self.setWindowTitle('/'.join((server, job, root, asset)))

    def _connect_signals(self):
        super()._connect_signals()
        self.thumbnailUpdated.connect(common.signals.thumbnailUpdated)
        self.itemCreated.connect(common.signals.assetAdded)

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        return '/'.join(
            (
                self.server,
                self.job,
                self.root,
                self.asset
            )
        )

    def init_data(self):
        """Initializes data.

        """
        self.init_db_data()
        self._disable_shotgun()
        self.description_editor.setFocus(QtCore.Qt.OtherFocusReason)

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
            self.asset
        )
        sg_properties.init()

        if not sg_properties.verify(bookmark=True):
            self.sg_type_editor.parent().parent().parent().setDisabled(True)

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        # When the asset isn't set, create one based on the name set
        if not self.asset:
            self.create_asset()

        self.save_changed_data_to_db()
        self.thumbnail_editor.save_image()
        self.thumbnailUpdated.emit(self.db_source())
        return True

    def sg_properties(self):
        """Returns the currently stored ShotGrid properties.

        Returns:
            An initialized :class:`~bookmarks.shotgun.SGProperties` instance.

        """
        sg_properties = shotgun.SGProperties(
            self.server,
            self.job,
            self.root,
            self.asset
        )
        sg_properties.init()

        sg_properties.asset_type = self.sg_type_editor.currentText()
        _id = self.sg_id_editor.text()
        _id = int(_id) if _id else None
        sg_properties.asset_id = _id
        sg_properties.asset_name = self.sg_name_editor.text()

        return sg_properties

    @common.error
    @QtCore.Slot()
    def link_button_clicked(self):
        """Slot connected to the link button.

        """
        if not self.sg_type_editor.currentText():
            common.show_message('Select an entity type before continuing', message_type='error')
            return

        sg_actions.link_asset_entity(
            self.server,
            self.job,
            self.root,
            self.asset,
            self.sg_type_editor.currentText()
        )
