"""Export script for Odyssey cloth sims.

The scripts automates the animation cache export from Maya.

It performs the follow steps:
    - Saves the current animation to studio library
    - Removes the animation from the body and root controllers
    - Adds a preroll with a reset pose
    - Saves the animation caches

Gergely Wootsch.
hello@gergely-wootsch.com
Studio Aka, 2023 October

"""
import os

import maya.cmds as cmds
from PySide2 import QtCore
from ... import common
from ... import database
from .. import base as mayabase
from .. import export
from . import aka_make_export_sets
from ...tokens import tokens


studiolibrary_dir = f'{common.active("server")}/{common.active("job")}/070_Assets/Character/studiolibrary'
reset_pose = f'{studiolibrary_dir}/Characters/IbogaineMarcus/Reset/A-Pose-v2-FullFK.pose/pose.json'

cache_destination_dir = '{studiolibrary_dir}/Shots/MAB/{asset0}_{shot}'

namespace = 'IbogaineMarcus_01'
controllers_set = f'{namespace}:rig_controllers_grp'

# These controllers should not be animated when exporting the caches
exclude_controllers1 = [
    f'{namespace}:body_C0_ctl',
    f'{namespace}:world_ctl',
    f'{namespace}:root_C0_ctl'
]

# These controllers should be excluded from the a-pose
exclude_controllers2 = [
    f'{namespace}:legUI_L0_ctl',
    f'{namespace}:armUI_R0_ctl',
    f'{namespace}:faceUI_C0_ctl',
    f'{namespace}:legUI_R0_ctl',
    f'{namespace}:spineUI_C0_ctl',
    f'{namespace}:armUI_L0_ctl'
]


def get_cache_path(set_name, ext, makedir=True):
    """Get the path of the output cache file.

    """
    workspace = cmds.workspace(q=True, fn=True)

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
    _version = 1
    while True:
        version = 'v' + f'{_version}'.zfill(3)

        file_path = '{dir}/{basename}_{version}.{ext}'.format(
            dir=file_info.dir().path(),
            basename=file_info.completeBaseName(),
            version=version,
            ext=file_info.suffix()
        )

        if not QtCore.QFileInfo(file_path).exists():
            break
        if _version >= 999:
            break

        _version += 1

    if makedir:
        QtCore.QFileInfo(file_path).dir().mkpath('.')
    return file_path


