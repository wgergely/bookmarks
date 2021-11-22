# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
import os
import random

from PySide2 import QtCore, QtWidgets

from .. import common
from . import base


class Test(base.BaseApplicationTest):
    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()

        if not os.path.exists(common.temp_path()):
            os.makedirs(common.temp_path())
        if not os.path.exists(common.temp_path() + '2'):
            os.makedirs(common.temp_path() + '2')
        if not os.path.exists(common.temp_path() + '3'):
            os.makedirs(common.temp_path() + '3')

    def test_instance(self):
        from .. import database
        with self.assertRaises(TypeError):
            database.BookmarkDB(None, None, None)
        with self.assertRaises(TypeError):
            database.BookmarkDB(b'str', b'str', b'str')

        db = database.BookmarkDB('invalid', 'path', 'root')
        self.assertFalse(db.is_valid())

        server, job, root = common.local_parent_paths()
        db = database.BookmarkDB(server, job, root)
        self.assertTrue(db.is_valid())

    def test_value(self):
        from .. import database
        db = database.BookmarkDB(*common.local_parent_paths())
        self.assertTrue(db.is_valid())

        self.assertIn(database.AssetTable, database.TABLES)
        self.assertIn(database.BookmarkTable, database.TABLES)
        self.assertIn(database.InfoTable, database.TABLES)

        for t in (database.BookmarkTable, database.AssetTable):
            for k in database.TABLES[t]:
                v = db.value(db.source(), k, table=t)
                self.assertIsNone(v)

        with self.assertRaises(TypeError):
            db.value(b'str', b'description', table=t)
        with self.assertRaises(TypeError):
            db.value(db.source(), base.random_ascii(), table=t)
        with self.assertRaises(ValueError):
            db.value(db.source(), base.random_str(36), table=t)

        for t in (database.BookmarkTable, database.AssetTable):
            for k in database.TABLES[t]:
                if k == 'id':
                    continue

                _type = database.TABLES[t][k]['type']
                if _type == str:
                    v = base.random_str(36)
                elif _type == int:
                    v = int(random.randrange(99999))
                elif _type == float:
                    v = float(random.randrange(99999))
                elif _type == dict:
                    v = {0: base.random_ascii(36), 0: base.random_str(36)}
                    db.setValue(db.source(), k, v, table=t)
                    _v = db.value(db.source(), k, table=t)
                    self.assertNotEqual(v, _v)

                    v = {'0': base.random_ascii(
                        128), '1': base.random_str(128)}
                else:
                    v = None

                db.setValue(db.source(), k, v, table=t)
                _v = db.value(db.source(), k, table=t)
                self.assertEqual(_v, v)
                self.assertIsInstance(_v, _type)

    def test_invalid(self):
        from .. import database
        server, job, root = common.local_parent_paths()
        root += base.random_str(32)

        db = database.BookmarkDB(server, job, root)
        self.assertFalse(db.is_valid())

        for t in (database.BookmarkTable, database.AssetTable):
            for k in database.TABLES[t]:
                if k == 'id':
                    continue

                _type = database.TABLES[t][k]['type']
                if _type == str:
                    v = base.random_str(36)
                elif _type == int:
                    v = int(random.randrange(99999))
                elif _type == float:
                    v = float(random.randrange(99999))
                elif _type == dict:
                    v = {
                        '0': base.random_ascii(128),
                        '1': base.random_str(128)
                    }
                else:
                    v = None

                db.setValue(db.source(), k, v, table=t)
                _v = db.value(db.source(), k, table=t)
                self.assertIsNone(_v)


    def test_copy_paste(self):
        from .. import database
        server, job, root = common.local_parent_paths()
        root += '2'

        db = database.BookmarkDB(server, job, root)
        self.assertTrue(db.is_valid())

        for t in (database.BookmarkTable, database.AssetTable):
            for k in database.TABLES[t]:
                if k == 'id':
                    continue

                _type = database.TABLES[t][k]['type']
                if _type == str:
                    v = base.random_str(36)
                elif _type == int:
                    v = int(random.randrange(99999))
                elif _type == float:
                    v = float(random.randrange(99999))
                elif _type == dict:
                    v = {
                        '0': base.random_ascii(128),
                        '1': base.random_str(128)
                    }
                else:
                    v = None

                db.setValue(db.source(), k, v, table=t)
                db.setValue(db.source('asset'), k, v, table=t)
                _v = db.value(db.source(), k, table=t)
                self.assertEqual(_v, v)


        v = database.copy_properties(server, job, root)
        self.assertIsNotNone(v)
        self.assertIsInstance(v, dict)
        for k in database.TABLES[database.BookmarkTable]:
            if k == 'id':
                continue
            self.assertIn(k, v)
            self.assertIsNotNone(v[k])

        v = database.copy_properties(server, job, root, asset='asset', table=database.AssetTable)
        self.assertIsNotNone(v)
        self.assertIsInstance(v, dict)
        for k in database.TABLES[database.AssetTable]:
            if k == 'id':
                continue
            self.assertIn(k, v)
            self.assertIsNotNone(v[k])

        for _ in range(10):
            database.paste_properties(server, job, root, asset=base.random_str(32), table=database.AssetTable)