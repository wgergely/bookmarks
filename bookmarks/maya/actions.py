# -*- coding: utf-8 -*-
"""This module contains the available Maya actions.

"""
import sys
import uuid
import time
import os
import re

import shiboken2
from PySide2 import QtWidgets, QtGui, QtCore

import maya.OpenMayaUI as OpenMayaUI  # pylint: disable=E0401
import maya.cmds as cmds  # pylint: disable=E0401

from .. import log
from .. import rv
from .. import common
from .. import ui
from .. import settings
from .. import main
from .. import actions
from .. import datacache
from . import base as mbase

from .. import __path__ as package_path


@common.error
@common.debug
def set_workspace(*args, **kwargs):
    # Get preference
    v = settings.instance().value(
        settings.SettingsSection,
        settings.WorkspaceSyncKey
    )
    # Set default value if none has been set previously
    v = QtCore.Qt.Unchecked if v is None else v

    # If workspace syncing has been explicitly disabled return
    if v == QtCore.Qt.Checked:
        return

    widget = main.instance().stackedwidget.widget(common.AssetTab)
    model = widget.model().sourceModel()

    # Nothing to do if there's no active index set
    index = model.active_index()
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
    props = mbase.MayaProperties()
    mbox = ui.MessageBox(
        u'Are you sure you want to apply the following settings?',
        props.get_info(),
        buttons=[ui.YesButton, ui.CancelButton],
    )
    res = mbox.exec_()
    if res == QtWidgets.QDialog.Rejected:
        return

    mbase.set_framerate(props.framerate)
    mbase.set_startframe(props.startframe)
    mbase.set_endframe(props.endframe)
    mbase.apply_default_render_values()
    mbase.set_render_resolution(props.width, props.height)


@common.error
@common.debug
def save_scene(increment=False, type='mayaAscii'):
    """Save the current scene using our file saver.

    Returns:
        unicode: Path to the saved scene file.

    """
    if type == 'mayaAscii':
        ext = u'ma'
    else:
        ext = u'mb'

    if not increment:
        _file = None
    else:
        _file = cmds.file(query=True, expandName=True) if increment else None
        if _file and not _file.lower().endswith(u'.' + ext):
            _file = _file + u'.' + ext

    widget = actions.show_add_file(
        extension=ext, file=_file, create_file=False, increment=increment)
    file_path = widget.exec_()
    if file_path == QtWidgets.QDialog.Rejected:
        return
    if not file_path:
        raise RuntimeError(u'Invalid destination path')

    file_info = QtCore.QFileInfo(file_path)

    # Let's make sure destination folder exists
    _dir = file_info.dir()
    if not _dir.exists():
        if not _dir.mkpath(u'.'):
            s = u'Could not create {}'.format(_dir.path())
            raise OSError(s)

    # Check to make sure we're not overwriting anything
    if file_info.exists():
        s = u'Unable to save file because {} already exists.'.format(file_path)
        raise RuntimeError(s)

    cmds.file(rename=file_path)
    cmds.file(force=True, save=True, type=type)

    common.signals.fileAdded.emit(file_path)
    return file_path


