"""
Module for saving and restoring Maya shading engine state.

This module provides functions to save the state of a shading engine in a JSON file,
and to restore the state of a shading engine from a JSON file.

The state includes attributes and connections of the shading engine and its connected nodes,
as well as the color ramps of aiRampRgb nodes.

Usage Example:
    # Save the state of a shading engine
    save_shading_engine_as_json("myShadingEngine", "/path/to/myShadingEngine.json")

    # Restore the state of a shading engine
    loads_shading_engine_as_json("/path/to/myShadingEngine.json")

Author:
    Gergely Wootsch
    hello@gergely-wootsch.com
    (c) Studio Aka, 2023.

"""
import functools
import json
import os
import re

import maya.api.OpenMaya as OpenMaya
import maya.cmds as cmds
from PySide2 import QtCore, QtGui, QtWidgets

from .. import base as mayabase

WINDOW_TITLE = 'Aka Shader Templates'
NUMERIC_TYPES = ['double', 'float', 'long', 'short', 'byte', 'int']

DEFAULT_PREFIX = 'main'

TEXTURE_FILE_PATTERNS = {
    'base': '.*{name}.*_base.*1001.*',
    'opacity': '.*{name}.*_opacity.*1001.*',
    'line': '.*{name}.*_lines.*1001.*',
    'mask': '.*{name}.*_toon.*1001.*',
    'displacement': '.*{name}.*_displacement.*1001.*'
}

IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'tif', 'tiff', 'tga', 'bmp', 'exr']

TEMPLATE_DIR_KEY = 'template_folder'

instance = None

HELP = f"""
<h3>Exporting/Importing and Node Naming</h3>
<p>The module exports each element of a shading network into a JSON file. For automatic naming to work the template 
shading network nodes should be prefix with '{DEFAULT_PREFIX}' so they are named '{DEFAULT_PREFIX}_color_texture', 
'{DEFAULT_PREFIX}_toon_lines', and so on.</p>
<p>When importing templates with '{DEFAULT_PREFIX}' nodes will be automatically renamed using the custom name set on 
the left hand side.</p>

<h3>Setting Texture Files</h3>
<p>You can manually enter the paths to texture files of base color, opacity, line, mask, and displacement.</p>
<p>The 'Find texture files' feature will automatically search for texture files in your current Maya project's 
sourceimages directory. This search is based on the name you've provided for your shader, defaulting to '
{DEFAULT_PREFIX}' if no name is provided. It expects the texture files to follow a specific naming convention, 
which includes the shader name and the texture type:
<ul>{TEXTURE_FILE_PATTERNS['base']}</ul>
<ul>{TEXTURE_FILE_PATTERNS['opacity']}</ul>
<ul>{TEXTURE_FILE_PATTERNS['line']}</ul>
<ul>{TEXTURE_FILE_PATTERNS['mask']}</ul>
<ul>{TEXTURE_FILE_PATTERNS['displacement']}</ul>
</p>
"""


def get_source_images_dir():
    w = cmds.workspace(query=True, rootDirectory=True)
    if not w:
        return []

    w = w.rstrip('/')
    candidates = ('textures', 'sourceimages', 'images', 'renders')
    rules = [f for f in cmds.workspace(fileRuleList=True, query=True) if f.lower() in candidates]
    return [f'{w}/{cmds.workspace(fileRuleEntry=f)}' for f in rules if
            QtCore.QFileInfo(f'{w}/{cmds.workspace(fileRuleEntry=f)}').exists()]


