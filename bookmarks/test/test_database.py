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

        server, job, root = common.pseudo_local_bookmark()
        db = database.BookmarkDB(server, job, root)
        self.assertTrue(db.is_valid())

    def test_value(self):
        from .. import common
        from .. import database
        db = database.BookmarkDB(*common.pseudo_local_bookmark())
        self.assertTrue(db.is_valid())

        self.assertIn(database.AssetTable, database.TABLES)
        self.assertIn(database.BookmarkTable, database.TABLES)
        self.assertIn(database.InfoTable, database.TABLES)

        for t in (database.BookmarkTable, database.AssetTable):
            for k in database.TABLES[t]:
                v = db.value(db.source(), k, t)
                self.assertIsNone(v)

        with self.assertRaises(TypeError):
            db.value(b'str', b'description', t)
        with self.assertRaises(TypeError):
            db.value(db.source(), base.random_ascii(), t)
        with self.assertRaises(ValueError):
            db.value(db.source(), base.random_str(36), t)

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
                    v = {0: base.random_ascii(36), 1: base.random_str(36)}
                    db.setValue(db.source(), k, v, t)
                    _v = db.value(db.source(), k, t)
                    self.assertNotEqual(v, _v)

                    v = {'0': base.random_ascii(
                        128), '1': base.random_str(128)}
                else:
                    v = None

                db.setValue(db.source(), k, v, t)
                _v = db.value(db.source(), k, t)
                self.assertEqual(_v, v)
                self.assertIsInstance(_v, _type)

    def test_invalid(self):
        from .. import common
        from .. import database
        server, job, root = common.pseudo_local_bookmark()
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

                db.setValue(db.source(), k, v, t)
                _v = db.value(db.source(), k, t)
                self.assertIsNone(_v)
