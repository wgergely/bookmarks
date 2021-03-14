# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
from PySide2 import QtCore, QtWidgets

from . import base


class Test(base.BaseApplicationTest):
    def test_import_oiio(self):
        try:
            import OpenImageIO
        except ImportError as err:
            self.fail(err)

    def test_import_scandir(self):
        try:
            import _scandir
        except ImportError as err:
            self.fail(err)

    def test_import_qt(self):
        try:
            from PySide2 import QtCore, QtGui, QtWidgets
        except ImportError as err:
            self.fail(err)

    def test_import_slack(self):
        try:
            import slackclient
        except ImportError as err:
            self.fail(err)

    def test_import_psutil(self):
        try:
            import psutil
        except ImportError as err:
            self.fail(err)

    def test_import_alembic(self):
        try:
            import alembic
        except ImportError as err:
            self.fail(err)

    def test_import_numpy(self):
        try:
            import numpy
        except ImportError as err:
            self.fail(err)

    def test_import_sqlite(self):
        try:
            import sqlite3
        except ImportError as err:
            self.fail(err)