def get_plug_tree(obj):
    if obj.isNull():
        return

    node_fn = OpenMaya.MFnDependencyNode(obj)
    attr_count = node_fn.attributeCount()

    attrs = {}
    for j in range(attr_count):
        attr_plug = OpenMaya.MPlug(obj, node_fn.attribute(j))
        a = f'{node_fn.name()}.{attr_plug.partialName()}'

        # Skip uninitialized attributes
        if '-1' in a:
            continue

        try:
            is_destination = cmds.connectionInfo(a, isDestination=True)
            is_source = cmds.connectionInfo(a, isSource=True)
            if is_destination or is_source:
                continue

            attr_type = cmds.getAttr(a, type=True)
            if attr_type in NUMERIC_TYPES:
                attr_value = cmds.getAttr(a)
                try:
                    default_attr_value = cmds.attributeQuery(
                        attr_plug.partialName(), node=node_fn.name(), listDefault=True
                    )[0]
                except RuntimeError:
                    print(f'Error: {node_fn.name()}.{attr_plug.partialName()}', attr_type)
                    continue
                if attr_value != default_attr_value:
                    attrs[f'{node_fn.name()}.{attr_plug.partialName()}'] = attr_value
        except Exception as e:
            print(f'Error: {node_fn.name()}.{attr_plug.partialName()}', e)

    has_source = False
    for i in range(attr_count):
        attr_obj = node_fn.attribute(i)
        attr_plug = OpenMaya.MPlug(obj, attr_obj)

        if attr_plug.isConnected and attr_plug.isDestination and attr_plug.source():
            has_source = True

            source_attr = attr_plug.source()
            source = OpenMaya.MFnDependencyNode(source_attr.node()).name()

            # Filter nodes
            if source == 'defaultColorMgtGlobals':
                continue

            # if f'{DEFAULT_PREFIX}_' not in node_fn.name():
            #     raise RuntimeError(f'{node_fn.name()}: incorrect name!')
            # if f'{DEFAULT_PREFIX}_' not in source:
            #     raise RuntimeError(f'{source}: incorrect name!')

            yield {
                'node': node_fn.name(),
                'type': node_fn.typeName,
                'attrs': attrs,
                'connection': {
                    'conn_source': f'{source}.{source_attr.partialName()}',
                    'conn_destination': f'{node_fn.name()}.{attr_plug.partialName()}'
                }
            }

            _obj = source_attr.node()
            if not _obj.isNull():
                for v in get_plug_tree(_obj):
                    yield v

    if not has_source:
        yield {
            'node': node_fn.name(),
            'type': node_fn.typeName,
            'attrs': attrs,
            'connection': {}
        }


def get_obj(node):
    """
    Get the MObject of the given node name.

    Args:
        node (str): The name of the node.

    Returns:
        MObject: The MObject of the node if found, or None if not found.
    """
    sl = OpenMaya.MSelectionList()
    sl.add(node)
    if sl.length() > 0:
        return sl.getDependNode(0)
    return None


def save_ramp_state(node):
    """
    Save the state of the given ramp node.

    Args:
        node (str): The name of the ramp node.

    Returns:
        list: A list of tuples containing the position, color, and interpolation of each entry.

    """
    indices = cmds.getAttr(node + ".ramp", multiIndices=True)

    ramp_state = []

    for i in indices:
        position = cmds.getAttr(f"{node}.ramp[{i}].ramp_Position")
        color = cmds.getAttr(f"{node}.ramp[{i}].ramp_Color")
        interp = cmds.getAttr(f"{node}.ramp[{i}].ramp_Interp")
        ramp_state.append((position, color, interp))

    return ramp_state


def restore_ramp_state(node, ramp_state):
    """
    Restore the state of the given ramp node.

    Args:
        node (str): The name of the ramp node.
        ramp_state (list): A list of tuples containing the position, color, and interpolation of each entry.

    """
    # remove existing ramp entries
    indices = cmds.getAttr(node + ".ramp", multiIndices=True)
    if indices:
        for i in indices:
            cmds.removeMultiInstance(f"{node}.ramp[{i}]", b=True)

    # create ramp entries
    for i, (position, color, interp) in enumerate(ramp_state):
        cmds.setAttr(f"{node}.ramp[{i}].ramp_Position", position)
        cmds.setAttr(f"{node}.ramp[{i}].ramp_Color", *color[0], type='double3')
        cmds.setAttr(f"{node}.ramp[{i}].ramp_Interp", interp)


