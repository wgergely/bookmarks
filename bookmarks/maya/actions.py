# -*- coding: utf-8 -*-
"""This module contains the available Maya actions.

"""
import os
import sys
import uuid
import time
import re

import shiboken2
from PySide2 import QtWidgets, QtCore

import maya.OpenMayaUI as OpenMayaUI  # pylint: disable=E0401
import maya.app.general.mayaMixin as mayaMixin
import maya.cmds as cmds  # pylint: disable=E0401

from .. import log
from .. import common
from .. import ui
from .. import actions

from .. external import rv
from .. import __path__ as package_path

from . import base
from . import main


@common.error
@common.debug
def set_workspace(*args, **kwargs):
    # Get preference
    v = common.settings.value(
        common.SettingsSection,
        common.WorkspaceSyncKey
    )
    # Set default value if none has been set previously
    v = QtCore.Qt.Unchecked if v is None else v

    # If workspace syncing has been explicitly disabled return
    if v == QtCore.Qt.Checked:
        return

    # Nothing to do if there's no active index set
    index = common.active_index(common.AssetTab)
    if not index.isValid():
        return

    file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))

    # Do nothing if the current workspace is already the active item
    current = cmds.workspace(q=True, sn=True)
    current = QtCore.QFileInfo(current)
    if file_info.filePath().lower() == current.filePath().lower():
        return

    # Set the current workspace
    path = os.path.normpath(file_info.filePath())
    cmds.workspace(path, openWorkspace=True)


@common.error
@common.debug
def apply_settings(*args, **kwargs):
    """Applies asset and bookmark item properties to the current scene.

    """
    props = base.MayaProperties()
    mbox = ui.MessageBox(
        'Are you sure you want to apply the following settings?',
        props.get_info(),
        buttons=[ui.YesButton, ui.CancelButton],
    )
    res = mbox.exec_()
    if res == QtWidgets.QDialog.Rejected:
        return

    base.patch_workspace_file_rules()
    base.set_framerate(props.framerate)
    base.set_startframe(props.startframe)
    base.set_endframe(props.endframe)
    base.apply_default_render_values()
    base.set_render_resolution(props.width, props.height)


@common.error
@common.debug
def save_scene(increment=False, type='mayaAscii'):
    """Save the current scene using our file saver.

    Returns:
        str: Path to the saved scene file.

    """
    if type == 'mayaAscii':
        ext = 'ma'
    else:
        ext = 'mb'

    if not increment:
        _file = None
    else:
        _file = cmds.file(query=True, expandName=True) if increment else None
        if _file and not _file.lower().endswith('.' + ext):
            _file = _file + '.' + ext

    widget = actions.show_add_file(
        extension=ext, file=_file, create_file=False, increment=increment)
    if not widget:
        return

    result = widget.exec_()

    if result == QtWidgets.QDialog.Rejected:
        return
    if not result:
        raise RuntimeError('Invalid destination path')

    file_info = QtCore.QFileInfo(result)

    # Let's make sure destination folder exists
    _dir = file_info.dir()
    if not _dir.exists():
        if not _dir.mkpath('.'):
            raise OSError(f'Could not create {_dir.path()}')

    # Check to make sure we're not overwriting anything
    if file_info.exists():
        raise RuntimeError(
            f'Unable to save file because {result} already exists.')

    cmds.file(rename=result)
    cmds.file(force=True, save=True, type=type)

    common.signals.fileAdded.emit(result)
    return result


