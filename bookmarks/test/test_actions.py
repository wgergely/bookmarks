# -*- coding: utf-8 -*-
import os
from PySide2 import QtCore, QtGui, QtWidgets

from .. import actions
from .. import common
from .. import templates

from . import base


class Test(base.BaseCase):
    def test_add_server(self):
        self.assertFalse(common.servers)
        v = base.random_str(32)
        actions.add_server(v)
        self.assertIn(v, common.servers)

    def test_remove_server(self):
        v = base.random_str(32)
        actions.add_server(v)
        self.assertIn(v, common.servers)
        actions.remove_server(v)
        self.assertNotIn(v, common.servers)

    def test_add_bookmark(self):
        self.assertFalse(common.bookmarks)

        with self.assertRaises(TypeError):
            actions.add_bookmark(None, None, None)

        server = base.random_str(32)
        job = base.random_str(32)
        root = base.random_str(32)
        k = common.bookmark_key(server, job, root)

        actions.add_bookmark(server, job, root)

        self.assertIn(k, common.bookmarks)

    def test_remove_bookmark(self):
        server = base.random_str(32)
        job = base.random_str(32)
        root = base.random_str(32)
        k = common.bookmark_key(server, job, root)
        actions.add_bookmark(server, job, root)
        self.assertIn(k, common.bookmarks)

        actions.remove_bookmark(server, job, root)
        self.assertNotIn(k, common.bookmarks)

    def test_add_favourite(self):
        self.assertFalse(common.favourites)

        with self.assertRaises(TypeError):
            actions.add_favourite(None, None)

        server = base.random_str(32)
        job = base.random_str(32)
        root = base.random_str(32)
        source_paths = (server, job, root)
        source = common.bookmark_key(
            server, job, root) + '/' + base.random_str(32)

        actions.add_favourite(source_paths, source)
        self.assertIn(source, common.favourites)

    def test_remove_favourite(self):
        server = base.random_str(32)
        job = base.random_str(32)
        root = base.random_str(32)
        source_paths = (server, job, root)
        source = common.bookmark_key(
            server, job, root) + '/' + base.random_str(32)

        actions.add_favourite(source_paths, source)
        self.assertIn(source, common.favourites)

        actions.remove_favourite(source_paths, source)
        self.assertNotIn(source, common.favourites)

    def test_clear_favourites(self):
        for _ in range(999):
            server = base.random_str(32)
            job = base.random_str(32)
            root = base.random_str(32)
            source_paths = (server, job, root)
            source = common.bookmark_key(
                server, job, root) + '/' + base.random_str(32)

            actions.add_favourite(source_paths, source)
            self.assertIn(source, common.favourites)

        actions.clear_favourites(prompt=False)
        self.assertFalse(common.favourites)

    def test_export_favourites(self):
        for _ in range(999):
            server = base.random_str(32)
            job = base.random_str(32)
            root = base.random_str(32)
            source_paths = (server, job, root)
            source = common.bookmark_key(
                server, job, root) + '/' + base.random_str(32)

            actions.add_favourite(source_paths, source)
            self.assertIn(source, common.favourites)

        for _ in range(3):
            self.assertTrue(common.favourites)
            destination = common.temp_path()
            if not os.path.isdir(destination):
                os.makedirs(destination)
            self.assertTrue(os.path.isdir(destination))

            destination = common.temp_path() + '/' + base.random_str(12) + \
                '.' + common.FAVOURITE_FILE_FORMAT

            v = actions.export_favourites(destination=destination)
            self.assertIsNotNone(v)
            self.assertTrue(os.path.isfile(v))

    def test_import_favourites(self):
        for _ in range(3):
            self.assertTrue(common.favourites)
            destination = common.temp_path()
            if not os.path.isdir(destination):
                os.makedirs(destination)
            destination = common.temp_path() + '/' + base.random_str(12) + \
                '.' + common.FAVOURITE_FILE_FORMAT
            actions.export_favourites(destination=destination)

        for f in os.listdir(common.temp_path()):
            if common.FAVOURITE_FILE_FORMAT not in f:
                continue
            actions.import_favourites(common.temp_path() + '/' + f)

    def test_prune_bookmarks(self):
        actions.prune_bookmarks()

    def test_set_active(self):
        with self.assertRaises(ValueError):
            actions.set_active(None, None)

        for k in common.ActiveSectionCacheKeys:
            actions.set_active(k, base.random_str(32))

        # Should reset and invalidate all active paths if they don't correspont
        # to real folders (the case here)
        common.settings.load_active_values()

        for k in common.ActiveSectionCacheKeys:
            self.assertIsNone(common.active(k))


class TestWidgetActions(base.BaseCase):
    @classmethod
    def setUpClass(cls):
        super(TestWidgetActions, cls).setUpClass()

        server = common.temp_path() + '/' + base.random_ascii(16)
        if not os.path.isdir(server):
            os.makedirs(server)
        actions.add_server(server)

        # Template path
        t = __file__ + os.sep + os.pardir + os.sep + os.pardir + os.sep + \
            'rsc' + os.sep + 'templates' + os.sep + 'Bookmarks_Default_Job.zip'
        t = os.path.normpath(t)

        for _ in range(2):
            job = base.random_ascii(16)
            v = templates.actions.extract_zip_template(t, server, job)

            actions.add_bookmark(server, job, 'data/asset')
            actions.add_bookmark(server, job, 'data/shot')

    # def test_activate(self):
    #     self.assertIsNotNone(main.instance())
    #
    #     w = common.widget(common.BookmarkTab)
    #     self.assertGreater(w.model().rowCount(), 0)
    #
    #     _w = common.widget(common.AssetTab)
    #     self.assertEqual(_w.model().rowCount(), 0)
    #
    #     for idx in range(w.model().rowCount()):
    #         index = w.model().index(idx, 0)
    #         w.activate(index)
    #         break
    #     for idx in range(w.model().rowCount()):
    #         index = w.model().index(idx, 0)
    #         self.assertTrue(index.flags() & common.MarkedAsActive)
    #         break
    #
    #     self.assertGreater(_w.model().rowCount(), 0)

    def test_toggle_sequence(self):
        pass

        # self.assertIsNotNone(main.instance())

        # w = common.widget(common.BookmarkTab)
        # self.assertGreater(w.model().rowCount(), 0)
        #
        # for idx in range(w.model().rowCount()):
        #     index = w.model().index(idx, 0)
        #     w.activate(index)
        #     break
        # for idx in range(w.model().rowCount()):
        #     index = w.model().index(idx, 0)
        #     self.assertTrue(index.flags() & common.MarkedAsActive)
        #     break
        #
        # self.assertGreater(_w.model().rowCount(), 0)
