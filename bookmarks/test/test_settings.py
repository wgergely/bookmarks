# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
import os
import random
import shutil

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common

from . import base


class Test(base.BaseCase):
    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()

        if not os.path.exists(common.temp_path()):
            os.makedirs(common.temp_path())

    def test_instance(self):
        self.assertIsInstance(common.settings, common.Settings)

    def test_values(self):
        v = common.settings.value(common.UIStateSection, common.CurrentList)
        self.assertIsNone(v)


        for _ in range(100):
            v = base.random_str(128)
            common.settings.setValue(
                common.UIStateSection,
                common.CurrentList,
                v
            )
            _v = common.settings.value(
                common.UIStateSection,
                common.CurrentList,
            )
            self.assertEqual(v, _v)

        for _ in range(100):
            v = base.random_ascii(128)
            common.settings.setValue(
                common.UIStateSection,
                common.CurrentList,
                v
            )
            _v = common.settings.value(
                common.UIStateSection,
                common.CurrentList,
            )
            self.assertEqual(v, _v)

        for _ in range(100):
            v = {0: base.random_ascii(128), 1: base.random_str(128)}
            common.settings.setValue(
                common.UIStateSection,
                common.CurrentList,
                v
            )
            _v = common.settings.value(
                common.UIStateSection,
                common.CurrentList,
            )
            self.assertEqual(v, _v)

        for _ in range(100):
            v = random.randrange(99999)
            common.settings.setValue(
                common.UIStateSection,
                common.CurrentList,
                v
            )
            _v = common.settings.value(
                common.UIStateSection,
                common.CurrentList,
            )
            self.assertEqual(v, _v)

        v = None
        common.settings.setValue(
            common.UIStateSection,
            common.CurrentList,
            v
        )
        _v = common.settings.value(
            common.UIStateSection,
            common.CurrentList,
        )
        self.assertEqual(v, _v)

        v = 'None'
        common.settings.setValue(
            common.UIStateSection,
            common.CurrentList,
            v
        )
        _v = common.settings.value(
            common.UIStateSection,
            common.CurrentList,
        )
        self.assertEqual(v, _v)

        v = 0.5
        common.settings.setValue(
            common.UIStateSection,
            common.CurrentList,
            v
        )
        _v = common.settings.value(
            common.UIStateSection,
            common.CurrentList,
        )
        self.assertEqual(v, _v)

        v = QtCore.QRect(0,0,50,50)
        common.settings.setValue(
            common.UIStateSection,
            common.CurrentList,
            v
        )
        _v = common.settings.value(
            common.UIStateSection,
            common.CurrentList,
        )
        self.assertEqual(v, _v)
