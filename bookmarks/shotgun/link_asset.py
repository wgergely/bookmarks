"""ShotGrid Entity linker widgets.

The widgets are used to link a ShotGrid entity with a local asset item.

"""

from . import actions as sg_actions
from . import link
from . import shotgun
from .. import common
from .. import database

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
    'sg_id': {
        'column': 'id',
        'overwrite': True,
        'type': database.TABLES[database.AssetTable]['sg_id']['type'],
    },
    'sg_name': {
        'column': 'code',
        'overwrite': True,
        'type': database.TABLES[database.AssetTable]['sg_name']['type'],
    },
    'sg_type': {
        'column': 'type',
        'overwrite': True,
        'type': database.TABLES[database.AssetTable]['sg_type']['type'],
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
        super().__init__(
            server, job, root, asset, entity_type, value_map, parent=parent
        )

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
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
        sg_properties = shotgun.SGProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(bookmark=True):
            raise RuntimeError('Bookmark not configured.')

        self.combobox.model().sourceModel().entityDataRequested.emit(
            self.combobox.model().sourceModel().uuid,
            self.server,
            self.job,
            self.root,
            self.asset,
            False,
            self.entity_type,
            [
                ['project', 'is', {
                    'type': 'Project',
                    'id': sg_properties.bookmark_id
                }],
            ],
            shotgun.entity_fields[self.entity_type]
        )

    @common.error
    @common.debug
    def create_entity(self, entity_name):
        entity = sg_actions.create_entity(self.entity_type, entity_name)
        self.combobox.append_entity(entity)
