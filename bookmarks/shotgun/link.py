"""ShotGrid Entity linker widgets.

The widgets are used to link a ShotGrid entity with a local item.

"""
from PySide2 import QtWidgets, QtCore, QtGui

from . import actions as sg_actions
from . import shotgun
from .. import common
from .. import ui


class BaseLinkWidget(QtWidgets.QDialog):
    """Widget used to link a ShotGrid entity with a local item.

    Args:
        entity_type (str): A shotgun entity type.

    """

    def __init__(self, server, job, root, asset, entity_type, value_map, parent=None):
        super().__init__(parent=parent)

        self.entity_type = entity_type

        self.server = server
        self.job = job
        self.root = root
        self.asset = asset

        self.value_map = value_map

        self.combobox = None
        self.link_button = None
        self.visit_button = None
        self.create_button = None

        if not self.parent():
            common.set_stylesheet(self)

        self.setWindowTitle(
            f'Link {self.db_source()} with {self.entity_type.title()} Entity'
        )

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.Size.Margin()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = ui.add_row(
            f'Select {self.entity_type.title()}',
            height=common.Size.RowHeight(),
            parent=self
        )

        self.combobox = shotgun.EntityComboBox(
            ['Select entity...', ], parent=self
        )
        self.combobox.model().set_entity_type(self.entity_type)
        self.combobox.setMinimumWidth(common.Size.DefaultWidth(0.5))

        self.create_button = ui.PaintedButton(
            'Create New', parent=self
        )
        self.visit_button = ui.PaintedButton('Visit', parent=self)

        row.layout().addWidget(self.combobox, 1)
        row.layout().addWidget(self.visit_button, 0)
        row.layout().addWidget(self.create_button, 0)

        row = ui.add_row(None, height=common.Size.RowHeight(), parent=self)

        self.link_button = ui.PaintedButton(
            f'Link {self.entity_type.title()} Entity',
            parent=self
        )

        row.layout().addWidget(self.link_button, 1)

    def _connect_signals(self):
        self.link_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted)
        )

        self.visit_button.clicked.connect(self.visit)
        self.create_button.clicked.connect(self.create)

        self.combobox.model().sourceModel().entityDataReceived.connect(
            self.select_candidate
        )

    @common.error
    @common.debug
    def request_data(self):
        """Request Loads a list of ShotGrid entities.

        """
        pass

    def done(self, result):
        if result == QtWidgets.QDialog.Accepted:
            self.save_data()
        super().done(result)

    def candidate(self):
        return 'MyNewEntity'

    @QtCore.Slot()
    def select_candidate(self):
        candidate = self.candidate()
        idx = self.combobox.findText(
            candidate, flags=QtCore.Qt.MatchFixedString
        )
        if idx == -1:
            self.combobox.select_first()
            return
        self.combobox.setCurrentIndex(idx)

    @common.error
    @common.debug
    def save_data(self):
        """Save the selected entity data to the Bookmark Database.

        """
        if not self.db_source():
            return

        entity = self.combobox.currentData(shotgun.EntityRole)
        if not entity:
            return

        sg_actions.save_entity_data_to_db(
            self.server,
            self.job,
            self.root,
            self.db_source(),
            self.db_table(),
            entity,
            self.value_map
        )

    def create(self):
        """Show a popup line editor to enter the name of a new entity.

        """
        editor = EntityNameEditor(parent=self)
        editor.nameSelected.connect(self.create_entity)
        if self.candidate():
            editor.editor.setText(self.candidate())
        editor.open()

    @common.error
    @common.debug
    @QtCore.Slot(str)
    def create_entity(self, name):
        """Creates a new ShotGrid entity.

        """
        pass

    @common.error
    @common.debug
    def visit(self):
        _id = self.combobox.currentData(shotgun.IdRole)
        _name = self.combobox.currentData(shotgun.NameRole)
        _type = self.combobox.currentData(shotgun.TypeRole)

        if not all((_id, _name, _type)):
            return

        sg_properties = shotgun.SGProperties(
            self.server,
            self.job,
            self.root,
            self.asset
        )
        sg_properties.init()

        if not sg_properties.verify(connection=True):
            return

        url = shotgun.ENTITY_URL.format(
            domain=sg_properties.domain,
            entity_type=_type,
            entity_id=_id
        )
        url = QtCore.QUrl(url)
        QtGui.QDesktopServices.openUrl(url)

    def showEvent(self, event):
        """Show event handler.

        """
        QtCore.QTimer.singleShot(100, self.request_data)
        common.center_window(self)

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            (
                    (common.Size.Margin(2.0)) +
                    (common.Size.RowHeight(2.0))
            )
        )


class EntityNameEditor(QtWidgets.QDialog):
    nameSelected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(EntityNameEditor, self).__init__(parent=parent)
        if not self.parent():
            common.set_stylesheet(self)

        self.editor = None
        self.ok_button = None

        self.setWindowTitle('Create a new Entity')

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.Size.Margin()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = ui.add_row('Enter Entity Name', parent=self)
        self.editor = ui.LineEdit(parent=self)
        self.editor.setPlaceholderText('Enter an entity name, for example, \'SH0010\'')
        self.setFocusProxy(self.editor)

        row.layout().addWidget(self.editor, 1)

        self.ok_button = ui.PaintedButton('Create', parent=self)
        self.layout().addWidget(self.ok_button, 1)

    def _connect_signals(self):
        self.ok_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted)
        )

    def showEvent(self, event):
        """Show event handler.

        """
        self.adjustSize()
        self.editor.setFocus()
        common.center_window(self)

    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            super(EntityNameEditor, self).done(result)
            return

        if not self.editor.text():
            return

        self.nameSelected.emit(self.editor.text())
        super(EntityNameEditor, self).done(result)

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            (
                    (common.Size.Margin(2.0)) +
                    (common.Size.RowHeight(2.0))
            )
        )
