"""Defines :class:`.FontDatabase`, a utility class used to load and store fonts used by Bookmarks.

The :class:`.FontDatabase` instance is saved at :attr:`bookmarks.common.font_db`.
QFont and QFontMetrics instances can be retrieved using:

.. code-block:: python
    :linenos:

    from bookmarks import common
    font, metrics = common.font_db.bold_font(common.size(common.size_font_small))

"""
import os

from PySide2 import QtGui, QtWidgets

from .. import common

font_primaryRole = 0
font_secondaryRole = 1
MetricsRole = 2
font_terciaryRole = 3


class FontDatabase(QtGui.QFontDatabase):
    """Custom ``QFontDatabase`` used to load and provide the fonts needed by Bookmarks.

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

        source = common.rsc('fonts')
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

    def bold_font(self, font_size):
        """The primary font used by the application.

        """
        if font_size in common.font_cache[font_primaryRole]:
            return common.font_cache[font_primaryRole][font_size]

        font = self.font(common.bold_font, 'Bold', font_size)
        if font.family() != common.bold_font:
            raise RuntimeError(
                'Failed to add required font to the application')

        font.setPixelSize(font_size)
        metrics = QtGui.QFontMetrics(font)
        common.font_cache[font_primaryRole][font_size] = (font, metrics)
        return common.font_cache[font_primaryRole][font_size]

    def medium_font(self, font_size):
        """The secondary font used by the application.

        """
        if font_size in common.font_cache[font_secondaryRole]:
            return common.font_cache[font_secondaryRole][font_size]

        font = self.font(common.medium_font, 'Medium', font_size)
        if font.family() != common.medium_font:
            raise RuntimeError(
                'Failed to add required font to the application')

        font.setPixelSize(font_size)
        metrics = QtGui.QFontMetrics(font)
        common.font_cache[font_secondaryRole][font_size] = (font, metrics)
        return common.font_cache[font_secondaryRole][font_size]

    def light_font(self, font_size):
        """The secondary font used by the application.

        """
        if font_size in common.font_cache[font_terciaryRole]:
            return common.font_cache[font_terciaryRole][font_size]

        font = self.font(common.medium_font, 'Medium', font_size)
        if font.family() != common.medium_font:
            raise RuntimeError(
                'Failed to add required font to the application')

        font.setPixelSize(font_size)
        metrics = QtGui.QFontMetrics(font)
        common.font_cache[font_terciaryRole][font_size] = (font, metrics)
        return common.font_cache[font_terciaryRole][font_size]


def init_font():
    """Initializes the font cache and database.

    """
    common.font_cache = {
        font_primaryRole: {},
        font_secondaryRole: {},
        font_terciaryRole: {},
        MetricsRole: {},
    }
    common.font_db = FontDatabase()
