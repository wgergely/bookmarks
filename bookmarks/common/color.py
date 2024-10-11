import colorsys
import random

__all__ = ['init_color_manager']


def init_color_manager():
    from . import common
    common.color_manager = ColorManager()


import colorsys
import hashlib


class ColorManager:
    def __init__(self):
        self.color_cache = {}  # Map from string to (R,G,B,A)
        self.palette = self._generate_color_palette()
        self.palette_size = len(self.palette)

    def get_color(self, input_string):
        """
        Returns an RGBA color tuple for the given input string.
        """
        if input_string in self.color_cache:
            return self.color_cache[input_string]
        else:
            index = self._get_palette_index(input_string)
            color = self.palette[index]
            self.color_cache[input_string] = color
            return color

    def _generate_color_palette(self):
        """
        Generates a palette of harmonious colors based on color theory.
        """
        base_hue = 0  # Base hue (e.g., blue)
        harmony_scheme = 'analogous'  # Can be 'analogous', 'complementary', 'triadic', 'tetradic'
        hues = self._get_harmony_hues(base_hue, harmony_scheme)

        palette = []
        for hue in hues:
            # Use muted saturation and value for modern UI
            saturation = 0.5  # Moderate saturation for muted colors
            value = 0.8  # Brightness suitable for dark themes
            hue_normalized = hue / 360.0
            r, g, b = colorsys.hsv_to_rgb(hue_normalized, saturation, value)
            r = int(r * 255)
            g = int(g * 255)
            b = int(b * 255)
            a = 255  # Full opacity
            palette.append((r, g, b, a))
        return palette

    def _get_harmony_hues(self, base_hue, scheme):
        """
        Generates a list of hues based on the selected harmony scheme.
        """
        if scheme == 'analogous':
            # Hues at -30, 0, +30 degrees from base hue
            hues = [(base_hue + angle) % 360 for angle in (-30, 0, 30)]
        elif scheme == 'complementary':
            # Base hue and its complement
            hues = [base_hue, (base_hue + 180) % 360]
        elif scheme == 'triadic':
            # Three hues evenly spaced around the color wheel
            hues = [(base_hue + angle) % 360 for angle in (0, 120, 240)]
        elif scheme == 'tetradic':
            # Four hues forming a rectangle
            hues = [(base_hue + angle) % 360 for angle in (0, 90, 180, 270)]
        else:
            # Default to base hue if scheme is unrecognized
            hues = [base_hue]

        # Expand hues to create a larger palette by adding slight variations
        expanded_hues = []
        for hue in hues:
            for offset in (-10, 0, 10):
                expanded_hues.append((hue + offset) % 360)
        return expanded_hues

    def _get_palette_index(self, input_string):
        """
        Maps the input string to an index in the color palette.
        """
        # Use a consistent hash function to get an integer
        hash_object = hashlib.sha256(input_string.encode())
        hash_int = int(hash_object.hexdigest(), 16)
        index = hash_int % self.palette_size
        return index