def save_shading_engine_as_json(shading_engine, json_file_path):
    """
    Saves a shading engine as a json file.

    Args:
        shading_engine (str): The name of the shading engine.
        json_file_path (str): The path to the json file.

    """

    # Log a success message
    OpenMaya.MGlobal.displayInfo(f'Saving shader template of {shading_engine} to {json_file_path}')

    if not cmds.objExists(shading_engine):
        raise RuntimeError(
            f'{shading_engine} not found! The available shading engines are:\n'
            f'{", ".join(f for f in cmds.ls(type="shadingEngine") if "initial" not in f)}'
        )

    if not cmds.nodeType(shading_engine) == 'shadingEngine':
        raise RuntimeError(f'{shading_engine} is not a shading engine!')

    data = {}
    obj = get_obj(shading_engine)

    if not obj:
        raise RuntimeError(f'{shading_engine} not found!')

    for v in get_plug_tree(obj):
        if v['node'] not in data:
            data[v['node']] = {}
            data[v['node']]['type'] = v['type']
            data[v['node']]['attrs'] = v['attrs']
            data[v['node']]['connections'] = []

            if v['type'] == 'aiRampRgb':
                data[v['node']]['ramp'] = save_ramp_state(v['node'])

        if v['connection'] not in data[v['node']]['connections']:
            data[v['node']]['connections'].append(v['connection'])

    # Write json file
    if not os.path.exists(os.path.dirname(json_file_path)):
        raise RuntimeError(f'{os.path.dirname(json_file_path)} not found!')

    with open(json_file_path, 'w') as f:
        json.dump(data, f, indent=4)

    # Log a success message
    OpenMaya.MGlobal.displayInfo(f'Saved {shading_engine} as {json_file_path}')


def loads_shading_engine_as_json(json_file_path, name='main'):
    """
    Loads a shading engine from a json file.

    Args:
        json_file_path (str): The path to the json file.
        name (str): The name of the shading engine. Optional, defaults to 'main'.

    """
    if not os.path.exists(json_file_path):
        raise RuntimeError(f'{json_file_path} not found!')

    with open(json_file_path, 'r') as f:
        data = json.load(f)

    cmds.undoInfo(openChunk=True)
    try:
        for k in data:
            if not cmds.objExists(k.replace(f'{DEFAULT_PREFIX}_', name + '_')):
                print(f'Creating {k}'.replace(f'{DEFAULT_PREFIX}_', name + '_'))

                if data[k]['type'] == 'shadingEngine':
                    # Create shading engine
                    cmds.sets(
                        name=k.replace(f'{DEFAULT_PREFIX}_', name + '_'),
                        renderable=True,
                        noSurfaceShader=True,
                        empty=True
                    )
                else:
                    cmds.createNode(data[k]['type'], name=k.replace(f'{DEFAULT_PREFIX}_', name + '_'))

        for k in data:
            for connection in data[k]['connections']:
                if not connection:
                    continue

                cmds.connectAttr(
                    connection['conn_source'].replace(f'{DEFAULT_PREFIX}_', name + '_'),
                    connection['conn_destination'].replace(f'{DEFAULT_PREFIX}_', name + '_'), force=True
                )

            for attr in data[k]['attrs']:
                cmds.setAttr(attr.replace(f'{DEFAULT_PREFIX}_', name + '_'), data[k]['attrs'][attr])

            if data[k]['type'] == 'aiRampRgb' and 'ramp' in data[k]:
                restore_ramp_state(k.replace(f'{DEFAULT_PREFIX}_', name + '_'), data[k]['ramp'])
    finally:
        cmds.undoInfo(closeChunk=True)


class ElidedLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWordWrap(False)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        metrics = QtGui.QFontMetrics(self.font())
        elided = metrics.elidedText(self.text(), QtCore.Qt.ElideMiddle, self.width())
        painter.drawText(self.rect(), self.alignment(), elided)


