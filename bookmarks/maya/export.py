"""Maya cache export classes and functions.

"""
import functools
import time

from PySide2 import QtCore, QtWidgets

try:
    from maya import cmds
except ImportError:
    raise ImportError('Could not find the Maya modules.')

from . import base as mayabase
from .. import common
from .. import log
from .. import ui
from ..editor import base
from ..tokens import tokens


def close():
    """Close :class:`ExportWidget`.

    """
    if common.maya_export_widget is None:
        return
    try:
        common.maya_export_widget.close()
        common.maya_export_widget.deleteLater()
    except:
        log.error('Could not close the editor')
    common.maya_export_widget = None


def show():
    """Shows :class:`ExportWidget`.

    """
    close()
    common.maya_export_widget = ExportWidget()
    common.maya_export_widget.open()
    return common.maya_export_widget


#: Maya cache export presets
PRESETS = {
    'alembic': {
        'name': 'Alembic',
        'extension': 'abc',
        'plugins': ('AbcExport.mll', 'matrixNodes.mll'),
        'action': 'export_alembic',
        'ogs_pause': True,
    },
    'ass': {
        'name': 'Arnold ASS',
        'extension': 'ass',
        'plugins': ('mtoa.mll',),
        'action': 'export_ass',
        'ogs_pause': True,
    },
    'obj': {
        'name': 'OBJ',
        'extension': 'obj',
        'plugins': ('objExport.mll',),
        'action': 'export_obj',
        'ogs_pause': True,
    },
    'ma': {
        'name': 'Maya Scene',
        'extension': 'ma',
        'plugins': (),
        'action': 'export_maya',
        'ogs_pause': False,
    },
}


class SetsComboBox(QtWidgets.QComboBox):
    """Export set picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        self.blockSignals(True)
        for k, v in mayabase.get_geo_sets().items():
            self.addItem(k, userData=v)
        self.blockSignals(False)


class TypeComboBox(QtWidgets.QComboBox):
    """Export type picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        self.blockSignals(True)
        for k, v in PRESETS.items():
            self.addItem(v['name'], userData=k)
        self.blockSignals(False)


