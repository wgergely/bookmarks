# -*- coding: utf-8 -*-
"""Various common Maya actions.

"""
import os
import re
import uuid

import maya.OpenMayaUI as OpenMayaUI
import maya.app.general.mayaMixin as mayaMixin
import maya.cmds as cmds
import shiboken2
from PySide2 import QtWidgets, QtCore

from . import base
from . import capture
from . import main
from .. import actions
from .. import common
from .. import log
from .. import ui
from ..external import rv


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
        extension=ext, file=_file, create_file=False, increment=increment
    )
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
            f'Unable to save file because {result} already exists.'
        )

    cmds.file(rename=result)
    cmds.file(force=True, save=True, type=type)

    common.signals.fileAdded.emit(result)
    return result


@QtCore.Slot()
@common.error
@common.debug
def execute(index):
    file_path = common.get_sequence_endpath(
        index.data(QtCore.Qt.StatusTipRole)
    )
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
        cmds.workspace(q=True, expandName=True)
    )
    scene_file = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

    if scene_file.baseName().lower() == 'untitled':
        return

    if workspace_info.path().lower() not in scene_file.filePath().lower():
        ui.MessageBox(
            'Looks like you are saving "{}" outside the current project\nThe '
            'current project is "{}"'.format(
                scene_file.fileName(),
                workspace_info.path()
            ),
            'If you didn\'t expect this message, is it possible the project was '
            'changed by {} from another instance of Maya?'.format(
                common.product
            )
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
                                                   idx][
                                                   common.FlagsRole] | \
                                               common.MarkedAsActive

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
    def get_namespaces_from_path(_path):
        _basename = _path.split('/')[-1]
        _basename = _basename.split('.')[0]

        nms = re.findall(r'\(.+?\)', _basename)
        nm = ':'.join(re.sub(r'[\(\)]', '', f) for f in nms)
        name = _basename.replace('_'.join(nms), '').strip('_')
        return nm, name

    p = common.get_sequence_endpath(path)
    file_info = QtCore.QFileInfo(p)
    _s = file_info.suffix().lower()
    if _s not in ('ma', 'mb', 'abc'):
        raise RuntimeError(f'{p} is not a valid scene.')

    # Load the alembic plugin
    if _s == 'abc':
        if not cmds.pluginInfo('AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcImport.mll", quiet=True)
        if not cmds.pluginInfo("AbcExport.mll", loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)

    if not file_info.exists():
        raise RuntimeError(f'{p} does not exist.')

    if cmds.file(
            q=True, sn=True
    ).lower() == file_info.filePath().lower() and reference:
        raise RuntimeError('Can\'t reference itself.')

    _, basename = get_namespaces_from_path(path)
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

    # This should always be a unique name in the maya scene
    id = uuid.uuid1().hex.replace('-', '_')
    ns = f'{basename}_{suffix}'
    rfn = f'{ns}_RN_{id}'

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
        rfn = cmds.rename(rfn, f'{ns}_RN')
        cmds.lockNode(rfn, lock=True)
    else:
        cmds.file(
            file_info.filePath(),
            i=True,
            ns=ns
        )
        base._add_suffix_attribute(ns, suffix, reference=reference)

    s = f'{file_info.filePath()} was imported.'
    log.success(s)
    return file_info.filePath()


@common.error
@common.debug
def capture_viewport(size=1.0):
    """Saves a versioned capture to the ``capture_folder`` defined in the
    preferences.

    The script will output to an image sequence and if FFFmpeg can be found
    converts it to a h264 movie file.
    It will also try to create a ``latest`` folder with a copy of the last
    exported image sequence.

    """
    ext = 'png'
    scene_info = QtCore.QFileInfo(cmds.file(q=True, expandName=True))

    # CAPTURE_DESTINATION
    capture_folder, workspace, base_destination_path = \
        base.capture_viewport_destination()

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

    # The panel settings using capture.py and update it with our
    # custom settings. See `base.CaptureOptions` for the hard-coded
    # defaults we're using here
    options = capture.parse_view(panel)
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
        capture.capture(
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
        log.success(f'Capture saved to {_dir.path()}')
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
                    int(ptr), QtWidgets.QWidget
                )
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
            base.DefaultPadding
        ),
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


@common.error
@QtCore.Slot()
def apply_viewport_preset(k):
    from . import viewport
    panel = cmds.getPanel(withFocus=True)
    if not cmds.modelPanel(panel, query=True, exists=True):
        return
    editor = cmds.modelPanel(panel, query=True, modelEditor=True)
    cmds.modelEditor(editor, edit=True, **viewport.presets[k])


@QtCore.Slot()
def import_camera_preset():
    path = common.get_rsc('maya/camera.ma')
    if cmds.objExists('camera'):
        print('An object named "camera" already exists. Nothing was imported.')
        return
    cmds.file(path, i=True, defaultNamespace=True)


@QtCore.Slot()
def show_shader_tool():
    from . import shadertool
    shadertool.show()
