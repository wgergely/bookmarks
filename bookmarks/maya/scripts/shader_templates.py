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
from PySide2 import QtWidgets

NUMERIC_TYPES = ['double', 'float', 'long', 'short', 'byte', 'int']

# The "templates" directory relative to this file
PRESET_DIR = os.path.normpath(f'{os.path.dirname(__file__)}/templates')

ShadingEnginePresetsWidget_widget = None


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

            if 'main_' not in node_fn.name():
                raise RuntimeError(f'{node_fn.name()}: incorrect name!')
            if 'main_' not in source:
                raise RuntimeError(f'{source}: incorrect name!')

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

    print(f'Saved {shading_engine} as {json_file_path}')


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
            if not cmds.objExists(k.replace('main_', name + '_')):
                print(f'Creating {k}'.replace('main_', name + '_'))
                cmds.createNode(data[k]['type'], name=k.replace('main_', name + '_'))

        for k in data:
            for connection in data[k]['connections']:
                if not connection:
                    continue

                cmds.connectAttr(
                    connection['conn_source'].replace('main_', name + '_'),
                    connection['conn_destination'].replace('main_', name + '_'), force=True
                )

            for attr in data[k]['attrs']:
                cmds.setAttr(attr.replace('main_', name + '_'), data[k]['attrs'][attr])

            if data[k]['type'] == 'aiRampRgb' and 'ramp' in data[k]:
                restore_ramp_state(k.replace('main_', name + '_'), data[k]['ramp'])
    finally:
        cmds.undoInfo(closeChunk=True)


