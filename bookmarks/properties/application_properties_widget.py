# -*- coding: utf-8 -*-

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import ui
from ..properties import base_widgets


DEFAULT_ITEM = {
    'name': None,
    'version': None,
    'path': None,
    'formats': [],
    'icon': None
}
THUMBNAIL_EDITOR_SIZE = common.MARGIN() * 5


class ApplicationItemWidget(QtWidgets.QWidget):
    """Widget used to edit launcher items associated with the current bookmark.

    """
    def __init__(self, parent=None):
        super(ApplicationItemWidget, self).__init__(parent=parent)
        self.thumbnail_editor = None

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        if not self.parent():
            common.set_custom_stylesheet(self)

        o = 0
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = ui.add_row(None, height=None, parent=self)
        self.thumbnail_editor = base_widgets.ThumbnailEditorWidget(
            'server', 'job', 'root',
            size=THUMBNAIL_EDITOR_SIZE,
            parent=self
        )
        row.layout().addWidget(self.thumbnail_editor)

        column = ui.add_row(None, height=None, vertical=True, parent=row)

    def _connect_signals(self):
        pass


class ApplicationPropertiesWidget(QtWidgets.QWidget):
    """Widget used to edit launcher items associated with the current bookmark.

    """

    def text(self):
        print '!!'

    def setText(self, v):
        if v == u'':
            v = None

        self.init_data(v)

    def init_data(self, v):
        pass
