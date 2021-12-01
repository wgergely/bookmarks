# -*- coding: utf-8 -*-
"""Defines `AssetEditor`, the widget used to create and edit asset items.

"""
import functools


from PySide2 import QtWidgets, QtGui, QtCore

from .. import common
from .. import ui
from .. import database
from .. import templates

from ..shotgun import shotgun
from ..shotgun import actions as sg_actions

from . import base
from . import base_widgets


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


def show(server, job, root, asset=None):
    global instance

    close()
    instance = AssetEditor(
        server,
        job,
        root,
        asset=asset
    )
    instance.open()
    return instance


SECTIONS = {
    0: {
        'name': 'Basic Settings',
        'icon': '',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'Name',
                    'key': None,
                    'validator': base.namevalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Name, eg. \'SH0010\'',
                    'description': 'The asset\'s name, eg. \'SH0010\'.',
                },
                1: {
                    'name': 'Description',
                    'key': 'description',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'A description, eg. \'My first shot\'',
                    'description': 'A short description of the asset, eg. \'My first shot.\'.',
                },
            },
            1: {
                0: {
                    'name': 'Template',
                    'key': None,
                    'validator': None,
                    'widget': functools.partial(templates.TemplatesWidget, templates.AssetTemplateMode),
                    'placeholder': None,
                    'description': 'Select a folder template to create this asset.',
                },
            },
        },
    },
    1: {
        'name': 'Shotgun Entity',
        'icon': 'sg',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': 'Link',
                    'key': 'link',
                    'validator': None,
                    'widget': None,
                    'placeholder': None,
                    'description': 'Link item with a Shotgun Entity',
                    'button': 'Link with Shotgun Entity',
                },
                1: {
                    'name': 'Type',
                    'key': 'shotgun_type',
                    'validator': base.intvalidator,
                    'widget': base_widgets.AssetTypesWidget,
                    'placeholder': None,
                    'description': 'Select the item\'s Shotgun type',
                },
                2: {
                    'name': 'ID',
                    'key': 'shotgun_id',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Shotgun Project ID, eg. \'123\'',
                    'description': 'The Shotgun ID number this item is associated with. Eg. \'123\'.',
                },
                3: {
                    'name': 'Name',
                    'key': 'shotgun_name',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Shotgun entity name, eg. \'MyProject\'',
                    'description': 'The Shotgun entity name. The entity can be a shot, sequence or asset.\nClick "Link with Shotgun" to get the name and the id from the Shotgun server.',
                },
            }
        }
    },
    2: {
        'name': 'Cut',
        'icon': 'todo',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'In Frame',
                    'key': 'cut_in',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'In frame, eg. \'1150\'',
                    'description': 'The frame this asset starts at, eg. \'1150\'.',
                },
                1: {
                    'name': 'Out Frame',
                    'key': 'cut_out',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Out frame, eg. \'1575\'',
                    'description': 'The frame this asset ends at, eg. \'1575\'.',
                },
                2: {
                    'name': 'Cut Duration',
                    'key': 'cut_duration',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Duration in frames, eg. \'425\'',
                    'description': 'The asset\'s duration in frames, eg. \'425\'.',
                },
            },
        },
    },
    3: {
        'name': 'Links',
        'icon': '',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'Primary',
                    'key': 'url1',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'https://my.custom-url.com',
                    'description': 'A custom url of the bookmarks, eg. https://sheets.google.com/123',
                    'button': 'Visit',
                },
                1: {
                    'name': 'Scondary',
                    'key': 'url2',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'https://my.custom-url.com',
                    'description': 'A custom url of the bookmarks, eg. https://sheets.google.com/123',
                    'button': 'Visit',
                }
            }
        }
    }
}


class AssetEditor(base.BasePropertyEditor):
    """Widget used to create a new asset in a specified bookmark, or when
    the optional `asset` argument is set, updates the asset properties.

    Args:
        path (str): Destination path for the new assets.
        update (bool=False): Enables the update mode, if the widget is used to edit an existing asset.

    """

    def __init__(self, server, job, root, asset=None, parent=None):
        if asset:
            buttons = ('Save', 'Cancel')
        else:
            buttons = ('Add Asset', 'Cancel')

        super().__init__(
            SECTIONS,
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
            # When `asset` is set, the template_editor is no longer used so
            # we're hiding it:
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
        self.itemCreated.connect(common.signals.assetAdded)

    def name(self):
        """Returns the name of the asset.

        """
        name = self.name_editor.text()
        name = self.asset if self.asset else name
        return name if name else None

    def db_source(self):
        """The source used to associate the saved data in the database.

        """
        if not self.name():
            return None
        return '/'.join((
            self.server,
            self.job,
            self.root,
            self.name()
        ))

    def init_data(self):
        """Load the current data from the database.

        """
        self.init_db_data()
        self._set_completer()
        self._disable_shotgun()

    def _disable_shotgun(self):
        sg_properties = shotgun.ShotgunProperties(
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
        source = '/'.join((self.server, self.job, self.root))
        items = [f.name for f in os.scandir(source) if f.is_dir()]
        completer = QtWidgets.QCompleter(items, parent=self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_custom_stylesheet(completer.popup())
        self.name_editor.setCompleter(completer)

    @common.error
    @common.debug
    def save_changes(self):
        """Save changed data to the database.

        """
        # When the asset is not set, we'll create one based on the name set
        if not self.asset:
            self.create_asset()

        self.save_changed_data_to_db()
        self.thumbnail_editor.save_image()
        self.thumbnailUpdated.emit(self.db_source())
        self.itemUpdated.emit(self.db_source())
        return True

    def shotgun_properties(self):
        sg_properties = shotgun.ShotgunProperties(
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

        path = '/'.join((self.server, self.job, self.root))
        editor.create(name, path)
        path = '/'.join((self.server, self.job, self.root, name))
        if not QtCore.QFileInfo(path).exists():
            raise RuntimeError('Failed to create asset.')

        self.itemCreated.emit(path)

    @common.error
    @QtCore.Slot()
    def link_button_clicked(self):
        if not self.shotgun_type_editor.currentText():
            ui.MessageBox('Select an entity type before continuing').open()
            return

        sg_actions.link_asset_entity(
            self.server,
            self.job,
            self.root,
            self.name(),
            self.shotgun_type_editor.currentText()
        )
