# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
import os

from . import base
from .. import common


class Test(base.BaseCase):

    def test_get_lock_path(self):
        v = common.get_lock_path()
        self.assertIsNotNone(v)
        self.assertIsInstance(v, str)

    def test_init(self):
        path = common.init_lock()
        self.assertIsNotNone(path)
        self.assertIsInstance(path, str)
        self.assertTrue(os.path.isfile(path))

        with open(path, 'r') as f:
            v = f.read()
        self.assertIn(int(v), (common.SynchronisedActivePaths, common.PrivateActivePaths))

    def test_prune(self):
        common.prune_lock()

    def test_toggle_active_mode(self):
        from .. import actions
        v = common.active_mode
        actions.toggle_active_mode()
        self.assertNotEqual(v, common.active_mode)

        v = common.active_mode
        actions.toggle_active_mode()
        self.assertNotEqual(v, common.active_mode)
