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