@QtCore.Slot(str)
@QtCore.Slot(dict)
@QtCore.Slot(bool)
@common.error
@common.debug
def export_set_to_ass(set_name, set_members, frame=True):
    """Main method to initiate an Arnold ASS export using Bookmarks's
    saver to generate the filename.

    Args:
        key (str):   The name of the object set to export.
        value (tuple): A list of object names inside the set.

    """
    # Ensure the plugin is loaded
    try:
        if not cmds.pluginInfo('mtoa.mll', loaded=True, q=True):
            cmds.loadPlugin('mtoa.mll', quiet=True)
    except Exception:
        raise

    # We want to handle the exact name of the file
    # We'll remove the namespace, strip underscores
    set_name = set_name.replace(':', '_').strip('_')
    set_name = re.sub(r'[0-9]*$', '', set_name)
    layer = cmds.editRenderLayerGlobals(
        query=True, currentRenderLayer=True)
    ext = 'ass'

    export_dir = base.DEFAULT_CACHE_DIR.format(
        export_dir=base.get_export_dir(),
        ext=base.get_export_subdir(ext)
    )

    file_path = base.CACHE_LAYER_PATH.format(
        workspace=cmds.workspace(q=True, fn=True),
        export_dir=export_dir,
        set=set_name,
        layer=layer,
        ext=ext
    )

    current_frame = cmds.currentTime(query=True)
    if frame:
        start = int(cmds.currentTime(query=True))
        end = int(cmds.currentTime(query=True))
    else:
        start = int(cmds.playbackOptions(query=True, animationStartTime=True))
        end = int(cmds.playbackOptions(query=True, animationEndTime=True))

    widget = actions.show_add_file(
        extension=ext,
        file=file_path,
        create_file=False,
        increment=True
    )

    file_path = widget.exec_()
    if file_path == QtWidgets.QDialog.Rejected:
        return
    if not file_path:
        raise RuntimeError('Invalid destination path')

    file_info = QtCore.QFileInfo(file_path)

    # Let's make sure destination folder exists
    _dir = file_info.dir()
    if not _dir.exists():
        if not _dir.mkpath('.'):
            s = 'Could not create {}'.format(_dir.path())
            raise OSError(s)

    sel = cmds.ls(selection=True)
    try:
        import arnold  # pylint: disable=E0401

        # Let's get the first renderable camera
        cams = cmds.ls(cameras=True)
        cam = None
        for cam in cams:
            if cmds.getAttr('{}.renderable'.format(cam)):
                break

        cmds.select(clear=True)
        cmds.select(set_members, replace=True)

        ext = file_path.split('.')[-1]
        _file_path = str(file_path)

        for fr in range(start, end + 1):
            if not frame:
                # Create a mock version, if does not exist
                open(file_path, 'a').close()
                cmds.currentTime(fr, edit=True)
                _file_path = file_path.replace('.{}'.format(ext), '')
                _file_path += '_'
                _file_path += '{}'.format(fr).zfill(base.DefaultPadding)
                _file_path += '.'
                _file_path += ext

            cmds.arnoldExportAss(
                f=_file_path,
                cam=cam,
                s=True,  # selected
                mask=arnold.AI_NODE_CAMERA |
                arnold.AI_NODE_SHAPE |
                arnold.AI_NODE_SHADER |
                arnold.AI_NODE_OVERRIDE |
                arnold.AI_NODE_LIGHT
            )
        cmds.currentTime(current_frame, edit=True)

        common.signals.fileAdded.emit(file_path)
        return file_path
    except:
        raise
    finally:
        cmds.select(clear=True)
        cmds.select(sel, replace=True)


@QtCore.Slot(str)
@QtCore.Slot(dict)
@QtCore.Slot(bool)
@common.error
@common.debug
def export_set_to_abc(set_name, set_members, frame=False):
    """Main method to initiate an alembic export using Bookmarks's
    saver to generate the filename.

    Args:
        key (str):   The name of the object set to export.
        value (tuple): A list of object names inside the set.

    """
    # Ensure theAlembic plugin is loaded
    if not cmds.pluginInfo('AbcExport.mll', loaded=True, q=True):
        cmds.loadPlugin('AbcExport.mll', quiet=True)
        cmds.loadPlugin('AbcImport.mll', quiet=True)

    # We want to handle the exact name of the file
    # We'll remove the namespace, strip underscores
    set_name = set_name.replace(':', '_').strip('_')
    set_name = re.sub(r'[0-9]*$', '', set_name)
    ext = 'abc'

    export_dir = base.DEFAULT_CACHE_DIR.format(
        export_dir=base.get_export_dir(),
        ext=base.get_export_subdir(ext)
    )

    file_path = base.CACHE_PATH.format(
        workspace=cmds.workspace(q=True, fn=True),
        export_dir=export_dir,
        set=set_name,
        ext=ext
    )

    # Let's make sure destination folder exists
    file_info = QtCore.QFileInfo(file_path)
    _dir = file_info.dir()
    if not _dir.exists():
        if not _dir.mkpath('.'):
            s = 'Could not create {}'.format(_dir.path())
            raise OSError(s)

    widget = actions.show_add_file(
        extension=ext,
        file=file_path,
        create_file=False,
        increment=True
    )

    file_path = widget.exec_()
    if file_path == QtWidgets.QDialog.Rejected:
        return
    if not file_path:
        raise RuntimeError('Invalid destination path')

    file_info = QtCore.QFileInfo(file_path)

    # Let's make sure destination folder exists
    _dir = file_info.dir()
    if not _dir.exists():
        if not _dir.mkpath('.'):
            s = 'Could not create {}'.format(_dir.path())
            raise OSError(s)

    # Check to make sure we're not overwriting anything...
    if file_info.exists():
        s = 'Unable to save alembic: {} already exists.'.format(file_path)
        raise RuntimeError(s)

    if frame:
        start = cmds.currentTime(query=True)
        end = cmds.currentTime(query=True)
    else:
        start = cmds.playbackOptions(query=True, animationStartTime=True)
        end = cmds.playbackOptions(query=True, animationEndTime=True)

    state = cmds.ogs(pause=True, query=True)
    if not state:
        cmds.ogs(pause=True)

    try:
        export_alembic(
            file_info.filePath(),
            set_members,
            start,
            end
        )
        common.signals.fileAdded.emit(file_path)
        return file_path
    except:
        raise
    finally:
        if not state:
            cmds.ogs(pause=True)


