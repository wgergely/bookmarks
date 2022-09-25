# -*- coding: utf-8 -*-
""":class:`.AssetPropertyEditor` is used to create new assets and edit existing asset
item properties.

Attributes:
    SECTIONS (dict): The property editor sections.

"""
import functools
import os

from PySide2 import QtWidgets, QtCore

from . import base
from . import base_widgets
from .. import common
from .. import database
from .. import templates
from .. import ui
from ..shotgun import actions as sg_actions
from ..shotgun import shotgun

instance = None


def close():
    """Close the :class:`AssetPropertyEditor` window.

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


def show(server, job, root, asset=None):
    """Show the :class:`AssetPropertyEditor` window.

    Args:
        server (str): Server name.
        job (str): Job name.
        root (str): Root name.
        asset (str, optional): Asset name. Defaults to `None`.

    """
    global instance

    close()
    instance = AssetPropertyEditor(
        server,
        job,
        root,
        asset=asset
    )
    instance.open()
    return instance


SECTIONS = {
    0: {
        'name': 'Settings',
        'icon': '',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'Name',
                    'key': None,
                    'validator': base.namevalidator,
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
                    'name': 'Link',
                    'key': 'link',
                    'validator': None,
                    'widget': None,
                    'placeholder': None,
                    'description': 'Link item with a ShotGrid Entity',
                    'button': 'Link with ShotGrid Entity',
                },
                1: {
                    'name': 'Type',
                    'key': 'shotgun_type',
                    'validator': base.intvalidator,
                    'widget': base_widgets.AssetTypesWidget,
                    'placeholder': None,
                    'description': 'Select the item\'s ShotGrid type',
                },
                2: {
                    'name': 'ID',
                    'key': 'shotgun_id',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'ShotGrid Project ID, e.g. \'123\'',
                    'description': 'The ShotGrid ID number this item is associated '
                                   'with. e.g. \'123\'.',
                },
                3: {
                    'name': 'Name',
                    'key': 'shotgun_name',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'ShotGrid entity name, e.g. \'MyProject\'',
                    'description': 'The ShotGrid entity name. The entity can be a '
                                   'shot, sequence or asset.\nClick "Link with '
                                   'ShotGrid" to get the name and the id from the '
                                   'ShotGrid server.',
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
                    'placeholder': 'In frame, e.g. \'1150\'',
                    'description': 'The frame this asset starts at, e.g. \'1150\'.',
                },
                1: {
                    'name': 'Out Frame',
                    'key': 'cut_out',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Out frame, e.g. \'1575\'',
                    'description': 'The frame this asset ends at, e.g. \'1575\'.',
                },
                2: {
                    'name': 'Cut Duration',
                    'key': 'cut_duration',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Duration in frames, e.g. \'425\'',
                    'description': 'The asset\'s duration in frames, e.g. \'425\'.',
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


class AssetPropertyEditor(base.BasePropertyEditor):
    """Property editor widget used to edit asset item properties.

    The class is a customized :class:`bookmarks.editor.base.BasePropertyEditor`,
    and implements asset creation on top of existing features.

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
        return '/'.join(
            (
                self.server,
                self.job,
                self.root,
                self.name()
            )
        )

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
        common.set_stylesheet(completer.popup())
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