@common.debug
@common.error
def run():
    try:
        import mutils
    except ImportError:
        raise RuntimeError('Could not export caches. Is Studio Library installed?')

    config = tokens.get(*common.active('root', args=True))

    seq, shot = common.get_sequence_and_shot(common.active('asset'))
    destination_dir = config.expand_tokens(
        cache_destination_dir,
        asset=common.active('asset'),
        shot=shot,
        sequence=seq,
        studiolibrary_dir=studiolibrary_dir
    )

    # Save the current options
    timeline_start = cmds.playbackOptions(animationStartTime=True, query=True)
    timeline_end = cmds.playbackOptions(animationEndTime=True, query=True)
    animation_start = cmds.playbackOptions(minTime=True, query=True)
    animation_end = cmds.playbackOptions(maxTime=True, query=True)

    db = database.get(*common.active('root', args=True))
    cut_in = db.value(common.active('asset', path=True), 'cut_in', database.AssetTable)
    cut_out = db.value(common.active('asset', path=True), 'cut_out', database.AssetTable)

    cmds.select(clear=True)

    # Create the export groups
    aka_make_export_sets.run()

    # Set the cache range up
    cmds.playbackOptions(animationStartTime=-50, minTime=-50, animationEndTime=cut_out, maxTime=cut_out)
    cmds.currentTime(cut_in)

    for n in (cut_in, cut_out):
        cmds.currentTime(n)
        cmds.select(cmds.sets(controllers_set, query=True), replace=True, ne=True)
        cmds.setKeyframe(
            cmds.sets(controllers_set, query=True),
            breakdown=False,
            preserveCurveShape=False,
            hierarchy='none',
            controlPoints=False,
            shape=True,
        )

    for node in cmds.sets(controllers_set, query=True):
        attrs = cmds.listAnimatable(node)
        if not attrs:
            continue
        for attr in attrs:
            if not cmds.keyframe(attr, query=True, time=(cut_in - 51, cut_in - 1)):
                continue
            cmds.cutKey(attr, time=(cut_in - 51, cut_in - 1))

    cmds.currentTime(cut_in)

    # Save the full animation
    try:
        mutils.saveAnim(
            cmds.sets(controllers_set, query=True),
            os.path.normpath(f'{destination_dir}/IbogaineMarcus_fullanim.anim'),
            time=(cut_in, cut_out),
            bakeConnected=False,
            metadata=''
        )
    except UnicodeDecodeError as e:
        print(e)

    # Save the animation start pose
    try:
        mutils.savePose(
            os.path.normpath(f'{destination_dir}/IbogaineMarcus_animstart.pose/pose.json'),
            exclude_controllers1,
        )
    except UnicodeDecodeError as e:
        print(e)

    # Parent a null locator to the hip bake it to world and save the world animation for alter use
    locator = cmds.spaceLocator(name="nullLocator")[0]
    constraint = cmds.parentConstraint('IbogaineMarcus_01:body_C0_ctl', locator, maintainOffset=False)[0]
    cmds.bakeResults(
        locator,
        time=(cut_in, cut_out),
        simulation=True,
        sampleBy=1,
        oversamplingRate=1,
        disableImplicitControl=True,
        preserveOutsideKeys=True,
        sparseAnimCurveBake=False,
        removeBakedAttributeFromLayer=False,
        bakeOnOverrideLayer=False,
        minimizeRotation=True,
        controlPoints=False,
        shape=True
    )

    # Save the hip animation
    try:
        mutils.saveAnim(
            [locator, ],
            os.path.normpath(f'{destination_dir}/IbogaineMarcus_hip.anim'),
            time=(cut_in, cut_out),
            bakeConnected=False,
            metadata=''
        )
    except UnicodeDecodeError as e:
        print(e)

    cmds.delete(constraint)
    cmds.delete(locator)

    # Remove animation from body and world controllers...
    # for obj in exclude_controllers1:
    #     animated_attrs = cmds.listAnimatable(obj)
    #     animated_attrs = animated_attrs if animated_attrs else []
    #     for attr in animated_attrs:
    #         cmds.cutKey(attr, clear=True)

    # ...but keep the pose at cut_in
    cmds.currentTime(cut_in)
    mutils.loadPose(
        os.path.normpath(f'{destination_dir}/IbogaineMarcus_animstart.pose/pose.json'),
        key=True
    )

    cmds.currentTime(cut_in - 51)

    mutils.loadPose(
        os.path.normpath(reset_pose),
        objects=list(
            set(cmds.sets(controllers_set, query=True)) - set(exclude_controllers1) - set(
                exclude_controllers2
            )
            ),
        key=True,
        namespaces=[namespace, ]
    )

    export.export_maya(
        get_cache_path('camera_export', 'ma'),
        cmds.sets('camera_export', query=True), cut_in, cut_out, step=1.0
    )
    export.export_alembic(
        get_cache_path('camera_export', 'abc'),
        cmds.sets('camera_export', query=True), cut_in, cut_out, step=1.0
    )
    export.export_alembic(
        get_cache_path('IbogaineMarcus_body_export', 'abc'),
        cmds.sets('IbogaineMarcus_body_export', query=True), cut_in - 51, cut_out, step=1.0
    )
    export.export_alembic(
        get_cache_path('IbogaineMarcus_cloth_export', 'abc'),
        cmds.sets('IbogaineMarcus_cloth_export', query=True), cut_in - 51, cut_in - 51, step=1.0
    )
    export.export_alembic(
        get_cache_path('IbogaineMarcus_extra_export', 'abc'),
        cmds.sets('IbogaineMarcus_extra_export', query=True), cut_in - 51, cut_out, step=1.0
    )

    mutils.loadAnims(
        [os.path.normpath(f'{destination_dir}/IbogaineMarcus_fullanim.anim'), ],
        objects=cmds.sets(controllers_set, query=True),
        currentTime=False,
        option='replaceCompletely',
        namespaces=[namespace, ]
    )

    cmds.playbackOptions(animationStartTime=cut_in, minTime=cut_in, animationEndTime=cut_out, maxTime=cut_out)
