# -*- coding: utf-8 -*-
import os
from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import settings
from .. import main
from ..bookmark_editor import server_editor
from ..bookmark_editor import job_editor
from ..bookmark_editor import bookmark_editor
from ..bookmark_editor import bookmark_editor_widget
from .. import actions
from ..templates import actions as template_actions
from . import base


class Test(base.BaseApplicationTest):
    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()

        common.init_standalone()
        common.init_pixel_ratio()
        common.init_ui_scale()
        common.init_session_lock()
        common.init_settings()
        common.init_font_db()

        if not os.path.isdir(common.temp_path()):
            os.makedirs(common.temp_path())

    def test_add_server(self):
        self.assertFalse(common.SERVERS)
        v = base.random_unicode(32)
        actions.add_server(v)
        self.assertIn(v, common.SERVERS)

    def test_remove_server(self):
        v = base.random_unicode(32)
        actions.add_server(v)
        self.assertIn(v, common.SERVERS)
        actions.remove_server(v)
        self.assertNotIn(v, common.SERVERS)

    def test_add_bookmark(self):
        self.assertFalse(common.BOOKMARKS)

        with self.assertRaises(TypeError):
            actions.add_bookmark('server', 'job', 'root')

        with self.assertRaises(TypeError):
            actions.add_bookmark(None, None, None)

        server = base.random_unicode(32)
        job = base.random_unicode(32)
        root = base.random_unicode(32)
        k = settings.bookmark_key(server, job, root)

        actions.add_bookmark(server, job, root)

        self.assertIn(k, common.BOOKMARKS)

    def test_remove_bookmark(self):
        server = base.random_unicode(32)
        job = base.random_unicode(32)
        root = base.random_unicode(32)
        k = settings.bookmark_key(server, job, root)
        actions.add_bookmark(server, job, root)
        self.assertIn(k, common.BOOKMARKS)

        actions.remove_bookmark(server, job, root)
        self.assertNotIn(k, common.BOOKMARKS)

    def test_add_favourite(self):
        self.assertFalse(common.FAVOURITES)

        with self.assertRaises(TypeError):
            actions.add_favourite(None, None)

        server = base.random_unicode(32)
        job = base.random_unicode(32)
        root = base.random_unicode(32)
        parent_paths = (server, job, root)
        source = settings.bookmark_key(server, job, root) + '/' + base.random_unicode(32)

        actions.add_favourite(parent_paths, source)
        self.assertIn(source, common.FAVOURITES)

    def test_remove_favourite(self):
        server = base.random_unicode(32)
        job = base.random_unicode(32)
        root = base.random_unicode(32)
        parent_paths = (server, job, root)
        source = settings.bookmark_key(server, job, root) + '/' + base.random_unicode(32)

        actions.add_favourite(parent_paths, source)
        self.assertIn(source, common.FAVOURITES)

        actions.remove_favourite(parent_paths, source)
        self.assertNotIn(source, common.FAVOURITES)

    def test_clear_favourites(self):
        for _ in xrange(999):
            server = base.random_unicode(32)
            job = base.random_unicode(32)
            root = base.random_unicode(32)
            parent_paths = (server, job, root)
            source = settings.bookmark_key(server, job, root) + '/' + base.random_unicode(32)

            actions.add_favourite(parent_paths, source)
            self.assertIn(source, common.FAVOURITES)

        actions.clear_favourites(prompt=False)
        self.assertFalse(common.FAVOURITES)


    def test_export_favourites(self):
        for _ in xrange(999):
            server = base.random_unicode(32)
            job = base.random_unicode(32)
            root = base.random_unicode(32)
            parent_paths = (server, job, root)
            source = settings.bookmark_key(server, job, root) + '/' + base.random_unicode(32)

            actions.add_favourite(parent_paths, source)
            self.assertIn(source, common.FAVOURITES)

        for _ in xrange(3):
            self.assertTrue(common.FAVOURITES)
            destination = common.temp_path()
            if not os.path.isdir(destination):
                os.makedirs(destination)
            self.assertTrue(os.path.isdir(destination))

            destination = common.temp_path() + u'/' + base.random_unicode(12) + '.' + common.FAVOURITE_FILE_FORMAT

            with self.assertRaises(TypeError):
                actions.export_favourites(destination='dest')

            v = actions.export_favourites(destination=destination)
            self.assertIsNotNone(v)
            self.assertTrue(os.path.isfile(v))

    def test_import_favourites(self):
        for _ in xrange(3):
            self.assertTrue(common.FAVOURITES)
            destination = common.temp_path()
            if not os.path.isdir(destination):
                os.makedirs(destination)
            destination = common.temp_path() + u'/' + base.random_unicode(12) + '.' + common.FAVOURITE_FILE_FORMAT
            actions.export_favourites(destination=destination)

        for f in os.listdir(common.temp_path()):
            if common.FAVOURITE_FILE_FORMAT not in f:
                continue
            actions.import_favourites(common.temp_path() + u'/' + f)

    def test_prune_bookmarks(self):
        actions.prune_bookmarks()

    def test_set_active(self):
        with self.assertRaises(ValueError):
            actions.set_active(None, None)

        for k in settings.ACTIVE_KEYS:
            actions.set_active(k, base.random_unicode(32))

        # Should reset and invalidate all active paths if they don't correspont
        # to real folders (the case here)
        settings.instance().verify_active()

        for k in settings.ACTIVE_KEYS:
            self.assertIsNone(settings.active(k))



