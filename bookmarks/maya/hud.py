"""
This module contains functions for creating a HUD with information about the current environment and scene.

"""
import functools

try:
    from PySide6 import QtWidgets, QtGui, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore

from . import base
from .. import common

STATUS_HUD = 'HUD_bookmarks_status'


def remove():
    """Remove the HUD created by this module.

    """
    from maya import cmds
    for hud in cmds.headsUpDisplay(listHeadsUpDisplays=True):
        if 'bookmarks_' not in hud:
            continue
        cmds.headsUpDisplay(hud, remove=True)


def add():
    """Create a HUD with information about the current environment and scene.

    """
    from maya import cmds

    remove()

    occupied_sections = set(
        [cmds.headsUpDisplay(f, query=True, section=True) for f in cmds.headsUpDisplay(listHeadsUpDisplays=True)]
    )
    available_sections = set([f for f in range(10)]) - occupied_sections

    if not available_sections:
        print('Could not add hud. All sections are occupied.')
    section = sorted(available_sections)[0]

    job = common.active('job').replace('/', ' | ') if common.active('job') else ''
    asset = common.active('asset').replace('/', ' | ') if common.active('asset') else ''

    data = [('', ''), ('Job:', job), ('Asset:', asset), ('', ''), ]

    warnings = get_warnings()
    data += warnings

    for n, item in enumerate(data):
        # label = item[0] if item[1] else ''
        v = item[1] if item[1] else ''

        cmds.headsUpDisplay(
            f'{STATUS_HUD}_{n}',
            section=section,
            allowOverlap=False,
            block=n,
            blockSize='small',
            blockAlignment='left',
            # label=label,
            # labelFontSize='small',
            # dataFontSize='small',
            # dataAlignment='right',
            command=functools.partial(lambda x: x, v),
            atr=True
        )


def toggle():
    """Toggle the visibility of the HUD created by this module.

    """
    from maya import cmds

    for hud in cmds.headsUpDisplay(listHeadsUpDisplays=True):
        if 'bookmarks_' not in hud:
            continue
        cmds.headsUpDisplay(hud, edit=True, visible=not cmds.headsUpDisplay(hud, query=True, visible=True))


def get_warnings():
    """Get a list of warnings related to the active environment and the current scene.

    """
    from maya import cmds

    data = []
    if not common.active('asset'):
        return data

    scene = cmds.file(query=True, sceneName=True)
    if common.active('asset', path=True) not in QtCore.QFileInfo(scene).filePath():
        data.append(('[Warning]', 'Current scene not part of asset'))

    # Get the active data from Bookmarks
    properties = base.MayaProperties()

    render_start_frame = cmds.getAttr('defaultRenderGlobals.startFrame')
    render_end_frame = cmds.getAttr('defaultRenderGlobals.endFrame')

    min_time = cmds.playbackOptions(q=True, minTime=True)
    max_time = cmds.playbackOptions(q=True, maxTime=True)
    anim_start_frame = cmds.playbackOptions(q=True, animationStartTime=True)
    anim_end_frame = cmds.playbackOptions(q=True, animationEndTime=True)

    if ((properties.startframe != min_time) or (properties.startframe != anim_start_frame) or (
            properties.endframe != max_time) or (properties.endframe != anim_end_frame)):
        data.append(('[Warning]', 'Timeline out of sync'))
    if (properties.startframe != render_start_frame or properties.endframe != render_end_frame):
        data.append(('[Warning]', 'Render range out of sync'))
    if base.get_framerate() != properties.framerate:
        data.append(('[Warning]', 'Frame-rate out of sync'))

    return data
