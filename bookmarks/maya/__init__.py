"""The Bookmarks Maya integration module..

"""
import functools

from PySide2 import QtCore
from maya import cmds


def initialize():
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
    from .. import common
    from . import actions

    actions.remove_maya_widget()
    actions.remove_maya_button()
    actions.remove_workspace_controls()

    common.uninitialize()
    # maya_widget._instance.hide()
