"""The widget used to link multiple local assets with ShotGrid entities.

"""
import functools

from PySide2 import QtWidgets, QtCore, QtGui

from . import shotgun
from .. import common
from .. import database
from .. import images
from .. import ui
from ..shotgun import actions as sg_actions

instance = None

NOT_LINKED = 'Not linked'
CURRENT_VALUES = 'Linked (keep current values)'

ROW_HEIGHT = common.Size.RowHeight()
ENTITY_TYPES = ('Asset', 'Shot', 'Sequence')


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


def show():
    global instance
    close()
    instance = LinkMultiple()
    instance.open()
    return instance


class TableWidget(QtWidgets.QTableWidget):
    """The table that contains our list of non-archived assets, and the combobox
    and button used to associate/create ShotGrid entities.

    """
    createEntity = QtCore.Signal(
        str, QtWidgets.QWidget, QtWidgets.QWidget
    )  # Name

    def __init__(self, parent=None):
        super(TableWidget, self).__init__(parent=parent)

        self.data = {}

        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(
            ('Local Assets', '', 'ShotGrid Entity', 'Create Entity')
        )
        self.verticalHeader().setVisible(False)

        header = QtWidgets.QHeaderView(QtCore.Qt.Horizontal, parent=self)
        self.setHorizontalHeader(header)

        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)

        self.setColumnWidth(1, common.Size.RowHeight())
        self.setColumnWidth(2, common.Size.DefaultWidth(0.4))
        self.setColumnWidth(3, common.Size.DefaultWidth(0.2))

        self.setShowGrid(False)

        item = QtWidgets.QTableWidgetItem('>')
        item.setFlags(QtCore.Qt.NoItemFlags)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.setItemPrototype(item)

    def add_row(self, name, editor, current_data):
        row = self.rowCount()
        self.insertRow(row)
        self.setRowHeight(row, ROW_HEIGHT)

        _item = QtWidgets.QTableWidgetItem(name)
        _item.setFlags(QtCore.Qt.ItemIsEnabled)
        _item.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        pixmap = images.rsc_pixmap(
            'asset', common.Color.DarkBackground(),
            common.Size.Margin()
        )
        icon = QtGui.QIcon()
        icon.addPixmap(pixmap, QtGui.QIcon.Normal)
        _item.setIcon(icon)
        self.setItem(row, 0, _item)

        item = QtWidgets.QTableWidgetItem('')
        item.setFlags(QtCore.Qt.NoItemFlags)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.setItem(row, 1, item)
        pixmap = images.rsc_pixmap(
            'branch_closed', common.Color.DarkBackground(),
            common.Size.Margin()
        )
        label = QtWidgets.QLabel()
        label.setPixmap(pixmap)
        self.setCellWidget(row, 1, label)

        item = QtWidgets.QTableWidgetItem('')
        item.setFlags(QtCore.Qt.NoItemFlags)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.setItem(row, 2, item)
        self.setCellWidget(row, 2, editor)

        item = QtWidgets.QTableWidgetItem('')
        item.setFlags(QtCore.Qt.NoItemFlags)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.setItem(row, 3, item)
        button = ui.PaintedButton('Create')
        button.clicked.connect(
            functools.partial(self.createEntity.emit, name, editor, button)
        )

        button.setDisabled(True)
        self.setCellWidget(row, 3, button)

        # Store the internal data
        self.data[row] = {
            'item': _item,
            'editor': editor,
            'button': button,
            'current_data': current_data
        }


