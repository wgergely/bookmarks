"""A Maya utility tool used to work with shaders.

"""
import functools
import re

import shiboken2
from PySide2 import QtWidgets, QtCore, QtGui
from maya import OpenMayaUI
from maya import cmds
from maya import mel
from maya.api import OpenMaya
from maya.app.general import mayaMixin

from .. import common


def show():
    _ = mel
    common.shaders_widget = ShadersWidget()
    common.shaders_widget.show(dockable=True)


def add_row(parent):
    widget = QtWidgets.QWidget(parent=parent)
    widget.setSizePolicy(
        QtWidgets.QSizePolicy.MinimumExpanding,
        QtWidgets.QSizePolicy.Maximum,
    )
    widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
    widget.setAttribute(QtCore.Qt.WA_NoSystemBackground)
    QtWidgets.QHBoxLayout(widget)
    widget.layout().setContentsMargins(0, 0, 0, 0)
    parent.layout().addWidget(widget, 0)
    widget.layout().setAlignment(QtCore.Qt.AlignCenter)
    return widget


def icon(name):
    return QtGui.QIcon(QtGui.QPixmap(f':/{name}'))


@functools.lru_cache(maxsize=1048576)
def elided_text(v):
    font = bold_font()
    metrics = QtGui.QFontMetrics(font)
    text = metrics.elidedText(v, QtCore.Qt.ElideLeft, 250)
    return text


@functools.lru_cache(maxsize=1024)
def bold_font():
    font = QtGui.QFont()
    font.setBold(True)
    return font


@functools.lru_cache(maxsize=1048576)
def get_attrs(shader):
    attrs = {}
    for attr in cmds.listAttr(shader):
        if '.' in attr:
            continue
        if cmds.attributeQuery(attr, node=shader, internal=True):
            continue
        if not cmds.attributeQuery(attr, node=shader, writable=True):
            continue
        if cmds.attributeQuery(attr, node=shader, listParent=True):
            continue
        _type = cmds.getAttr(f'{shader}.{attr}', type=True)
        if _type not in ('float3', 'float'):
            continue
        if any(f in attr for f in ('Camera', 'Id', 'Matte', 'Direction')):
            continue
        attrs[attr] = _type
    return attrs


class RenameDialog(QtWidgets.QDialog):
    renameRequested = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        QtWidgets.QVBoxLayout(self)
        widget = add_row(self)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Rename Shader')
        self.prefix_editor = QtWidgets.QLineEdit(parent=self)
        self.prefix_editor.setValidator(
            QtGui.QRegExpValidator(QtCore.QRegExp(r'[a-zA-Z][:a-zA-Z0-9]*'))
        )
        self.prefix_editor.setPlaceholderText('Shader prefix...')
        self.suffix_editor = QtWidgets.QLineEdit(parent=self)
        self.suffix_editor.setValidator(
            QtGui.QRegExpValidator(QtCore.QRegExp(r'[a-zA-Z][:a-zA-Z0-9]*'))
        )
        self.suffix_editor.setPlaceholderText('Shader suffix...')
        widget.layout().addWidget(self.prefix_editor, 0)
        widget.layout().addWidget(self.suffix_editor, 0)

        widget = add_row(self)
        self.ok_button = QtWidgets.QPushButton('Finish')
        self.cancel_button = QtWidgets.QPushButton('Cancel')
        widget.layout().addWidget(self.ok_button, 0)
        widget.layout().addWidget(self.cancel_button, 0)

        self.ok_button.clicked.connect(self.action)
        self.cancel_button.clicked.connect(self.close)

    def action(self):
        prefix = self.prefix_editor.text()
        suffix = self.suffix_editor.text()
        if not all((prefix, suffix)):
            OpenMaya.MGlobal.displayWarning(f'Prefix or suffix not set')
            return

        shader = f'{prefix}_{suffix}_shader'
        if cmds.objExists(shader):
            OpenMaya.MGlobal.displayWarning(f'"{shader}" already exist.')
            return

        self.renameRequested.emit(f'{prefix}_{suffix}')
        self.done(QtWidgets.QDialog.Accepted)

    def sizeHint(self):
        return QtCore.QSize(480, 60)


class ShaderModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.internal_data = {}

        self.update_timer = QtCore.QTimer(parent=self)
        self.update_timer.setInterval(333)
        self.update_timer.setTimerType(QtCore.Qt.CoarseTimer)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.init_data)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.internal_data)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4

    def flags(self, parent=QtCore.QModelIndex()):
        return (
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable
        )

    def index(self, row, column, parent=QtCore.QModelIndex()):
        return self.createIndex(row, column, parent=parent)

    def data(self, index, role=QtCore.Qt.DisplayRole, parent=QtCore.QModelIndex()):
        if role == QtCore.Qt.SizeHintRole:
            if index.column() == 0:
                metrics = QtGui.QFontMetrics(bold_font())
                width = metrics.horizontalAdvance(
                    self.data(index, role=QtCore.Qt.DisplayRole)
                ) + 12
                return QtCore.QSize(width, 18)
            else:
                metrics = QtGui.QFontMetrics(QtGui.QFont())
                width = metrics.horizontalAdvance(
                    self.data(index, role=QtCore.Qt.DisplayRole)
                ) + 12
                return QtCore.QSize(width, 18)
        if role == QtCore.Qt.ToolTipRole:
            v = self.internal_data[index.row()]['shapes']
            return '\n'.join(v)
        if role == QtCore.Qt.TextAlignmentRole and index.column() != 0:
            return QtCore.Qt.AlignCenter
        if role == QtCore.Qt.FontRole and index.column() == 0:
            return bold_font()
        if not index.isValid():
            return None
        if index.column() == 0 and role == QtCore.Qt.DisplayRole:
            v = str(self.internal_data[index.row()][QtCore.Qt.DisplayRole])
            return elided_text(v)
        if index.column() == 1 and role == QtCore.Qt.DisplayRole:
            return str(self.internal_data[index.row()]['type'])
        if index.column() == 2 and role == QtCore.Qt.DisplayRole:
            v = self.internal_data[index.row()]['shapes']
            return f'{len(v)} shapes' if v else '-'
        if index.column() == 3 and role == QtCore.Qt.DisplayRole:
            v = self.internal_data[index.row()]['connections']
            return f'{len(v)} cnxs' if v else '-'
        return None

    def headerData(self, column, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if column == 0:
                    return 'Shader'
                if column == 1:
                    return 'Type'
                if column == 2:
                    return 'Meshes'
                if column == 3:
                    return 'Connections'
        return None

    def init_data(self):
        self.beginResetModel()

        arnold_shaders = cmds.listNodeTypes(
            'rendernode/arnold/shader/surface'
        )
        surface_shaders = ['standardSurface', ]
        if arnold_shaders:
            surface_shaders += arnold_shaders

        self.internal_data = {}
        for node in cmds.ls(type='shadingEngine'):
            for attr in cmds.listAttr(node):
                if '.' in attr:
                    continue
                if cmds.attributeQuery(attr, node=node, internal=True):
                    continue
                if not cmds.attributeQuery(attr, node=node, writable=True):
                    continue
                if cmds.attributeQuery(attr, node=node, listParent=True):
                    continue
                _type = cmds.getAttr(f'{node}.{attr}', type=True)
                if _type not in ('float3', 'float', 'Tdata'):
                    continue
                if any(f in attr for f in ('Camera', 'Id', 'Matte', 'Direction')):
                    continue

                if cmds.connectionInfo(f'{node}.{attr}', isDestination=True):
                    source = cmds.connectionInfo(
                        f'{node}.{attr}', sourceFromDestination=True
                    )
                    shader = source.split('.')[0]

                    if cmds.objectType(shader) not in surface_shaders:
                        continue

                    if not re.match(r'.*[a-zA-Z0-9]+_[a-zA-Z0-9]+_shader$', shader):
                        continue

                    attrs = get_attrs(shader)
                    cnxs = [
                        a for a in attrs if
                        cmds.connectionInfo(f'{shader}.{a}', id=True)
                    ]

                    item_data = {
                        QtCore.Qt.DisplayRole: shader,
                        'shader': shader,
                        'type': cmds.objectType(shader),
                        'shadingEngine': node,
                        'attributes': attrs,
                        'connections': cnxs,
                        'shapes': []
                    }

                    nodes = cmds.sets(node, query=True)
                    nodes = nodes if nodes else []

                    for _node in nodes:
                        for n in cmds.ls(_node, long=True):
                            item_data['shapes'].append(n)
                    item_data['shapes'] = sorted(item_data['shapes'])
                    self.internal_data[len(self.internal_data)] = item_data

        self.endResetModel()


class ShaderView(QtWidgets.QTableView):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.verticalHeader().setHidden(True)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(18)
        self.horizontalHeader().setSectionsMovable(False)
        self.setSortingEnabled(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setAutoFillBackground(True)
        self.setModel(ShaderModel())

        self._selection = None
        self.callbacks = []

        self.activated.connect(self.item_activated)
        self.selectionModel().selectionChanged.connect(self.selection_changed)

        self.model().modelReset.connect(self.resizeColumnsToContents)
        self.model().modelAboutToBeReset.connect(self.save_selection)
        self.model().modelReset.connect(self.restore_selection)

    def save_selection(self):
        if not self.selectionModel().hasSelection():
            return
        index = next(f for f in self.selectionModel().selectedIndexes())
        if not index.isValid():
            return
        data = index.model().internal_data
        self._selection = data[index.row()][QtCore.Qt.DisplayRole]

    def restore_selection(self):
        if not self._selection:
            return

        for row in range(self.model().rowCount()):
            v = self.model().internal_data[row][QtCore.Qt.DisplayRole]
            if v == self._selection:
                index = self.model().index(row, 0)
                self.selectionModel().select(
                    index,
                    QtCore.QItemSelectionModel.ClearAndSelect |
                    QtCore.QItemSelectionModel.Rows
                )
                self.scrollTo(
                    index, QtWidgets.QAbstractItemView.PositionAtCenter
                )

    @QtCore.Slot()
    def select_shapes(self, *args, **kwargs):
        if not self.selectionModel().hasSelection():
            return
        index = next(f for f in self.selectionModel().selectedIndexes())
        if not index.isValid():
            return
        shader = index.model().internal_data[index.row()]['shader']

        cmds.hyperShade(objects=shader)

    @QtCore.Slot(QtCore.QModelIndex)
    def selection_changed(self, index):
        if not self.selectionModel().hasSelection():
            return
        index = next(f for f in self.selectionModel().selectedIndexes())
        if not index.isValid():
            return
        # shader = self.model().internal_data[index.row()]['shader']
        # cmds.select(shader, replace=True)

    @QtCore.Slot(QtCore.QModelIndex)
    def item_activated(self, index):
        data = index.model().internal_data
        node = data[index.row()]['shadingEngine']
        shader = data[index.row()]['shader']
        cmds.select(node, replace=True)
        cmds.select(shader, add=True)
        cmds.HypershadeWindow()
        melcmd = \
            'hyperShadePanelGraphCommand("hyperShadePanel1", "showUpAndDownstream");'
        'evalDeferred -lp "hyperShadeRefreshActiveNode";'
        cmd = f"from maya import mel;mel.eval('{melcmd}')"
        cmds.evalDeferred(cmd)

    def init_callbacks(self):
        if self.callbacks:
            return

        cb = OpenMaya.MDGMessage.addNodeAddedCallback(
            self.callback,
            'dependNode',
            clientData='addNodeAddedCallback'
        )
        self.callbacks.append(cb)
        cb = OpenMaya.MDGMessage.addNodeRemovedCallback(
            self.callback,
            'dependNode',
            clientData='addNodeRemovedCallback'
        )
        self.callbacks.append(cb)
        cb = OpenMaya.MDGMessage.addConnectionCallback(
            self.callback,
            clientData='addNodeAddedCallback'
        )
        self.callbacks.append(cb)
        cb = OpenMaya.MDagMessage.addAllDagChangesCallback(
            self.callback,
            clientData='addAllDagChangesCallback'
        )
        # self.callbacks.append(cb)

    def remove_callbacks(self):
        for cb in self.callbacks:
            OpenMaya.MMessage.removeCallback(cb)
        self.callbacks = []

    def callback(self, *args, clientData=None):
        self.model().update_timer.start(self.model().update_timer.interval())


class ShadersWidget(mayaMixin.MayaQWidgetDockableMixin, QtWidgets.QWidget):
    def __init__(self):

        ptr = OpenMayaUI.MQtUtil.mainWindow()
        if ptr:
            parent = shiboken2.wrapInstance(int(ptr), QtWidgets.QMainWindow)
        else:
            parent = None
        super().__init__(parent=parent)
        common.set_stylesheet(self)

        self.setWindowTitle('Shader Setup Utility')
        self.setWindowFlags(
            QtCore.Qt.Dialog
        )
        self.add_layer_button = None
        self.active_layer_editor = None
        self.show_layers_button = None
        self.visible_layer_editor = None
        self.search_editor = None
        self.property_override_row = None
        self.shader_override_row = None
        self.prefix_editor = None
        self.suffix_editor = None
        self.type_picker = None

        self._create_ui()
        self._connect_signals()
        self.init_data()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = 6
        self.layout().setContentsMargins(o, o, o, o)

        # =====
        group = QtWidgets.QGroupBox(parent=self)
        QtWidgets.QVBoxLayout(group)
        self.layout().addWidget(group, 0)

        # =====
        widget = add_row(group)
        self.prefix_editor = QtWidgets.QLineEdit(parent=self)
        self.prefix_editor.setValidator(
            QtGui.QRegExpValidator(QtCore.QRegExp(r'[a-zA-Z][:a-zA-Z0-9]*'))
        )
        self.prefix_editor.setPlaceholderText('Shader prefix...')
        self.suffix_editor = QtWidgets.QLineEdit(parent=self)
        self.suffix_editor.setValidator(
            QtGui.QRegExpValidator(QtCore.QRegExp(r'[a-zA-Z][:a-zA-Z0-9]*'))
        )
        self.suffix_editor.setPlaceholderText('Shader suffix...')
        self.type_picker = QtWidgets.QComboBox(parent=self)
        self.type_picker.setView(QtWidgets.QListView())
        widget.layout().addWidget(self.prefix_editor, 0)
        widget.layout().addWidget(self.suffix_editor, 0)
        widget.layout().addWidget(self.type_picker, 0)

        # Row9
        widget = add_row(group)
        self.create_shader_button = QtWidgets.QPushButton(
            '&Create Shader', parent=self
        )
        self.rename_assigned_button = QtWidgets.QPushButton(
            'Rename Assigned', parent=self
        )
        self.assign_shader_button = QtWidgets.QPushButton('Assign', parent=self)
        widget.layout().addWidget(self.create_shader_button, 1)
        widget.layout().addWidget(self.rename_assigned_button, 0)
        widget.layout().addWidget(self.assign_shader_button, 0)

        group = QtWidgets.QGroupBox(parent=self)
        QtWidgets.QVBoxLayout(group)
        self.layout().addWidget(group, 1)

        # =====
        widget = add_row(group)
        self.select_button = QtWidgets.QPushButton(
            icon('edit'), '&Select Meshes'
        )
        self.rename_button = QtWidgets.QPushButton(
            icon('textBeam'), 'Re&name'
        )
        self.duplicate_button = QtWidgets.QPushButton(
            icon('shaderList'), '&Duplicate'
        )
        self.refresh_button = QtWidgets.QPushButton(
            icon('refresh'), 'Refresh'
        )

        widget.layout().addWidget(self.select_button, 0)
        widget.layout().addWidget(self.rename_button, 0)
        widget.layout().addWidget(self.duplicate_button, 0)
        widget.layout().addWidget(self.refresh_button, 0)
        widget.layout().addStretch(1)

        # =====
        self.shader_view = ShaderView(parent=self)
        group.layout().addWidget(self.shader_view, 1)

    def _connect_signals(self):
        self.refresh_button.clicked.connect(
            self.shader_view.model().init_data
        )
        self.refresh_button.clicked.connect(
            self.init_data
        )
        self.select_button.clicked.connect(
            self.shader_view.select_shapes
        )
        self.create_shader_button.clicked.connect(
            self.create_shader_button_clicked
        )
        self.duplicate_button.clicked.connect(
            self.duplicate_button_clicked
        )
        self.shader_view.selectionModel().selectionChanged.connect(
            self.selection_changed
        )
        self.rename_button.clicked.connect(self.rename_button_clicked)
        self.assign_shader_button.clicked.connect(self.assign_shader_button_clicked)
        self.rename_assigned_button.clicked.connect(
            self.rename_assigned_button_clicked
        )
        # Make sure the callbacks are removed
        self.destroyed.connect(self.shader_view.remove_callbacks)

    @QtCore.Slot()
    def rename_assigned_button_clicked(self):
        v = self._selected_prefix_suffix()
        if not v:
            return
        sel = cmds.ls(selection=True)
        if not sel:
            OpenMaya.MGlobal.displayWarning('Nothing is selected')
        self.rename_assigned_nodes(f'{v[0]}_{v[1]}', sel)

    @QtCore.Slot()
    def assign_shader_button_clicked(self):
        if not self.shader_view.selectionModel().hasSelection():
            OpenMaya.MGlobal.displayWarning('No shader selection')
            return
        if not cmds.ls(selection=True):
            OpenMaya.MGlobal.displayWarning('Nothing is selected')
            return

        index = next(
            f for f in self.shader_view.selectionModel().selectedIndexes()
        )
        if not index.isValid():
            return
        shader = index.model().internal_data[index.row()]['shader']
        cmds.hyperShade(assign=shader)

    @QtCore.Slot()
    def rename_button_clicked(self):
        v = self._selected_prefix_suffix()
        if not v:
            return
        w = RenameDialog(parent=self)
        w.prefix_editor.setText(v[0])
        w.suffix_editor.setText(v[1])
        old_name = f'{v[0]}_{v[1]}'
        w.renameRequested.connect(functools.partial(self.rename, old_name))
        w.open()

    @QtCore.Slot(str)
    @QtCore.Slot(str)
    def rename(self, old_name, new_name):
        if old_name == new_name:
            OpenMaya.MGlobal.displayWarning(f'Old and new names are the same.')
            return

        for node in cmds.ls(long=True):
            if old_name not in node:
                continue

            try:
                _node = node.replace(old_name, new_name)
                cmds.rename(node, _node)
                OpenMaya.MGlobal.displayInfo(f'Renamed {node} > {_node}')
            except:
                OpenMaya.MGlobal.displayWarning(f'Could not rename {node}')

        self.shader_view.model().init_data()

    @QtCore.Slot(QtCore.QItemSelection)
    def selection_changed(self, selection):
        v = self._selected_prefix_suffix()
        if not v:
            return
        index = next(f for f in self.shader_view.selectionModel().selectedIndexes())
        _type = index.model().internal_data[index.row()]['type']
        self.type_picker.setCurrentText(_type)
        self.prefix_editor.setText(v[0])
        self.suffix_editor.setText(v[1])

    def _selected_prefix_suffix(self):
        if not self.shader_view.selectionModel().hasSelection():
            return None
        index = next(f for f in self.shader_view.selectionModel().selectedIndexes())
        if not index.isValid():
            return None
        name = index.data(role=QtCore.Qt.DisplayRole)
        match = re.match(
            r'([a-zA-Z0-9:]+?)_([a-zA-Z0-9]+?)_.*',
            name
        )
        if not match:
            return None
        return match.group(1), match.group(2)

    @QtCore.Slot()
    def duplicate_button_clicked(self):
        v = self._selected_prefix_suffix()
        if not v:
            return
        w = RenameDialog(parent=self)
        w.prefix_editor.setText(v[0])
        w.suffix_editor.setText(v[1])
        old_name = f'{v[0]}_{v[1]}'
        w.renameRequested.connect(functools.partial(self.duplicate, old_name))
        w.open()

    @QtCore.Slot(str)
    @QtCore.Slot(str)
    def duplicate(self, old_name, new_name):
        index = next(f for f in self.shader_view.selectionModel().selectedIndexes())
        if not index.isValid():
            return
        sg = index.model().internal_data[index.row()]['shadingEngine']
        nodes = cmds.duplicate(sg, renameChildren=True, upstreamNodes=True)

        for node in nodes:
            node = cmds.ls(node, long=True)[0]
            if old_name not in node:
                continue
            try:
                _node = node.replace(old_name, new_name)
                _node = re.sub(r'[0-9]+$', '', _node)
                if cmds.objExists(_node):
                    _node += 'Meshes'
                cmds.rename(node, _node)
                OpenMaya.MGlobal.displayInfo(f'Renamed {node} > {_node}')
            except:
                OpenMaya.MGlobal.displayWarning(f'Could not rename {node}')

        self.shader_view.model().init_data()

    @QtCore.Slot()
    def init_data(self):
        arnold_shaders = cmds.listNodeTypes(
            'rendernode/arnold/shader/surface'
        )
        surface_shaders = ['standardSurface', ]
        if arnold_shaders:
            surface_shaders += arnold_shaders
        self.type_picker.clear()
        for item in surface_shaders:
            self.type_picker.addItem(item)

        _types = cmds.listNodeTypes('rendernode/arnold/shader/volume')
        _types = _types if _types else []
        for item in _types:
            self.type_picker.addItem(item)

    @QtCore.Slot()
    def create_shader_button_clicked(self):
        sel = cmds.ls(selection=True)
        sel = sel if sel else []
        rel = cmds.listRelatives(
            sel, allDescendents=True, type='mesh',
            path=True
        )
        rel = rel if rel else []

        prefix = self.prefix_editor.text()
        suffix = self.suffix_editor.text()

        if not all((prefix, suffix)):
            OpenMaya.MGlobal.displayWarning(f'Prefix or suffix not set')
            return

        _type = self.type_picker.currentText()
        if not _type:
            return

        shader = f'{prefix}_{suffix}_shader'
        if cmds.objExists(shader):
            OpenMaya.MGlobal.displayWarning(f'"{shader}" already exist.')
            return
        cmds.shadingNode(
            _type,
            asShader=True, name=shader
        )

        material = f'{prefix}_{suffix}_material'
        if cmds.objExists(material):
            OpenMaya.MGlobal.displayWarning(f'"{material}" already exist.')
            cmds.delete(shader)
            return
        cmds.sets(
            name=material,
            renderable=True,
            noSurfaceShader=True,
            empty=True
        )
        cmds.connectAttr(
            f'{shader}.outColor',
            f'{material}.surfaceShader',
            force=True
        )

        displacement = f'{prefix}_{suffix}_displacement'
        if cmds.objExists(displacement):
            OpenMaya.MGlobal.displayWarning(f'"{displacement}" already exist.')
        else:
            cmds.shadingNode(
                'displacementShader',
                asShader=True,
                name=displacement
            )
            cmds.connectAttr(
                f'{displacement}.displacement',
                f'{material}.displacementShader',
                force=True
            )

        # Rename selected elements
        cmds.select(rel + sel, replace=True)
        if rel + sel:
            cmds.hyperShade(assign=shader)
        if sel:
            self.rename_assigned_nodes(f'{prefix}_{suffix}', sel)

    def rename_assigned_nodes(self, name, sel):
        SUFFIXES = {
            'transform': '_t',
            'mesh': 'Shape',
            'nurbsSurface': 'Shape',
            'nurbsCurve': 'Crv',
            'bezierCurve': 'Crv',
            'locator': 'Loc',
        }

        def _filter(lst):
            """ Returns a filtered list accepting only the specified object types.
            The resulting list is reverse sorted, to avoid missing object names when
            renaming."""

            lst = set(lst)
            if not lst:
                return []
            arr = []
            for i in lst:
                for typ in SUFFIXES:
                    if cmds.objectType(i) == typ:
                        arr.append(i)

            arr.sort(key=lambda x: x.count('|'))
            return arr[::-1]  # reverse list

        _shapes = ['mesh', 'nurbsSurface']
        _f = [f for f in sel if cmds.objectType(f) == 'transform']
        f_ = [cmds.listRelatives(f, parent=True)[0] for f in sel if
              cmds.objectType(f) in _shapes]
        sel = _filter(_f + f_)
        sel = sorted(sel) if sel else []

        if not sel:
            return []

        if not name:
            return []

        for node in sel:
            if name in node:
                continue

            suffix = [SUFFIXES[f] for f in SUFFIXES if f == cmds.objectType(node)]
            if not suffix:
                continue

            suffix = suffix[0]
            cmds.rename(
                node,
                f'{name}{suffix}#',
                ignoreShape=False
            )

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.BackgroundColor))
        painter.drawRect(self.rect())
        painter.end()

    def showEvent(self, event):
        super().showEvent(event)
        self.shader_view.model().init_data()
        self.shader_view.init_callbacks()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.shader_view.remove_callbacks()

    def closeEvent(self, event):
        super().closeEvent(event)
        self.shader_view.remove_callbacks()
