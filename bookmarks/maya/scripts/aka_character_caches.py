"""Export script for Odyssey cloth sims.

The script automates the animation cache export from Maya.

It performs the follow steps:
    - Saves the current animation to studio library
    - Removes the animation from the body and root controllers
    - Adds a preroll with a reset pose
    - Saves the animation caches

Gergely Wootsch.
hello@gergely-wootsch.com
Studio Aka, 2023 October

"""
import json
import os
import sys

import maya.cmds as cmds
from PySide2 import QtWidgets, QtCore

from . import aka_make_export_sets
from .. import base as mayabase
from .. import export
from ... import actions
from ... import common
from ... import database
from ... import images
from ... import log
from ... import ui
from ...tokens import tokens

instance = None

#: The path of the output cache file
cache_path = '{dir}/{basename}_{version}.{ext}'

#: The default values for the dialog
DEFAULT_VALUES = {
    'Studio Library': {
        'studio_library_folder': {
            'default': '',
            'placeholder': 'C:/Users/aka/Documents/studiolibrary',
            'widget': ui.LineEdit,
        },
        'studio_library_reset_pose': {
            'default': 'Characters/IbogaineMarcus/Reset/A-Pose-v2-FullFK.pose/pose.json',
            'placeholder': 'relative/path/to/pose.json',
            'widget': ui.LineEdit,
        },
        'studio_library_output_folder': {
            'default': 'Shots/{prefix}/{asset0}_{shot}',
            'placeholder': 'relative/path/to/output/dir',
            'widget': ui.LineEdit,
        },
    },
    'Character': {
        'namespace': {
            'default': 'IbogaineMarcus_01',
            'placeholder': 'CharacterNamespace_01',
            'widget': ui.LineEdit,
        },
        'controllers_set': {
            'default': 'rig_controllers_grp',
            'placeholder': 'controller_set_name',
            'widget': ui.LineEdit,
        },
        'hip_controller': {
            'default': 'body_C0_ctl',
            'placeholder': 'hip_controller_name',
            'widget': ui.LineEdit,
        },
        'exclude_reset_pose_from': {
            'default': 'legUI_L0_ctl, armUI_R0_ctl, faceUI_C0_ctl, legUI_R0_ctl, spineUI_C0_ctl, armUI_L0_ctl, body_C0_ctl, world_ctl, root_C0_ctl',
            'placeholder': 'list, of, controllers, to, exclude',
            'widget': ui.LineEdit,
        },
        'apply_animation_exclusions': {
            'default': True,
            'placeholder': '',
            'widget': lambda: QtWidgets.QCheckBox('Apply Animation Exclusions'),
        },
        'exclude_animation_from': {
            'default': 'body_C0_ctl, world_ctl, root_C0_ctl',
            'placeholder': 'list, of, controllers, to, exclude',
            'widget': ui.LineEdit,
        },
    }
}


def export_nullLocator_to_alembic(output_file_path, cut_in, cut_out):
    """Export the nullLocator to Alembic.

    Args:
        output_file_path (str): The output file path.
        cut_in (int): The cut in frame.
        cut_out (int): The cut out frame.

    """
    # Check if the nullLocator exists
    if not cmds.objExists('nullLocator'):
        raise ValueError('nullLocator does not exist in the scene.')

    # Ensure that the nullLocator is in world space
    parent = cmds.listRelatives('nullLocator', parent=True)
    if parent:
        # Parent it to the world
        cmds.parent('nullLocator', world=True)

    # Export to Alembic
    export_command = (
        f'-frameRange {cut_in} {cut_out} '
        f'-worldSpace '  # Ensures the object is exported in world space
        f'-root nullLocator '  # The object we want to export
        f'-file "{output_file_path}"'
    )
    cmds.AbcExport(j=export_command)

    print("Exported nullLocator to: {}".format(output_file_path))


