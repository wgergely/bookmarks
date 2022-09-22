"""Basic definitions related to how we're parsing folder structures and
interact with the Studio Aka project environment.

"""
import os
import re

from PySide2 import QtCore

from .. import common

Sequence = 'SEQ'
Shot = 'SH'


def get_seq_shot(path):
    """Returns the sequence and shot name of the given path.

    E.g. if the path is `C:/SEQ050/SH010/my_file.ma` will return
    `('SEQ050', 'SH010')`.

    Args:
        path (unicode): Path to a file or a folder.

    Returns:
        tuple(unicode, unicode):    Sequence and shot name, or `(None, None)`
                                    if not found.

    """
    match = re.search(
        fr'.*({Sequence}[0-9]{{3}})',
        path,
    )
    seq = match.group(1) if match else None
    match = re.search(
        fr'.*({Shot}[0-9]{{3}})',
        path,
    )
    shot = match.group(1) if match else None
    return seq, shot


def get_dir_entry_from_path(path):
    """Get a scandir entry from a path

    Args:
        path (str): Path to  directory

    Returns:
         scandir.DirEntry: A scandir entry item, or None if not found.

    """
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return None
    _path = file_info.dir().path()
    for entry in os.scandir(_path):
        if not entry.is_dir():
            continue
        if entry.name == file_info.fileName():
            return entry
    return None


def get_client_project():
    """Job names are composites of client/project names inside akapipe. This
    function will try to extract the client/project names from the action job.

    Returns:
        tuple (str, str, str): The server, client, project names, or
                (None, None, None).

    """
    job = common.active(common.JobKey)
    if '/' not in job:
        return None, None
    if job.count('/') > 1:
        return None, None
    client, project = job.split('/')
    return client, project


def item_generator(path):
    """The item generator responsible for returning the asset and shot
    items from a Studio Aka project.

    """
    try:
        from akapipe.core import templates
    except:
        return
        yield

    server = common.active(common.ServerKey)
    client, project = get_client_project()
    if not all((client, project)):
        return
        yield

    # Let's check if the source path is one of the token defined paths
    for token in (
            templates.PR_CharacterAssets,
            templates.PR_ModelAssets,
            templates.PR_Shots,
            templates.PR_Sandbox
    ):
        root = templates.expand_token(
            token,
            PR_NetworkPath=server,
            client=client,
            project=project,
        )
        if path not in root:
            continue

        # Get the root item. This can be either an asset name or a sequence
        for entry in os.scandir(root):
            if not entry.is_dir():
                continue
            if entry.name.startswith('.'):
                continue

            if token in (templates.PR_CharacterAssets, templates.PR_ModelAssets):
                asset = entry.name

                for _token in (
                        templates.AS_CharacterMayaAnimation,
                        templates.AS_CharacterMayaRender,
                        templates.AS_CharacterHouAnimation,
                        templates.AS_CharacterHouRender,
                        templates.AS_PropMayaAnimation,
                        templates.AS_PropMayaRender,
                        templates.AS_PropHouAnimation,
                        templates.AS_PropHouRender,
                ):
                    _path = templates.expand_token(
                        _token,
                        PR_NetworkPath=server,
                        client=client,
                        project=project,
                        asset=asset
                    )
                    asset_entry = get_dir_entry_from_path(_path)
                    if asset_entry:
                        yield asset_entry

            if token in (templates.PR_Shots,):
                for shot_entry in os.scandir(entry.path):
                    if not shot_entry.is_dir():
                        continue
                    if shot_entry.name.startswith('.'):
                        continue

                    for _token in (
                            templates.SH_MayaAnimation,
                            templates.SH_MayaFX,
                            templates.SH_MayaRender,
                            templates.SH_HouAnimation,
                            templates.SH_HouFX,
                            templates.SH_HouRender,
                    ):
                        _path = templates.expand_token(
                            _token,
                            PR_NetworkPath=server,
                            client=client,
                            project=project,
                            sequence=entry.name,
                            shot=shot_entry.name
                        )
                        _shot_entry = get_dir_entry_from_path(_path)
                        if _shot_entry:
                            yield _shot_entry

    return
    yield
