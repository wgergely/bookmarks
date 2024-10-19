"""Autodesk Maya plugin.

See the :mod:`bookmarks.maya.plugin` for the installable Maya plugin.

This module provides an implementation to embed Bookmarks into the Maya UI. See
:class:`bookmarks.maya.main.MayaWidget`. It also defines extra asset referencing,
loading and exporting features. ``plugin.py`` is responsible for setting up the
environment to run Bookmarks. This can be tricky as Maya needs to be told where to find
the dynamic libraries and python modules used by OpenImageIO. The libraries the plugin
is pointing at mirror the current distribution package structure but can be customized
to suit site-specific needs.

"""
import functools

from PySide2 import QtCore

try:
    from maya import cmds
except ImportError:
    raise ImportError('Could not find Maya modules.')


def initialize():
    """Initializes the Bookmarks Maya module.

    This will start Bookmarks in :attr:`~bookmarks.common.Mode.Embedded` and will create the settings
    and widgets needed to embed it into the Maya UI.

    """
    from .. import common
    common.initialize(common.Mode.Embedded)

    from . import main
    main.init_maya_widget()
    main.init_tool_button()

    currentval = cmds.optionVar(q='workspacesLockDocking')
    cmds.optionVar(intValue=('workspacesLockDocking', False))

    main.show()

    cmds.evalDeferred(
        functools.partial(
            cmds.optionVar,
            intValue=('workspacesLockDocking', currentval)
        )
    )

    # Initialize the data
    cmds.evalDeferred(
        functools.partial(
            QtCore.QTimer.singleShot,
            100,
            common.main_widget.initialize
        )
    )


def shutdown():
    """Removes the embedded Bookmarks elements from Maya.

    """
    from .. import common
    from . import actions

    actions.remove_maya_widget()
    actions.remove_maya_button()
    actions.remove_workspace_controls()
    actions.remove_hud()

    common.shutdown()
