"""ShotGrid Entity linker widgets.

The widgets are used to link a ShotGrid entity with a local bookmark item.

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


def show(server, job, root):
    global instance
    close()
    instance = LinkBookmarkWidget(server, job, root)
    instance.open()
    return instance


value_map = {
    'sg_id': {
        'column': 'id',
        'overwrite': True,
        'type': database.TABLES[database.BookmarkTable]['sg_id']['type'],
    },
    'sg_name': {
        'column': 'name',
        'overwrite': True,
        'type': database.TABLES[database.BookmarkTable]['sg_name']['type'],
    },
    'sg_type': {
        'column': 'type',
        'overwrite': True,
        'type': database.TABLES[database.BookmarkTable]['sg_type']['type'],
    },
}


class LinkBookmarkWidget(link.BaseLinkWidget):
    def __init__(self, server, job, root, parent=None):
        super().__init__(
            server, job, root, None, 'Project', value_map, parent=parent
        )

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        if not all((self.server, self.job, self.root)):
            return None
        return '/'.join((self.server, self.job, self.root))

    def db_table(self):
        return database.BookmarkTable

    def candidate(self):
        index = common.selected_index(common.BookmarkTab)
        return index.data(common.ParentPathRole)[1] if index.isValid() else None

    @common.error
    @common.debug
    def request_data(self):
        """Request Loads a list of ShotGrid entities.

        """
        self.combobox.model().sourceModel().entityDataRequested.emit(
            self.combobox.model().sourceModel().uuid,
            self.server,
            self.job,
            self.root,
            self.asset,
            False,
            'Project',
            [
                ['is_demo', 'is', False],
                ['is_template', 'is', False],
                ['is_template_project', 'is', False],
                ['archived', 'is', False],
            ],
            shotgun.entity_fields['Project']
        )

    @common.error
    @common.debug
    def create_entity(self, entity_name):
        entity = sg_actions.create_project(
            self.server, self.job, self.root, entity_name
        )
        self.combobox.append_entity(entity)
