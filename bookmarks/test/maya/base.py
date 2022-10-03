#!mayapy
"""Maya module testing base methods."""
import os
import sys

import maya.cmds
import maya.mel
import maya.standalone
from PySide2 import QtCore

k = 'BOOKMARKS_ROOT'

path = __file__ + os.pardir.join([os.path.sep, ] * 5)
path = os.path.normpath(path)
assert (os.path.isdir(path))

plugin = __file__ + os.pardir.join(
    [os.path.sep, ] * 4) + os.path.sep + 'maya' + os.path.sep + 'plugin.py'
plugin = os.path.normpath(plugin)
assert os.path.isfile(plugin)


def init_environment():
    sys.path.insert(0, path)

    if k not in os.environ:
        raise EnvironmentError(
            'Is Bookmarks installed? Could not find BOOKMARKS_ROOT environment variable')

    shared = os.environ[k] + os.path.sep + 'shared'
    sys.path.insert(1, shared)
    paths = os.environ['PATH'].split(';')
    _bin = os.environ[k] + os.path.sep + 'bin'
    paths.insert(0, _bin)
    os.environ['PATH'] = ';'.join(paths)


def init_maya_standalone():
    maya.standalone.initialize(name='python')
    maya.mel.eval('')

    maya.cmds.playbackOptions(minTime=1.0)
    maya.cmds.playbackOptions(animationStartTime=1.0)
    maya.cmds.playbackOptions(maxTime=10.0)
    maya.cmds.playbackOptions(animationEndTime=10.0)

    meshes = []
    for _ in range(10):
        s = maya.cmds.polyCube(name='testMesh#')
        meshes.append(s[0])
    maya.cmds.sets(meshes, name='testMesh_geo_set')
    maya.cmds.sets([], name='emptyTestMesh_geo_set')


def load_plugin():
    if not os.path.isfile(plugin):
        raise RuntimeError('Could not find `plugin.py`')

    name = 'BookmarksMayaPlugin'
    maya.cmds.loadPlugin(plugin, name=name)
    if maya.cmds.pluginInfo(name, query=True, loaded=True):
        print('{} loaded.'.format(name))


def unload_plugin():
    if not os.path.isfile(plugin):
        raise RuntimeError('Could not find `plugin.py`')

    name = 'BookmarksMayaPlugin'
    maya.cmds.unloadPlugin(name)
    if not maya.cmds.pluginInfo(name, query=True, loaded=True):
        print('{} unloaded.'.format(name))


def reload_plugin():
    unload_plugin()

    QtCore.QTimer.singleShot(3000, load_plugin)
    QtCore.QTimer.singleShot(6000, unload_plugin)


def verify_environ():
    if 'path' not in os.environ:
        raise RuntimeError('Path not found. Is this a supported OS?')

    # Let's find the Mayapy executable.
    # This has to be available to the path environment variable, otherwise,
    # we won't be able to execute our test

    b = None
    for path in os.environ['path'].split(';'):
        if not os.path.isdir(path):
            continue

        for f in os.listdir(path):
            if 'mayapy' in f.lower():
                b = os.path.normpath(path + os.path.sep + f)
                if not os.path.isfile(b):
                    raise RuntimeError('Invalid file')
                break
    if b is None:
        raise RuntimeError(
            'The mayapy executable was not found in the path. This should be added to the path befre running this script. The executable should be located in the $MAYA_ROOT/bin folder.')


def init():
    init_maya_standalone()
    load_plugin()