@QtCore.Slot(str)
@QtCore.Slot(dict)
@QtCore.Slot(bool)
@common.error
@common.debug
def export_set_to_obj(set_name, set_members, frame=False):
    """Main method to initiate an alembic export using Bookmarks's
    saver to generate the filename.

    Args:
        key (str):   The name of the object set to export.
        value (tuple): A list of object names inside the set.

    """
    # Ensure the plugin is loaded
    try:
        if not cmds.pluginInfo('objExport.mll', loaded=True, q=True):
            cmds.loadPlugin('objExport.mll', quiet=True)
    except:
        s = 'Could not load the `objExport` plugin'
        raise RuntimeError(s)

    # We want to handle the exact name of the file
    # We'll remove the namespace, strip underscores
    set_name = set_name.replace(':', '_').strip('_')
    set_name = re.sub(r'[0-9]*$', '', set_name)
    ext = 'obj'

    export_dir = base.DEFAULT_CACHE_DIR.format(
        export_dir=base.get_export_dir(),
        ext=base.get_export_subdir(ext)
    )

    file_path = base.CACHE_PATH.format(
        workspace=cmds.workspace(q=True, fn=True),
        export_dir=export_dir,
        set=set_name,
        ext=ext
    )

    current_frame = cmds.currentTime(query=True)
    if frame:
        start = int(cmds.currentTime(query=True))
        end = int(cmds.currentTime(query=True))
    else:
        start = int(cmds.playbackOptions(query=True, animationStartTime=True))
        end = int(cmds.playbackOptions(query=True, animationEndTime=True))

    # Let's make sure destination folder exists
    file_info = QtCore.QFileInfo(file_path)
    _dir = file_info.dir()
    if not _dir.exists():
        if not _dir.mkpath('.'):
            s = 'Could not create {}'.format(_dir.path())
            raise OSError(s)

    widget = actions.show_add_file(
        extension=ext, file=file_path, create_file=False, increment=True)
    file_path = widget.exec_()
    if file_path == QtWidgets.QDialog.Rejected:
        return
    if not file_path:
        raise RuntimeError('Invalid destination path')

    file_info = QtCore.QFileInfo(file_path)

    # Let's make sure destination folder exists
    _dir = file_info.dir()
    if not _dir.exists():
        if not _dir.mkpath('.'):
            s = 'Could not create {}'.format(_dir.path())
            raise OSError(s)

    # Last-ditch check to make sure we're not overwriting anything...
    if file_info.exists():
        s = 'Unable to save set: {} already exists.'.format(file_path)
        raise RuntimeError(s)

    sel = cmds.ls(selection=True)
    file_path = file_info.filePath()
    ext = file_path.split('.')[-1]
    _file_path = str(file_path)

    try:
        cmds.select(clear=True)
        cmds.select(set_members, replace=True)

        for fr in range(start, end + 1):
            if not frame:
                # Create a mock version, if does not exist
                open(file_path, 'a').close()
                cmds.currentTime(fr, edit=True)
                _file_path = file_path.replace('.{}'.format(ext), '')
                _file_path += '_'
                _file_path += '{}'.format(fr).zfill(base.DefaultPadding)
                _file_path += '.'
                _file_path += ext

            cmds.file(
                _file_path,
                preserveReferences=True,
                type='OBJexport',
                exportSelected=True,
                options='groups=1;ptgroups=1;materials=1;smoothing=1; normals=1'
            )
        cmds.currentTime(current_frame, edit=True)

        common.signals.fileAdded.emit(file_path)
        return file_path
    except:
        raise
    finally:
        cmds.select(clear=True)
        cmds.select(sel, replace=True)


