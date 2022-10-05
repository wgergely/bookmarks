"""Maya-specific methods and values.

"""
import re
import string
import sys
import time
import uuid

try:
    import maya.cmds as cmds
except ImportError:
    raise ImportError('Could not find the Maya modules.')

from PySide2 import QtWidgets, QtCore

from .. import common
from .. import database
from ..tokens import tokens

GEO_SUFFIX = 'export'
TEMP_NAMESPACE = f'Temp_{uuid.uuid4().hex}'

#: Maya frame-rate enum definitions
MAYA_FPS = {
    'hour': 2.777777777777778e-4,
    'min': 0.0166667,
    'sec': 1.0,
    'millisec': 1000.0,
    'game': 15.0,
    'film': 24.0,
    'pal': 25.0,
    'ntsc': 30.0,
    'show': 48.0,
    'palf': 50.0,
    'ntscf': 60.0,
    '2fps': 2.0,
    '3fps': 3.0,
    '4fps': 4.0,
    '5fps': 5.0,
    '6fps': 6.0,
    '8fps': 8.0,
    '10fps': 10.0,
    '12fps': 12.0,
    '16fps': 16.0,
    '20fps': 20.0,
    '40fps': 40.0,
    '75fps': 75.0,
    '100fps': 100.0,
    '120fps': 120.0,
    '200fps': 200.0,
    '240fps': 240.0,
    '250fps': 250.0,
    '300fps': 300.0,
    '400fps': 400.0,
    '500fps': 500.0,
    '600fps': 600.0,
    '750fps': 750.0,
    '1200fps': 1200.0,
    '1500fps': 1500.0,
    '2000fps': 2000.0,
    '3000fps': 3000.0,
    '6000fps': 6000.0,
    '23.976fps': 23.976,
    '29.97fps': 29.976,
    '29.97df': 29.976,
    '47.952fps': 47.952,
    '59.94fps': 59.94,
    '44100fps': 44100.0,
    '48000fps': 48000.0,
}

#: Default viewport display options
DisplayOptions = {
    "displayGradient": True,
    "background": (0.5, 0.5, 0.5),
    "backgroundTop": (0.6, 0.6, 0.6),
    "backgroundBottom": (0.4, 0.4, 0.4),
}

#: Default camera display options
CameraOptions = {
    "displayGateMask": False,
    "displayResolution": False,
    "displayFilmGate": False,
    "displayFieldChart": False,
    "displaySafeAction": False,
    "displaySafeTitle": False,
    "displayFilmPivot": False,
    "displayFilmOrigin": False,
    "overscan": 1.0,
    "depthOfField": False,
}

#: Default camera capture options
CaptureOptions = {
    "wireframeOnShaded": False,
    "displayAppearance": 'smoothShaded',
    "selectionHiliteDisplay": False,
    "headsUpDisplay": False,
    "imagePlane": False,
    "nurbsCurves": False,
    "nurbsSurfaces": False,
    "polymeshes": True,
    "subdivSurfaces": True,
    "planes": True,
    "cameras": False,
    "controlVertices": False,
    "lights": False,
    "grid": False,
    "hulls": False,
    "joints": False,
    "ikHandles": False,
    "deformers": False,
    "dynamics": False,
    "fluids": False,
    "hairSystems": False,
    "follicles": False,
    "nCloths": False,
    "nParticles": False,
    "nRigids": False,
    "dynamicConstraints": False,
    "locators": False,
    "manipulators": False,
    "dimensions": False,
    "handles": False,
    "pivots": False,
    "strokes": False,
    "motionTrails": False
}

#: Default frame padding
DefaultPadding = 4

#: Default cache export path template
CACHE_PATH = '{workspace}/{export_dir}/{set}/{set}.{ext}'

#: Default cache directory template
DEFAULT_CACHE_DIR = '{export_dir}/{ext}'

#: Viewport capture direction name
DEFAULT_CAPTURE_DIR = 'capture'

#: Default cache destination template
CACHE_LAYER_PATH = '{workspace}/{export_dir}/{set}/{set}_{layer}.{ext}'

#: Default capture destination path template
CAPTURE_DESTINATION = '{workspace}/{capture_folder}/{scene}/{scene}'

