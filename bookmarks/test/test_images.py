# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
import os
import shutil

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import images
from . import base


class Test(base.BaseApplicationTest):

    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()

        if not os.path.exists(common.temp_path()):
            os.makedirs(common.temp_path())
        open(common.temp_path() + u'/' + u'thumbnail.png', 'a').close()

        root = __file__ + os.sep + os.pardir + os.sep + \
            os.pardir + os.sep + 'rsc' + os.sep + 'gui'
        root = os.path.normpath(root)
        for f in os.listdir(root):
            shutil.copy(root + os.sep + f, common.temp_path())

    def test_pixel_ratio(self):
        common.init_pixel_ratio()
        self.assertIsNotNone(images.pixel_ratio)
        self.assertIsInstance(images.pixel_ratio, float)

    def test_get_oiio_namefilters(self):
        v = images.get_oiio_namefilters()
        self.assertIsNotNone(v)
        self.assertIsInstance(v, unicode)
        self.assertIn(u'png', v)
        self.assertIn(u'jpg', v)

    def test_get_oiio_extensions(self):
        v = images.get_oiio_extensions()
        self.assertIsNotNone(v)
        self.assertIsInstance(v, list)
        self.assertIn(u'png', v)
        self.assertIn(u'jpg', v)

    def test_check_for_thumbnail_image(self):
        v = images.check_for_thumbnail_image(common.temp_path())
        self.assertIsNotNone(v)
        self.assertIsInstance(v, unicode)
        self.assertIsInstance(v, unicode)

        v = images.check_for_thumbnail_image(common.temp_path() + u'1')
        self.assertIsNone(v)

    def test_get_placeholder_path(self):
        for ext in (u'ma', 'aep'):
            p = base.random_unicode(32) + '.' + ext

            v = images.get_placeholder_path(p)
            self.assertIsInstance(v, unicode)
            self.assertTrue(os.path.isfile(v))

    def test_oiio_make_thumbnail(self):
        server, job, root = common.local_parent_paths()
        size = int(round(images.THUMBNAIL_IMAGE_SIZE * 0.5))

        for f in os.listdir(common.temp_path()):
            if '.png' not in f:
                continue
            if 'thumbnail.png' == f:
                continue

            source = QtCore.QFileInfo(
                common.temp_path() + os.path.sep + f).filePath()
            self.assertTrue(os.path.isfile(source))

            dest = images.get_cached_thumbnail_path(server, job, root, source)
            self.assertIsInstance(dest, unicode)

            d = QtCore.QFileInfo(dest).dir()
            d.mkpath('.')
            self.assertTrue(os.path.isdir(d.path()))

            res = images.ImageCache.oiio_make_thumbnail(source, dest, size)
            self.assertTrue(res)
            self.assertTrue(os.path.isfile(dest))

    def test_get_thumbnail(self):
        server, job, root = common.local_parent_paths()

        source = 'str.png'
        with self.assertRaises(TypeError):
            v = images.get_thumbnail(server, job, root, source)

        # Invalid
        source = u'/'.join((server, job, root, u'thumbnail.png'))
        self.assertTrue(os.path.isfile(source))

        # Invalid
        v = images.get_thumbnail(
            server, job, root, source, size=images.THUMBNAIL_IMAGE_SIZE)
        self.assertIsInstance(v, tuple)

        self.assertIsInstance(v[0], QtGui.QPixmap)
        self.assertIsNone(v[1])

        self.assertFalse(v[0].isNull())
        m = max(v[0].size().height(), v[0].size().width())
        self.assertEqual(m, images.THUMBNAIL_IMAGE_SIZE * images.pixel_ratio)

        s = int(images.THUMBNAIL_IMAGE_SIZE)
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
                size=images.THUMBNAIL_IMAGE_SIZE,
                fallback_thumb=u'bogusfallback'
            )
            self.assertIsInstance(v, tuple)

            self.assertIsInstance(v[0], QtGui.QPixmap)
            self.assertIsInstance(v[1], QtGui.QColor)

            self.assertFalse(v[0].isNull())

            m = max(v[0].size().height(), v[0].size().width())
            self.assertEqual(m, s * images.pixel_ratio)

    def test_get_cached_thumbnail_path(self):
        server, job, root = common.local_parent_paths()
        arr = []

        with self.assertRaises(TypeError):
            images.get_cached_thumbnail_path(
                server, job, root,
                'str'
            )

        for _ in xrange(999):
            v = images.get_cached_thumbnail_path(
                server, job, root,
                base.random_unicode(16)
            )
            arr.append(v)
            self.assertIsInstance(v, unicode)
        self.assertEqual(len(arr), len(set(arr)))

    def test_test_image_cache(self):
        for f in os.listdir(common.temp_path()):
            if f == 'thumbnail.png':
                continue
            if u'png' not in f:
                continue
            p = common.temp_path() + u'/' + f
            from .. import actions
            self.assertTrue(os.path.isfile(p))

            s = int(images.THUMBNAIL_IMAGE_SIZE)
            v = images.ImageCache.get_pixmap(p, s)
            self.assertIsInstance(v, QtGui.QPixmap)
            self.assertFalse(v.isNull())
            self.assertEqual(
                max(v.size().width(), v.size().height()),
                s
            )

            s = int(images.THUMBNAIL_IMAGE_SIZE / 0.5)
            v = images.ImageCache.get_pixmap(p, s)
            self.assertIsInstance(v, QtGui.QPixmap)
            self.assertFalse(v.isNull())
            self.assertEqual(v.size().width(), s)

            s = int(images.THUMBNAIL_IMAGE_SIZE)
            v = images.ImageCache.get_image(p, s)
            self.assertIsInstance(v, QtGui.QImage)
            self.assertFalse(v.isNull())
            self.assertEqual(v.size().width(), s)

            s = int(images.THUMBNAIL_IMAGE_SIZE / 0.5)
            v = images.ImageCache.get_image(p, s)
            self.assertIsInstance(v, QtGui.QImage)
            self.assertFalse(v.isNull())
            self.assertEqual(v.size().width(), s)
