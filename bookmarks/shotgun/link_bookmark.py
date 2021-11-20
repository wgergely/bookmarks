# -*- coding: utf-8 -*-
"""Shotgun Entity linker widgets.

The widets are used to link a Shotgun entity with a local item.

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


def show(server, job, root):
    global instance
    close()
    instance = LinkBookmarkWidget(server, job, root)
    instance.open()
    return instance


value_map = {
    'shotgun_id': {
        'column': 'id',
        'overwrite': True,
        'type': database.TABLES[database.BookmarkTable]['shotgun_id']['type'],
    },
    'shotgun_name': {
        'column': 'name',
        'overwrite': True,
        'type': database.TABLES[database.BookmarkTable]['shotgun_name']['type'],
    },
    'shotgun_type': {
        'column': 'type',
        'overwrite': True,
        'type': database.TABLES[database.BookmarkTable]['shotgun_type']['type'],
    },
}


class LinkBookmarkWidget(link.BaseLinkWidget):
    def __init__(self, server, job, root, parent=None):
        super(LinkBookmarkWidget, self).__init__(
            server, job, root, None, 'Project', value_map, parent=parent)

    def db_source(self):
        if not all((self.server, self.job, self.root)):
            return None
        return '/'.join((self.server, self.job, self.root))

    def db_table(self):
        return database.BookmarkTable

    def candidate(self):
        from .. import main
        widget = main.instance().stackedwidget.widget(common.BookmarkTab)
        if widget.selectionModel().hasSelection():
            index = widget.selectionModel().currentIndex()
            return index.data(common.ParentPathRole)[1]
        return None

    @common.error
    @common.debug
    def request_data(self):
        """Request Loads a list of Shotgun entities.

        """
        self.combobox.model().sourceModel().entityDataRequested.emit(
            self.combobox.model().sourceModel().uuid,
            self.server,
            self.job,
            self.root,
            self.asset,
            'Project',
            [
                ['is_demo', 'is', False],
                ['is_template', 'is', False],
                ['is_template_project', 'is', False],
                ['archived', 'is', False],
            ],
            shotgun.fields['Project']
        )

    @common.error
    @common.debug
    def create_entity(self, entity_name):
        entity = sg_actions.create_project(
            self.server, self.job, self.root, entity_name)
        self.combobox.append_entity(entity)