class VersionsComboBox(QtWidgets.QComboBox):
    """Version number picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        self.blockSignals(True)
        self.addItem('No Version', userData=None)
        for v in [f'v{str(n).zfill(3)}' for n in range(1, 1000)]:
            self.addItem(v, userData=v)
        self.blockSignals(False)


#: UI layout definition
SECTIONS = {
    0: {
        'name': 'Export',
        'icon': '',
        'color': common.color(common.color_dark_background),
        'groups': {
            0: {
                0: {
                    'name': 'Select Set',
                    'key': 'maya_export/set',
                    'validator': None,
                    'widget': SetsComboBox,
                    'placeholder': None,
                    'description': 'Select the set to export.',
                    'help': 'Select the set to export. If your set is not listed '
                            'above make sure its name ends with <span '
                            f'style="color:white">\"_'
                            f'{mayabase.GEO_SUFFIX}\"</span>, '
                            'otherwise it won\'t be listed.'
                },
            },
            1: {
                0: {
                    'name': 'Export Type',
                    'key': 'maya_export/type',
                    'validator': None,
                    'widget': TypeComboBox,
                    'placeholder': None,
                    'description': 'Select the export format.',
                },
                1: {
                    'name': 'Timeline',
                    'key': 'maya_export/timeline',
                    'validator': None,
                    'widget': functools.partial(
                        QtWidgets.QCheckBox, 'Export Timeline'
                    ),
                    'placeholder': 'Tick if you want to export the whole timeline, '
                                   'or just the current frame.',
                    'description': 'Tick if you want to export the whole timeline, '
                                   'or just the current frame.',
                },
            },
            2: {
                0: {
                    'name': 'Version',
                    'key': None,
                    'validator': None,
                    'widget': VersionsComboBox,
                    'placeholder': None,
                    'description': 'Select export version.',
                    'help': 'Versioned exports have an additional <span '
                            'style="color:white">"_v001"</span> prepended to their '
                            'name that will be incremented every subsequent '
                            're-export.'

                },
            },
            3: {
                0: {
                    'name': 'Reveal',
                    'key': 'maya_export/reveal',
                    'validator': None,
                    'widget': functools.partial(
                        QtWidgets.QCheckBox, 'Reveal after export'
                    ),
                    'placeholder': None,
                    'description': 'Reveal after export',
                },
                1: {
                    'name': 'Keep Open',
                    'key': 'maya_export/keep_open',
                    'validator': None,
                    'widget': functools.partial(
                        QtWidgets.QCheckBox, 'Keep window open'
                    ),
                    'placeholder': None,
                    'description': 'Keep the window open after export',
                },
            },
        },
    },
}


class ExportWidget(base.BasePropertyEditor):
    """The widget used to start an export process.

    """

    def __init__(self, parent=None):
        super().__init__(
            SECTIONS,
            None,
            None,
            None,
            fallback_thumb='file',
            hide_thumbnail_editor=True,
            buttons=('Export', 'Close'),
            parent=parent
        )

        self.progress_widget = None

        self._interrupt_requested = False
        self.setWindowTitle('Export Sets')
        self._connect_settings_save_signals(common.SECTIONS['maya_export'])

    def init_progress_bar(self):
        """Initializes the export progress bar.

        """
        self.progress_widget = QtWidgets.QProgressDialog(parent=self)
        self.progress_widget.setFixedWidth(common.size(common.size_width))
        self.progress_widget.setLabelText('Exporting, please wait...')
        self.progress_widget.setWindowTitle('Export Progress')

    @common.error
    @common.debug
    def init_data(self):
        """Initializes data.

        """
        self.maya_export_set_editor.currentIndexChanged.connect(
            self.check_version
        )
        self.maya_export_type_editor.currentIndexChanged.connect(
            self.check_version
        )
        self.version_editor.currentIndexChanged.connect(
            self.check_version
        )

        self.load_saved_user_settings(common.SECTIONS['maya_export'])
        self.check_version()

    @QtCore.Slot()
    def check_version(self, *args, **kwargs):
        """Verify export item version.

        """
        if self.version_editor.currentData() is None:
            return

        self.version_editor.blockSignals(True)
        self.version_editor.setCurrentIndex(1)
        while QtCore.QFileInfo(self.db_source()).exists():
            self.version_editor.setCurrentIndex(
                self.version_editor.currentIndex() + 1
            )
        self.version_editor.blockSignals(False)

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        self._interrupt_requested = False

        items = self.maya_export_set_editor.currentData()
        _k = self.maya_export_set_editor.currentText()
        if not items:
            raise RuntimeError(f'{_k} is empty.')

        file_path = self.db_source()
        if not self.db_source():
            raise RuntimeError('The output path is not set.')

        file_info = QtCore.QFileInfo(file_path)

        # Let's make sure destination folder exists
        _dir = file_info.dir()
        if not _dir.exists():
            if not _dir.mkpath('.'):
                raise OSError(f'Could not create {_dir.path()}')
        if not _dir.isReadable():
            raise OSError(f'{_dir.path()} is not readable')

        if file_info.exists():
            mbox = ui.MessageBox(
                f'{file_info.fileName()} already exists.',
                'Are you sure you want to overwrite it?',
                buttons=[ui.YesButton, ui.NoButton]
            )
            if mbox.exec_() == QtWidgets.QDialog.Rejected:
                return
            if not QtCore.QFile(file_path).remove():
                raise RuntimeError(f'Could not remove {file_info.fileName()}.')

        # Frame range
        if self.maya_export_timeline_editor.isChecked():
            start = cmds.playbackOptions(query=True, animationStartTime=True)
            end = cmds.playbackOptions(query=True, animationEndTime=True)
        else:
            start = cmds.currentTime(query=True)
            end = cmds.currentTime(query=True)

        # Plugin
        k = self.maya_export_type_editor.currentData()
        if not k:
            raise RuntimeError('Must select an export type.')

        if PRESETS[k]['plugins']:
            for plugin in PRESETS[k]['plugins']:
                if not cmds.pluginInfo(plugin, loaded=True, q=True):
                    cmds.loadPlugin(plugin, quiet=True)

        state = cmds.ogs(pause=True, query=True)
        if PRESETS[k]['ogs_pause'] and not state:
            cmds.ogs(pause=True)

        try:
            sel = cmds.ls(selection=True)
            t = cmds.currentTime(query=True)

            self.init_progress_bar()
            self.progress_widget.setMinimum(int(start))
            self.progress_widget.setMaximum(int(end))
            self.progress_widget.setRange(int(start), int(end))
            self.progress_widget.open()

            action = getattr(self, PRESETS[k]['action'])
            action(file_path, items, int(start), int(end))
            common.signals.fileAdded.emit(file_path)

            if self.maya_export_reveal_editor.isChecked():
                from .. import actions
                actions.reveal(file_path)
            if not self.maya_export_keep_open_editor.isChecked():
                self.close()
        except:
            raise
        finally:
            self.progress_widget.close()
            cmds.currentTime(t, edit=True)
            cmds.select(clear=True)
            cmds.select(sel, replace=True)
            if PRESETS[k]['ogs_pause'] and not state:
                cmds.ogs(pause=True)
            self.check_version()

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        k = self.maya_export_type_editor.currentData()
        ext = PRESETS[k]['extension']

        workspace = cmds.workspace(q=True, fn=True)
        if not workspace:
            return None

        set_name = self.maya_export_set_editor.currentText()
        if not set_name:
            return None

        export_dir = mayabase.DEFAULT_CACHE_DIR.format(
            export_dir=tokens.get_folder(tokens.CacheFolder),
            ext=tokens.get_subfolder(tokens.CacheFolder, ext)
        )
        file_path = mayabase.CACHE_PATH.format(
            workspace=workspace,
            export_dir=export_dir,
            set=set_name,
            ext=ext
        )
        file_path = mayabase.sanitize_namespace(file_path)

        file_info = QtCore.QFileInfo(file_path)
        if self.version_editor.currentData():
            version = self.version_editor.currentText()
            file_path = '{dir}/{basename}_{version}.{ext}'.format(
                dir=file_info.dir().path(),
                basename=file_info.completeBaseName(),
                version=version,
                ext=file_info.suffix()
            )
        return file_path

    def keyPressEvent(self, event):
        """Key press event handler.

        """
        if event.key() == QtCore.Qt.Key_Escape:
            self._interrupt_requested = True

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width) * 0.66,
            common.size(common.size_height * 1.2)
        )

    def export_maya(
            self, destination, outliner_set, start_frame, end_frame, step=1.0
    ):
        """Main Maya scene export function.

        Args:
            start_frame (int): Start frame.
            end_frame (int): End frame.
            destination (str): Path to the output file.
            outliner_set (tuple): A list of transforms contained in a geometry set.
            step (float): Frame step.

        """
        common.check_type(destination, str)
        common.check_type(outliner_set, (tuple, list))
        common.check_type(start_frame, (int, float))
        common.check_type(end_frame, (int, float))
        common.check_type(step, (float, int))

        _destination = str(destination)

        cmds.select(outliner_set, replace=True)

        cmds.file(
            _destination,
            force=True,
            preserveReferences=True,
            type='mayaAscii',
            exportSelected=True,
            options="v=0;"
        )

    def export_alembic(
            self, destination, outliner_set, start_frame, end_frame, step=1.0
    ):
        """Main alembic export function.

        Only shapes, normals and uvs are exported by this implementation. The list
        of shapes contained in the `outliner_set` will be rebuilt in the root of
        the scene to avoid parenting issues.

        Args:
            start_frame (int): Start frame.
            end_frame (int): End frame.
            destination (str): Path to the output file.
            outliner_set (tuple): A list of transforms contained in a geometry set.
            step (int, float): Frame step.

        """
        common.check_type(destination, str)
        common.check_type(outliner_set, (tuple, list))
        common.check_type(start_frame, (int, float))
        common.check_type(end_frame, (int, float))
        common.check_type(step, (float, int))

        def _is_intermediate(s):
            return cmds.getAttr(f'{s}.intermediateObject')

        def teardown():
            """We will delete the previously created namespace and the objects
            contained inside. I wrapped the call into an evalDeferred to let maya
            recover after the export and delete the objects more safely.

            """

            def _teardown():
                cmds.namespace(
                    removeNamespace=mayabase.TEMP_NAMESPACE,
                    deleteNamespaceContent=True
                )

            cmds.evalDeferred(_teardown)

        # We'll need to use the DecomposeMatrix Nodes, let's check if the plugin
        # is loaded and ready to use

        world_shapes = []
        valid_shapes = []

        # First, we will collect the available shapes from the given set
        for item in outliner_set:
            shapes = cmds.listRelatives(item, fullPath=True)
            for shape in shapes:
                if _is_intermediate(shape):
                    continue

                basename = shape.split('|')[-1]
                try:
                    # AbcExport will fail if a transform or a shape node's name is
                    # not unique. This was suggested on a forum - listing the
                    # relatives for an object without a unique name should raise a
                    # ValueError
                    cmds.listRelatives(basename)
                except ValueError as err:
                    s = f'"{shape}" does not have a unique name. This is not ' \
                        f'usually allowed for alembic exports and might cause the ' \
                        f'export to fail.'
                    log.error(s)

                # Camera's don't have mesh nodes, but we still want to export them!
                if cmds.nodeType(shape) != 'camera':
                    if not cmds.attributeQuery('outMesh', node=shape, exists=True):
                        continue
                valid_shapes.append(shape)

        if not valid_shapes:
            nodes = '", "'.join(outliner_set)
            raise RuntimeError(
                f'Could not find any nodes to export in the set. The set contains:\n'
                f'"{nodes}"'
            )

        cmds.select(clear=True)

        # Creating a temporary namespace to avoid name-clashes later when we
        # duplicate the meshes. We will delete this namespace, and it's contents
        # after the export
        if cmds.namespace(exists=mayabase.TEMP_NAMESPACE):
            cmds.namespace(
                removeNamespace=mayabase.TEMP_NAMESPACE,
                deleteNamespaceContent=True
            )
        cmds.namespace(add=mayabase.TEMP_NAMESPACE)
        ns = mayabase.TEMP_NAMESPACE

        world_transforms = []

        try:
            # For meshes, we will create an empty mesh node and connect the
            # outMesh and UV attributes from our source. We will also apply the
            # source mesh's transform matrix to the newly created mesh
            for shape in valid_shapes:
                basename = shape.split('|').pop()
                if cmds.nodeType(shape) != 'camera':
                    # Create new empty shape node
                    world_shape = cmds.createNode('mesh', name=f'{ns}:{basename}')

                    # outMesh -> inMesh
                    cmds.connectAttr(
                        f'{shape}.outMesh',
                        f'{world_shape}.inMesh',
                        force=True
                    )
                    # uvSet -> uvSet
                    cmds.connectAttr(
                        f'{shape}.uvSet',
                        f'{world_shape}.uvSet',
                        force=True
                    )

                    # worldMatrix -> transform
                    decompose_matrix = cmds.createNode(
                        'decomposeMatrix',
                        name=f'{ns}:decomposeMatrix#'
                    )
                    cmds.connectAttr(
                        f'{shape}.worldMatrix[0]',
                        f'{decompose_matrix}.inputMatrix',
                        force=True
                    )

                    transform = cmds.listRelatives(
                        world_shape,
                        fullPath=True,
                        type='transform',
                        parent=True
                    )[0]
                    world_transforms.append(transform)

                    cmds.connectAttr(
                        f'{decompose_matrix}.outputTranslate',
                        f'{transform}.translate',
                        force=True
                    )
                    cmds.connectAttr(
                        f'{decompose_matrix}.outputRotate',
                        f'{transform}.rotate',
                        force=True
                    )
                    cmds.connectAttr(
                        f'{decompose_matrix}.outputScale',
                        f'{transform}.scale',
                        force=True
                    )
                else:
                    world_shape = shape
                    world_transforms.append(
                        cmds.listRelatives(
                            world_shape,
                            fullPath=True,
                            type='transform',
                            parent=True
                        )[0]
                    )
                world_shapes.append(world_shape)
        except:
            teardown()
            raise RuntimeError('Failed to prepare scene.')

        try:
            # Our custom progress callback
            perframecallback = f'"from bookmarks.maya import base;' \
                               f'base.report_export_progress(' \
                               f'{start_frame}, #FRAME#, {end_frame}, ' \
                               f'{time.time()})"'

            # Build the export command
            cmd = '{f} {fr} {s} {uv} {ws} {wv} {wuvs} {wcs} {wfs} {sn} {rt} {df} {pfc} {ro}'
            cmd = cmd.format(
                f=f'-file "{destination}"',
                fr=f'-framerange {start_frame} {end_frame}',
                s=f'-step {step}',
                uv='-uvWrite',
                ws='-worldSpace',
                wv='-writeVisibility',
                # eu='-eulerFilter',
                wuvs='-writeuvsets',
                wcs='-writeColorSets',
                wfs='-writeFaceSets',
                sn='-stripNamespaces',
                rt=f'-root {" -root ".join(world_transforms)}',
                df='-dataFormat ogawa',
                pfc=f'-pythonperframecallback {perframecallback}',
                ro='-renderableOnly'
            )
            s = f'Alembic Export Job Arguments:\n{cmd}'
            log.success(s)
            cmds.AbcExport(jobArg=cmd)
            log.success(f'{destination} exported successfully.')
        except Exception:
            log.error('The alembic export failed.')
            raise
        finally:
            teardown()

    def export_ass(
            self, destination, outliner_set, start_frame, end_frame, step=1.0
    ):
        """Main Arnold ASS export function.

        Args:
            start_frame (int): Start frame.
            end_frame (int): End frame.
            destination (str): Path to the output file.
            outliner_set (tuple): A list of transforms contained in a geometry set.
            step (float, int): Frame step.

        """
        common.check_type(destination, str)
        common.check_type(outliner_set, (tuple, list))
        common.check_type(start_frame, (int, float))
        common.check_type(end_frame, (int, float))
        common.check_type(step, (float, int))

        try:
            import arnold
        except ImportError:
            raise ImportError('Could not find arnold.')

        # Let's get the first renderable camera. This is a bit of a leap of faith but
        # ideally there's only one renderable camera in the scene.
        cams = cmds.ls(cameras=True)
        cam = None
        for cam in cams:
            if cmds.getAttr(f'{cam}.renderable'):
                break

        cmds.select(outliner_set, replace=True)

        ext = destination.split('.')[-1]
        _destination = str(destination)
        start_time = time.time()

        for fr in range(start_frame, end_frame + 1):
            QtWidgets.QApplication.instance().processEvents()
            if self._interrupt_requested:
                self._interrupt_requested = False
                return

            cmds.currentTime(fr, edit=True)
            if self.progress_widget.wasCanceled():
                return
            else:
                self.progress_widget.setValue(fr)

            if not start_frame == end_frame:
                # Create a mock version, if it does not exist
                open(destination, 'a').close()
                _destination = destination.replace(f'.{ext}', '')
                _destination += '_'
                _destination += str(fr).zfill(mayabase.DefaultPadding)
                _destination += '.'
                _destination += ext

            cmds.arnoldExportAss(
                f=_destination,
                cam=cam,
                s=True,  # selected
                mask=arnold.AI_NODE_CAMERA |
                     arnold.AI_NODE_SHAPE |
                     arnold.AI_NODE_SHADER |
                     arnold.AI_NODE_OVERRIDE |
                     arnold.AI_NODE_LIGHT
            )

            mayabase.report_export_progress(start_frame, fr, end_frame, start_time)

    def export_obj(
            self, destination, outliner_set, start_frame, end_frame, step=1.0
    ):
        """Main obj export function.

        Args:
            start_frame (int): Start frame.
            end_frame (int): End frame.
            destination (str): Path to the output file.
            outliner_set (tuple): A list of transforms contained in a geometry set.
            step (float, int): Frame step.

        """
        common.check_type(destination, str)
        common.check_type(outliner_set, (tuple, list))
        common.check_type(start_frame, (int, float))
        common.check_type(end_frame, (int, float))
        common.check_type(step, (float, int))

        ext = destination.split('.')[-1]
        _destination = str(destination)
        start_time = time.time()

        cmds.select(outliner_set, replace=True)

        for fr in range(start_frame, end_frame + 1):
            QtWidgets.QApplication.instance().processEvents()
            if self._interrupt_requested:
                self._interrupt_requested = False
                return

            cmds.currentTime(fr, edit=True)
            if self.progress_widget.wasCanceled():
                return
            else:
                self.progress_widget.setValue(fr)

            if not start_frame == end_frame:
                # Create a mock version, if it does not exist
                open(destination, 'a').close()
                _destination = destination.replace(f'.{ext}', '')
                _destination += '_'
                _destination += str(fr).zfill(mayabase.DefaultPadding)
                _destination += '.'
                _destination += ext

            if (
                    QtCore.QFileInfo(_destination).exists() and
                    not QtCore.QFile(_destination).remove()
            ):
                raise RuntimeError(f'Failed to remove {_destination}')

            cmds.file(
                _destination,
                preserveReferences=True,
                type='OBJexport',
                exportSelected=True,
                options='groups=1;ptgroups=1;materials=1;smoothing=1; normals=1'
            )

            mayabase.report_export_progress(start_frame, fr, end_frame, start_time)