class LinkMultiple(QtWidgets.QDialog):
    """The main widget used to link multiple local assets with their ShotGrid
    counterparts.

    """
    sgAssetsLinked = QtCore.Signal()
    entityTypeFilterChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(LinkMultiple, self).__init__(parent=parent)
        self.entity_type_filter = None
        self.ok_button = None
        self.cancel_button = None
        self.table = None

        self.model = None

        self.setWindowTitle('Link Local Assets with ShotGrid')

        self._create_ui()
        self._connect_signals()
        self.restore_current_filter()

    def _create_ui(self):
        if not self.parent():
            common.set_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        o = common.Size.Margin()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        # Init the type filter
        self.entity_type_filter = shotgun.EntityComboBox(
            ENTITY_TYPES, parent=self
        )
        row = ui.add_row('Select Entity Type', parent=self)
        row.layout().addWidget(self.entity_type_filter, 1)

        self.table = TableWidget(parent=None)
        self.layout().addWidget(self.table, 1)

        row = ui.add_row(None, parent=self)
        self.ok_button = ui.PaintedButton('Done', parent=self)
        self.cancel_button = ui.PaintedButton('Cancel', parent=self)
        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.cancel_button, 0)

    @common.error
    def _connect_signals(self):
        self.ok_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted)
        )
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected)
        )

        self.entity_type_filter.activated.connect(self.save_current_filter)
        self.entity_type_filter.activated.connect(self.emit_filter_changed)
        self.table.createEntity.connect(self.create_entity)

    def restore_current_filter(self):
        v = common.settings.value('sg_link_multiple/filter')
        if v:
            self.blockSignals(True)
            self.entity_type_filter.setCurrentText(v)
            self.blockSignals(False)
            return

    def save_current_filter(self, *args, **kwargs):
        v = self.entity_type_filter.itemData(
            self.entity_type_filter.currentIndex(),
            role=QtCore.Qt.DisplayRole
        )
        common.settings.setValue('sg_link_multiple/filter', v)

    def emit_filter_changed(self, *args, **kwargs):
        v = self.entity_type_filter.currentData(role=QtCore.Qt.DisplayRole)
        self.entityTypeFilterChanged.emit(v)

    def source(self):
        server = common.active('server')
        job = common.active('job')
        root = common.active('root')

        if not all((server, job, root)):
            return None

        return '/'.join((server, job, root))

    @common.error
    @common.debug
    def init_data(self):
        """Initializes data.

        """
        if not self.source():
            raise RuntimeError('Invalid context.')

        sg_properties = shotgun.SGProperties(active=True)

        db = database.get(
            sg_properties.server,
            sg_properties.job,
            sg_properties.root
        )
        sg_properties.init(db=db)

        if not sg_properties.verify(connection=True):
            raise RuntimeError(
                'Bookmark is not configured to use ShotGrid.'
            )

        self.emit_request(sg_properties)

        model = common.source_model(common.AssetTab)
        data = model.model_data()

        for idx in data:
            if data[idx][common.FlagsRole] & common.MarkedAsArchived:
                continue

            # Manually create an entity based on the current db values
            s = data[idx][common.ParentPathRole][3]
            t = database.AssetTable
            entity = {
                'id': db.value(s, 'sg_id', t),
                'code': db.value(s, 'sg_name', t),
                'type': db.value(s, 'sg_type', t),
                'cut_out': db.value(s, 'cut_out', t),
                'cut_in': db.value(s, 'cut_in', t),
                'cut_duration': db.value(s, 'cut_duration', t),
                'description': db.value(s, 'description', t),
            }

            # Add rows to the table widget
            editor = shotgun.EntityComboBox(
                [NOT_LINKED, CURRENT_VALUES], fixed_height=None, parent=None
            )
            editor.set_model(self.model)

            proxy = editor.model()
            self.entityTypeFilterChanged.connect(proxy.set_entity_type)
            self.model.entityDataReceived.connect(self.select_candidates)

            self.table.add_row(s, editor, entity)

        self.entityTypeFilterChanged.connect(self.select_candidates)
        self.emit_filter_changed()

    @common.error
    @common.debug
    def emit_request(self, sg_properties):
        self.model = shotgun.EntityModel([NOT_LINKED, CURRENT_VALUES])

        request_filter = [
            ['project', 'is', {
                'type': 'Project',
                'id': sg_properties.bookmark_id
            }],
        ]

        for entity_type in ENTITY_TYPES:
            self.model.entityDataRequested.emit(
                self.model.uuid,
                sg_properties.server,
                sg_properties.job,
                sg_properties.root,
                None,
                False,
                entity_type,
                request_filter,
                shotgun.entity_fields[entity_type]
            )

        for row in self.table.data:
            data = self.table.data[row]
            # data['editor'].setCurrentIndex(0)

    @common.error
    @common.debug
    def select_candidates(self, *args, **kwargs):
        """Selects matching entity candidates in our combobox editors.

        """
        for row in self.table.data:
            data = self.table.data[row]
            name = data['item'].text()
            editor = data['editor']
            button = data['button']

            # Find the local asset, and select it if found
            idx = editor.findText(name, flags=QtCore.Qt.MatchFixedString)
            if idx > 0:
                # An entity with the same name as our local asset already exists
                editor.setCurrentIndex(idx)
                button.setDisabled(True)
                continue

            # No matching entity was found, let the user be able to create
            # a new entity
            button.setDisabled(False)

            # Let's check if the local asset has already a valid configuration
            # and select a default choice based on the result
            if all(
                    (
                            data['current_data']['id'],
                            data['current_data']['type'],
                            data['current_data']['code'],
                    )
            ):
                # ALready has a valid configuration
                editor.setCurrentIndex(1)
            else:
                # Entity is not linked
                editor.setCurrentIndex(0)

    @common.error
    @common.debug
    def create_entity(self, entity_name, editor, button):
        """Create and add and select a new entity."""
        entity_type = self.entity_type_filter.currentText()
        entity = sg_actions.create_entity(entity_type, entity_name)
        editor.append_entity(entity)
        button.setDisabled(True)

    @common.error
    @common.debug
    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            super(LinkMultiple, self).done(result)
            return
        self.save_data()
        self.sgAssetsLinked.emit()
        super(LinkMultiple, self).done(result)

    def save_data(self):
        """Save the selected entity data to the bookmark database.

        """
        server = common.active('server')
        job = common.active('job')
        root = common.active('root')

        for row in self.table.data:
            data = self.table.data[row]

            # Skip if the user chose not to link any new data
            if data['editor'].currentText() == CURRENT_VALUES:
                continue

            # If not lined is selected, we'll unset id, type and name
            if data['editor'].currentText() == NOT_LINKED:
                entity = {
                    'type': None,
                    'id': None,
                    'code': None,
                }
            else:
                entity = data['editor'].currentData(role=shotgun.EntityRole)
                if not entity:
                    continue

            asset = data['item'].text()
            source = '/'.join((server, job, root, asset))

            from . import link_asset
            sg_actions.save_entity_data_to_db(
                server,
                job,
                root,
                source,
                database.AssetTable,
                entity,
                link_asset.value_map
            )

    def showEvent(self, event):
        """Show event handler.

        """
        common.center_window(self)
        QtCore.QTimer.singleShot(100, self.init_data)

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight()
        )
