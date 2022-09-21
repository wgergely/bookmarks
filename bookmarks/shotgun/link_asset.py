# -*- coding: utf-8 -*-
"""Shotgun Entity linker widgets.

The widgets are used to link a ShotGrid entity with a local asset item.

"""
from PySide2 import QtWidgets, QtCore, QtGui

from .. import common
from .. import database
from . import shotgun
from . import link
from . import actions as sg_actions


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


def show(server, job, root, asset, entity_type):
    global instance
    close()
    instance = LinkAssetWidget(server, job, root, asset, entity_type)
    instance.open()
    return instance


value_map = {
    'shotgun_id': {
        'column': 'id',
        'overwrite': True,
        'type': database.TABLES[database.AssetTable]['shotgun_id']['type'],
    },
    'shotgun_name': {
        'column': 'code',
        'overwrite': True,
        'type': database.TABLES[database.AssetTable]['shotgun_name']['type'],
    },
    'shotgun_type': {
        'column': 'type',
        'overwrite': True,
        'type': database.TABLES[database.AssetTable]['shotgun_type']['type'],
    },
    'description': {
        'column': 'description',
        'overwrite': False,
        'type': database.TABLES[database.AssetTable]['description']['type'],
    },
    'cut_in': {
        'column': 'cut_in',
        'overwrite': False,
        'type': database.TABLES[database.AssetTable]['cut_in']['type'],
    },
    'cut_out': {
        'column': 'cut_out',
        'overwrite': False,
        'type': database.TABLES[database.AssetTable]['cut_out']['type'],
    },
    'cut_duration': {
        'column': 'cut_duration',
        'overwrite': False,
        'type': database.TABLES[database.AssetTable]['cut_duration']['type'],
    },
}


class LinkAssetWidget(link.BaseLinkWidget):
    def __init__(self, server, job, root, asset, entity_type, parent=None):
        super(LinkAssetWidget, self).__init__(
            server, job, root, asset, entity_type, value_map, parent=parent)

    def db_source(self):
        if not all((self.server, self.job, self.root, self.asset)):
            return None
        return '/'.join((self.server, self.job, self.root, self.asset))

    def db_table(self):
        return database.AssetTable

    def candidate(self):
        widget = common.widget(common.AssetTab)
        index = common.get_selected_index(widget)
        if not index.isValid():
            return None
        return index.data(common.ParentPathRole)[3]

    @common.error
    @common.debug
    def request_data(self):
        """Request Loads a list of ShotGrid entities.

        """
        sg_properties = shotgun.ShotgunProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(bookmark=True):
            raise RuntimeError('Bookmark not configured.')

        self.combobox.model().sourceModel().entityDataRequested.emit(
            self.combobox.model().sourceModel().uuid,
            self.server,
            self.job,
            self.root,
            self.asset,
            self.entity_type,
            [
                ['project', 'is', {'type': 'Project',
                                   'id': sg_properties.bookmark_id}],
            ],
            shotgun.fields[self.entity_type]
        )

    @common.error
    @common.debug
    def create_entity(self, entity_name):
        entity = sg_actions.create_entity(self.entity_type, entity_name)
        self.combobox.append_entity(entity)