@QtCore.Slot()
@common.error
@common.debug
def execute(index):
    file_path = common.get_sequence_endpath(
        index.data(QtCore.Qt.StatusTipRole))
    file_info = QtCore.QFileInfo(file_path)

    # Open alembic, and maya files:
    if file_info.suffix().lower() in ('ma', 'mb', 'abc'):
        open_scene(file_info.filePath())
        return

    # Otherwise execute the item as normal
    actions.execute(index)


@common.error
@common.debug
def save_warning(*args):
    """Shows the user a warning when a file is saved outside the current
    workspace.

    """
    # Get preference
    v = common.settings.value(
        common.SettingsSection,
        common.SaveWarningsKey
    )
    # Set default value if none has been set previously
    v = QtCore.Qt.Unchecked if v is None else v

    # If save warning has been explicitly disabled return
    if v == QtCore.Qt.Checked:
        return

    workspace_info = QtCore.QFileInfo(
        cmds.workspace(q=True, expandName=True))
    scene_file = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

    if scene_file.baseName().lower() == 'untitled':
        return

    if workspace_info.path().lower() not in scene_file.filePath().lower():
        ui.MessageBox(
            'Looks like you are saving "{}" outside the current project\nThe current project is "{}"'.format(
                scene_file.fileName(),
                workspace_info.path()),
            'If you didn\'t expect this message, is it possible the project was changed by {} from another instance of Maya?'.format(
                common.product)
        ).open()


@common.error
@common.debug
def unmark_active(*args):
    """Callback responsible for keeping the active-file in the list updated."""
    common.source_model(common.FileTab).unset_active()


@common.error
@common.debug
def update_active_item(*args):
    """Callback responsible for keeping the active-file in the list updated.

    """
    f = common.widget(common.FileTab)
    model = f.model().sourceModel()
    active_index = model.active_index()

    if active_index.isValid():
        model.unset_active()

    scene = cmds.file(query=True, expandName=True)

    p = model.source_path()
    k = model.task()
    t1 = model.data_type()
    t2 = common.FileItem if t1 == common.SequenceItem else common.SequenceItem

    for t in (t1, t2):
        if t == common.SequenceItem:
            scene = common.proxy_path(scene)
        ref = common.get_data_ref(p, k, t)
        for idx in ref().keys():
            if not ref():
                continue
            if t == common.FileItem:
                s = ref()[idx][QtCore.Qt.StatusTipRole]
            else:
                s = common.proxy_path(ref()[idx][QtCore.Qt.StatusTipRole])

            if scene == s and ref():
                # Set flag to be active
                ref()[idx][common.FlagsRole] = ref()[
                    idx][common.FlagsRole] | common.MarkedAsActive

                if t == t1:
                    # Select and scroll to item
                    source_index = model.index(idx, 0)
                    index = f.model().mapFromSource(source_index)
                    f.selectionModel().setCurrentIndex(
                        index,
                        QtCore.QItemSelectionModel.ClearAndSelect
                    )
                    f.scrollTo(index)


