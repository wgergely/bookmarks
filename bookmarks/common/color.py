__all__ = ['init_color_manager']

from PySide2 import QtGui


def init_color_manager():
    from . import common
    common.color_manager = ColorManager()


import colorsys
import hashlib


class ColorManager:
    def __init__(self, default_base_hue=0, default_palette_size=12, default_harmony_scheme='analogous'):
        self.color_cache = {}  # Map from (input_string, base_hue, palette_size, harmony_scheme) to (R,G,B,A)
        self.default_base_hue = default_base_hue
        self.default_palette_size = default_palette_size
        self.default_harmony_scheme = default_harmony_scheme
        # Initialize the default palette
        self.default_palette = self._generate_color_palette(
            base_hue=self.default_base_hue,
            palette_size=self.default_palette_size,
            harmony_scheme=self.default_harmony_scheme
        )

    def get_color(self, input_string, qcolor=False, base_hue=None, palette_size=None, harmony_scheme=None):
        """
        Returns an RGBA color tuple for the given input string.
        """
        if base_hue is None:
            base_hue = self.default_base_hue
        if palette_size is None:
            palette_size = self.default_palette_size
        if harmony_scheme is None:
            harmony_scheme = self.default_harmony_scheme

        cache_key = (input_string, base_hue, palette_size, harmony_scheme)

        if cache_key in self.color_cache:
            color = self.color_cache[cache_key]
        else:
            # Generate the palette
            if (base_hue == self.default_base_hue and
                palette_size == self.default_palette_size and
                harmony_scheme == self.default_harmony_scheme):
                palette = self.default_palette
            else:
                palette = self._generate_color_palette(
                    base_hue=base_hue,
                    palette_size=palette_size,
                    harmony_scheme=harmony_scheme
                )
            # Get the index
            index = self._get_palette_index(input_string, palette_size)
            color = palette[index]
            self.color_cache[cache_key] = color

        if qcolor:
            return QtGui.QColor(*color)
        return color

    def _generate_color_palette(self, base_hue, palette_size, harmony_scheme):
        """
        Generates a palette of harmonious colors based on the base hue, palette size, and harmony scheme.
        """
        hues = self._get_harmony_hues(base_hue, harmony_scheme, palette_size)

        palette = []
        for hue in hues:
            # Use muted saturation and value for modern UI
            saturation = 0.5  # Moderate saturation for muted colors
            value = 0.8       # Brightness suitable for dark themes
            hue_normalized = hue / 360.0
            r, g, b = colorsys.hsv_to_rgb(hue_normalized, saturation, value)
            r = int(r * 255)
            g = int(g * 255)
            b = int(b * 255)
            a = 255  # Full opacity
            palette.append((r, g, b, a))
        return palette

    def _get_harmony_hues(self, base_hue, scheme, palette_size):
        """
        Generates a list of hues based on the selected harmony scheme and desired palette size.
        """
        if scheme == 'analogous':
            # Hues at -30, 0, +30 degrees from base hue
            angles = [-30, -20, -10, 0, 10, 20, 30]
        elif scheme == 'complementary':
            # Base hue and its complement
            angles = [0, 180]
        elif scheme == 'triadic':
            # Three hues evenly spaced around the color wheel
            angles = [0, 120, 240]
        elif scheme == 'tetradic':
            # Four hues forming a rectangle
            angles = [0, 90, 180, 270]
        else:
            # Default to base hue if scheme is unrecognized
            angles = [0]

        # Expand hues to match the desired palette size
        hues = []
        repeats = (palette_size + len(angles) - 1) // len(angles)
        for i in range(repeats):
            for angle in angles:
                hue = (base_hue + angle + i * 10) % 360
                hues.append(hue)
                if len(hues) >= palette_size:
                    break
            if len(hues) >= palette_size:
                break

        return hues[:palette_size]

    def _get_palette_index(self, input_string, palette_size):
        """
        Maps the input string to an index in the color palette.
        """
        # Use a consistent hash function to get an integer
        hash_object = hashlib.sha256(input_string.encode())
        hash_int = int(hash_object.hexdigest(), 16)
        index = hash_int % palette_size
        return index
