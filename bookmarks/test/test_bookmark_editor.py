# -*- coding: utf-8 -*-
import os

from PySide2 import QtCore

from . import base
from .. import common


class Test(base.BaseCase):
    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()

        if not os.path.isdir(common.temp_path()):
            os.makedirs(common.temp_path())

    def test_server_editor(self):
        from ..bookmark_editor import server_editor
        v = server_editor.ServerListWidget()

        self.assertIsInstance(v, server_editor.ServerListWidget)
        v.init_data()

    def test_job_editor(self):
        from ..bookmark_editor import job_editor
        v = job_editor.JobListWidget()

        self.assertIsInstance(v, job_editor.JobListWidget)
        v.init_data()
        self.assertEqual(v.count(), 0)

    def test_bookmark_editor(self):
        from ..bookmark_editor import bookmark_editor
        v = bookmark_editor.BookmarkListWidget()

        self.assertIsInstance(v, bookmark_editor.BookmarkListWidget)
        v.init_data()
        self.assertEqual(v.count(), 0)

    def test_bookmark_editor_widget(self):
        from ..bookmark_editor import server_editor
        from ..bookmark_editor import job_editor
        from ..bookmark_editor import bookmark_editor_widget
        from .. import actions

        v = bookmark_editor_widget.BookmarkEditorWidget()

        self.assertIsInstance(v, bookmark_editor_widget.BookmarkEditorWidget)
        v.init_data()

        s = v.server_editor
        self.assertIsInstance(s, server_editor.ServerListWidget)
        j = v.job_editor
        self.assertIsInstance(j, job_editor.JobListWidget)

        # ==============================================================
        # Testing servers
        servers = {}
        for n in range(5):
            server = common.temp_path() + os.sep + base.random_ascii(32)
            os.makedirs(server)
            servers[server] = server
        common.settings.set_servers(servers)

        s.init_data(reset=True)
        self.assertGreaterEqual(s.count(), len(servers))

        for n in range(s.count()):
            _v = s.item(n).data(QtCore.Qt.DisplayRole)
            self.assertTrue(os.path.isdir(_v))

        for server in servers.keys():
            actions.remove_server(server)

        self.assertEqual(len(common.servers), 0)
        self.assertEqual(s.count(), 0)

        # Add test server and select it
        server = common.temp_path() + '/' + base.random_str(32)
        if not os.path.isdir(server):
            os.makedirs(server)

        self.assertTrue(os.path.isdir(server))
        self.assertNotIn(server, common.servers)
        actions.add_server(server)
        self.assertIn(server, common.servers)

        for idx in range(s.count()):
            item = s.item(idx)
            if item.data(QtCore.Qt.DisplayRole) == server:
                s.setCurrentItem(item)
                break

        self.assertEqual(s.currentItem().data(QtCore.Qt.DisplayRole), server)
        self.assertEqual(j.server, server)
        self.assertTrue(QtCore.QFileInfo(server).exists())


        #########################################################
        # Test jobs

        # Add a series of folders to the root of the server
        for idx in range(10):
            job = base.random_str(16)
            path = server + '/' + job

            QtCore.QDir(path).mkpath('.')
            self.assertTrue(os.path.isdir(path))

        self.assertEqual(j.model().rowCount(), 0)
        j.init_data()
        self.assertEqual(j.model().rowCount(), 10)

    def test_create_job_template(self):
        from ..bookmark_editor import server_editor
        from ..bookmark_editor import job_editor
        from ..bookmark_editor import bookmark_editor
        from ..bookmark_editor import bookmark_editor_widget
        from ..templates import actions as actions

        v = bookmark_editor_widget.BookmarkEditorWidget()

        self.assertIsInstance(v, bookmark_editor_widget.BookmarkEditorWidget)
        v.init_data()

        s = v.server_editor
        self.assertIsInstance(s, server_editor.ServerListWidget)
        j = v.job_editor
        self.assertIsInstance(j, job_editor.JobListWidget)
        b = v.bookmark_editor
        self.assertIsInstance(b, bookmark_editor.BookmarkListWidget)

        self.assertEqual(b.count(), 0)

        # Add test server and select it
        server = common.temp_path() + '/' + base.random_str(48)
        self.assertNotIn(server, common.servers)
        actions.add_server(server)
        self.assertIn(server, common.servers)

        if not os.path.isdir(server):
            os.makedirs(server)

        for idx in range(s.count()):
            item = s.item(idx)
            if item.data(QtCore.Qt.DisplayRole) == server:
                s.setCurrentItem(item)
                break
        self.assertEqual(s.currentItem().data(QtCore.Qt.DisplayRole), server)

        # Template path
        t = __file__ + os.sep + os.pardir + os.sep + os.pardir + os.sep + 'rsc' + \
            os.sep + 'templates' + os.sep + 'Bookmarks_Default_Job.zip'
        t = os.path.normpath(t)
        t = str(t)
        self.assertTrue(os.path.isfile(t))
        self.assertTrue(os.path.isdir(server))

        for _ in range(50):
            job = base.random_ascii(32)

            self.assertIsInstance(t, str)
            self.assertIsInstance(server, str)
            self.assertIsInstance(job, str)

            # Will trigger an automatic reload and select
            v = actions.extract_zip_template(t, server, job)
            self.assertIsNotNone(v)
            self.assertTrue(os.path.isdir(v))

            # The default template has 3 bookmarks in it
            self.assertGreater(b.count(), 0)

        self.assertEqual(j.count(), 50)
