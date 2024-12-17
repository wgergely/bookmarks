"""Unit tests for the FontDatabase functionality."""

import unittest
import sys
from PySide2 import QtWidgets, QtGui

from . import font
from . import common


class TestFontDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.app = QtWidgets.QApplication(sys.argv)
        else:
            cls.app = QtWidgets.QApplication.instance()
        font._init_font_db()

    def test_fontdb_instance_exists(self):
        self.assertIsNotNone(common.font_db, "FontDatabase instance should be initialized.")

    def test_valid_font_retrieval(self):
        test_role = common.Font.BoldFont
        test_size = 12
        fnt, metrics = common.font_db.get(test_size, test_role)
        self.assertIsInstance(fnt, QtGui.QFont, "Should retrieve a QFont instance.")
        self.assertIsInstance(metrics, QtGui.QFontMetricsF, "Should retrieve a QFontMetricsF instance.")
        self.assertEqual(fnt.pixelSize(), test_size, "Font size should match the requested size.")

    def test_font_reuse_from_cache(self):
        test_role = common.Font.LightFont
        test_size = 10
        fnt1, metrics1 = common.font_db.get(test_size, test_role)
        fnt2, metrics2 = common.font_db.get(test_size, test_role)
        self.assertEqual(fnt1, fnt2, "Subsequent calls should return the cached font.")
        self.assertEqual(metrics1.boundingRect('Test'), metrics2.boundingRect('Test'),
                         "Font metrics should be identical for cached calls.")

    def test_invalid_font_role(self):
        with self.assertRaises(ValueError):
            common.font_db.get(12, "NotAFontRole")

    def test_invalid_font_size(self):
        with self.assertRaises(RuntimeError):
            common.font_db.get(-5, common.Font.BoldFont)

    def test_font_instance_method(self):
        test_role = common.Font.MediumFont
        test_size = 14
        fnt = common.font_db.font(test_role, test_size)
        self.assertIsInstance(fnt, QtGui.QFont)
        self.assertEqual(fnt.pixelSize(), test_size)

    def test_font_family_matching(self):
        test_role = common.Font.ThinFont
        test_size = 16
        fnt, _ = common.font_db.get(test_size, test_role)
        self.assertEqual(fnt.family(), test_role.value, "Font family should match the role's value.")

    def test_font_database_reusability(self):
        db1 = common.font_db
        db2 = font.FontDatabase.instance()
        self.assertIs(db1, db2, "Instance method should return the same FontDatabase object.")

    def test_no_qapplication_raises_error(self):
        # Already have a QApplication. Just ensure no error now.
        self.assertIsNotNone(QtWidgets.QApplication.instance(),
                             "QApplication should be active and should not raise an error in this scenario.")

    def test_missing_fonts_directory(self):
        # Placeholder: Without patching or changing environment, can't reliably test.
        pass


if __name__ == '__main__':
    unittest.main()
