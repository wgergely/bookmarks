import unittest

from ..common.dcc import get_all_known_dcc_formats, normalize_dcc_name


class TestNormalizeDCCName(unittest.TestCase):
    """Tests for the normalize_dcc_name function."""

    def test_removing_years(self):
        """Test that years are correctly removed."""
        test_cases = [
            ('Adobe Photoshop 2020', 'photoshop'),
            ('Houdini FX 18.5', 'houdini'),
            ('Maya 2022', 'maya'),
            ('Cinema 4D R23', 'cinema4d'),
        ]
        for input_name, expected in test_cases:
            result = normalize_dcc_name(input_name)
            self.assertEqual(result, expected, f"Failed to remove years from '{input_name}'")

    def test_removing_versions(self):
        """Test that version numbers are correctly removed."""
        test_cases = [
            ('Blender 2.93', 'blender'),
            ('Unity 2020.1.2f1', 'unity'),
            ('ZBrush 4R8', 'zbrush'),  # '4R8' is part of the product name
        ]
        for input_name, expected in test_cases:
            result = normalize_dcc_name(input_name)
            self.assertEqual(result, expected, f"Failed to remove versions from '{input_name}'")

    def test_removing_special_characters(self):
        """Test that special characters are correctly removed."""
        test_cases = [
            ('After-Effects!', 'aftereffects'),
            ('Maya-2022', 'maya'),
            ('Substance_Painter', 'substancepainter'),
            ('  Unreal Engine 4  ', 'unrealengine'),
            ('3ds Max', '3dsmax'),
        ]
        for input_name, expected in test_cases:
            result = normalize_dcc_name(input_name)
            self.assertEqual(result, expected, f"Failed to remove special characters from '{input_name}'")

    def test_normalizing_to_lowercase(self):
        """Test that the output is in lowercase."""
        test_cases = [
            ('Blender', 'blender'),
            ('UNITY', 'unity'),
            ('After Effects', 'aftereffects'),
            ('ZBrush', 'zbrush'),
            ('Mocha Pro', 'mocha'),
        ]
        for input_name, expected in test_cases:
            result = normalize_dcc_name(input_name)
            self.assertEqual(result, expected, f"Failed to convert to lowercase for '{input_name}'")

    def test_stripping_leading_trailing_characters(self):
        """Test that leading and trailing underscores, hyphens, and spaces are stripped."""
        test_cases = [
            ('_Blender_', 'blender'),
            ('-Maya-', 'maya'),
            ('   Houdini   ', 'houdini'),
            ('--ZBrush--', 'zbrush'),
            ('___Unity___', 'unity'),
        ]
        for input_name, expected in test_cases:
            result = normalize_dcc_name(input_name)
            self.assertEqual(result, expected, f"Failed to strip leading/trailing characters for '{input_name}'")

    def test_get_all_know_dcc_formats(self):
        """Test that all known DCC formats are returned."""
        result = get_all_known_dcc_formats()
        self.assertIn('hip', result)
        self.assertIn('ma', result)
        self.assertIn('blend', result)
        self.assertIn('max', result)
        self.assertIn('c4d', result)
        self.assertIn('ztl', result)
        self.assertIn('mra', result)
        self.assertIn('mocha', result)
        self.assertIn('aep', result)