class ShadingEnginePresetsWidget(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(ShadingEnginePresetsWidget, self).__init__(parent)

        self.setWindowTitle('Shading Engine Manager')
        self.setMinimumWidth(300)
        self.setMaximumHeight(200)

        # Main layout
        self.main_layout = QtWidgets.QVBoxLayout()

        # Save group
        self.save_group = QtWidgets.QGroupBox('Save Shading Engine')
        self.save_layout = QtWidgets.QVBoxLayout()

        self.shading_engine_combo = QtWidgets.QComboBox()
        self.shading_engine_combo.addItems(f for f in cmds.ls(type='shadingEngine') if 'initial' not in f)

        self.save_button = QtWidgets.QPushButton('Save Preset')
        self.save_button.clicked.connect(self.save_preset)

        self.save_layout.addWidget(self.shading_engine_combo)
        self.save_layout.addWidget(self.save_button)

        self.save_group.setLayout(self.save_layout)

        # Load group
        self.load_group = QtWidgets.QGroupBox('Load Shading Engine')
        self.load_layout = QtWidgets.QVBoxLayout()

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText('Enter Name, e.g. "body"')

        self.load_button = QtWidgets.QPushButton('Load Preset')
        self.load_button.clicked.connect(self.load_preset)

        self.textures_group = QtWidgets.QGroupBox('Set texture paths')
        self.textures_load_layout = QtWidgets.QVBoxLayout()

        self.find_textures_button = QtWidgets.QPushButton('Find Textures')
        self.find_textures_button.clicked.connect(self.find_textures)
        self.textures_load_layout.addWidget(self.find_textures_button)

        self.base_path = QtWidgets.QLineEdit()
        self.base_path.setPlaceholderText('base color texture path')
        self.pick_base_path = QtWidgets.QPushButton('...')
        self.pick_base_path.clicked.connect(functools.partial(self.pick_texture_path, self.base_path))
        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(self.base_path)
        widget.layout().addWidget(self.pick_base_path)
        self.textures_load_layout.addWidget(widget)

        self.opacity_path = QtWidgets.QLineEdit()
        self.opacity_path.setPlaceholderText('opacity texture path')
        self.pick_opacity_path = QtWidgets.QPushButton('...')
        self.pick_opacity_path.clicked.connect(functools.partial(self.pick_texture_path, self.opacity_path))
        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(self.opacity_path)
        widget.layout().addWidget(self.pick_opacity_path)
        self.textures_load_layout.addWidget(widget)

        self.line_path = QtWidgets.QLineEdit()
        self.line_path.setPlaceholderText('line texture path')
        self.pick_line_path = QtWidgets.QPushButton('...')
        self.pick_line_path.clicked.connect(functools.partial(self.pick_texture_path, self.line_path))
        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(self.line_path)
        widget.layout().addWidget(self.pick_line_path)
        self.textures_load_layout.addWidget(widget)

        self.mask_path = QtWidgets.QLineEdit()
        self.mask_path.setPlaceholderText('mask texture path')
        self.pick_mask_path = QtWidgets.QPushButton('...')
        self.pick_mask_path.clicked.connect(functools.partial(self.pick_texture_path, self.mask_path))
        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(self.mask_path)
        widget.layout().addWidget(self.pick_mask_path)
        self.textures_load_layout.addWidget(widget)

        self.displacement_path = QtWidgets.QLineEdit()
        self.displacement_path.setPlaceholderText('displacement texture path')
        self.pick_displacement_path = QtWidgets.QPushButton('...')
        self.pick_displacement_path.clicked.connect(functools.partial(self.pick_texture_path, self.displacement_path))
        widget = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(self.displacement_path)
        widget.layout().addWidget(self.pick_displacement_path)
        self.textures_load_layout.addWidget(widget)

        self.textures_group.setLayout(self.textures_load_layout)
        self.load_group.setLayout(self.load_layout)

        self.load_layout.addWidget(self.name_edit)
        self.load_layout.addWidget(self.textures_group)

        # Add to main layout
        self.main_layout.addWidget(self.save_group)
        self.main_layout.addWidget(self.load_group)
        self.main_layout.addWidget(self.load_button)

        self.setLayout(self.main_layout)

    def pick_texture_path(self, editor):
        # default to the current maya project's sourceimages folder
        source_images = os.path.join(cmds.workspace(q=True, rd=True), 'sourceimages')
        path = QtWidgets.QFileDialog.getOpenFileName(self, 'Pick Base Color Texture', source_images)[0]
        if path:
            editor.setText(path)

    def save_preset(self):
        shading_engine = self.shading_engine_combo.currentText()
        filename = f'{shading_engine}.json'
        file_path = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Preset', os.path.join(PRESET_DIR, filename), 'JSON Files (*.json)'
        )[0]

        # check if the file path is valid and if it already exists
        # if it does, ask the user if they want to overwrite it
        if os.path.exists(file_path):
            overwrite = QtWidgets.QMessageBox.question(
                self, 'Overwrite File?', f'File {file_path} already exists. Overwrite?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
            )
            if overwrite == QtWidgets.QMessageBox.No:
                return

        if file_path:
            save_shading_engine_as_json(shading_engine, file_path)

    def load_preset(self):
        file_path = QtWidgets.QFileDialog.getOpenFileName(self, 'Load Preset', PRESET_DIR, 'JSON Files (*.json)')[0]

        name = self.name_edit.text()
        name = name if name else 'main'

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

    def find_textures(self):
        print('Looking for textures...')

        name = self.name_edit.text()
        name = name if name else 'main'

        # find textures in the current maya project's sourceimages folder
        source_images = os.path.join(cmds.workspace(q=True, rd=True), 'sourceimages')

        search_patterns = {
            'base': re.compile(fr'.*{name}.*_base.*1001.*', re.IGNORECASE),
            'opacity': re.compile(fr'.*{name}.*_opacity.*1001.*', re.IGNORECASE),
            'line': re.compile(fr'.*{name}.*_lines.*1001.*', re.IGNORECASE),
            'mask': re.compile(fr'.*{name}.*_toon.*1001.*', re.IGNORECASE),
            'displacement': re.compile(fr'.*{name}.*_displacement.*1001.*', re.IGNORECASE)
        }

        data = {
            'base': [],
            'opacity': [],
            'line': [],
            'mask': [],
            'displacement': []
        }

        # recursive entry generator
        valid_extensions = ['jpg', 'jpeg', 'png', 'tif', 'tiff', 'tga', 'bmp', 'exr']

        def _files(path):
            for entry in os.scandir(path):
                if entry.is_dir():
                    for _path in _files(entry.path):
                        yield _path.replace('\\', '/')

                if entry.is_file():
                    if any(entry.name.lower().endswith(f) for f in valid_extensions):
                        yield entry.path.replace('\\', '/')
                    else:
                        print(f'Skipping {entry.path}, not a valid texture file')

        for e in _files(source_images):
            for key, pattern in search_patterns.items():
                if pattern.match(e.lower()):
                    data[key].append(e.replace('\\', '/'))

        for k in data:
            if not data[k]:
                continue
            v = sorted(data[k])[-1]
            print(f'Found texture: {v}')
            getattr(self, f'{k}_path').setText(v)


def run():
    global ShadingEnginePresetsWidget_widget
    if ShadingEnginePresetsWidget_widget:
        try:
            ShadingEnginePresetsWidget_widget.deleteLater()
            ShadingEnginePresetsWidget_widget = None
        except:
            pass
    ShadingEnginePresetsWidget_widget = ShadingEnginePresetsWidget()
    ShadingEnginePresetsWidget_widget.open()


if __name__ == '__main__':
    run()
