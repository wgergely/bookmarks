"""Bookmarks test environment setup and teardown."""
import os

from . import base
from .. import common


class Test(base.BaseCase):
    def test_initialize(self):
        self.assertTrue(common.init_mode == common.StandaloneMode)
        self.assertIsNotNone(common.active_mode)
        self.assertIsNotNone(common.stylesheet)
        self.assertIsNotNone(common.signals)
        self.assertIsNotNone(common.settings)
        self.assertIsNotNone(common.cursor)
        self.assertIsNotNone(common.font_db)
        self.assertIsNotNone(common.product)
        self.assertIsNotNone(common.env_key)
        self.assertIsNotNone(common.bookmark_cache_dir)
        self.assertIsNotNone(common.favorite_file_ext)
        self.assertIsNotNone(common.default_bookmarks_template)
        self.assertIsNotNone(common.max_list_items)
        self.assertIsNotNone(common.ui_scale_factors)
        self.assertIsNotNone(common.bold_font)
        self.assertIsNotNone(common.medium_font)
        self.assertIsNotNone(common.size_font_small)
        self.assertIsNotNone(common.size_font_medium)
        self.assertIsNotNone(common.size_font_large)
        self.assertIsNotNone(common.size_row_height)
        self.assertIsNotNone(common.size_bookmark_row_height)
        self.assertIsNotNone(common.size_asset_row_height)
        self.assertIsNotNone(common.size_separator)
        self.assertIsNotNone(common.size_margin)
        self.assertIsNotNone(common.size_indicator)
        self.assertIsNotNone(common.size_width)
        self.assertIsNotNone(common.size_height)
        self.assertIsNotNone(common.color_background)
        self.assertIsNotNone(common.color_light_background)
        self.assertIsNotNone(common.color_dark_background)
        self.assertIsNotNone(common.color_text)
        self.assertIsNotNone(common.color_secondary_text)
        self.assertIsNotNone(common.color_selected_text)
        self.assertIsNotNone(common.color_disabled_text)
        self.assertIsNotNone(common.color_separator)
        self.assertIsNotNone(common.color_blue)
        self.assertIsNotNone(common.color_red)
        self.assertIsNotNone(common.color_green)
        self.assertIsNotNone(common.color_opaque)
        self.assertIsNotNone(common.main_widget)

    def test_config_resources(self):
        with self.assertRaises(RuntimeError):
            common.rsc(base.random_str(32))

        self.assertIsInstance(common.rsc('icon.ico'), str)
        self.assertTrue(os.path.isfile(common.rsc('icon.ico')))

        self.assertIsInstance(common.rsc(common.stylesheet_file), str)
        self.assertTrue(os.path.isfile(common.rsc(common.stylesheet_file)))

    def test_check_type(self):
        common.typecheck_on = True
        with self.assertRaises(TypeError):
            common.check_type(base.random_str(32), int)

        common.check_type(base.random_str(32), str)

        common.typecheck_on = False
        common.check_type(base.random_str(32), int)

        common.typecheck_on = True

    def test_get_hash(self):
        with self.assertRaises(TypeError):
            common.get_hash(0)
        with self.assertRaises(TypeError):
            common.get_hash(1.0)
        with self.assertRaises(TypeError):
            common.get_hash({})

        v = base.random_str(128)
        _v = common.get_hash(v)
        self.assertIsInstance(_v, str)

    def test_get_platform(self):
        self.assertIn(
            common.get_platform(),
            (common.PlatformWindows, common.PlatformMacOS, common.PlatformUnsupported)
        )

    def test_get_username(self):
        self.assertIsInstance(common.get_username(), str)

    def test_pseudo_local_bookmark(self):
        self.assertIsInstance(common.pseudo_local_bookmark(), tuple)
        self.assertTrue(all(common.pseudo_local_bookmark()))

    def test_temp_path(self):
        self.assertIsInstance(common.temp_path(), str)
        self.assertTrue(os.path.isdir(common.temp_path()))

    def test_DataDict(self):
        d = common.DataDict()
        self.assertIsInstance(d, dict)

    def test_Timer(self):
        from PySide2 import QtCore
        t = common.Timer(parent=self)
        self.assertIsInstance(t, QtCore.QTimer)

    def test_ui_scale(self):
        self.assertIsInstance(common.ui_scale_factor, float)
        self.assertIn(common.ui_scale_factor, common.ui_scale_factors)

    def test_active_mode(self):
        self.assertIsInstance(common.active_mode, int)
        self.assertIn(
            common.active_mode,
            (common.SynchronisedActivePaths, common.PrivateActivePaths)
        )

    def test_init_font_db(self):
        self.assertIsInstance(common.font_db, common.FontDatabase)

    def test_size(self):
        self.assertEqual(common.size(10), common.size(10.5))
        self.assertIsInstance(common.size(10), int)

    def test_proxy_path(self):
        seq_path = '{}/{}_v001.ext'.format(
            base.random_str(16), base.random_str(16)
        )
        non_seq_path = '{}/{}_abcd.ext'.format(
            base.random_str(16), base.random_str(16)
        )

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
            base.random_str(32), base.random_str(32)
        )
        non_seq_path = '{}/{}_abcd.ext'.format(
            base.random_str(32), base.random_str(32)
        )
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

    def test_get_data(self):
        p = (base.random_str(16), base.random_str(16), base.random_str(16))
        k = base.random_str(16)
        t = common.FileItem

        d = common.get_data(p, k, t)
        self.assertIsInstance(d, common.DataDict)
        _d = common.get_data(p, k, t)
        self.assertIs(d, _d)

        _d = common.get_data(p, k, common.SequenceItem)
        self.assertIsInstance(_d, common.DataDict)
        self.assertIsNot(d, _d)

    def test_get_task_data(self):
        p = (base.random_str(16), base.random_str(16), base.random_str(16))
        k = base.random_str(16)

        d = common.get_task_data(p, k)
        self.assertIsInstance(d, common.DataDict)
        _d = common.get_task_data(p, k)
        self.assertIs(d, _d)
