# -*- coding: utf-8 -*-
"""Defines `AssetPropertiesWidget`, the widget used to create and edit assets.

"""
import functools
import _scandir

from PySide2 import QtWidgets, QtGui, QtCore

from .. import common
from .. import ui
from .. import bookmark_db

from ..templates import templates
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
    instance = AssetPropertiesWidget(
        server,
        job,
        root,
        asset=asset
    )
    instance.open()
    return instance


SECTIONS = {
    0: {
        'name': u'Basic Settings',
        'icon': u'',
        'color': common.DARK_BG,
        'groups': {
            0: {
                0: {
                    'name': u'Name',
                    'key': None,
                    'validator': base.namevalidator,
                    'widget': ui.LineEdit,
                    'placeholder': u'Name, eg. \'SH0010\'',
                    'description': u'The asset\'s name, eg. \'SH0010\'.',
                },
                1: {
                    'name': u'Description',
                    'key': u'description',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': u'A description, eg. \'My first shot\'',
                    'description': u'A short description of the asset, eg. \'My first shot.\'.',
                },
            },
            1: {
                0: {
                    'name': u'Template',
                    'key': None,
                    'validator': None,
                    'widget': functools.partial(templates.TemplatesWidget, templates.AssetTemplateMode),
                    'placeholder': None,
                    'description': u'Select a folder template to create this asset.',
                },
            },
        },
    },
    1: {
        'name': u'Shotgun Entity',
        'icon': u'shotgun',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': 'Link',
                    'key': 'link',
                    'validator': None,
                    'widget': None,
                    'placeholder': None,
                    'description': u'Link item with a Shotgun Entity',
                    'button': u'Link with Shotgun Entity',
                },
                1: {
                    'name': u'Type',
                    'key': u'shotgun_type',
                    'validator': base.intvalidator,
                    'widget': base_widgets.AssetTypesWidget,
                    'placeholder': None,
                    'description': u'Select the item\'s Shotgun type',
                },
                2: {
                    'name': u'ID',
                    'key': u'shotgun_id',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': u'Shotgun Project ID, eg. \'123\'',
                    'description': u'The Shotgun ID number this item is associated with. Eg. \'123\'.',
                },
                3: {
                    'name': u'Name',
                    'key': u'shotgun_name',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': u'Shotgun entity name, eg. \'MyProject\'',
                    'description': u'The Shotgun entity name. The entity can be a shot, sequence or asset.\nClick "Link with Shotgun" to get the name and the id from the Shotgun server.',
                },
            }
        }
    },
    2: {
        'name': u'Cut',
        'icon': u'todo',
        'color': common.DARK_BG,
        'groups': {
            0: {
                0: {
                    'name': u'In Frame',
                    'key': u'cut_in',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': u'In frame, eg. \'1150\'',
                    'description': u'The frame this asset starts at, eg. \'1150\'.',
                },
                1: {
                    'name': u'Out Frame',
                    'key': u'cut_out',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': u'Out frame, eg. \'1575\'',
                    'description': u'The frame this asset ends at, eg. \'1575\'.',
                },
                2: {
                    'name': u'Cut Duration',
                    'key': u'cut_duration',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': u'Duration in frames, eg. \'425\'',
                    'description': u'The asset\'s duration in frames, eg. \'425\'.',
                },
            },
        },
    },
    3: {
        'name': u'URLs',
        'icon': u'',
        'color': common.DARK_BG,
        'groups': {
            0: {
                0: {
                    'name': u'Primary',
                    'key': u'url1',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'https://my.custom-url.com',
                    'description': u'A custom url of the bookmarks, eg. https://sheets.google.com/123',
                    'button': u'Visit',
                },
                1: {
                    'name': u'Scondary',
                    'key': u'url2',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'https://my.custom-url.com',
                    'description': u'A custom url of the bookmarks, eg. https://sheets.google.com/123',
                    'button': u'Visit',
                }
            }
        }
    }
}


class AssetPropertiesWidget(base.PropertiesWidget):
    """Widget used to create a new asset in a specified bookmark, or when
    the optional `asset` argument is set, updates the asset properties.

    Args:
        path (unicode): Destination path for the new assets.
        update (bool=False): Enables the update mode, if the widget is used to edit an existing asset.

    """

    def __init__(self, server, job, root, asset=None, parent=None):
        if asset:
            buttons = (u'Save', u'Cancel')
        else:
            buttons = (u'Create Asset', u'Cancel')

        super(AssetPropertiesWidget, self).__init__(
            SECTIONS,
            server,
            job,
            root,
            asset=asset,
            db_table=bookmark_db.AssetTable,
            fallback_thumb=u'thumb_item_gray',
            buttons=buttons,
            parent=parent
        )

        if asset:
            # When `asset` is set, the template_editor is no longer used so
            # we're hiding it:
            self.name_editor.setText(asset)
            self.name_editor.setDisabled(True)
            self.template_editor.parent().parent().setHidden(True)
            self.setWindowTitle(u'/'.join((server, job, root, asset)))
        else:
            self.setWindowTitle(
                u'{}/{}/{}: Create Asset'.format(server, job, root))
            self.name_editor.setFocus()

    def _connect_signals(self):
        super(AssetPropertiesWidget, self)._connect_signals()
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
        return u'/'.join((
            self.server,
            self.job,
            self.root,
            self.name()
        ))

    def init_data(self):
        """Load the current data from the database.

        """
        self._init_db_data()
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
        source = u'/'.join((self.server, self.job, self.root))
        items = [f.name for f in _scandir.scandir(source) if f.is_dir()]
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

        self._save_db_data()
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
            raise RuntimeError(u'Must enter a name to create asset.')

        path = u'/'.join((self.server, self.job, self.root))
        editor.create(name, path)
        path = u'/'.join((self.server, self.job, self.root, name))
        if not QtCore.QFileInfo(path).exists():
            raise RuntimeError('Failed to create asset.')

        self.itemCreated.emit(path)

    @common.error
    @QtCore.Slot()
    def link_button_clicked(self):
        if not self.shotgun_type_editor.currentText():
            ui.MessageBox(u'Select an entity type before continuing').open()
            return

        sg_actions.link_asset_entity(
            self.server,
            self.job,
            self.root,
            self.name(),
            self.shotgun_type_editor.currentText()
        )
