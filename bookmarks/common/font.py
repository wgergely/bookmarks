"""Define :class:`.FontDatabase`.

The :class:`.FontDatabase` instance is saved at :attr:`bookmarks.common.font_db`.
QFont and QFontMetrics instances can be retrieved using:

.. code-block:: python
    :linenos:

    from bookmarks import common
    font, metrics = common.Font.BoldFont(common.Size.SmallText())

"""
import os

from PySide2 import QtGui, QtWidgets

from .. import common


class FontDatabase(QtGui.QFontDatabase):
    """Custom ``QFontDatabase`` used to load and provide the fonts needed by Bookmarks.

    """

    def __init__(self):
        if not QtWidgets.QApplication.instance():
            raise RuntimeError(
                'FontDatabase must be created after a QApplication was initiated.'
            )

        super().__init__()

        self._metrics = {}
        self._init_custom_fonts()

    def _init_custom_fonts(self):
        """Load the fonts used by Bookmarks to the font database.

        """
        source = common.rsc('fonts')

        for entry in os.scandir(source):
            if not entry.name.endswith('ttf'):
                continue

            idx = self.addApplicationFont(entry.path)
            if idx < 0:
                raise RuntimeError('Failed to add required font to the application')

            family = self.applicationFontFamilies(idx)
            if not family:
                raise RuntimeError('Failed to add required font to the application')

    def get(self, size, role):
        """Retrieve the font and metrics for the given font size and
        font role.

        Args:
            size (float): The font size.
            role (int): The font role (Font.BoldFont, Font.MediumFont, Font.LightFont).

        Returns:
            tuple: The QFont and QFontMetrics instances.

        """
        from .core import Font

        if role not in [f for f in Font]:
            raise ValueError(f'Invalid font role, expected one of {[f for f in Font]}')

        if size in common.font_cache[role] and size in common.metrics_cache[role]:
            return common.font_cache[role][size], common.metrics_cache[role][size]

        if role == Font.BlackFont:
            style = 'Black'
        elif role == Font.BoldFont:
            style = 'Bold'
        elif role == Font.MediumFont:
            style = 'Medium'
        elif role == Font.LightFont:
            style = 'Light'
        elif role == Font.ThinFont:
            style = 'Thin'
        else:
            raise ValueError(f'Invalid font role, expected one of {[f for f in Font]}')

        font = super().font(role.value, style, size)

        # Verify family
        if font.family() != role.value:
            raise RuntimeError('Failed to add required font to the application')

        font.setPixelSize(size)

        common.font_cache[role][size] = font
        common.metrics_cache[role][size] = QtGui.QFontMetrics(font)

        return common.font_cache[role][size], common.metrics_cache[role][size]

    def font(self, role, size):
        """Retrieve the font for the given role and size.

        Args:
            role (Font): The font role.
            size (float): The font size.

        Returns:
            QFont: The font instance.

        """
        if size in common.font_cache[role]:
            return common.font_cache[role][size]
        return self.get(size, role)[0]

    @staticmethod
    def instance():
        """Return the instance of the FontDatabase."""
        return common.font_db


def _init_font_db():
    """Initializes the font cache and database."""
    from .core import Font

    for role in Font:
        common.font_cache[role] = {}
        common.metrics_cache[role] = {}

    common.font_db = FontDatabase()