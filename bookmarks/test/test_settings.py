# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
import os
import random
import shutil

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import settings
from . import base


class Test(base.BaseApplicationTest):
    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()

        if not os.path.exists(common.temp_path()):
            os.makedirs(common.temp_path())

    def test_instance(self):
        self.assertIsInstance(settings.instance(), settings.Settings)

    def test_values(self):
        v = settings.instance().value(settings.UIStateSection, settings.CurrentList)
        self.assertIsNone(v)


        for _ in range(100):
            v = base.random_str(128)
            settings.instance().setValue(
                settings.UIStateSection,
                settings.CurrentList,
                v
            )
            _v = settings.instance().value(
                settings.UIStateSection,
                settings.CurrentList,
            )
            self.assertEqual(v, _v)

        for _ in range(100):
            v = base.random_ascii(128)
            settings.instance().setValue(
                settings.UIStateSection,
                settings.CurrentList,
                v
            )
            _v = settings.instance().value(
                settings.UIStateSection,
                settings.CurrentList,
            )
            self.assertEqual(v, _v)

        for _ in range(100):
            v = {0: base.random_ascii(128), 1: base.random_str(128)}
            settings.instance().setValue(
                settings.UIStateSection,
                settings.CurrentList,
                v
            )
            _v = settings.instance().value(
                settings.UIStateSection,
                settings.CurrentList,
            )
            self.assertEqual(v, _v)

        for _ in range(100):
            v = random.randrange(99999)
            settings.instance().setValue(
                settings.UIStateSection,
                settings.CurrentList,
                v
            )
            _v = settings.instance().value(
                settings.UIStateSection,
                settings.CurrentList,
            )
            self.assertEqual(v, _v)

        v = None
        settings.instance().setValue(
            settings.UIStateSection,
            settings.CurrentList,
            v
        )
        _v = settings.instance().value(
            settings.UIStateSection,
            settings.CurrentList,
        )
        self.assertEqual(v, _v)

        v = 'None'
        settings.instance().setValue(
            settings.UIStateSection,
            settings.CurrentList,
            v
        )
        _v = settings.instance().value(
            settings.UIStateSection,
            settings.CurrentList,
        )
        self.assertEqual(v, _v)

        v = 0.5
        settings.instance().setValue(
            settings.UIStateSection,
            settings.CurrentList,
            v
        )
        _v = settings.instance().value(
            settings.UIStateSection,
            settings.CurrentList,
        )
        self.assertEqual(v, _v)

        v = QtCore.QRect(0,0,50,50)
        settings.instance().setValue(
            settings.UIStateSection,
            settings.CurrentList,
            v
        )
        _v = settings.instance().value(
            settings.UIStateSection,
            settings.CurrentList,
        )
        self.assertEqual(v, _v)