#: Default capture file path template
CAPTURE_FILE = '{workspace}/{capture_folder}/{scene}/{scene}.{frame}.{ext}'
#: Default capture agnostic publish path template
CAPTURE_PUBLISH_DIR = '{workspace}/{capture_folder}/latest'
#: Default capture agnostic publish file name template
AGNOSTIC_CAPTURE_FILE = '{workspace}/{capture_folder}/latest/{asset}_capture_{' \
                        'frame}.{ext}'

#: Workspace file format rules
EXPORT_FILE_RULES = {
    'Alembic': 'abc',
    'alembicimport': 'abc',
    'alembicexport': 'abc',
    'alembicCache': 'abc',
    'alembic import': 'abc',
    'alembic export': 'abc',
    'assexport': 'ass',
    'ass export': 'ass',
    'ass import': 'ass',
    'OBJ': 'obj',
    'objimport': 'obj',
    'obj import': 'obj',
    'objexport': 'obj',
    'OBJexport': 'obj',
    'obj export': 'obj',
    'fbxexport': 'fbx',
    'fbx export': 'fbx',
    'fbximport': 'fbx',
    'fbx import': 'fbx',
    'Arnold-USD': 'usd',
    'USD Import': 'usd',
    'USD Export': 'usd',
}

#: Default render template
RENDER_NAME_TEMPLATE = '<RenderLayer>/<Version>/<RenderPass>/<RenderLayer>_' \
                       '<RenderPass>_<Version>'

SUFFIX_LABEL = 'Select a suffix for this import.\n\n\
Suffixes are always unique and help differentiate imports when the same file \
is imported multiple times.'

# The list of database tables and column containing relevant properties
DB_KEYS = {
    database.BookmarkTable: (
        'width',
        'height',
        'framerate',
        'startframe',
        'duration'
    ),
    database.AssetTable: (
        'cut_duration',
        'cut_out',
        'cut_in'
    ),
}


