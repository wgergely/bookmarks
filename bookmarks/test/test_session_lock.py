# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
import os
import random

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import session_lock
from .. import actions
from . import base


class Test(base.BaseApplicationTest):
    def test_default_mode(self):
        self.assertEqual(common.SESSION_MODE, common.SyncronisedActivePaths)

    def test_init(self):
        path = session_lock.init()
        self.assertIsNotNone(path)
        self.assertIsInstance(path, unicode)
        self.assertTrue(os.path.isfile(path))
        with open(path, 'r') as f:
            v = f.read()
        self.assertIn(int(v), (common.SyncronisedActivePaths, common.PrivateActivePaths))

        # init second lockfile
        pid = random.randrange(9999)
        _path = session_lock.init(pid=pid)
        self.assertIsNotNone(_path)
        self.assertIsInstance(_path, unicode)
        self.assertTrue(os.path.isfile(_path))
        self.assertNotEqual(_path, path)

        # Mode should be private since there's already a Syncronised lock
        path_ = session_lock.init()
        self.assertIsNotNone(path_)
        self.assertIsInstance(path_, unicode)
        self.assertTrue(os.path.isfile(path_))
        with open(path, 'r') as f:
            v = f.read()
        self.assertEqual(int(v), common.PrivateActivePaths)

    def test_prune(self):
        paths = []
        for _ in xrange(99):
            pid = random.randrange(999999)
            path = session_lock.init(pid=pid)
            self.assertIsNotNone(path)
            self.assertIsInstance(path, unicode)
            self.assertTrue(os.path.isfile(path))
            paths.append(path)

        session_lock.prune()
        v = [f for f in paths if os.path.isfile(f)]
        self.assertFalse(v)

    def test_toggle_session_mode(self):
        v = common.SESSION_MODE
        actions.toggle_session_mode()
        self.assertNotEqual(v, common.SESSION_MODE)
