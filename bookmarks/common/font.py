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
    """Custom QFontDatabase used to load and provide the fonts needed by Bookmarks."""

    def __init__(self):
        if not QtWidgets.QApplication.instance():
            raise RuntimeError('FontDatabase must be created after a QApplication is initiated.')
        super().__init__()
        self._init_custom_fonts()

    def _init_custom_fonts(self):
        """Load the fonts used by Bookmarks into the font database."""
        source = common.rsc('fonts')
        with os.scandir(source) as it:
            for entry in it:
                if not entry.name.endswith('ttc'):
                    continue
                idx = self.addApplicationFont(entry.path)
                if idx < 0:
                    raise RuntimeError(f'Could not load font file: {entry.path}')
                family = self.applicationFontFamilies(idx)
                if not family:
                    raise RuntimeError(f'Could not find font family in file: {entry.path} ({idx})')

    def get(self, size, role):
        """Retrieve the font and metrics for the given font size and role.

        Args:
            size (float): The font size.
            role (Font): The font role.

        Returns:
            tuple: (QFont, QFontMetricsF)
        """
        # Validate role
        if not isinstance(role, common.Font):
            raise ValueError(f'Invalid font role: {role}. Must be a member of common.Font.')

        # Validate size
        if size <= 0:
            raise RuntimeError(f'Font size must be greater than 0, got {size}')

        # Check cache
        if size in common.font_cache[role] and size in common.metrics_cache[role]:
            return (QtGui.QFont(common.font_cache[role][size]),
                    QtGui.QFontMetricsF(common.metrics_cache[role][size]))

        # Map role to style
        if role == common.Font.BlackFont:
            style = 'SemiBold'
        elif role == common.Font.BoldFont:
            style = 'Bold'
        elif role == common.Font.MediumFont:
            style = 'Medium'
        elif role == common.Font.LightFont:
            style = 'Regular'
        elif role == common.Font.ThinFont:
            style = 'Thin'
        else:
            raise ValueError(f'Invalid font role: {role}')

        # Retrieve font from database
        font = super().font(role.value, style, size)
        if font.family() != role.value:
            raise RuntimeError(f'Could not find font: {role.value} {style} {size}')

        font.setPixelSize(size)

        # Cache the font and metrics
        common.font_cache[role][size] = font
        common.metrics_cache[role][size] = QtGui.QFontMetricsF(font)

        return font, common.metrics_cache[role][size]

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
    """Initialize the font cache and database."""
    for role in common.Font:
        common.font_cache[role] = {}
        common.metrics_cache[role] = {}

    common.font_db = FontDatabase()