def find_studio_library():
    for path in sys.path:
        if not os.path.isdir(path):
            continue
        for entry in os.scandir(path):
            if 'studiolibrary' in entry.name:
                if os.path.isdir(f'{entry.path}/src'):
                    return os.path.normpath(os.path.abspath(f'{entry.path}/src'))
    return None


def add_studio_library_to_path():
    path = find_studio_library()
    if not path:
        raise RuntimeError('Could not find Studio Library.')

    if path not in sys.path:
        sys.path.insert(0, path)


def get_cache_path(set_name, ext, makedir=True):
    """Get the path of the output cache file.

    """
    workspace = cmds.workspace(q=True, fn=True)

    export_dir = mayabase.DEFAULT_CACHE_DIR.format(
        export_dir=tokens.get_folder(tokens.CacheFolder), ext=tokens.get_subfolder(tokens.CacheFolder, ext)
    )
    file_path = mayabase.CACHE_PATH.format(
        workspace=workspace, export_dir=export_dir, set=set_name, ext=ext
    )
    file_path = mayabase.sanitize_namespace(file_path)

    file_info = QtCore.QFileInfo(file_path)
    _version = 1
    while True:
        version = 'v' + f'{_version}'.zfill(3)

        file_path = cache_path.format(
            dir=file_info.dir().path(), basename=file_info.completeBaseName(), version=version, ext=file_info.suffix()
        )

        if not QtCore.QFileInfo(file_path).exists():
            break
        if _version >= 999:
            break

        _version += 1

    if makedir:
        QtCore.QFileInfo(file_path).dir().mkpath('.')
    return file_path


def get_studio_library_default_library():
    """Get the default library from the Studio Library settings file."""
    try:
        import studiolibrary
        import mutils
    except ImportError as e:
        try:
            add_studio_library_to_path()
        except ImportError:
            raise e
        else:
            import studiolibrary
            import mutils

    s = studiolibrary.settingsPath()
    if not s or not QtCore.QFileInfo(s).exists():
        raise RuntimeError('Could not find the Studio Library settings file.')

    with open(s, 'r') as f:
        studio_library_settings = json.loads(f.read())

    if 'Default' not in studio_library_settings:
        raise RuntimeError('Studio Library does not seem to have been configured. Please check your settings.')
    if 'path' not in studio_library_settings['Default']:
        raise RuntimeError('Studio Library seems to be missing a required settings key "path"')

    v = studio_library_settings['Default']['path']
    if not QtCore.QFileInfo(v).exists():
        raise RuntimeError(
            'Could not find the default Studio Library directory. Check that everything is configured correctly.'
        )

    return v


