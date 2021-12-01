import os

from PySide2 import QtGui, QtWidgets

from .. import common

PrimaryFontRole = 0
SecondaryFontRole = 1
MetricsRole = 2


class FontDatabase(QtGui.QFontDatabase):
    """Utility class for loading and getting the application's custom fonts.

    """

    def __init__(self, parent=None):
        if not QtWidgets.QApplication.instance():
            raise RuntimeError(
                'FontDatabase must be created after a QApplication was initiated.')

        super().__init__(parent=parent)

        self._metrics = {}
        self.add_custom_fonts()

    def add_custom_fonts(self):
        """Load the fonts used by Bookmarks to the font database.

        """
        if common.medium_font in self.families():
            return

        source = common.get_rsc('fonts')
        for entry in os.scandir(source):
            if not entry.name.endswith('ttf'):
                continue
            idx = self.addApplicationFont(entry.path)
            if idx < 0:
                raise RuntimeError(
                    'Failed to add required font to the application')
            family = self.applicationFontFamilies(idx)
            if not family:
                raise RuntimeError(
                    'Failed to add required font to the application')

    def primary_font(self, font_size):
        """The primary font used by the application.

        """
        if font_size in common.font_cache[PrimaryFontRole]:
            return common.font_cache[PrimaryFontRole][font_size]

        font = self.font(common.bold_font, 'Bold', font_size)
        if font.family() != common.bold_font:
            raise RuntimeError(
                'Failed to add required font to the application')

        font.setPixelSize(font_size)
        metrics = QtGui.QFontMetrics(font)
        common.font_cache[PrimaryFontRole][font_size] = (font, metrics)
        return common.font_cache[PrimaryFontRole][font_size]

    def secondary_font(self, font_size):
        """The secondary font used by the application.

        """
        if font_size in common.font_cache[SecondaryFontRole]:
            return common.font_cache[SecondaryFontRole][font_size]

        font = self.font(common.medium_font, 'Medium', font_size)
        if font.family() != common.medium_font:
            raise RuntimeError(
                'Failed to add required font to the application')

        font.setPixelSize(font_size)
        metrics = QtGui.QFontMetrics(font)
        common.font_cache[SecondaryFontRole][font_size] = (font, metrics)
        return common.font_cache[SecondaryFontRole][font_size]


def init_font():
    common.font_cache = {
        PrimaryFontRole: {},
        SecondaryFontRole: {},
        MetricsRole: {},
    }
    common.font_db = FontDatabase()