class TestWidgetActions(base.BaseApplicationTest):
    @classmethod
    def setUpClass(cls):
        super(TestWidgetActions, cls).setUpClass()

        common.init_standalone()
        common.init_pixel_ratio()
        common.init_ui_scale()
        common.init_session_lock()
        common.init_settings()
        common.init_font_db()

        if not os.path.isdir(common.temp_path()):
            os.makedirs(common.temp_path())

        server = common.temp_path() + u'/' + base.random_ascii(16)
        if not os.path.isdir(server):
            os.makedirs(server)
        actions.add_server(server)


        # Template path
        t = __file__ + os.sep + os.pardir + os.sep + os.pardir + os.sep + 'rsc' + os.sep + 'templates' + os.sep + 'Bookmarks_Default_Job.zip'
        t = os.path.normpath(t)
        t = unicode(t)

        for _ in xrange(2):
            job = base.random_ascii(16)
            v = template_actions.extract_zip_template(t, server, job)

            actions.add_bookmark(server, job, u'data/asset')
            actions.add_bookmark(server, job, u'data/shot')

            # Add a random files to the dir
        #     for seq in (base.random_ascii(16), u'_v001', u'_v002', u'_v003'):
        #         for ext in ('.png', '.ma'):
        #             for f in os.listdir(v):
        #                 p = v + u'/' + f
        #                 for _ in xrange(3):
        #                         f = p + u'/' + base.random_ascii(8) + seq + ext
        #                         open(f, 'w').close()

        # main.init()

    # def test_activate(self):
    #     self.assertIsNotNone(main.instance())
    #
    #     w = main.instance().stackedwidget.widget(common.BookmarkTab)
    #     self.assertGreater(w.model().rowCount(), 0)
    #
    #     _w = main.instance().stackedwidget.widget(common.AssetTab)
    #     self.assertEqual(_w.model().rowCount(), 0)
    #
    #     for idx in xrange(w.model().rowCount()):
    #         index = w.model().index(idx, 0)
    #         w.activate(index)
    #         break
    #     for idx in xrange(w.model().rowCount()):
    #         index = w.model().index(idx, 0)
    #         self.assertTrue(index.flags() & common.MarkedAsActive)
    #         break
    #
    #     self.assertGreater(_w.model().rowCount(), 0)

    def test_toggle_sequence(self):
        pass

        # self.assertIsNotNone(main.instance())

        # w = main.instance().stackedwidget.widget(common.BookmarkTab)
        # self.assertGreater(w.model().rowCount(), 0)
        #
        # for idx in xrange(w.model().rowCount()):
        #     index = w.model().index(idx, 0)
        #     w.activate(index)
        #     break
        # for idx in xrange(w.model().rowCount()):
        #     index = w.model().index(idx, 0)
        #     self.assertTrue(index.flags() & common.MarkedAsActive)
        #     break
        #
        # self.assertGreater(_w.model().rowCount(), 0)
