"""Bookmarks test environment setup and teardown."""
import os
import random

from PySide2 import QtCore

from . import base
from .. import common


class Test(base.BaseCase):
    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()

        if not os.path.exists(common.temp_path()):
            os.makedirs(common.temp_path())

    def test_initialized(self):
        self.assertIsInstance(common.settings, common.UserSettings)

    def test_active(self):
        with self.assertRaises(KeyError):
            common.active(base.random_str(128))

        for k in common.SECTIONS['active']:
            v = common.active(k)
            self.assertIsInstance(v, (type(None), str))

        v = common.active('asset', path=True)
        self.assertIsInstance(v, (type(None), str))

        v = common.active('asset', args=True)
        self.assertIsInstance(v, (type(None), tuple))

    def test_values(self):
        for _ in range(100):
            v = base.random_str(128)
            common.settings.setValue('test/value', v)
            _v = common.settings.value('test/value')
            self.assertEqual(v, _v)

        for _ in range(100):
            v = base.random_ascii(128)
            common.settings.setValue('test/value', v)
            _v = common.settings.value('test/value')
            self.assertEqual(v, _v)

        for _ in range(100):
            v = {0: base.random_ascii(128), 1: base.random_str(128)}
            common.settings.setValue('test/value', v)
            _v = common.settings.value('test/value')
            self.assertEqual(v, _v)

        for _ in range(100):
            v = random.randrange(99999)
            common.settings.setValue('test/value', v)
            _v = common.settings.value('test/value')
            self.assertEqual(v, _v)

        v = None
        common.settings.setValue('test/value', v)
        _v = common.settings.value('test/value')
        self.assertEqual(v, _v)

        v = 0.5
        common.settings.setValue('test/value', v)
        _v = common.settings.value('test/value')
        self.assertEqual(v, _v)

        v = QtCore.QRect(0, 0, 50, 50)
        common.settings.setValue('test/value', v)
        _v = common.settings.value('test/value')
        self.assertEqual(v, _v)

    def test_get_user_settings_path(self):
        v = common.get_user_settings_path()
        self.assertIsInstance(v, str)
        self.assertTrue(self, os.path.isfile(v))