@QtCore.Slot(unicode)
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
        if not cmds.pluginInfo(u'mtoa.mll', loaded=True, q=True):
            cmds.loadPlugin(u'mtoa.mll', quiet=True)
    except Exception as e:
        raise

    # We want to handle the exact name of the file
    # We'll remove the namespace, strip underscores
    set_name = set_name.replace(u':', u'_').strip(u'_')
    set_name = re.sub(ur'[0-9]*$', u'', set_name)
    ext = u'ass'

    exportdir = mbase.find_project_folder(u'ass export')
    exportdir = exportdir if exportdir else u'export/ass'
    layer = cmds.editRenderLayerGlobals(
        query=True, currentRenderLayer=True)

    file_path = mbase.CACHE_LAYER_PATH.format(
        workspace=cmds.workspace(q=True, fn=True),
        exportdir=exportdir,
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
        if not _dir.mkpath(u'.'):
            s = u'Could not create {}'.format(_dir.path())
            raise OSError(s)

    sel = cmds.ls(selection=True)
    try:
        import arnold  # pylint: disable=E0401

        # Let's get the first renderable camera
        cams = cmds.ls(cameras=True)
        cam = None
        for cam in cams:
            if cmds.getAttr(u'{}.renderable'.format(cam)):
                break

        cmds.select(clear=True)
        cmds.select(set_members, replace=True)

        ext = file_path.split('.')[-1]
        _file_path = unicode(file_path)

        for fr in xrange(start, end + 1):
            if not frame:
                # Create a mock version, if does not exist
                open(file_path, 'a').close()
                cmds.currentTime(fr, edit=True)
                _file_path = file_path.replace(u'.{}'.format(ext), u'')
                _file_path += u'_'
                _file_path += u'{}'.format(fr).zfill(mbase.DefaultPadding)
                _file_path += u'.'
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


@QtCore.Slot(unicode)
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
    if not cmds.pluginInfo(u'AbcExport.mll', loaded=True, q=True):
        cmds.loadPlugin(u'AbcExport.mll', quiet=True)
        cmds.loadPlugin(u'AbcImport.mll', quiet=True)

    # We want to handle the exact name of the file
    # We'll remove the namespace, strip underscores
    set_name = set_name.replace(u':', u'_').strip(u'_')
    set_name = re.sub(ur'[0-9]*$', u'', set_name)
    ext = u'abc'

    # Let's get the cache folder root location by querrying
    exportdir = mbase.find_project_folder(u'alembic export')
    exportdir = exportdir if exportdir else mbase.DEFAULT_CACHE_DIR
    file_path = mbase.CACHE_PATH.format(
        workspace=cmds.workspace(q=True, fn=True),
        exportdir=exportdir,
        set=set_name,
        ext=ext
    )

    # Let's make sure destination folder exists
    file_info = QtCore.QFileInfo(file_path)
    _dir = file_info.dir()
    if not _dir.exists():
        if not _dir.mkpath(u'.'):
            s = u'Could not create {}'.format(_dir.path())
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
        if not _dir.mkpath(u'.'):
            s = u'Could not create {}'.format(_dir.path())
            raise OSError(s)

    # Check to make sure we're not overwriting anything...
    if file_info.exists():
        s = u'Unable to save alembic: {} already exists.'.format(file_path)
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


@QtCore.Slot(unicode)
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
        if not cmds.pluginInfo(u'objExport.mll', loaded=True, q=True):
            cmds.loadPlugin(u'objExport.mll', quiet=True)
    except:
        s = u'Could not load the `objExport` plugin'
        raise RuntimeError(s)

    # We want to handle the exact name of the file
    # We'll remove the namespace, strip underscores
    set_name = set_name.replace(u':', u'_').strip(u'_')
    set_name = re.sub(ur'[0-9]*$', u'', set_name)
    ext = u'obj'

    exportdir = mbase.find_project_folder(u'objexport')
    exportdir = exportdir if exportdir else u'export/obj'

    file_path = mbase.CACHE_PATH.format(
        workspace=cmds.workspace(q=True, fn=True),
        exportdir=exportdir,
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
        if not _dir.mkpath(u'.'):
            s = u'Could not create {}'.format(_dir.path())
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
        if not _dir.mkpath(u'.'):
            s = u'Could not create {}'.format(_dir.path())
            raise OSError(s)

    # Last-ditch check to make sure we're not overwriting anything...
    if file_info.exists():
        s = u'Unable to save set: {} already exists.'.format(file_path)
        raise RuntimeError(s)

    sel = cmds.ls(selection=True)
    file_path = file_info.filePath()
    ext = file_path.split('.')[-1]
    _file_path = unicode(file_path)

    try:
        cmds.select(clear=True)
        cmds.select(set_members, replace=True)

        for fr in xrange(start, end + 1):
            if not frame:
                # Create a mock version, if does not exist
                open(file_path, 'a').close()
                cmds.currentTime(fr, edit=True)
                _file_path = file_path.replace(u'.{}'.format(ext), u'')
                _file_path += u'_'
                _file_path += u'{}'.format(fr).zfill(mbase.DefaultPadding)
                _file_path += u'.'
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
    if file_info.suffix().lower() in (u'ma', u'mb', u'abc'):
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
    v = settings.instance().value(
        settings.SettingsSection,
        settings.SaveWarningsKey
    )
    # Set default value if none has been set previously
    v = QtCore.Qt.Unchecked if v is None else v

    # If save warning has been explicitly disabled return
    if v == QtCore.Qt.Checked:
        return

    workspace_info = QtCore.QFileInfo(
        cmds.workspace(q=True, expandName=True))
    scene_file = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

    if scene_file.baseName().lower() == u'untitled':
        return

    if workspace_info.path().lower() not in scene_file.filePath().lower():
        ui.MessageBox(
            u'Looks like you are saving "{}" outside the current project\nThe current project is "{}"'.format(
                scene_file.fileName(),
                workspace_info.path()),
            u'If you didn\'t expect this message, is it possible the project was changed by {} from another instance of Maya?'.format(
                common.PRODUCT)
        ).open()


@common.error
@common.debug
def unmark_active(*args):
    """Callback responsible for keeping the active-file in the list updated."""
    f = main.instance().stackedwidget.widget(common.FileTab)
    if not f.model().sourceModel().active_index().isValid():
        return
    f.deactivate(f.model().sourceModel().active_index())


@common.error
@common.debug
def update_active_item(*args):
    """Callback responsible for keeping the active-file in the list updated."""
    f = main.instance().stackedwidget.widget(common.FileTab)
    active_index = f.model().sourceModel().active_index()
    if active_index.isValid():
        f.deactivate(active_index.active_index())

    scene = cmds.file(query=True, expandName=True)
    model = f.model().sourceModel()

    p = model.parent_path()
    k = model.task()
    t1 = model.data_type()
    t2 = common.FileItem if t1 == common.SequenceItem else common.SequenceItem

    for t in (t1, t2):
        if t == common.SequenceItem:
            scene = common.proxy_path(scene)
        ref = datacache.get_data_ref(p, k, t)
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
        unicode: The name of the input scene if the load was successfull.

    Raises:
        RuntimeError: When and invalid scene file is passed.

    """
    p = common.get_sequence_endpath(path)
    file_info = QtCore.QFileInfo(p)

    _s = file_info.suffix().lower()
    if _s not in (u'ma', u'mb', u'abc'):
        s = u'{} is not a valid scene.'.format(p)
        raise RuntimeError(s)

    if _s == 'abc':
        if not cmds.pluginInfo('AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcImport.mll", quiet=True)
        if not cmds.pluginInfo("AbcExport.mll", loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)

    if not file_info.exists():
        s = u'{} does not exist.'.format(p)
        raise RuntimeError(s)

    if mbase.is_scene_modified() == QtWidgets.QMessageBox.Cancel:
        return
    cmds.file(file_info.filePath(), open=True, force=True)
    s = u'Scene opened {}\n'.format(file_info.filePath())
    log.success(s)
    return file_info.filePath()


@common.error
@common.debug
def import_scene(path, reference=False):
    """Imports a Maya or alembic file to the current Maya scene.

    Args:
        path (unicode): Path to a Maya scene file.
        reference (bool): When `true` the import will be a reference.

    """
    p = common.get_sequence_endpath(path)
    file_info = QtCore.QFileInfo(p)
    _s = file_info.suffix().lower()
    if _s not in (u'ma', u'mb', u'abc'):
        s = u'{} is not a valid scene.'.format(p)
        raise RuntimeError(s)

    # Load the alembic plugin
    if _s == 'abc':
        if not cmds.pluginInfo('AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcImport.mll", quiet=True)
        if not cmds.pluginInfo("AbcExport.mll", loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)

    if not file_info.exists():
        s = u'{} does not exist.'.format(p)
        raise RuntimeError(s)

    if cmds.file(q=True, sn=True).lower() == file_info.filePath().lower() and reference:
        raise RuntimeError('Can\'t reference itself.')

    match = common.get_sequence(file_info.fileName())
    basename = match.group(1) if match else file_info.baseName()
    basename = re.sub(ur'_v$', u'', basename, flags=re.IGNORECASE)

    alphabet = mbase._get_available_suffixes(basename)
    if not alphabet:  # no more suffixes to assign
        return None

    w = QtWidgets.QInputDialog()
    w.setWindowTitle(u'Assign suffix')
    w.setLabelText(mbase.SUFFIX_LABEL)
    w.setComboBoxItems(alphabet)
    w.setCancelButtonText(u'Cancel')
    w.setOkButtonText(u'Import')
    res = w.exec_()
    if not res:
        return None
    suffix = w.textValue()

    id = u'{}'.format(uuid.uuid1()).replace(u'-', u'_')
    # This should always be a unique name in the maya scene
    ns = u'{}_{}'.format(basename, suffix)
    rfn = u'{}_RN_{}'.format(ns, id)

    if reference:
        cmds.file(
            file_info.filePath(),
            reference=True,
            ns=ns,
            rfn=rfn,
        )
        mbase._add_suffix_attribute(rfn, suffix, reference=reference)

        # The reference node is locked by default
        cmds.lockNode(rfn, lock=False)
        rfn = cmds.rename(rfn, u'{}_RN'.format(ns))
        cmds.lockNode(rfn, lock=True)
    else:
        cmds.file(
            file_info.filePath(),
            i=True,
            ns=ns
        )
        mbase._add_suffix_attribute(ns, suffix, reference=reference)

    s = u'{} was imported.'.format(file_info.filePath())
    log.success(s)
    return file_info.filePath()


def export_alembic(destination_path, outliner_set, startframe, endframe, step=1.0):
    """Main alembic export definition.

    Only shapes, normals and uvs are exported by this implementation. The list
    of shapes contained in the `outliner_set` will be rebuilt in the root of
    the scene to avoid parenting issues.

    Args:
        destination_path (unicode): Path to the output file.
        outliner_set (tuple): A list of transforms contained in a geometry set.

    """
    # ======================================================
    # ERROR CHECKING
    # Check destination before proceeding
    if not isinstance(outliner_set, (tuple, list)):
        raise TypeError(
            u'Expected <type \'list\'>, got {}'.format(type(outliner_set)))

    destination_info = QtCore.QFileInfo(destination_path)
    destination_dir = destination_info.dir()
    _destination_dir_info = QtCore.QFileInfo(destination_dir.path())

    if not _destination_dir_info.exists():
        s = u'Unable to save the alembic file, {} does not exists.'.format(
            _destination_dir_info.filePath())
        ui.ErrorBox(
            u'Alembic export failed.',
            s
        ).open()
        log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    if not _destination_dir_info.isReadable():
        s = u'Unable to save the alembic file, {} is not readable.'.format(
            _destination_dir_info.filePath())
        ui.ErrorBox(
            u'Alembic export failed.',
            s
        ).open()
        log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    if not _destination_dir_info.isWritable():
        s = u'Unable to save the alembic file, {} is not writable.'.format(
            _destination_dir_info.filePath())
        ui.ErrorBox(
            u'Alembic export failed.',
            s
        ).open()
        log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    # ======================================================

    destination_path = QtCore.QFileInfo(destination_path).filePath()

    # If the extension is missing, we'll add it here
    if not destination_path.lower().endswith('.abc'):
        destination_path = destination_path + u'.abc'

    def is_intermediate(s): return cmds.getAttr(
        u'{}.intermediateObject'.format(s))

    # We'll need to use the DecomposeMatrix Nodes, let's check if the plugin
    # is loaded and ready to use
    if not cmds.pluginInfo(u'matrixNodes.mll', loaded=True, q=True):
        cmds.loadPlugin(u'matrixNodes.mll', quiet=True)

    world_shapes = []
    valid_shapes = []

    # First, we will collect the available shapes from the given set
    for item in outliner_set:
        shapes = cmds.listRelatives(item, fullPath=True)
        for shape in shapes:
            if is_intermediate(shape):
                continue

            basename = shape.split(u'|').pop()
            try:
                # AbcExport will fail if a transform or a shape node's name is not unique
                # This was suggested on a forum - listing the relatives for a
                # an object without a unique name should raise a ValueError
                cmds.listRelatives(basename)
            except ValueError as err:
                s = u'"{shape}" does not have a unique name. This is not usually allowed for alembic exports and might cause the export to fail.\nError: {err}'.format(
                    shape=shape, err=err)
                log.error(s)

            # Camera's don't have mesh nodes but we still want to export them!
            if cmds.nodeType(shape) != u'camera':
                if not cmds.attributeQuery(u'outMesh', node=shape, exists=True):
                    continue
            valid_shapes.append(shape)

    if not valid_shapes:
        raise RuntimeError(
            u'# No valid shapes found in "{}" to export! Aborting...'.format(outliner_set))

    cmds.select(clear=True)

    # Creating a temporary namespace to avoid name-clashes later when we duplicate
    # the meshes. We will delete this namespace, and it's contents after the export
    if cmds.namespace(exists=u'mayaExport'):
        cmds.namespace(removeNamespace=u'mayaExport',
                       deleteNamespaceContent=True)
    ns = cmds.namespace(add=u'mayaExport')

    world_transforms = []

    try:
        # For meshes, we will create an empty mesh node and connect the outMesh and
        # UV attributes from our source.
        # We will also apply the source mesh's transform matrix to the newly created mesh
        for shape in valid_shapes:
            basename = shape.split(u'|').pop()
            if cmds.nodeType(shape) != u'camera':
                # Create new empty shape node
                world_shape = cmds.createNode(
                    u'mesh', name=u'{}:{}'.format(ns, basename))

                # outMesh -> inMesh
                cmds.connectAttr(u'{}.outMesh'.format(
                    shape), u'{}.inMesh'.format(world_shape), force=True)
                # uvSet -> uvSet
                cmds.connectAttr(u'{}.uvSet'.format(shape),
                                 u'{}.uvSet'.format(world_shape), force=True)

                # worldMatrix -> transform
                decompose_matrix = cmds.createNode(
                    u'decomposeMatrix', name=u'{}:decomposeMatrix#'.format(ns))
                cmds.connectAttr(
                    u'{}.worldMatrix[0]'.format(shape), u'{}.inputMatrix'.format(decompose_matrix), force=True)
                #
                transform = cmds.listRelatives(
                    world_shape, fullPath=True, type='transform', parent=True)[0]
                world_transforms.append(transform)
                #
                cmds.connectAttr(
                    u'{}.outputTranslate'.format(decompose_matrix), u'{}.translate'.format(transform), force=True)
                cmds.connectAttr(
                    u'{}.outputRotate'.format(decompose_matrix), u'{}.rotate'.format(transform), force=True)
                cmds.connectAttr(
                    u'{}.outputScale'.format(decompose_matrix), u'{}.scale'.format(transform), force=True)
            else:
                world_shape = shape
                world_transforms.append(cmds.listRelatives(
                    world_shape, fullPath=True, type='transform', parent=True)[0])
            world_shapes.append(world_shape)

        # Our custom progress callback
        perframecallback = u'"import {}.maya.widget as w;w.report_export_progress({}, #FRAME#, {}, {})"'.format(
            common.PRODUCT.lower(), startframe, endframe, time.time())

        # Let's build the export command
        jobArg = u'{f} {fr} {s} {uv} {ws} {wv} {wuvs} {sn} {rt} {df} {pfc} {ro}'.format(
            f=u'-file "{}"'.format(destination_path),
            fr=u'-framerange {} {}'.format(startframe, endframe),
            s=u'-step {}'.format(step),
            uv=u'-uvWrite',
            ws=u'-worldSpace',
            wv=u'-writeVisibility',
            # eu='-eulerFilter',
            wuvs=u'-writeuvsets',
            sn=u'-stripNamespaces',
            rt=u'-root {}'.format(u' -root '.join(world_transforms)),
            df=u'-dataFormat {}'.format(u'ogawa'),
            pfc=u'-pythonperframecallback {}'.format(perframecallback),
            ro='-renderableOnly'
        )
        s = u'# jobArg: `{}`'.format(jobArg)

        cmds.AbcExport(jobArg=jobArg)
        log.success(s)

    except Exception as err:
        ui.ErrorBox(
            u'An error occured exporting Alembic cache',
            u'{}'.format(err)
        ).open()
        log.error(u'Could not open the plugin window.')
        raise

    finally:
        # Finally, we will delete the previously created namespace and the object
        # contained inside. I wrapped the call into an evalDeferred to let maya
        # recover after the export and delete the objects more safely.

        def teardown():
            cmds.namespace(
                removeNamespace=u'mayaExport', deleteNamespaceContent=True)
        cmds.evalDeferred(teardown)


@common.error
@common.debug
def capture_viewport(size=1.0):
    """Saves a versioned capture to the ``capture_folder`` defined in the preferences.

    The script will output to the an image sequence and if FFmpeg is present converts it to a h264 movie file.
    It will also try to create a ``latest`` folder with a copy of the last exported image sequence.

    Usage:

        .. code-block:: python

        PluginWidget.capture_viewport()


    """
    ext = u'png'
    scene_info = QtCore.QFileInfo(cmds.file(q=True, expandName=True))

    # CAPTURE_DESTINATION
    capture_folder, workspace, base_destination_path = mbase.capture_viewport_destination()

    _dir = QtCore.QFileInfo(base_destination_path).dir()
    if not _dir.exists():
        _dir.mkpath(u'.')

    # Use our custom ModelPanel picker to select the viewport we want to
    # capture
    from . import widget

    picker = widget.PanelPicker()
    picker.exec_()
    panel = picker.panel

    # Cancel if no selection was made
    if not panel:
        return

    # Make sure we have selected a valid panel as not all panels are modelEditors
    if panel is None or cmds.objectTypeUI(panel) != u'modelEditor':
        s = u'Activate a viewport before starting a capture.'
        raise RuntimeError(s)

    camera = cmds.modelPanel(panel, query=True, camera=True)

    # The the panel settings using mCapture.py and update it with our
    # custom settings. See `mbase.CaptureOptions` for the hard-coded
    # defaults we're using here
    from . import mCapture
    options = mCapture.parse_view(panel)
    options['viewport_options'].update(mbase.CaptureOptions)

    # Hide existing panels
    current_state = {}
    for panel in cmds.getPanel(type=u'modelPanel'):
        if not cmds.modelPanel(panel, exists=True):
            continue

        try:
            ptr = OpenMayaUI.MQtUtil.findControl(panel)
            if not ptr:
                continue
            panel_widget = shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)
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
            display_options=mbase.DisplayOptions,
            camera_options=mbase.CameraOptions,
            viewport2_options=options['viewport2_options'],
            viewport_options=options['viewport_options'],
            format=u'image',
            compression=ext,
            filename=base_destination_path,
            overwrite=True,
            viewer=False
        )
        log.success(u'Capture saved to {}'.format(_dir.path()))
    except:
        raise
    finally:
        cmds.ogs(reset=True)

        # Show hidden panels
        for panel in cmds.getPanel(type=u'modelPanel'):
            if not cmds.modelPanel(panel, exists=True):
                continue
            try:
                ptr = OpenMayaUI.MQtUtil.findControl(panel)
                if not ptr:
                    continue
                panel_widget = shiboken2.wrapInstance(
                    long(ptr), QtWidgets.QWidget)
                if panel_widget:
                    if panel in current_state:
                        panel_widget.setVisible(current_state[panel])
                    else:
                        panel_widget.setVisible(True)
            except:
                print '# Could not restore {} after capture'.format(panel)


    # Publish output
    publish_capture(workspace, capture_folder, scene_info, ext)

    # Push and reveal output
    path = mbase.CAPTURE_FILE.format(
        workspace=workspace,
        capture_folder=capture_folder,
        scene=scene_info.baseName(),
        frame=u'{}'.format(int(cmds.playbackOptions(q=True, minTime=True))).zfill(mbase.DefaultPadding),
        ext=ext
    )
    push_capture(path)
    reveal_capture(path)


def push_capture(path):
    # Get preference
    v = settings.instance().value(
        settings.SettingsSection,
        settings.PushCaptureToRVKey
    )
    # Set default value if none has been set previously
    v = QtCore.Qt.Unchecked if v is None else v

    # If save warning has been explicitly disabled return
    if v == QtCore.Qt.Checked:
        return

    rv.push(path)


def reveal_capture(path):
    # Get preference
    v = settings.instance().value(
        settings.SettingsSection,
        settings.RevealCaptureKey
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
    v = settings.instance().value(
        settings.SettingsSection,
        settings.PublishCaptureKey
    )
    # Set default value if none has been set previously
    v = QtCore.Qt.Unchecked if v is None else v

    # If save warning has been explicitly disabled return
    if v == QtCore.Qt.Checked:
        return

    asset = workspace.split(u'/').pop()
    start = int(cmds.playbackOptions(q=True, minTime=True))
    end = int(cmds.playbackOptions(q=True, maxTime=True))
    duration = (end - start) + 1

    publish_folder = mbase.CAPTURE_PUBLISH_DIR.format(
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
        s = u'{} is not writable.'.format(publish_folder)
        raise OSError(s)

    import _scandir
    for entry in _scandir.scandir(publish_folder):
        os.remove(entry.path)

    idx = 0
    for n in xrange(int(duration)):
        frame = str(n + int(start)).zfill(mbase.DefaultPadding)
        source = mbase.CAPTURE_FILE.format(
            workspace=workspace,
            capture_folder=capture_folder,
            scene=scene_info.baseName(),
            frame=frame,
            ext=ext
        )
        dest = mbase.AGNOSTIC_CAPTURE_FILE.format(
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


def remove_button():
    from . import widget as maya_widget

    ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
    if not ptr:
        widgets = QtWidgets.QApplication.instance().allWidgets()
        widget = [f for f in widgets if f.objectName() ==
                  maya_widget.object_name]
        if not widget:
            return
        widget = widget[0]

    else:
        widget = shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)
        if not widget:
            return

        widget = widget.findChild(maya_widget.ToolButton)

    widget.hide()
    widget.deleteLater()


def remove_workspace_control(workspace_control):
    from . import widget as maya_widget

    if cmds.workspaceControl(workspace_control, q=True, exists=True):
        cmds.deleteUI(workspace_control)
        if cmds.workspaceControlState(workspace_control, ex=True):
            cmds.workspaceControlState(workspace_control, remove=True)
    try:
        for k in maya_widget.mayaMixin.mixinWorkspaceControls.items():
            if u'PluginWidget' in k:
                del maya_widget.mayaMixin.mixinWorkspaceControls[k]
    except:
        print 'Could not remove workspace controls'

    sys.stdout.write(
        u'# {}: UI deleted.\n'.format(common.PRODUCT))


def quit():
    from . import widget as maya_widget
    if not maya_widget._instance:
        raise RuntimeError('Not initialized.')

    maya_widget._instance.remove_context_callbacks()
    maya_widget._instance.deleteLater()
    maya_widget._instance = None
    remove_button()
    # maya_widget._instance.hide()

    for widget in QtWidgets.QApplication.instance().allWidgets():
        if re.match(ur'PluginWidget.*WorkspaceControl', widget.objectName()):
            remove_workspace_control(widget.objectName())
