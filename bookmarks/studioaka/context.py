"""This module contains linkage with the experimental StudioAka module.

AkaPipe is not part of Bookmarks, nor is it under development but the module
shall serve as a placeholder for a future Studio Aka pipline integration.

"""
from PySide2 import QtCore

from akapipe.core import context
from akapipe.core import database
from akapipe.core import db
from akapipe.core import signals
from akapipe.core import templates
from akapipe.scenes import sc

from . import base
from .. import common


def show_akapipe():
    signals.signals.initialized.connect(connect_signals)
    import akapipe
    akapipe.show()


@QtCore.Slot()
def connect_signals():
    """This slot is called when the akapipe finished initializing.

    """
    common.signals.bookmarkActivated.connect(bookmark_activated)
    common.signals.assetActivated.connect(asset_activated)


@QtCore.Slot(str)
@QtCore.Slot(str)
@QtCore.Slot(str)
def bookmark_activated(server, job, root):
    if not all((server, job, root)):
        return

    client, project = base.get_client_project()
    if not all((client, project)):
        return False

    client_id = database.get_value(db.CL, client, db.CL_client_id)
    context.set(
        db.CL,
        {db.IdRole: client_id, db.NameRole: client}
    )

    project_id = database.get_value(db.PR, project, db.PR_project_id)
    context.set(
        db.PR,
        {db.IdRole: project_id, db.NameRole: project}
    )
    return True


@QtCore.Slot(str)
@QtCore.Slot(str)
@QtCore.Slot(str)
@QtCore.Slot(str)
def asset_activated(server, job, root, asset):
    """The asset activation in bookmarks covers setting both
    the active asset in akapipe and changing the current workspace.

    We have to do some gymnastics but using the tokens we can
    find out the asset/shot type from the file path and the
    workspace type too.

    """
    bookmark_activated(server, job, root)

    if not all((server, job, root, asset)):
        return

    # An asset could be any number of things...
    path = '/'.join((server, job, root, asset))
    for token in (
            templates.PR_ModelAssets,
            templates.PR_CharacterAssets,
            templates.PR_Shots,
    ):
        p = templates.expand_token(
            token,
        )

        # This is an aka asset
        if p in path and token in (
                templates.PR_ModelAssets,
                templates.PR_CharacterAssets,
        ):
            _asset = asset.split('/')[0]
            asset_id = database.get_value(
                db.AS,
                _asset,
                db.AS_asset_id,
                parent_id=context.context[db.PR][db.IdRole]
            )
            context.set(
                db.AS,
                {db.IdRole: asset_id, db.NameRole: _asset}
            )

            # Changing workspace
            for workspaces in sc.workspaces[db.AS].values():
                for label, _token in workspaces.items():
                    if path in templates.expand_token(_token):
                        signals.signals.workspaceChangedExternally.emit(label)
                        return

        elif p in path and token == templates.PR_Shots:
            sequence, shot = base.get_seq_shot(path)
            if not all((sequence, shot)):
                return
            sequence_id = database.get_value(
                db.SQ,
                sequence,
                db.SQ_sequence_id,
                parent_id=context.context[db.PR][db.IdRole]
            )
            context.set(
                db.SQ,
                {db.IdRole: sequence_id, db.NameRole: sequence}
            )

            shot_id = database.get_value(
                db.SH,
                shot,
                db.SH_shot_id,
                parent_id=context.context[db.SQ][db.IdRole]
            )
            context.set(
                db.SH,
                {db.IdRole: shot_id, db.NameRole: shot}
            )

            for label, _token in sc.workspaces[db.SH].items():
                if path in templates.expand_token(_token):
                    signals.signals.workspaceChangedExternally.emit(label)
                    return



