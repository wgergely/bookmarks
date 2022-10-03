
from . import base
from .. import common


class Test(base.BaseCase):

    def test_initialize(self):
        from .. import main

        with self.assertRaises(RuntimeError):
            w = main.MainWidget()
        with self.assertRaises(RuntimeError):
            w = main.init()

        self.assertFalse(common.main_widget.is_initialized)
        self.assertIsInstance(common.main_widget, main.MainWidget)

        common.main_widget.initialize()
        self.assertTrue(common.main_widget.is_initialized)
