# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import main
from . import base


class Test(base.BaseCase):
    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()

        common.init_standalone()
        common.init_pixel_ratio()
        common.init_ui_scale()
        common.init_session_lock()
        common.init_settings()
        common.init_font_db()

    def test_initialize_destroy(self):
        with self.assertRaises(RuntimeError):
            v = main.instance()

        v = main.MainWidget()
        self.assertFalse(v.is_initialized)
        self.assertIsInstance(v, main.MainWidget)
        self.assertIsInstance(main.instance(), main.MainWidget)
        v.initialize()
        self.assertTrue(v.is_initialized)

        common.quit()
        self.assertFalse(v.is_initialized)

        # import sys
        # self.assertLessEqual(sys.getrefcount(v), 3)
