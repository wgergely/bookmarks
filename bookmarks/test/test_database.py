"""Bookmarks test environment setup and teardown."""
import os
import random

from . import base


class Test(base.BaseCase):
    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()
        from .. import common
        if not os.path.exists(common.temp_path()):
            os.makedirs(common.temp_path())
        if not os.path.exists(common.temp_path() + '2'):
            os.makedirs(common.temp_path() + '2')
        if not os.path.exists(common.temp_path() + '3'):
            os.makedirs(common.temp_path() + '3')

    def test_instance(self):
        from .. import common
        from .. import database
        with self.assertRaises(TypeError):
            database.BookmarkDB(None, None, None)
        with self.assertRaises(TypeError):
            database.BookmarkDB(b'str', b'str', b'str')

        db = database.BookmarkDB('invalid', 'path', 'root')
        self.assertFalse(db.is_valid())
