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
        from .. import bookmark_db
        with self.assertRaises(TypeError):
            bookmark_db.BookmarkDB(None, None, None)
        with self.assertRaises(TypeError):
            bookmark_db.BookmarkDB('str', 'str', 'str')

        db = bookmark_db.BookmarkDB(u'invalid', u'path', u'root')
        self.assertFalse(db.is_valid())

        server, job, root = common.local_parent_paths()
        db = bookmark_db.BookmarkDB(server, job, root)
        self.assertTrue(db.is_valid())

    def test_value(self):
        from .. import bookmark_db
        db = bookmark_db.BookmarkDB(*common.local_parent_paths())
        self.assertTrue(db.is_valid())

        self.assertIn(bookmark_db.AssetTable, bookmark_db.TABLES)
        self.assertIn(bookmark_db.BookmarkTable, bookmark_db.TABLES)
        self.assertIn(bookmark_db.InfoTable, bookmark_db.TABLES)

        for t in (bookmark_db.BookmarkTable, bookmark_db.AssetTable):
            for k in bookmark_db.TABLES[t]:
                v = db.value(db.source(), k, table=t)
                self.assertIsNone(v)

        with self.assertRaises(TypeError):
            db.value('str', 'description', table=t)
        with self.assertRaises(TypeError):
            db.value(db.source(), base.random_ascii(), table=t)
        with self.assertRaises(ValueError):
            db.value(db.source(), base.random_unicode(36), table=t)

        for t in (bookmark_db.BookmarkTable, bookmark_db.AssetTable):
            for k in bookmark_db.TABLES[t]:
                if k == 'id':
                    continue

                _type = bookmark_db.TABLES[t][k]['type']
                if _type == unicode:
                    v = base.random_unicode(36)
                elif _type == int:
                    v = int(random.randrange(99999))
                elif _type == float:
                    v = float(random.randrange(99999))
                elif _type == dict:
                    v = {0: base.random_ascii(36), 0: base.random_unicode(36)}
                    db.setValue(db.source(), k, v, table=t)
                    _v = db.value(db.source(), k, table=t)
                    self.assertNotEqual(v, _v)

                    v = {'0': base.random_ascii(
                        128), '1': base.random_unicode(128)}
                else:
                    v = None

                db.setValue(db.source(), k, v, table=t)
                _v = db.value(db.source(), k, table=t)
                self.assertEqual(_v, v)
                self.assertIsInstance(_v, _type)

    def test_invalid(self):
        from .. import bookmark_db
        server, job, root = common.local_parent_paths()
        root += base.random_unicode(32)

        db = bookmark_db.BookmarkDB(server, job, root)
        self.assertFalse(db.is_valid())

        for t in (bookmark_db.BookmarkTable, bookmark_db.AssetTable):
            for k in bookmark_db.TABLES[t]:
                if k == 'id':
                    continue

                _type = bookmark_db.TABLES[t][k]['type']
                if _type == unicode:
                    v = base.random_unicode(36)
                elif _type == int:
                    v = int(random.randrange(99999))
                elif _type == float:
                    v = float(random.randrange(99999))
                elif _type == dict:
                    v = {
                        '0': base.random_ascii(128),
                        '1': base.random_unicode(128)
                    }
                else:
                    v = None

                db.setValue(db.source(), k, v, table=t)
                _v = db.value(db.source(), k, table=t)
                self.assertIsNone(_v)


    def test_copy_paste(self):
        from .. import bookmark_db
        server, job, root = common.local_parent_paths()
        root += '2'

        db = bookmark_db.BookmarkDB(server, job, root)
        self.assertTrue(db.is_valid())

        for t in (bookmark_db.BookmarkTable, bookmark_db.AssetTable):
            for k in bookmark_db.TABLES[t]:
                if k == 'id':
                    continue

                _type = bookmark_db.TABLES[t][k]['type']
                if _type == unicode:
                    v = base.random_unicode(36)
                elif _type == int:
                    v = int(random.randrange(99999))
                elif _type == float:
                    v = float(random.randrange(99999))
                elif _type == dict:
                    v = {
                        '0': base.random_ascii(128),
                        '1': base.random_unicode(128)
                    }
                else:
                    v = None

                db.setValue(db.source(), k, v, table=t)
                db.setValue(db.source(u'asset'), k, v, table=t)
                _v = db.value(db.source(), k, table=t)
                self.assertEqual(_v, v)


        v = bookmark_db.copy_properties(server, job, root)
        self.assertIsNotNone(v)
        self.assertIsInstance(v, dict)
        for k in bookmark_db.TABLES[bookmark_db.BookmarkTable]:
            if k == 'id':
                continue
            self.assertIn(k, v)
            self.assertIsNotNone(v[k])

        v = bookmark_db.copy_properties(server, job, root, asset=u'asset', table=bookmark_db.AssetTable)
        self.assertIsNotNone(v)
        self.assertIsInstance(v, dict)
        for k in bookmark_db.TABLES[bookmark_db.AssetTable]:
            if k == 'id':
                continue
            self.assertIn(k, v)
            self.assertIsNotNone(v[k])

        for _ in xrange(10):
            bookmark_db.paste_properties(server, job, root, asset=base.random_unicode(32), table=bookmark_db.AssetTable)

    def test_contextmanager(self):
        from .. import bookmark_db
        server, job, root = common.local_parent_paths()
        root += '3'
        with bookmark_db.transactions(server, job, root) as db:
            self.assertTrue(db.is_valid())

    def test_contextmanager2(self):
        from .. import bookmark_db
        server, job, root = common.local_parent_paths()
        root += '3'

        with bookmark_db.transactions(server, job, root) as db:
            self.assertTrue(db.is_valid())