def patch_workspace_file_rules():
    """Patches the current maya workspace to use the directories defined in the
    active bookmark item's token configuration.

    """
    for rule, ext in EXPORT_FILE_RULES.items():
        v = DEFAULT_CACHE_DIR.format(
            export_dir=tokens.get_folder(tokens.CacheFolder),
            ext=tokens.get_subfolder(tokens.CacheFolder, ext)
        )
        cmds.workspace(fr=(rule, v))

    cmds.workspace(fr=('scene', tokens.get_folder(tokens.SceneFolder)))
    cmds.workspace(fr=('sourceImages', tokens.get_folder(tokens.TextureFolder)))
    cmds.workspace(fr=('images', tokens.get_folder(tokens.RenderFolder)))

    cmds.workspace(fr=('timeEditor', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('renderData', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('translatorData', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('sceneAssembly', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('diskCache', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('diskCache', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('fluidCache', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('offlineEdit', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('furShadowMap', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('shaders', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('furFiles', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('furEqualMap', tokens.get_folder(tokens.DataFolder)))
    cmds.workspace(fr=('movie', tokens.get_folder(tokens.DataFolder)))


def set_startframe(frame):
    """Sets the scene's animation start time.

    Args:
        frame (int): The start frame.

    """
    if not isinstance(frame, int):
        frame = int(round(frame, 0))

    # Set the current timeline to `frame`
    cmds.playbackOptions(animationStartTime=frame)
    cmds.playbackOptions(minTime=frame)

    # Set the render start frame to `frame`
    cmds.setAttr('defaultRenderGlobals.startFrame', frame)

    # Make sure the current frame is not outside our range
    current_frame = round(cmds.currentTime(query=True))
    if current_frame <= frame:
        cmds.currentTime(frame, edit=True)
    else:
        cmds.currentTime(current_frame, edit=True)


def set_endframe(frame):
    """Sets the scene's animation end time.

    Args:
        frame (int): The end frame.

    """
    if not isinstance(frame, int):
        frame = int(round(frame, 0))

    # Set the current timeline to `frame`
    cmds.playbackOptions(animationEndTime=frame)
    cmds.playbackOptions(maxTime=frame)

    # Set the render start frame to `frame`
    cmds.setAttr('defaultRenderGlobals.endFrame', frame)

    # Make sure the current frame is not outside our range
    current_frame = round(cmds.currentTime(query=True))
    if current_frame >= frame:
        cmds.currentTime(frame, edit=True)
    else:
        cmds.currentTime(current_frame, edit=True)


def apply_default_render_values():
    """Sets the default render values for the current scene.

    """
    cmds.setAttr('perspShape.renderable', 0)

    # Enable versioned outputs
    cmds.setAttr(
        'defaultRenderGlobals.imageFilePrefix',
        RENDER_NAME_TEMPLATE,
        type='string'
    )
    if not cmds.getAttr('defaultRenderGlobals.renderVersion'):
        cmds.setAttr(
            'defaultRenderGlobals.renderVersion',
            'v001',
            type='string',
        )

    cmds.setAttr('defaultRenderGlobals.extensionPadding', 4)
    cmds.setAttr('defaultRenderGlobals.animation', 1)
    cmds.setAttr('defaultRenderGlobals.putFrameBeforeExt', 1)
    cmds.setAttr('defaultRenderGlobals.periodInExt', 2)
    cmds.setAttr('defaultRenderGlobals.useFrameExt', 0)
    cmds.setAttr('defaultRenderGlobals.outFormatControl', 0)
    cmds.setAttr('defaultRenderGlobals.imageFormat', 8)

    # Mostly because of After Effects
    try:
        cmds.setAttr('defaultArnoldDriver.mergeAOVs', 0)
    except:
        pass


def set_render_resolution(width, height):
    """Sets the render resolution of the current scene.

    """
    cmds.setAttr('defaultResolution.width', width)
    cmds.setAttr('defaultResolution.height', height)


def set_framerate(fps):
    """Sets the frame-rate speed of the current scene.

    """
    if not isinstance(fps, float):
        fps = float(fps)

    # Make sure the proposed fps is a valid Maya value
    if fps not in MAYA_FPS.values():
        raise ValueError('Invalid framerate')

    data = {
        'animationStartTime': None,
        'minTime': None,
        'animationEndTime': None,
        'maxTime': None,
    }

    # Store current values
    for k in data:
        data[k] = cmds.playbackOptions(**{k: True, 'query': True})

    # Set the frame range
    for k, v in MAYA_FPS.items():
        if fps == v:
            cmds.currentUnit(time=k)
            break

    # Reapply original values
    for k, v in data.items():
        cmds.playbackOptions(**{k: v})


def get_framerate():
    """Returns the value of the current frame-rate enum.

    """
    return MAYA_FPS[cmds.currentUnit(query=True, time=True)]


def find_project_folder(key):
    """Return the relative path of a project folder.

    Args:
        key (str): The name of a Maya project folder name, e.g. 'sourceImages'.

    Return:
        str: The name of the folder that corresponds with `key`.

    """
    if not key:
        raise ValueError('Key must be specified.')

    _file_rules = cmds.workspace(
        fr=True,
        query=True,
    )

    file_rules = {}
    for n, _ in enumerate(_file_rules):
        m = n % 2
        k = _file_rules[n - m].lower()
        if m == 0:
            file_rules[k] = None
        if m == 1:
            file_rules[k] = _file_rules[n]

    key = key.lower()
    if key in file_rules:
        return file_rules[key]
    return key


def _get_available_suffixes(basename):
    """Checks for already used suffixes in the current scene and returns a list
    of available ones.

    """
    alphabet = string.ascii_uppercase
    transforms = cmds.ls(transforms=True)
    for s in transforms:
        if basename not in s:
            continue
        if not cmds.attributeQuery('instance_suffix', node=s, exists=True):
            continue
        suffix = cmds.getAttr(f'{s}.instance_suffix')
        alphabet = alphabet.replace(string.ascii_uppercase[suffix], '')
    return alphabet


def _add_suffix_attribute(rfn, suffix, reference=True):
    """Adds a custom attribute to the imported scene.

    """
    _id = string.ascii_uppercase.index(suffix)

    if reference:
        nodes = cmds.referenceQuery(rfn, nodes=True)
    else:
        nodes = cmds.namespaceInfo(rfn, listNamespace=True)

    for node in nodes:
        # Conflict of duplicate name would prevent import... this is a hackish,
        # yikes, workaround!
        try:
            _node = cmds.ls(node, long=True)[0]

            if cmds.nodeType(_node) != 'transform':
                continue
            if cmds.listRelatives(_node, parent=True) is None:
                if cmds.attributeQuery('instance_suffix', node=node, exists=True):
                    continue
                cmds.addAttr(
                    _node, ln='instance_suffix', at='enum',
                    en=':'.join(string.ascii_uppercase)
                )
                cmds.setAttr('{}.instance_suffix'.format(_node), _id)
        except:
            print(f'Could not add attribute to {node}')


def is_scene_modified():
    """If the current scene was modified since the last save, the user will be
    prompted to save the scene.

    """
    if not cmds.file(q=True, modified=True):
        return

    mbox = QtWidgets.QMessageBox()
    mbox.setText(
        'Current scene has unsaved changes.'
    )
    mbox.setInformativeText('Do you want to save before continuing?')
    mbox.setStandardButtons(
        QtWidgets.QMessageBox.Save
        | QtWidgets.QMessageBox.No
        | QtWidgets.QMessageBox.Cancel
    )
    mbox.setDefaultButton(QtWidgets.QMessageBox.Save)
    result = mbox.exec_()

    if result == QtWidgets.QMessageBox.Cancel:
        return result
    elif result == QtWidgets.QMessageBox.Save:
        cmds.SaveScene()
        return result

    return result


def report_export_progress(start, current, end, start_time):
    """A litle progress report get some export feedback."""
    elapsed = time.time() - start_time
    elapsed = time.strftime('%H:%M.%Ssecs', time.localtime(elapsed))

    start = int(start)
    current = int(current)
    end = int(end)

    _current = current - start
    _end = end - start

    if _end < 1:
        progress = float(_current) * 100
    else:
        progress = float(_current) / float(_end) * 100

    progress = '[{}{}] {}%'.format(
        '#' * int(progress),
        ' ' * (100 - int(progress)),
        int(progress)
    )

    msg = '# Exporting frame {current} of {end}\n# {progress}\n# Elapsed: {' \
          'elapsed}\n'.format(
        current=current,
        end=end,
        progress=progress,
        elapsed=elapsed
    )
    sys.stdout.write(msg)


def _is_set_created_by_user(name):
    """From the good folks at cgsociety - filters the in-scene sets to return
    the user-created items only.

    https://forums.cgsociety.org/t/maya-mel-python-list-object-sets-visible-in
    -the-dag/1586067/2

    Returns:
        bool: True if the user created the set, otherwise False.

    """
    try:
        # We first test for plug-in object sets.
        apiNodeType = cmds.nodeType(name, api=True)
    except RuntimeError:
        return False

    if apiNodeType == "kPluginObjectSet":
        return True

    # We do not need to test is the object is a set, since that test
    # has already been done by the outliner
    try:
        nodeType = cmds.nodeType(name)
    except RuntimeError:
        return False

    # We do not want any rendering sets
    if nodeType == "shadingEngine":
        return False

    # if the object is not a set, return false
    if not (nodeType == "objectSet" or
            nodeType == "textureBakeSet" or
            nodeType == "vertexBakeSet" or
            nodeType == "character"):
        return False

    # We also do not want any sets with restrictions
    restrictionAttrs = ["verticesOnlySet", "edgesOnlySet",
                        "facetsOnlySet", "editPointsOnlySet",
                        "renderableOnlySet"]
    if any(
            cmds.getAttr(f'{name}.{attr}') for attr in
            restrictionAttrs
    ):
        return False

    # Do not show layers
    if cmds.getAttr(f'{name}.isLayer'):
        return False

    # Do not show bookmarks
    annotation = cmds.getAttr(f'{name}.annotation')
    if annotation == "bookmarkAnimCurves":
        return False

    return True


def sanitize_namespace(s):
    """Converts the input string so that it can be safely used as a file name.
    Any namespace will be enclosed in brackets and the ':' characters will be 
    replaced with underscores.
    
    Args:
        s (str): A string that contains namespace names.

    Returns:
        str: The sanitized string.

    """
    namespaces = {f.group(1) for f in re.finditer(r'([^/:|\\:]+):(?!/|\\)', s)}
    for ns in namespaces:
        s = s.replace(ns, f'({ns})')
    s = re.sub(r':+', ':', s)
    s = re.sub(rf'_{GEO_SUFFIX}', '', s)
    return re.sub(r'([)a-zA-Z0-9])(:)([(a-zA-Z0-9])', r'\1_\3', s)


def get_geo_sets():
    """The main function responsible for returning the user created object sets
    from the current Maya scene. There's an extra caveat: the set has to contain
    the word 'GEO_SUFFIX' to be considered valid.

    Returns:
        dict: A dict of set name / mesh list pairs.

    """
    sets_data = {}
    for s in sorted([k for k in cmds.ls(sets=True) if _is_set_created_by_user(k)]):
        # Filter sets based on their names
        if GEO_SUFFIX not in s:
            continue

        dag_set_members = cmds.listConnections(f'{s}.dagSetMembers')
        if not dag_set_members:
            continue

        # We can ignore this group is it does not contain any shapes
        members = [
            cmds.ls(f, long=True)[-1] for f in dag_set_members if
            cmds.listRelatives(f, shapes=True, fullPath=True)]
        if not members:
            continue

        sets_data[s] = members

    return sets_data


def capture_viewport_destination():
    """Returns a tuple of destination parameters.

    """
    # Note that CAPTURE_DESTINATION does not actually refer to the full filename
    # the padded frame numbers and the extensions are added to the base name
    # by `capture.py`
    workspace = cmds.workspace(q=True, rootDirectory=True).rstrip('/')
    scene = QtCore.QFileInfo(cmds.file(q=True, expandName=True))
    dest = CAPTURE_DESTINATION.format(
        workspace=workspace,
        capture_folder=DEFAULT_CAPTURE_DIR,
        scene=scene.baseName()
    )
    return DEFAULT_CAPTURE_DIR, workspace, dest


class MayaProperties(object):
    """Utility class used to interface with values stored in the bookmark item's database.

    """

    def __init__(self, parent=None):
        super().__init__()

        server = common.active('server')
        job = common.active('job')
        root = common.active('root')
        asset = common.active('asset')

        if not all((server, job, root, asset)):
            raise RuntimeError('Could not find active asset.')

        self.data = {}

        self.init_data(server, job, root, asset)

    def init_data(self, server, job, root, asset):
        """Initializes the maya properties instance.

        """
        # Bookmark properties
        db = database.get_db(server, job, root)
        for k in DB_KEYS[database.BookmarkTable]:
            self.data[k] = db.value(
                db.source(),
                k,
                database.BookmarkTable
            )
        for k in DB_KEYS[database.AssetTable]:
            self.data[k] = db.value(
                db.source(asset),
                k,
                database.AssetTable
            )

    @property
    def framerate(self):
        """A current frame-rate value.

        """
        v = self.data['framerate']
        if isinstance(v, (float, int)) and float(v) in MAYA_FPS.values():
            return v
        return get_framerate()

    @property
    def startframe(self):
        """A current start-frame value.

        """
        # If the asset has an explicit in frame, we'll use that
        v = self.data['cut_in']
        if isinstance(v, (float, int)):
            return v

        # Otherwise, we'll use the default bookmark frame
        v = self.data['startframe']
        if isinstance(v, (float, int)):
            return v

        return cmds.playbackOptions(animationStartTime=True, query=True)

    @property
    def endframe(self):
        """A current end-frame value.

        If the asset has an explicit out frame set that is bigger than the start
        frame we'll use that value instead.

        """
        v = self.data['cut_out']
        if isinstance(v, (float, int)):
            if v > self.startframe:
                return v

        # If the asset has an explicit duration set we'll use that value
        v = self.data['cut_duration']
        if isinstance(v, (float, int)):
            return self.startframe + v

        # Otherwise, we'll use the default bookmark duration
        # If the asset has an explicit duration we'll use that value
        v = self.data['duration']
        if isinstance(v, (float, int)):
            return self.startframe + v

        return cmds.playbackOptions(animationEndTime=True, query=True)

    @property
    def width(self):
        """A current width value.

        """
        v = self.data['width']
        if isinstance(v, (float, int)):
            return v
        return cmds.getAttr('defaultResolution.width')

    @property
    def height(self):
        """A current height value.

        """
        v = self.data['height']
        if isinstance(v, (float, int)):
            return v
        return cmds.getAttr('defaultResolution.height')

    def get_info(self):
        """Returns an informative text about the current Maya properties.

        """
        duration = self.endframe - self.startframe
        info = 'Resolution:  {w}{h}\nFrame-rate:  {fps}\nCut:  {start}{' \
               'duration}'.format(
            w='{}'.format(int(self.width)) if (
                    self.width and self.height) else '',
            h='x{}px'.format(int(self.height)) if (
                    self.width and self.height) else '',
            fps='{}fps'.format(
                self.framerate
            ) if self.framerate else '',
            start='{}'.format(
                int(self.startframe)
            ) if self.startframe else '',
            duration='-{} ({} frames)'.format(
                int(self.startframe) + int(duration),
                int(duration) if duration else ''
            ) if duration else ''
        )
        return info
