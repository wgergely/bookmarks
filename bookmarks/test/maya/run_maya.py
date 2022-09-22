#!mayapy
"""Tests the Maya plugin.
Make sure to run this file using Maya's bundled python interpreter (mayapy).

"""
import imp
import os

from PySide2 import QtCore, QtWidgets

if __name__ == '__main__':
    p = __file__ + os.pardir.join([os.path.sep, ] * 3) + 'maya' + os.path.sep + 'base.py'
    p = os.path.normpath(p)
    assert os.path.isfile(p)
    base = imp.load_source('base', p)

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseOpenGLES, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication([])
    QtCore.QTimer.singleShot(100, base.init)
    app.exec_()
