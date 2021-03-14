#!mayapy
"""Tests the Maya plugin.
Make sure to run this file using Maya's bundled python interpreter (mayapy).

"""
import os
import imp
from PySide2 import QtCore, QtWidgets

if __name__ == '__main__':
    p = __file__ + os.pardir.join([os.path.sep,] * 3) + 'maya' + os.path.sep + 'base.py'
    p = os.path.normpath(p)
    assert os.path.isfile(p)
    base = imp.load_source('base', p)

    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    QtCore.QTimer.singleShot(20000, app.quit)
    QtCore.QTimer.singleShot(100, base.init)
    QtCore.QTimer.singleShot(5000, base.reload_plugin)
    app.exec_()