class ExportCharacterCachesDialog(QtWidgets.QDialog):
    statusChanged = QtCore.Signal(str, str)

    """Dialog to provide options for exporting character caches."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = QtCore.QSettings('StudioAka', 'ExportCharacterCaches')
        self.setWindowTitle('Export Character Caches')

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        if not self.parent():
            common.set_stylesheet(self)

        QtWidgets.QVBoxLayout(self)

        pixmap, color = images.get_thumbnail(
            common.active('server'),
            common.active('job'),
            common.active('root'),
            common.active('asset', path=True),
            size=common.size(common.size_row_height) * 3,
            fallback_thumb='placeholder',
            get_path=False
        )

        row = ui.add_row(None, height=None, parent=self)
        label = QtWidgets.QLabel(parent=self)
        label.setPixmap(pixmap)
        row.layout().addWidget(label, 0)
        row.layout().addSpacing(common.size(common.size_margin) * 0.5)

        active_index = common.active_index(common.AssetTab)
        if not active_index or not active_index.isValid():
            raise RuntimeError('Could not find active asset. Please make sure an asset is activated.')
        asset_name = active_index.data(QtCore.Qt.DisplayRole)
        asset_name = asset_name if asset_name else 'Export Cache'

        row.layout().addWidget(ui.PaintedLabel(asset_name, size=common.size(common.size_font_large)))

        for k in DEFAULT_VALUES:
            grp = ui.get_group(parent=self, )

            for _k, _v in DEFAULT_VALUES[k].items():
                v = self.settings.value(_k, _v['default'])
                editor = _v['widget']()

                if isinstance(editor, QtWidgets.QCheckBox):
                    if not isinstance(v, bool):
                        v = True
                    editor.setChecked(v)

                if isinstance(editor, ui.LineEdit):
                    if not isinstance(v, str):
                        v = ''
                    editor.setText(v)
                    if isinstance(_v['placeholder'], str):
                        editor.setPlaceholderText(_v['placeholder'])

                row = ui.add_row(_k.replace('_', ' ').title(), parent=grp)
                if _k == 'studio_library_folder':
                    row.setHidden(True)
                row.layout().addWidget(editor)

                setattr(self, f'{_k}_editor', editor)

            self.layout().addWidget(grp)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.ok_button = ui.PaintedButton('Export Caches')
        self.cancel_button = ui.PaintedButton('Cancel')
        self.apply_hip_pose_button = ui.PaintedButton('Apply Hip Pose')

        button_layout.addWidget(self.ok_button, 1)
        button_layout.addWidget(self.apply_hip_pose_button, 1)
        button_layout.addWidget(self.cancel_button, 0)

        self.layout().addStretch(1)
        self.layout().addLayout(button_layout)

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.statusChanged.connect(self.show_status)
        self.apply_hip_pose_button.clicked.connect(self.apply_hip_pose)

    @QtCore.Slot(str, str)
    def show_status(self, title, body):
        common.show_message(
            title, body=body, message_type=None, buttons=[], disable_animation=True, parent=self
        )

    def accept(self):
        """Save the settings and accept the dialog.

        """
        # Get database and config
        if not all(common.active('asset', args=True)):
            raise RuntimeError('An asset must be active to export.')

        try:
            cmds.ogs(pause=True)
        except:
            pass

        try:
            cmds.refresh(suspend=True)
        except:
            pass

        try:
            output_paths = self.export()
        finally:
            try:
                cmds.refresh(suspend=False)
            except:
                pass

            try:
                cmds.ogs(pause=False)
            except:
                pass

        common.show_message(
            'Success', f'All cache files were exported. Check the console for details.', message_type='success'
        )

        log.success(f'Character caches were exported successfully.')
        print('\n\n>>> ======================')
        print('>>> Exported files:')
        for path in output_paths:
            print(QtCore.QFileInfo(path).filePath())

        super().accept()

    def _get_options(self):
        # Collect all the current settings to a dictionary
        self.statusChanged.emit('Preparing...', 'Validating options, please wait')

        options = {}
        for k in DEFAULT_VALUES:
            for _k, _v in DEFAULT_VALUES[k].items():
                options[_k] = self.settings.value(_k, _v['default'])

        config = tokens.get(*common.active('root', args=True))
        seq, shot = common.get_sequence_and_shot(common.active('asset'))

        db = database.get(*common.active('root', args=True))
        cut_in = db.value(common.active('asset', path=True), 'cut_in', database.AssetTable)
        cut_out = db.value(common.active('asset', path=True), 'cut_out', database.AssetTable)
        prefix = db.value(common.active('root', path=True), 'prefix', database.BookmarkTable)

        # --- Validate values ---
        if not all((seq, shot)):
            raise RuntimeError('Could not find sequence and shot names.')

        # Check if none of the values are None
        if any((x is None for x in (cut_in, cut_out, prefix))):
            raise RuntimeError('Not all required values are set: We need cut_in, cut_out or prefix to be set.')

        if cut_out <= cut_in:
            raise RuntimeError(f'Cut out is smaller than cut in: {cut_out} <= {cut_in}')

        # --- Validate the options ---

        # Get the default library from the Studio Library settings file
        options['studio_library_folder'] = get_studio_library_default_library()

        # studio_library_reset_pose
        if not options['studio_library_reset_pose']:
            raise RuntimeError('Please specify a reset pose.')

        # Check if we specified a valid reset pose
        _p = options['studio_library_folder'].replace('\\', '/')
        __p = options['studio_library_reset_pose'].replace('\\', '/')
        options['studio_library_reset_pose'] = f'{_p}/{__p}'.replace('\\', '/')

        if not QtCore.QFileInfo(options['studio_library_reset_pose']).exists():
            raise RuntimeError(f'Reset pose "{options["studio_library_reset_pose"]}" does not exist.')

        # studio_library_output_folder
        if not options['studio_library_output_folder']:
            raise RuntimeError('Please specify an output folder template.')

        _p = options['studio_library_folder'].replace('\\', '/')
        __p = options['studio_library_output_folder'].replace('\\', '/')
        __p = config.expand_tokens(
            __p,
            asset=common.active('asset'),
            shot=shot,
            sequence=seq,
            prefix=prefix.split('_')[-1].upper(),
        ).replace('\\', '/')
        options['studio_library_output_folder'] = f'{_p}/{__p}'

        # namespace
        if not options['namespace']:
            raise RuntimeError('Please specify a namespace.')
        # Check if we specified a valid namespace
        if not cmds.namespace(exists=options['namespace']):
            raise RuntimeError(f'Namespace "{options["namespace"]}" does not exist.')

        # controllers_set
        if not options['controllers_set']:
            raise RuntimeError('Please specify a controllers set.')
        # Check if we specified a valid set. The controllers set should be an object set and part of the namespace.
        if not cmds.objExists(f'{options["namespace"]}:{options["controllers_set"]}'):
            raise RuntimeError(f'Controllers set "{options["namespace"]}:{options["controllers_set"]}" does not exist.')
        options['controllers_set'] = f'{options["namespace"]}:{options["controllers_set"]}'

        # Hip controller
        if not options['hip_controller']:
            raise RuntimeError('Please specify a hip controller.')
        # Check if we specified a valid hip controller
        if not cmds.objExists(f'{options["namespace"]}:{options["hip_controller"]}'):
            raise RuntimeError(f'Hip controller "{options["namespace"]}:{options["hip_controller"]}" does not exist.')
        options['hip_controller'] = f'{options["namespace"]}:{options["hip_controller"]}'

        # apply_animation_exclusions
        # Change the value to a boolean
        options['apply_animation_exclusions'] = self.apply_animation_exclusions_editor.isChecked()

        # exclude_animation_from
        if options['apply_animation_exclusions']:
            _not_found = options['exclude_animation_from'].split(',')
            _not_found = [x.strip() for x in _not_found]
            _not_found = [f'{options["namespace"]}:{x}' for x in _not_found if
                          not cmds.objExists(f'{options["namespace"]}:{x}')]

            if _not_found:
                print(f'Warning: Could not find the following controllers: {_not_found}')

            options['exclude_animation_from'] = options['exclude_animation_from'].split(',')
            options['exclude_animation_from'] = [x.strip() for x in options['exclude_animation_from']]
            options['exclude_animation_from'] = [f'{options["namespace"]}:{x}' for x in
                                                 options['exclude_animation_from'] if
                                                 x and cmds.objExists(f'{options["namespace"]}:{x}')]
        else:
            options['exclude_animation_from'] = []

        print(f'Excluding animation from: {options["exclude_animation_from"]}')

        # exclude_reset_pose_from
        _not_found = options['exclude_reset_pose_from'].split(',')
        _not_found = [x.strip() for x in _not_found]
        _not_found = [f'{options["namespace"]}:{x}' for x in _not_found if
                      not cmds.objExists(f'{options["namespace"]}:{x}')]

        if _not_found:
            print(f'Warning: Could not find the following controllers: {_not_found}')

        options['exclude_reset_pose_from'] = options['exclude_reset_pose_from'].split(',')
        options['exclude_reset_pose_from'] = [x.strip() for x in options['exclude_reset_pose_from']]
        options['exclude_reset_pose_from'] = [f'{options["namespace"]}:{x}' for x in options['exclude_reset_pose_from']
                                              if
                                              x and cmds.objExists(f'{options["namespace"]}:{x}')]

        print(f'Excluding reset pose from: {options["exclude_reset_pose_from"]}')

        options['cut_in'] = cut_in
        options['cut_out'] = cut_out
        options['prefix'] = prefix

        return options

    @common.error
    def export(self):
        """The main export function.

        """
        # Save the current settings
        for k in DEFAULT_VALUES:
            for _k, _v in DEFAULT_VALUES[k].items():
                editor = getattr(self, f'{_k}_editor')
                if isinstance(editor, QtWidgets.QCheckBox):
                    self.settings.setValue(_k, editor.isChecked())
                if isinstance(editor, QtWidgets.QLineEdit):
                    self.settings.setValue(_k, editor.text())

        options = self._get_options()
        cut_in = options['cut_in']
        cut_out = options['cut_out']

        # --- Start the export process ---
        preroll = 51

        # Save current selection
        original_selection = cmds.ls(selection=True)
        output_paths = []

        # Clear selection
        cmds.select(clear=True)

        # Let's make the export sets
        try:
            aka_make_export_sets.run()
        except RuntimeError as e:
            raise RuntimeError(f'Could not create export sets: {e}')

        # Add pre-roll to the timeline
        cmds.playbackOptions(
            animationStartTime=cut_in - preroll, minTime=-cut_in - preroll, animationEndTime=cut_out, maxTime=cut_out
        )

        # Move the current time to cut_in
        cmds.currentTime(cut_in)

        self.statusChanged.emit('Exporting...', 'Clearing keyframes...')

        # Let's keyframe the controllers at cut_in and cut_out
        for n in (cut_in, cut_out):
            cmds.currentTime(n)
            cmds.select(cmds.sets(options['controllers_set'], query=True), replace=True, ne=True)
            cmds.setKeyframe(
                cmds.sets(
                    options['controllers_set'], query=True
                ), breakdown=False, preserveCurveShape=False, hierarchy='none', controlPoints=False, shape=True, )

        # Remove any keyframes before between cut_in and cut_in - preroll - 1
        for node in cmds.sets(options['controllers_set'], query=True):
            attrs = cmds.listAnimatable(node)
            if not attrs:
                continue
            for attr in attrs:
                if not cmds.keyframe(attr, query=True, time=(cut_in - preroll - 1, cut_in - 1)):
                    continue
                cmds.cutKey(attr, time=(cut_in - preroll - 1, cut_in - 1))

        # Move the current time to cut_in
        cmds.currentTime(cut_in)

        # Studio Library: Save the full current animation
        _dir = QtCore.QDir(options["studio_library_output_folder"])
        _dir.mkpath('.')

        self.statusChanged.emit('Exporting...', 'Exporting Studio Library clips...')

        try:
            import studiolibrary
            import mutils
        except ImportError as e:
            try:
                add_studio_library_to_path()
            except ImportError:
                raise e
            else:
                import studiolibrary
                import mutils

        try:
            mutils.saveAnim(
                cmds.sets(
                    options['controllers_set'], query=True
                ), os.path.normpath(
                    f'{options["studio_library_output_folder"]}/'
                    f'{options["namespace"]}_fullanim.anim'
                ), time=(cut_in, cut_out), bakeConnected=False, metadata=''
            )
            p = os.path.normpath(
                f'{options["studio_library_output_folder"]}/'
                f'{options["namespace"]}_fullanim.anim'
            )
            log.success(f'Studio Library clip saved to:\n{p}')
        except UnicodeDecodeError as e:
            # Might be a bug in the Studio Library module, seems like it can be ignored
            print(e)

        # Studio Library: Save the animation start pose
        try:
            # Move the current time to cut_in
            cmds.currentTime(cut_in)

            mutils.savePose(
                os.path.normpath(
                    f'{options["studio_library_output_folder"]}/{options["namespace"]}_animstart.pose/pose.json'
                ), cmds.sets(
                    options['controllers_set'], query=True
                ), )
            p = os.path.normpath(
                f'{options["studio_library_output_folder"]}/{options["namespace"]}_animstart.pose/pose.json'
            )
            output_paths.append(p)
            log.success(f'Studio Library pose saved to:\n{p}')
        except UnicodeDecodeError as e:
            print(e)

        self.statusChanged.emit('Exporting...', 'Baking hip animation...')

        # Parent and bake a null to the hip and save the world animation for later use
        locator = cmds.spaceLocator(name='nullLocator')[0]
        constraint = cmds.parentConstraint(options['hip_controller'], locator, maintainOffset=False)[0]

        cmds.bakeResults(
            locator,
            time=(cut_in,cut_out),
            simulation=True,
            sampleBy=1, oversamplingRate=1, disableImplicitControl=True,
            preserveOutsideKeys=True, sparseAnimCurveBake=False, removeBakedAttributeFromLayer=False,
            bakeOnOverrideLayer=False, minimizeRotation=True, controlPoints=False, shape=True
        )

        self.statusChanged.emit('Exporting...', 'Saving hip animation...')

        # Save the hip animation
        try:
            mutils.saveAnim(
                [locator, ], os.path.normpath(
                    f'{options["studio_library_output_folder"]}/'
                    f'{options["namespace"]}_hip.anim'
                ), time=(cut_in, cut_out), bakeConnected=False, metadata=''
            )
            p = os.path.normpath(
                f'{options["studio_library_output_folder"]}/'
                f'{options["namespace"]}_hip.anim'
            )
            output_paths.append(p)
            log.success(f'Studio Library clip saved to:\n{p}')
        except UnicodeDecodeError as e:
            print(e)

        # Export the nullLocator to Alembic
        self.statusChanged.emit('Exporting...', 'Saving nullLocator animation...')
        p = get_cache_path('nullLocator', 'abc')
        output_paths.append(p)
        export_nullLocator_to_alembic(p, cut_in, cut_out)

        # Cleanup
        cmds.delete(constraint)
        cmds.delete(locator)

        # Remove all animation from any specified excluded controllers
        if options['apply_animation_exclusions'] and options['exclude_animation_from']:
            for node in options['exclude_animation_from']:
                print(f'Removing animation from: {node}')
                cmds.cutKey(node, clear=True)

        # Make sure the pose is unaltered at cut_in
        cmds.currentTime(cut_in)
        mutils.loadPose(
            os.path.normpath(
                f'{options["studio_library_output_folder"]}/{options["namespace"]}_animstart.pose/pose.json'
            ), key=True
        )

        # Move the current time to cut_in - preroll
        cmds.currentTime(cut_in - preroll)

        # Studio Library: Apply the reset pose at cut_in - preroll
        # We only want to apply the reset pose to the controllers that are not excluded
        _s1 = set(cmds.sets(options['controllers_set'], query=True))
        _s3 = set(options["exclude_reset_pose_from"])

        mutils.loadPose(
            os.path.normpath(options["studio_library_reset_pose"]),
            objects=list(_s1 - _s3),
            key=True,
            namespaces=[options['namespace'], ]
        )

        # -- Cache exports --

        self.statusChanged.emit('Caching...', 'Saving camera cache...')

        # Export the camera
        if cmds.objExists('camera_export') and cmds.sets('camera_export', query=True):
            p = get_cache_path('camera_export', 'ma')
            output_paths.append(p)
            export.export_maya(
                p, cmds.sets('camera_export', query=True), cut_in, cut_out, step=1.0
            )
            log.success(f'Camera cache saved to:\n{p}')

            p = get_cache_path('camera_export', 'abc')
            output_paths.append(p)
            export.export_alembic(
                p, cmds.sets('camera_export', query=True), cut_in, cut_out,
                step=1.0
            )
            log.success(f'Camera cache saved to:\n{p}')
        else:
            print('Warning: "camera_export" not found, or empty. Skipping export.')

        # Export character caches
        # In the case of namespaces suffixed by _01, we want to remove the suffix
        # as the export sets are not suffixed by _01 (this does not apply to _02, _03, etc.)
        if options['namespace'].endswith('_01'):
            export_namespace = options['namespace'].replace('_01', '')
        else:
            export_namespace = options['namespace']

        # Body
        self.statusChanged.emit('Caching...', 'Saving body cache...')

        if cmds.objExists(f'{export_namespace}_body_export') and cmds.sets(
                f'{export_namespace}_body_export', query=True
        ):
            p = get_cache_path(f'{export_namespace}_body_export', 'abc')
            output_paths.append(p)
            export.export_alembic(
                p, cmds.sets(f'{export_namespace}_body_export', query=True), cut_in - preroll, cut_out, step=1.0
            )
            log.success(f'Body cache saved to:\n{p}')
        else:
            print(f'Warning: "{export_namespace}_body_export" not found, or empty. Skipping export.')

        # Cloth
        self.statusChanged.emit('Caching...', 'Saving cloth cache...')

        if cmds.objExists(f'{export_namespace}_cloth_export') and cmds.sets(
                f'{export_namespace}_cloth_export', query=True
        ):
            p = get_cache_path(f'{export_namespace}_cloth_export', 'abc')
            output_paths.append(p)
            export.export_alembic(
                p, cmds.sets(
                    f'{export_namespace}_cloth_export', query=True
                ), cut_in - preroll, cut_in - preroll, step=1.0
            )
            log.success(f'Cloth cache saved to:\n{p}')
        else:
            print(f'Warning: "{export_namespace}_cloth_export" not found, or empty. Skipping export.')

        # Extra
        self.statusChanged.emit('Caching...', 'Saving extra cache...')

        if cmds.objExists(f'{export_namespace}_extra_export') and cmds.sets(
                f'{export_namespace}_extra_export', query=True
        ):
            p = get_cache_path(f'{export_namespace}_extra_export', 'abc')
            output_paths.append(p)
            export.export_alembic(
                p, cmds.sets(f'{export_namespace}_extra_export', query=True), cut_in - preroll, cut_out, step=1.0
            )
            log.success(f'Extra cache saved to:\n{p}')

        # -- Cleanup --

        # Studio Library: Load back the full animation
        mutils.loadAnims(
            [os.path.normpath(
                f'{options["studio_library_output_folder"]}/{options["namespace"]}_fullanim.anim'
            ), ], objects=cmds.sets(
                options['controllers_set'], query=True
            ), currentTime=False, option='replaceCompletely', namespaces=[options['namespace'], ]
        )

        cmds.playbackOptions(animationStartTime=cut_in, minTime=cut_in, animationEndTime=cut_out, maxTime=cut_out)

        # Move the current time to cut_in
        cmds.currentTime(cut_in)

        # Reset the selection
        cmds.select(original_selection, replace=True)

        return output_paths

    @common.error
    def apply_hip_pose(self):
        self._apply_hip_pose()
        common.show_message('Success', 'Hip pose applied successfully.', message_type='success')

    def _apply_hip_pose(self):
        try:
            import studiolibrary
            import mutils
        except ImportError as e:
            try:
                add_studio_library_to_path()
            except ImportError:
                raise e
            else:
                import studiolibrary
                import mutils

        sel = cmds.ls(selection=True)
        if not sel:
            raise RuntimeError('Please select a single object.')
        node = sel[0]

        cmds.select(clear=True)

        # make sure the selection is a transformable node (e.g. not a shape)
        if not cmds.listRelatives(node, shapes=True):
            raise RuntimeError('Please select a transformable node.')

        # Collect all the current settings to a dictionary
        self.statusChanged.emit('Working...', 'Validating options, please wait')

        options = {}
        for k in DEFAULT_VALUES:
            for _k, _v in DEFAULT_VALUES[k].items():
                options[_k] = self.settings.value(_k, _v['default'])

        config = tokens.get(*common.active('root', args=True))
        seq, shot = common.get_sequence_and_shot(common.active('asset'))

        db = database.get(*common.active('root', args=True))
        cut_in = db.value(common.active('asset', path=True), 'cut_in', database.AssetTable)
        cut_out = db.value(common.active('asset', path=True), 'cut_out', database.AssetTable)
        prefix = db.value(common.active('root', path=True), 'prefix', database.BookmarkTable)

        # --- Validate values ---
        if not all((seq, shot)):
            raise RuntimeError('Could not find sequence and shot names.')

        # Check if none of the values are None
        if any((x is None for x in (cut_in, cut_out, prefix))):
            raise RuntimeError('Not all required values are set: We need cut_in, cut_out or prefix to be set.')

        if cut_out <= cut_in:
            raise RuntimeError(f'Cut out is smaller than cut in: {cut_out} <= {cut_in}')

        # --- Validate the options ---

        # Get the default library from the Studio Library settings file
        options['studio_library_folder'] = get_studio_library_default_library()

        if not options['namespace']:
            raise RuntimeError('Please specify a namespace.')

        # studio_library_output_folder
        if not options['studio_library_output_folder']:
            raise RuntimeError('Please specify an output folder template.')

        _p = options['studio_library_folder'].replace('\\', '/')
        __p = options['studio_library_output_folder'].replace('\\', '/')
        __p = config.expand_tokens(
            __p,
            asset=common.active('asset'),
            shot=shot,
            sequence=seq,
            prefix=prefix.split('_')[-1].upper(),
        ).replace('\\', '/')
        options['studio_library_output_folder'] = f'{_p}/{__p}'

        # Delete the locator if it exists
        if cmds.objExists('nullLocator'):
            cmds.delete('nullLocator')

        locator = cmds.spaceLocator(name='nullLocator')[0]

        if not QtCore.QFileInfo(f'{options["studio_library_output_folder"]}/{options["namespace"]}_hip.anim').exists():
            raise RuntimeError(f'Could not find hip animation: {options["studio_library_output_folder"]}/{options["namespace"]}_hip.anim')

        self.statusChanged.emit('Working...', 'Importing animation...')

        # Load the hip animation onto the locator
        mutils.loadAnims(
            [os.path.normpath(
                f'{options["studio_library_output_folder"]}/{options["namespace"]}_hip.anim'
            ), ],
            objects=[locator,],
            currentTime=False,
            option='replaceCompletely'
        )

        # Move the current time to cut_in
        cmds.currentTime(cut_in)

        # Reset node transforms
        cmds.move(0, 0, 0, node, worldSpace=True)
        cmds.rotate(0, 0, 0, node, worldSpace=True)
        cmds.scale(1, 1, 1, node, worldSpace=True)

        # Parent constrain the selection to the locator
        cmds.parentConstraint(locator, node, maintainOffset=True)[0]
    def showEvent(self, event):
        super().showEvent(event)
        common.center_window(self)

    def sizeHint(self):
        return QtCore.QSize(common.size(common.size_width), common.size(common.size_height))


def run():
    global instance
    if instance:
        try:
            instance.close()
            instance.deleteLater()
            instance = None
        except:
            pass

    instance = ExportCharacterCachesDialog()
    instance.accepted.connect(lambda: common.source_model(common.FileTab).reset_data(force=True))
    actions.change_tab(common.FileTab)
    actions.set_task_folder(tokens.get_folder(tokens.CacheFolder))

    instance.open()
    instance.raise_()
