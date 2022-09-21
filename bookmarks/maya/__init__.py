"""Autodesk Maya integrations.

"""
import functools

from PySide2 import QtCore

try:
    from maya import cmds
except ImportError:
    raise ImportError('Could not find Maya modules.')


def initialize():
    """Initializes the Bookmarks Maya module.

    This will start Bookmarks in ``common.EmbeddedMode`` and will create the settings
    and widgets needed to embed it into the Maya UI.

    """
    from .. import common
    common.initialize(common.EmbeddedMode)

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


def uninitialize():
    """Removes the embedded Bookmarks elements from Maya.

    """
    from .. import common
    from . import actions

    actions.remove_maya_widget()
    actions.remove_maya_button()
    actions.remove_workspace_controls()

    common.uninitialize()
