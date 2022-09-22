# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
import os
import shutil

from PySide2 import QtCore, QtGui

from . import base
from .. import common


class Test(base.BaseCase):

    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()

        if not os.path.exists(common.temp_path()):
            os.makedirs(common.temp_path())
        assert os.path.isdir(common.temp_path())
        open(common.temp_path() + '/' + 'thumbnail.png', 'a').close()

        root = __file__ + os.sep + os.pardir + os.sep + \
               os.pardir + os.sep + 'rsc' + os.sep + 'gui'
        root = os.path.normpath(root)
        for f in os.listdir(root):
            shutil.copy(root + os.sep + f, common.temp_path())

    def test_get_oiio_namefilters(self):
        from .. import images
        v = images.get_oiio_namefilters()
        self.assertIsNotNone(v)
        self.assertIsInstance(v, str)
        self.assertIn('png', v)
        self.assertIn('jpg', v)

    def test_get_oiio_extensions(self):
        from .. import images
        v = images.get_oiio_extensions()
        self.assertIsNotNone(v)
        self.assertIsInstance(v, list)
        self.assertIn('png', v)
        self.assertIn('jpg', v)

    def test_get_placeholder_path(self):
        from .. import images
        for ext in ('ma', 'aep'):
            p = base.random_str(32) + '.' + ext

            v = images.get_placeholder_path(p, 'placeholder')
            self.assertIsInstance(v, str)
            self.assertTrue(os.path.isfile(v))

    def test_oiio_make_thumbnail(self):
        from .. import images
        server, job, root = common.pseudo_local_bookmark()
        size = int(round(common.thumbnail_size * 0.5))

        for f in os.listdir(common.temp_path()):
            if '.png' not in f:
                continue
            if 'thumbnail.png' == f:
                continue

            source = QtCore.QFileInfo(
                common.temp_path() + os.path.sep + f).filePath()
            self.assertTrue(os.path.isfile(source))

            dest = images.get_cached_thumbnail_path(server, job, root, source)
            self.assertIsInstance(dest, str)

            d = QtCore.QFileInfo(dest).dir()
            d.mkpath('.')
            self.assertTrue(os.path.isdir(d.path()))

            res = images.ImageCache.oiio_make_thumbnail(source, dest, size)
            self.assertTrue(res)
            self.assertTrue(os.path.isfile(dest))

    def test_get_thumbnail(self):
        from .. import images
        server, job, root = common.pseudo_local_bookmark()

        # Invalid
        source = '/'.join((server, job, root, 'thumbnail.png'))
        self.assertTrue(os.path.isfile(source))

        # Invalid
        v = images.get_thumbnail(
            server, job, root, source, size=common.thumbnail_size)
        self.assertIsInstance(v, tuple)

        self.assertIsInstance(v[0], QtGui.QPixmap)
        self.assertIsNone(v[1])

        self.assertFalse(v[0].isNull())
        m = max(v[0].size().height(), v[0].size().width())
        self.assertEqual(m, common.thumbnail_size * common.pixel_ratio)

        s = int(common.thumbnail_size)
        for f in os.listdir(common.temp_path()):
            if '.png' not in f:
                continue
            if f == 'thumbnail.png':
                continue

            file_info = QtCore.QFileInfo(common.temp_path() + os.path.sep + f)
            source = file_info.filePath()

            dest = images.get_cached_thumbnail_path(server, job, root, source)
            d = QtCore.QFileInfo(dest).dir()
            d.mkpath('.')
            self.assertTrue(os.path.isdir(d.path()))

            res = images.ImageCache.oiio_make_thumbnail(source, dest, s)
            self.assertTrue(res)
            self.assertTrue(os.path.isfile(dest))

            v = images.get_thumbnail(
                server,
                job,
                root,
                source,
                size=common.thumbnail_size,
                fallback_thumb='bogusfallback'
            )
            self.assertIsInstance(v, tuple)

            self.assertIsInstance(v[0], QtGui.QPixmap)
            self.assertIsInstance(v[1], QtGui.QColor)

            self.assertFalse(v[0].isNull())

            m = max(v[0].size().height(), v[0].size().width())
            self.assertEqual(m, s * common.pixel_ratio)

    def test_get_cached_thumbnail_path(self):
        from .. import images
        server, job, root = common.pseudo_local_bookmark()
        arr = []

        for _ in range(999):
            v = images.get_cached_thumbnail_path(
                server, job, root,
                base.random_str(16)
            )
            arr.append(v)
            self.assertIsInstance(v, str)
        self.assertEqual(len(arr), len(set(arr)))

    def test_image_cache(self):
        from .. import images
        for f in os.listdir(common.temp_path()):
            if f == 'thumbnail.png':
                continue
            if 'png' not in f:
                continue
            p = common.temp_path() + '/' + f
            self.assertTrue(os.path.isfile(p))

            s = int(common.thumbnail_size)
            v = images.ImageCache.get_pixmap(p, s)
            self.assertIsInstance(v, QtGui.QPixmap)
            self.assertFalse(v.isNull())
            self.assertEqual(
                max(v.size().width(), v.size().height()),
                s
            )

            s = int(common.thumbnail_size / 0.5)
            v = images.ImageCache.get_pixmap(p, s)
            self.assertIsInstance(v, QtGui.QPixmap)
            self.assertFalse(v.isNull())
            self.assertEqual(v.size().width(), s)

            s = int(common.thumbnail_size * 2)
            v = images.ImageCache.get_pixmap(p, s)
            self.assertIsInstance(v, QtGui.QPixmap)
            self.assertFalse(v.isNull())
            self.assertEqual(v.size().width(), s)

            s = int(common.thumbnail_size)
            v = images.ImageCache.get_image(p, s)
            self.assertIsInstance(v, QtGui.QImage)
            self.assertFalse(v.isNull())
            self.assertEqual(v.size().width(), s)

            s = int(common.thumbnail_size / 0.5)
            v = images.ImageCache.get_image(p, s)
            self.assertIsInstance(v, QtGui.QImage)
            self.assertFalse(v.isNull())
            self.assertEqual(v.size().width(), s)

            s = int(common.thumbnail_size * 2)
            v = images.ImageCache.get_image(p, s)
            self.assertIsInstance(v, QtGui.QImage)
            self.assertFalse(v.isNull())
            self.assertEqual(v.size().width(), s)
