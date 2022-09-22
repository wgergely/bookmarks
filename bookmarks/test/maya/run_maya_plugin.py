#!mayapy
"""Maya plugin load/unload tester.

Make sure to run this from the Python boundled with the Maya installation.
THe script will test the Maya plugin `initializePlugin` and `uninitializePlugin`.

"""
import os
import sys

sys.path.append(
    os.path.normpath(
        os.path.join(
            __file__,
            os.pardir,
            os.pardir,
            os.pardir,
            os.pardir,
        )
    )
)

from PySide2 import QtCore, QtWidgets
import maya.standalone as standalone
import maya.cmds as cmds

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseOpenGLES, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

app = QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False)

standalone.initialize(name='python')

from bookmarks.maya import plugin

plugin.init_environment('BOOKMARKS_ROOT')

cmds.evalDeferred(lambda: plugin.initializePlugin('Bookmarks'))
QtCore.QTimer.singleShot(3000, lambda: cmds.evalDeferred(
    lambda: plugin.uninitializePlugin('Bookmarks')))
QtCore.QTimer.singleShot(6000, lambda: cmds.evalDeferred(
    lambda: plugin.initializePlugin('Bookmarks')))
QtCore.QTimer.singleShot(9000, lambda: cmds.evalDeferred(
    lambda: plugin.uninitializePlugin('Bookmarks')))
QtCore.QTimer.singleShot(12000, lambda: cmds.evalDeferred(
    lambda: plugin.initializePlugin('Bookmarks')))
app.exec_()