class PopupMessage(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #465945; /* This is a green color. */
                color: white;
                padding: 30px;
                border-radius: 6px; /* Makes the edges of the popup rounded. */
                font-weight: bold; /* Makes the text bold. */
                text-align: center; /* Centers the text. */
            }
            """
        )

        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel('')
        layout.addWidget(self.label)

        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)

        self.opacity_anim = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(400)

        self.setGraphicsEffect(self.opacity_effect)

    def show_widget(self):
        self.show()

        n = 0.5
        width = self.parent().geometry().width()
        height = self.geometry().height()

        self.setGeometry(
            self.parent().geometry().x() + ((width * (1 - n)) * 0.5),
            self.parent().frameGeometry().y() + ((height * (1 - n)) * 0.5),
            width * n,
            height * n,
        )

        self.opacity_effect.setOpacity(0.0)

        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

        QtCore.QTimer.singleShot(2000, self.hide_widget)

    def hide_widget(self):
        self.opacity_effect.setOpacity(1.0)
        self.opacity_anim.setStartValue(1.0)
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.start()
        QtCore.QTimer.singleShot(self.opacity_anim.duration(), self.hide)

    def show_message(self, message):
        self.label.setText(message)
        self.show_widget()


def get_icon(name):
    for resource in cmds.resourceManager(nameFilter="*"):
        if os.path.splitext(resource)[0] == name:
            return QtGui.QIcon(":" + name)

    for root in os.environ.get("XBMLANGPATH", "").split(os.pathsep):
        if not os.path.exists(root):
            continue
        _, _, filenames = next(os.walk(root))
        for fname in filenames:
            if os.path.splitext(fname)[0] == name:
                return QtGui.QIcon(os.path.join(root, fname))
    return None


class JSONFileModel(QtCore.QAbstractListModel):
    def __init__(self):
        super().__init__()
        self.directory = None
        self.file_list = []

        self.icon = get_icon("out_shadingEngine")
        self.settings = QtCore.QSettings('StudioAka', 'ShaderTemplateManager')

        self.file_watcher = QtCore.QFileSystemWatcher()
        self.file_watcher.directoryChanged.connect(self.update_file_list)

    def set_directory(self, directory):
        self.directory = directory
        self.update_file_list()

        all_paths = self.file_watcher.directories() + self.file_watcher.files()
        self.file_watcher.removePaths(all_paths)
        self.file_watcher.addPath(directory)

    def get_json_files(self):
        return [f for f in os.listdir(self.directory) if f.endswith('.json')]

    def update_file_list(self):
        self.beginResetModel()
        self.file_list = self.get_json_files()
        self.endResetModel()
        self.layoutChanged.emit()

    def rowCount(self, parent=None):
        return len(self.file_list)

    def data(self, index, role):
        if not self.file_list:
            return None
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return self.file_list[index.row()]
        if role == QtCore.Qt.DecorationRole:
            return self.icon
        if role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(200, 32)
        if role == QtCore.Qt.UserRole:
            template_folder = self.settings.value(TEMPLATE_DIR_KEY, '')
            return f'{template_folder}/{self.file_list[index.row()]}'


class TemplateComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModel(JSONFileModel())
        self.settings = QtCore.QSettings('StudioAka', 'ShaderTemplateManager')

        self.model().modelReset.connect(lambda: self.setCurrentIndex(-1))
        self.model().modelReset.connect(self.restore_state)

    def restore_state(self):
        saved_index = self.settings.value('template_combo_index', 0)
        try:
            saved_index = int(saved_index)
        except ValueError:
            saved_index = 0

        if 0 <= saved_index < self.count():
            self.setCurrentIndex(saved_index)

    def save_state(self):
        self.settings.setValue('template_combo_index', self.currentIndex())

    def closeEvent(self, event):
        self.save_state()
        super().closeEvent(event)

    def hideEvent(self, event):
        self.save_state()
        super().hideEvent(event)


class JSONHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, document):
        super(JSONHighlighter, self).__init__(document)

        self.rules = [
            # property keys
            (r'"[^"\\]*(?:\\.[^"\\]*)*":', QtGui.QColor("#569cd6")),  # Light Blue
            # string literals
            (r'"[^"\\]*(?:\\.[^"\\]*)*"', QtGui.QColor("#ce9178")),  # Light Red
            # numbers
            (r'\b\d+(\.\d+)?\b', QtGui.QColor("#b5cea8")),  # Light Green
            # true, false, null
            (r'\b(true|false|null)\b', QtGui.QColor("#4ec9b0")),  # Aqua
            # structural characters
            (r'[\{\}\[\]:,]', QtGui.QColor("#d4d4d4"))  # White
        ]

    def highlightBlock(self, text):
        for pattern, color in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), color)


class JSONViewerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        self.highlighter = JSONHighlighter(self.text_edit.document())

        font = QtGui.QFont('Consolas', 9)  # Change the font to 'Courier New' and size to 12
        self.text_edit.setFont(font)

        # Create layout and add widget
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)

    def set_text(self, json_path):
        if not json_path:
            self.text_edit.setPlainText('')
            return

        if not QtCore.QFileInfo(json_path).exists():
            self.text_edit.setPlainText('')
            return

        with open(json_path, 'r') as json_file:
            # Load JSON content from the file
            json_content = json.load(json_file)

            # Convert JSON to a formatted string and set as QTextEdit content
            formatted_json = json.dumps(json_content, indent=4)
            self.text_edit.setPlainText(formatted_json)

    def sizeHint(self):
        return QtCore.QSize(520, 320)


class PresetsWidget(QtWidgets.QDialog):
    templateFolderChanged = QtCore.Signal(str)
    templateSelectionChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.message_widget = PopupMessage(parent=self)

        self.settings = QtCore.QSettings('StudioAka', 'ShaderTemplateManager')
        self.template_dir = None

        self.setWindowTitle(WINDOW_TITLE)
        self.setObjectName('AkaShaderPresetsManagerOdyssey')
        self.setMinimumWidth(600)

        self._create_ui()
        self._connect_signals()
        self.init_data()

    def init_data(self):
        self.template_dir = self.settings.value(TEMPLATE_DIR_KEY, '')
        if self.template_dir and QtCore.QFileInfo(self.template_dir).exists():
            self.templateFolderChanged.emit(self.template_dir)

    def _create_ui(self):
        self.main_layout = QtWidgets.QVBoxLayout()

        # Settings button
        self.settings_button = QtWidgets.QPushButton('...')
        self.settings_button.setMaximumWidth(25)
        self.settings_label = ElidedLabel('No yet initialized')

        self.template_combobox = TemplateComboBox()
        self.template_combobox.setModel(JSONFileModel())

        # Save group
        self.save_group = QtWidgets.QGroupBox()
        self.save_layout = QtWidgets.QVBoxLayout()

        self.shading_engine_combo = QtWidgets.QComboBox()
        self.shading_engine_combo.addItems(f for f in cmds.ls(type='shadingEngine') if 'initial' not in f)

        self.reload_button = QtWidgets.QPushButton('Reload')

        self.save_button = QtWidgets.QPushButton('Save New Preset')

        self.save_layout.addWidget(self.shading_engine_combo)
        self.save_layout.addWidget(self.reload_button)
        self.save_layout.addWidget(self.save_button)

        self.save_group.setLayout(self.save_layout)

        # Load group
        self.import_group = QtWidgets.QGroupBox()
        self.import_layout = QtWidgets.QVBoxLayout()

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText('Name, for example "body"')

        self.import_button = QtWidgets.QPushButton('Import/Update Shader')

        self.import_layout.addWidget(self.template_combobox)
        self.import_layout.addWidget(self.name_edit)

        self.find_textures_button = QtWidgets.QPushButton('Find')
        self.find_textures_button.setFixedWidth(48)
        self.import_layout.addWidget(self.find_textures_button, 0)

        self.base_path = QtWidgets.QLineEdit()
        self.base_path.setPlaceholderText('base color texture path')
        self.pick_base_path = QtWidgets.QPushButton('...')

        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(self.base_path)
        widget.layout().addWidget(self.pick_base_path)
        self.import_layout.addWidget(widget)

        self.opacity_path = QtWidgets.QLineEdit()
        self.opacity_path.setPlaceholderText('opacity texture path')
        self.pick_opacity_path = QtWidgets.QPushButton('...')

        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(self.opacity_path)
        widget.layout().addWidget(self.pick_opacity_path)
        self.import_layout.addWidget(widget)

        self.line_path = QtWidgets.QLineEdit()
        self.line_path.setPlaceholderText('line texture path')
        self.pick_line_path = QtWidgets.QPushButton('...')

        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(self.line_path)
        widget.layout().addWidget(self.pick_line_path)
        self.import_layout.addWidget(widget)

        self.mask_path = QtWidgets.QLineEdit()
        self.mask_path.setPlaceholderText('mask texture path')
        self.pick_mask_path = QtWidgets.QPushButton('...')

        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(self.mask_path)
        widget.layout().addWidget(self.pick_mask_path)
        self.import_layout.addWidget(widget)

        self.displacement_path = QtWidgets.QLineEdit()
        self.displacement_path.setPlaceholderText('displacement texture path')
        self.pick_displacement_path = QtWidgets.QPushButton('...')

        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(self.displacement_path)
        widget.layout().addWidget(self.pick_displacement_path)
        self.import_layout.addWidget(widget)

        self.import_group.setLayout(self.import_layout)
        self.import_layout.addWidget(self.import_button)

        self.main_layout.addStretch(1)
        self.main_layout.addWidget(self.save_group, 0)
        self.main_layout.addSpacing(8)
        self.main_layout.addWidget(self.import_group, 1)
        self.main_layout.addStretch(1)

        QtWidgets.QHBoxLayout(self)

        main_layout_widget = QtWidgets.QWidget()
        main_layout_widget.setLayout(self.main_layout)
        help_label = QtWidgets.QLabel(HELP)
        help_label.setWordWrap(True)

        side_widget = QtWidgets.QWidget()
        side_widget.setMaximumWidth(480)

        QtWidgets.QVBoxLayout(side_widget)
        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)

        row.layout().addWidget(self.settings_label, 1)
        row.layout().addWidget(self.settings_button, 0)

        side_widget.layout().addWidget(row, 0)
        side_widget.layout().addWidget(help_label, 1)

        self.template_preview_widget = JSONViewerWidget()

        self.layout().addWidget(main_layout_widget, 1)
        self.layout().addWidget(side_widget)
        self.layout().addWidget(self.template_preview_widget)

    def _connect_signals(self):
        self.settings_button.clicked.connect(self.pick_template_directory)

        self.save_button.clicked.connect(self.save_preset)

        self.import_button.clicked.connect(self.import_preset)
        self.find_textures_button.clicked.connect(self.find_textures)

        self.pick_base_path.clicked.connect(functools.partial(self.pick_texture_path, self.base_path))
        self.pick_opacity_path.clicked.connect(functools.partial(self.pick_texture_path, self.opacity_path))
        self.pick_line_path.clicked.connect(functools.partial(self.pick_texture_path, self.line_path))
        self.pick_mask_path.clicked.connect(functools.partial(self.pick_texture_path, self.mask_path))
        self.pick_displacement_path.clicked.connect(functools.partial(self.pick_texture_path, self.displacement_path))

        self.templateFolderChanged.connect(lambda x: self.settings.setValue(TEMPLATE_DIR_KEY, x))
        self.templateFolderChanged.connect(self.template_combobox.model().set_directory)
        self.templateFolderChanged.connect(self.template_combobox.restore_state)
        self.templateFolderChanged.connect(lambda x: self.settings_label.setText(f'Template folder: {x}'))
        self.template_combobox.currentIndexChanged.connect(
            lambda x: self.templateSelectionChanged.emit(self.template_combobox.currentData())
        )

        self.template_combobox.model().modelAboutToBeReset.connect(lambda: self.templateSelectionChanged.emit(''))
        self.template_combobox.model().modelAboutToBeReset.connect(lambda: self.template_preview_widget.set_text(''))

        self.templateSelectionChanged.connect(self.template_preview_widget.set_text)

        self.reload_button.clicked.connect(self.reload_shading_endinges)

    def sizeHint(self):
        return QtCore.QSize(1400, 300)

    @QtCore.Slot()
    def reload_shading_endinges(self):
        self.shading_engine_combo.clear()
        self.shading_engine_combo.addItems(f for f in cmds.ls(type='shadingEngine') if 'initial' not in f)

    def show_message(self, message):
        self.message_widget.show_message(message)

    @QtCore.Slot()
    def pick_texture_path(self, editor):
        dirs = get_source_images_dir()
        root = dirs[0] if dirs else None
        path = QtWidgets.QFileDialog.getOpenFileName(self, 'Pick Base Color Texture', root)[0]
        if path:
            editor.setText(path)

    @QtCore.Slot()
    def pick_template_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Template Directory", self.template_dir)
        if directory:
            self.template_dir = directory
            self.templateFolderChanged.emit(self.template_dir)
            return directory
        return None

    @QtCore.Slot()
    def save_preset(self):
        shading_engine = self.shading_engine_combo.currentText()
        filename = f'{shading_engine}.json'

        if not self.template_dir or not QtCore.QFileInfo(self.template_dir).exists():
            self.pick_template_directory()
        if not self.template_dir:
            return

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Shader Preset', self.template_dir, 'JSON Files (*.json)'
        )

        # check if the file path is valid and if it already exists
        # if it does, ask the user if they want to overwrite it
        if os.path.exists(file_path):
            overwrite = QtWidgets.QMessageBox.question(
                self,
                'Overwrite File?',
                f'File {file_path} already exists. Overwrite?',
                QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.No
            )
            if overwrite == QtWidgets.QMessageBox.No:
                return

        if file_path:
            save_shading_engine_as_json(shading_engine, file_path)
            self.show_message(f'Saved {shading_engine} as {file_path}')

    @QtCore.Slot()
    def import_preset(self):
        if not self.template_dir or not QtCore.QFileInfo(self.template_dir).exists():
            self.pick_template_directory()
        if not self.template_dir:
            return

        if not self.template_combobox.currentText():
            return

        file_path = f'{self.template_dir}/{self.template_combobox.currentText()}'
        if not QtCore.QFileInfo(file_path).exists():
            raise RuntimeError(f'{file_path} was not found.')

        name = self.name_edit.text()
        name = name if name else DEFAULT_PREFIX

        if file_path:
            loads_shading_engine_as_json(file_path, name=name)

        # Apply the textures
        if self.base_path.text() and os.path.isfile(self.base_path.text()):
            # Find the base color file node
            node = [f for f in cmds.ls(type='file') if f == f'{name}_color_file']
            if node:
                cmds.setAttr(f'{node[0]}.fileTextureName', self.base_path.text(), type='string')
                cmds.setAttr(f'{node[0]}.uvTilingMode', 3)

        if self.opacity_path.text() and os.path.isfile(self.opacity_path.text()):
            # Find the opacity file node
            node = [f for f in cmds.ls(type='file') if f == f'{name}_opacity_file']
            if node:
                cmds.setAttr(f'{node[0]}.fileTextureName', self.opacity_path.text(), type='string')
                cmds.setAttr(f'{node[0]}.uvTilingMode', 3)

        if self.line_path.text() and os.path.isfile(self.line_path.text()):
            # Find the line file node
            node = [f for f in cmds.ls(type='file') if f == f'{name}_lines_file']
            if node:
                cmds.setAttr(f'{node[0]}.fileTextureName', self.line_path.text(), type='string')
                cmds.setAttr(f'{node[0]}.uvTilingMode', 3)

        if self.mask_path.text() and os.path.isfile(self.mask_path.text()):
            # Find the mask file node
            node = [f for f in cmds.ls(type='file') if f == f'{name}_linestrength_file']
            if node:
                cmds.setAttr(f'{node[0]}.fileTextureName', self.mask_path.text(), type='string')
                cmds.setAttr(f'{node[0]}.uvTilingMode', 3)

        if self.displacement_path.text() and os.path.isfile(self.displacement_path.text()):
            # Find the displacement file node
            node = [f for f in cmds.ls(type='file') if f == f'{name}_displacement_file']
            if node:
                cmds.setAttr(f'{node[0]}.fileTextureName', self.displacement_path.text(), type='string')
                cmds.setAttr(f'{node[0]}.uvTilingMode', 3)

        self.show_message(f'Shader added template was added to the scene!')

    @QtCore.Slot()
    def find_textures(self):
        print('Looking for textures...')

        name = self.name_edit.text()
        name = name if name else DEFAULT_PREFIX

        data = {
            'base': [],
            'opacity': [],
            'line': [],
            'mask': [],
            'displacement': []
        }

        def _files(path):
            for entry in os.scandir(path):
                if entry.is_dir():
                    print(f'Parsing {path}')
                    yield from _files(entry.path.replace('\\', '/'))

                if entry.is_file():
                    if any(entry.name.lower().endswith(f) for f in IMAGE_EXTENSIONS):
                        yield entry.path.replace('\\', '/')
                    else:
                        print(f'Skipping {entry.path}, not a valid texture file')

        for d in get_source_images_dir():
            for e in _files(d):
                for key, pattern in TEXTURE_FILE_PATTERNS.items():
                    if re.match(pattern.format(name=name), e.lower(), re.IGNORECASE):
                        data[key].append(e.replace('\\', '/'))

        for k in data:
            if not data[k]:
                continue
            v = sorted(data[k])[-1]
            print(f'Found texture: {v}')
            getattr(self, f'{k}_path').setText(v)


def run():
    global instance
    try:
        instance.close()
        instance.deleteLater()
    except:

        pass
    instance = PresetsWidget(parent=mayabase.get_maya_window())
    instance.show()


if __name__ == '__main__':
    run()