@common.error
@common.debug
def open_scene(path):
    """Opens the given path using ``cmds.file``.

    Returns:
        str: The name of the input scene if the load was successfull.

    Raises:
        RuntimeError: When and invalid scene file is passed.

    """
    p = common.get_sequence_endpath(path)
    file_info = QtCore.QFileInfo(p)

    _s = file_info.suffix().lower()
    if _s not in ('ma', 'mb', 'abc'):
        s = '{} is not a valid scene.'.format(p)
        raise RuntimeError(s)

    if _s == 'abc':
        if not cmds.pluginInfo('AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcImport.mll", quiet=True)
        if not cmds.pluginInfo("AbcExport.mll", loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)

    if not file_info.exists():
        s = '{} does not exist.'.format(p)
        raise RuntimeError(s)

    if base.is_scene_modified() == QtWidgets.QMessageBox.Cancel:
        return
    cmds.file(file_info.filePath(), open=True, force=True)
    s = 'Scene opened {}\n'.format(file_info.filePath())
    log.success(s)
    return file_info.filePath()


@common.error
@common.debug
def import_scene(path, reference=False):
    """Imports a Maya or alembic file to the current Maya scene.

    Args:
        path (str): Path to a Maya scene file.
        reference (bool): When `true` the import will be a reference.

    """
    p = common.get_sequence_endpath(path)
    file_info = QtCore.QFileInfo(p)
    _s = file_info.suffix().lower()
    if _s not in ('ma', 'mb', 'abc'):
        s = '{} is not a valid scene.'.format(p)
        raise RuntimeError(s)

    # Load the alembic plugin
    if _s == 'abc':
        if not cmds.pluginInfo('AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcImport.mll", quiet=True)
        if not cmds.pluginInfo("AbcExport.mll", loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)

    if not file_info.exists():
        s = '{} does not exist.'.format(p)
        raise RuntimeError(s)

    if cmds.file(q=True, sn=True).lower() == file_info.filePath().lower() and reference:
        raise RuntimeError('Can\'t reference itself.')

    match = common.get_sequence(file_info.fileName())
    basename = match.group(1) if match else file_info.baseName()
    basename = re.sub(r'_v$', '', basename, flags=re.IGNORECASE)

    alphabet = base._get_available_suffixes(basename)
    if not alphabet:  # no more suffixes to assign
        return None

    w = QtWidgets.QInputDialog()
    w.setWindowTitle('Assign suffix')
    w.setLabelText(base.SUFFIX_LABEL)
    w.setComboBoxItems(alphabet)
    w.setCancelButtonText('Cancel')
    w.setOkButtonText('Import')
    res = w.exec_()
    if not res:
        return None
    suffix = w.textValue()

    id = '{}'.format(uuid.uuid1()).replace('-', '_')
    # This should always be a unique name in the maya scene
    ns = '{}_{}'.format(basename, suffix)
    rfn = '{}_RN_{}'.format(ns, id)

    if reference:
        cmds.file(
            file_info.filePath(),
            reference=True,
            ns=ns,
            rfn=rfn,
        )
        base._add_suffix_attribute(rfn, suffix, reference=reference)

        # The reference node is locked by default
        cmds.lockNode(rfn, lock=False)
        rfn = cmds.rename(rfn, '{}_RN'.format(ns))
        cmds.lockNode(rfn, lock=True)
    else:
        cmds.file(
            file_info.filePath(),
            i=True,
            ns=ns
        )
        base._add_suffix_attribute(ns, suffix, reference=reference)

    s = '{} was imported.'.format(file_info.filePath())
    log.success(s)
    return file_info.filePath()


def export_alembic(destination_path, outliner_set, startframe, endframe, step=1.0):
    """Main alembic export definition.

    Only shapes, normals and uvs are exported by this implementation. The list
    of shapes contained in the `outliner_set` will be rebuilt in the root of
    the scene to avoid parenting issues.

    Args:
        destination_path (str): Path to the output file.
        outliner_set (tuple): A list of transforms contained in a geometry set.

    """
    # ======================================================
    # ERROR CHECKING
    # Check destination before proceeding
    common.check_type(outliner_set, (tuple, list))

    destination_info = QtCore.QFileInfo(destination_path)
    destination_dir = destination_info.dir()
    _destination_dir_info = QtCore.QFileInfo(destination_dir.path())

    if not _destination_dir_info.exists():
        s = 'Unable to save the alembic file, {} does not exists.'.format(
            _destination_dir_info.filePath())
        ui.ErrorBox(
            'Alembic export failed.',
            s
        ).open()
        log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    if not _destination_dir_info.isReadable():
        s = 'Unable to save the alembic file, {} is not readable.'.format(
            _destination_dir_info.filePath())
        ui.ErrorBox(
            'Alembic export failed.',
            s
        ).open()
        log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    if not _destination_dir_info.isWritable():
        s = 'Unable to save the alembic file, {} is not writable.'.format(
            _destination_dir_info.filePath())
        ui.ErrorBox(
            'Alembic export failed.',
            s
        ).open()
        log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    # ======================================================

    destination_path = QtCore.QFileInfo(destination_path).filePath()

    # If the extension is missing, we'll add it here
    if not destination_path.lower().endswith('.abc'):
        destination_path = destination_path + '.abc'

    def is_intermediate(s): return cmds.getAttr(
        '{}.intermediateObject'.format(s))

    # We'll need to use the DecomposeMatrix Nodes, let's check if the plugin
    # is loaded and ready to use
    if not cmds.pluginInfo('matrixNodes.mll', loaded=True, q=True):
        cmds.loadPlugin('matrixNodes.mll', quiet=True)

    world_shapes = []
    valid_shapes = []

    # First, we will collect the available shapes from the given set
    for item in outliner_set:
        shapes = cmds.listRelatives(item, fullPath=True)
        for shape in shapes:
            if is_intermediate(shape):
                continue

            basename = shape.split('|').pop()
            try:
                # AbcExport will fail if a transform or a shape node's name is not unique
                # This was suggested on a forum - listing the relatives for a
                # an object without a unique name should raise a ValueError
                cmds.listRelatives(basename)
            except ValueError as err:
                s = '"{shape}" does not have a unique name. This is not usually allowed for alembic exports and might cause the export to fail.\nError: {err}'.format(
                    shape=shape, err=err)
                log.error(s)

            # Camera's don't have mesh nodes but we still want to export them!
            if cmds.nodeType(shape) != 'camera':
                if not cmds.attributeQuery('outMesh', node=shape, exists=True):
                    continue
            valid_shapes.append(shape)

    if not valid_shapes:
        raise RuntimeError(
            '# No valid shapes found in "{}" to export! Aborting...'.format(outliner_set))

    cmds.select(clear=True)

    # Creating a temporary namespace to avoid name-clashes later when we duplicate
    # the meshes. We will delete this namespace, and it's contents after the export
    if cmds.namespace(exists='mayaExport'):
        cmds.namespace(removeNamespace='mayaExport',
                       deleteNamespaceContent=True)
    ns = cmds.namespace(add='mayaExport')

    world_transforms = []

    try:
        # For meshes, we will create an empty mesh node and connect the outMesh and
        # UV attributes from our source.
        # We will also apply the source mesh's transform matrix to the newly created mesh
        for shape in valid_shapes:
            basename = shape.split('|').pop()
            if cmds.nodeType(shape) != 'camera':
                # Create new empty shape node
                world_shape = cmds.createNode(
                    'mesh', name='{}:{}'.format(ns, basename))

                # outMesh -> inMesh
                cmds.connectAttr('{}.outMesh'.format(
                    shape), '{}.inMesh'.format(world_shape), force=True)
                # uvSet -> uvSet
                cmds.connectAttr('{}.uvSet'.format(shape),
                                 '{}.uvSet'.format(world_shape), force=True)

                # worldMatrix -> transform
                decompose_matrix = cmds.createNode(
                    'decomposeMatrix', name='{}:decomposeMatrix#'.format(ns))
                cmds.connectAttr(
                    '{}.worldMatrix[0]'.format(shape), '{}.inputMatrix'.format(decompose_matrix), force=True)
                #
                transform = cmds.listRelatives(
                    world_shape, fullPath=True, type='transform', parent=True)[0]
                world_transforms.append(transform)
                #
                cmds.connectAttr(
                    '{}.outputTranslate'.format(decompose_matrix), '{}.translate'.format(transform), force=True)
                cmds.connectAttr(
                    '{}.outputRotate'.format(decompose_matrix), '{}.rotate'.format(transform), force=True)
                cmds.connectAttr(
                    '{}.outputScale'.format(decompose_matrix), '{}.scale'.format(transform), force=True)
            else:
                world_shape = shape
                world_transforms.append(cmds.listRelatives(
                    world_shape, fullPath=True, type='transform', parent=True)[0])
            world_shapes.append(world_shape)

        # Our custom progress callback
        perframecallback = '"from {}.maya import base;base.report_export_progress({}, #FRAME#, {}, {})"'.format(
            common.product, startframe, endframe, time.time())

        # Let's build the export command
        jobArg = '{f} {fr} {s} {uv} {ws} {wv} {wuvs} {sn} {rt} {df} {pfc} {ro}'.format(
            f='-file "{}"'.format(destination_path),
            fr='-framerange {} {}'.format(startframe, endframe),
            s='-step {}'.format(step),
            uv='-uvWrite',
            ws='-worldSpace',
            wv='-writeVisibility',
            # eu='-eulerFilter',
            wuvs='-writeuvsets',
            sn='-stripNamespaces',
            rt='-root {}'.format(' -root '.join(world_transforms)),
            df='-dataFormat {}'.format('ogawa'),
            pfc='-pythonperframecallback {}'.format(perframecallback),
            ro='-renderableOnly'
        )
        s = '# jobArg: `{}`'.format(jobArg)

        cmds.AbcExport(jobArg=jobArg)
        log.success(s)

    except Exception as err:
        ui.ErrorBox(
            'An error occured exporting Alembic cache',
            '{}'.format(err)
        ).open()
        log.error('Could not open the plugin window.')
        raise

    finally:
        # Finally, we will delete the previously created namespace and the object
        # contained inside. I wrapped the call into an evalDeferred to let maya
        # recover after the export and delete the objects more safely.

        def teardown():
            cmds.namespace(
                removeNamespace='mayaExport', deleteNamespaceContent=True)
        cmds.evalDeferred(teardown)


@common.error
@common.debug
def capture_viewport(size=1.0):
    """Saves a versioned capture to the ``capture_folder`` defined in the preferences.

    The script will output to the an image sequence and if FFmpeg is present converts it to a h264 movie file.
    It will also try to create a ``latest`` folder with a copy of the last exported image sequence.

    Usage:

        .. code-block:: python

        MayaWidget.capture_viewport()


    """
    ext = 'png'
    scene_info = QtCore.QFileInfo(cmds.file(q=True, expandName=True))

    # CAPTURE_DESTINATION
    capture_folder, workspace, base_destination_path = base.capture_viewport_destination()

    _dir = QtCore.QFileInfo(base_destination_path).dir()
    if not _dir.exists():
        _dir.mkpath('.')

    # Use our custom ModelPanel picker to select the viewport we want to
    # capture
    from . import main

    picker = main.PanelPicker()
    picker.exec_()
    panel = picker.panel

    # Cancel if no selection was made
    if not panel:
        return

    # Make sure we have selected a valid panel as not all panels are modelEditors
    if panel is None or cmds.objectTypeUI(panel) != 'modelEditor':
        s = 'Activate a viewport before starting a capture.'
        raise RuntimeError(s)

    camera = cmds.modelPanel(panel, query=True, camera=True)

    # The the panel settings using mCapture.py and update it with our
    # custom common. See `base.CaptureOptions` for the hard-coded
    # defaults we're using here
    from . import mCapture
    options = mCapture.parse_view(panel)
    options['viewport_options'].update(base.CaptureOptions)

    # Hide existing panels
    current_state = {}
    for panel in cmds.getPanel(type='modelPanel'):
        if not cmds.modelPanel(panel, exists=True):
            continue

        try:
            ptr = OpenMayaUI.MQtUtil.findControl(panel)
            if not ptr:
                continue
            panel_widget = shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)
            current_state[panel] = panel_widget.isVisible()
            if panel_widget:
                panel_widget.hide()
        except:
            log.error('# An error occured hiding {}'.format(panel))

    width = int(cmds.getAttr('defaultResolution.width') * size)
    height = int(cmds.getAttr('defaultResolution.height') * size)

    try:
        mCapture.capture(
            camera=camera,
            width=width,
            height=height,
            display_options=base.DisplayOptions,
            camera_options=base.CameraOptions,
            viewport2_options=options['viewport2_options'],
            viewport_options=options['viewport_options'],
            format='image',
            compression=ext,
            filename=base_destination_path,
            overwrite=True,
            viewer=False
        )
        log.success('Capture saved to {}'.format(_dir.path()))
    except:
        raise
    finally:
        cmds.ogs(reset=True)

        # Show hidden panels
        for panel in cmds.getPanel(type='modelPanel'):
            if not cmds.modelPanel(panel, exists=True):
                continue
            try:
                ptr = OpenMayaUI.MQtUtil.findControl(panel)
                if not ptr:
                    continue
                panel_widget = shiboken2.wrapInstance(
                    int(ptr), QtWidgets.QWidget)
                if panel_widget:
                    if panel in current_state:
                        panel_widget.setVisible(current_state[panel])
                    else:
                        panel_widget.setVisible(True)
            except:
                print(f'# Could not restore {panel} after capture')

    # Publish output
    publish_capture(workspace, capture_folder, scene_info, ext)

    # Push and reveal output
    path = base.CAPTURE_FILE.format(
        workspace=workspace,
        capture_folder=capture_folder,
        scene=scene_info.baseName(),
        frame='{}'.format(int(cmds.playbackOptions(q=True, minTime=True))).zfill(
            base.DefaultPadding),
        ext=ext
    )
    push_capture(path)
    reveal_capture(path)


def push_capture(path):
    # Get preference
    v = common.settings.value(
        common.SettingsSection,
        common.PushCaptureToRVKey
    )
    # Set default value if none has been set previously
    v = QtCore.Qt.Unchecked if v is None else v

    # If save warning has been explicitly disabled return
    if v == QtCore.Qt.Checked:
        return

    rv.push(path)


def reveal_capture(path):
    # Get preference
    v = common.settings.value(
        common.SettingsSection,
        common.RevealCaptureKey
    )
    # Set default value if none has been set previously
    v = QtCore.Qt.Unchecked if v is None else v

    # If save warning has been explicitly disabled return
    if v == QtCore.Qt.Checked:
        return

    actions.reveal(path)


def publish_capture(workspace, capture_folder, scene_info, ext):
    """Publish the latest capture sequence as a version agnostic copy.

    """
    # Get preference
    v = common.settings.value(
        common.SettingsSection,
        common.PublishCaptureKey
    )
    # Set default value if none has been set previously
    v = QtCore.Qt.Unchecked if v is None else v

    # If save warning has been explicitly disabled return
    if v == QtCore.Qt.Checked:
        return

    asset = workspace.split('/').pop()
    start = int(cmds.playbackOptions(q=True, minTime=True))
    end = int(cmds.playbackOptions(q=True, maxTime=True))
    duration = (end - start) + 1

    publish_folder = base.CAPTURE_PUBLISH_DIR.format(
        workspace=workspace,
        capture_folder=capture_folder,
        asset=asset,
    )
    _dir = QtCore.QDir(publish_folder)
    if not _dir.exists():
        if not _dir.mkpath('.'):
            s = 'Could not create {}.'.format(publish_folder)
            raise OSError(s)

    if not QtCore.QFileInfo(publish_folder).isWritable():
        s = '{} is not writable.'.format(publish_folder)
        raise OSError(s)

    for entry in os.scandir(publish_folder):
        os.remove(entry.path)

    idx = 0
    for n in range(int(duration)):
        frame = str(n + int(start)).zfill(base.DefaultPadding)
        source = base.CAPTURE_FILE.format(
            workspace=workspace,
            capture_folder=capture_folder,
            scene=scene_info.baseName(),
            frame=frame,
            ext=ext
        )
        dest = base.AGNOSTIC_CAPTURE_FILE.format(
            workspace=workspace,
            capture_folder=capture_folder,
            asset=asset,
            frame=frame,
            ext=ext
        )
        # Check if the first file exists
        if idx == 0 and not QtCore.QFileInfo(source).exists():
            raise RuntimeError('Could not find {}'.format(source))

        QtCore.QFile.copy(source, dest)
        idx += 1


def remove_maya_widget():
    if isinstance(common.maya_widget, main.MayaWidget):
        common.maya_widget.remove_context_callbacks()
        common.maya_widget.close()
        common.maya_widget.deleteLater()
    common.maya_widget = None


def remove_maya_button():
    if isinstance(common.maya_button_widget, main.MayaButtonWidget):
        common.maya_button_widget.close()
        common.maya_button_widget.deleteLater()
    common.maya_button_widget = None


def remove_workspace_controls():
    for k in list(mayaMixin.mixinWorkspaceControls):
        if common.product in k:
            del mayaMixin.mixinWorkspaceControls[k]

    for widget in QtWidgets.QApplication.instance().allWidgets():
        try:
            name = widget.objectName()
        except:
            continue

        if re.match(f'{common.product}.*WorkspaceControl', name):
            remove_workspace_control(widget.objectName())


def remove_workspace_control(workspace_control):
    if cmds.workspaceControl(workspace_control, q=True, exists=True):
        cmds.deleteUI(workspace_control)
        if cmds.workspaceControlState(workspace_control, ex=True):
            cmds.workspaceControlState(workspace_control, remove=True)
