# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
from PySide2 import QtCore, QtWidgets

from .. import common

from . import base


class Test(base.NonInitializedAppTest):
    def test_init_standalone(self):
        common.init_standalone()
        self.assertTrue(common.get_init_mode() == common.StandaloneMode)

    def test_init_settings(self):

        self.assertIsNone(common._instance)
        common.init_settings()
        self.assertIsInstance(common._instance, common.Settings)

    def test_init_resources(self):
        from .. import images
        self.assertFalse(images.RESOURCES[images.GuiResource])
        common.init_resources()
        self.assertTrue(images.RESOURCES[images.GuiResource])

    def test_init_ui_scale(self):

        self.assertIsInstance(common.ui_scale_factor, float)
        common.init_ui_scale()
        self.assertIsInstance(common.ui_scale_factor, float)
        self.assertIn(common.ui_scale_factor, common.scale_factors)

    def test_init_session_lock(self):
        self.assertIsInstance(common.session_mode, int)
        common.init_session_lock()
        self.assertIsInstance(common.session_mode, int)
        self.assertIn(
            common.session_mode,
            (common.SyncronisedActivePaths, common.PrivateActivePaths)
        )

    def test_init_font_db(self):
        common.init_font_db()
        self.assertIsInstance(common.font_db, common.FontDatabase)

    def test_psize(self):

        self.assertIsInstance(common.psize(10), float)

    def test_sizes(self):

        self.assertIsInstance(common.size(common.FontSizeSmall), int)
        self.assertIsInstance(common.size(common.FontSizeMedium), int)
        self.assertIsInstance(common.size(common.FontSizeLarge), int)

        self.assertIsInstance(common.size(common.HeightRow), int)
        self.assertIsInstance(common.size(common.HeightBookmark), int)
        self.assertIsInstance(common.size(common.HeightAsset), int)
        self.assertIsInstance(common.size(common.HeightSeparator), int)
        self.assertIsInstance(common.size(common.WidthMargin), int)
        self.assertIsInstance(common.size(common.WidthIndicator), int)
        self.assertIsInstance(common.size(common.DefaultWidth), int)
        self.assertIsInstance(common.size(common.DefaultHeight), int)

    def test_hash(self):

        self.assertIsInstance(common.hashes, dict)
        self.assertFalse(common.hashes)

        with self.assertRaises(TypeError):
            common.get_hash(0)
        with self.assertRaises(TypeError):
            common.get_hash(1.0)
        with self.assertRaises(TypeError):
            common.get_hash({})

        v = base.random_str(128)
        _v = common.get_hash(v)
        self.assertIsInstance(_v, str)
        self.assertTrue(common.hashes)
        self.assertEqual(len(common.hashes), 1)

        for _ in range(10):
            _v = common.get_hash(v)
        self.assertEqual(len(common.hashes), 1)

    def test_proxy_path(self):
        seq_path = '{}/{}_v001.ext'.format(
            base.random_str(16), base.random_str(16))
        non_seq_path = '{}/{}_abcd.ext'.format(
            base.random_str(16), base.random_str(16))

        self.assertNotEqual(seq_path, non_seq_path)

        with self.assertRaises(TypeError):
            common.proxy_path(0)
        with self.assertRaises(TypeError):
            common.proxy_path(0.0)
        with self.assertRaises(TypeError):
            common.proxy_path(None)

        seq = common.proxy_path(non_seq_path)
        self.assertEqual(seq, non_seq_path)
        seq = common.proxy_path(seq_path)

        self.assertIn(common.SEQSTART, seq)
        self.assertIn(common.SEQEND, seq)
        self.assertIn(common.SEQPROXY, seq)

    def test_is_collapsed(self):
        with self.assertRaises(TypeError):
            common.is_collapsed(None)
        with self.assertRaises(TypeError):
            common.is_collapsed(dict)
        with self.assertRaises(TypeError):
            common.is_collapsed(0)
        with self.assertRaises(TypeError):
            common.is_collapsed(0.0)

        collapsed_path = '{}/{}_{}_{}.ext'.format(
            base.random_str(32),
            base.random_str(32),
            common.SEQPROXY,
            base.random_str(32),
        )
        collapsed_path2 = '{}/{}_{}1-10{}_{}.ext'.format(
            base.random_str(32),
            base.random_str(32),
            common.SEQSTART,
            common.SEQEND,
            base.random_str(32),
        )
        noncollapsed_path = '{}/{}_v001_{}.ext'.format(
            base.random_str(32),
            base.random_str(32),
            base.random_str(32),
        )

        c = common.is_collapsed(collapsed_path)
        self.assertIsNotNone(c)
        c = common.is_collapsed(collapsed_path2)
        self.assertIsNotNone(c)
        c = common.is_collapsed(noncollapsed_path)
        self.assertIsNone(c)

    def test_get_sequence(self):
        with self.assertRaises(TypeError):
            common.get_sequence(None)
        with self.assertRaises(TypeError):
            common.get_sequence(0)

        seq_path = '{}/{}_v001.ext'.format(
            base.random_str(32), base.random_str(32))
        non_seq_path = '{}/{}_abcd.ext'.format(
            base.random_str(32), base.random_str(32))
        self.assertNotEqual(seq_path, non_seq_path)

        collapsed_path = '{}/{}_{}_{}.ext'.format(
            base.random_str(32),
            base.random_str(32),
            common.SEQPROXY,
            base.random_str(32),
        )
        with self.assertRaises(RuntimeError):
            common.get_sequence(collapsed_path)

        seq = common.get_sequence(non_seq_path)
        self.assertFalse(seq)

        seq = common.get_sequence(seq_path)
        self.assertTrue(seq)
        self.assertEqual(len(seq.groups()), 4)
        for grp in seq.groups():
            self.assertIsInstance(grp, str)
