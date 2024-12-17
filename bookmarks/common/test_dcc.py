import unittest
from .dcc import normalize_dcc_name, get_dcc_icon_name, get_all_known_dcc_formats


class TestNormalizeDCCName(unittest.TestCase):
    """Tests for the normalize_dcc_name function."""

    def test_removing_years(self):
        test_cases = [
            ('Adobe Photoshop 2020', 'photoshop'),
            ('Houdini FX 18.5', 'houdini'),
            ('Maya 2022', 'maya'),
            ('Cinema 4D R23', 'cinema4d'),
        ]
        for input_name, expected in test_cases:
            self.assertEqual(normalize_dcc_name(input_name), expected)

    def test_removing_versions(self):
        test_cases = [
            ('Blender 2.93', 'blender'),
            ('Unity 2020.1.2f1', 'unity'),
            ('ZBrush 4R8', 'zbrush'),
        ]
        for input_name, expected in test_cases:
            self.assertEqual(normalize_dcc_name(input_name), expected)

    def test_removing_special_characters(self):
        test_cases = [
            ('After-Effects!', 'aftereffects'),
            ('Maya-2022', 'maya'),
            ('Substance_Painter', 'substancepainter'),
            ('  Unreal Engine 4  ', 'unrealengine'),
            ('3ds Max', '3dsmax'),
        ]
        for input_name, expected in test_cases:
            self.assertEqual(normalize_dcc_name(input_name), expected)

    def test_normalizing_to_lowercase(self):
        test_cases = [
            ('Blender', 'blender'),
            ('UNITY', 'unity'),
            ('After Effects', 'aftereffects'),
            ('ZBrush', 'zbrush'),
            ('Mocha Pro', 'mocha'),
        ]
        for input_name, expected in test_cases:
            self.assertEqual(normalize_dcc_name(input_name), expected)

    def test_stripping_leading_trailing_characters(self):
        test_cases = [
            ('_Blender_', 'blender'),
            ('-Maya-', 'maya'),
            ('   Houdini   ', 'houdini'),
            ('--ZBrush--', 'zbrush'),
            ('___Unity___', 'unity'),
        ]
        for input_name, expected in test_cases:
            self.assertEqual(normalize_dcc_name(input_name), expected)


class TestGetDCCIconName(unittest.TestCase):
    """Tests for the get_dcc_icon_name function."""

    def test_known_dcc(self):
        test_cases = [
            ('Maya', 'maya'),
            ('ZBrush', 'zbrush'),
            ('Houdini', 'houdini'),
            ('Blender', 'blender'),
        ]
        for input_name, expected in test_cases:
            self.assertEqual(get_dcc_icon_name(input_name), expected)

    def test_aliases(self):
        test_cases = [
            ('Adobe Photoshop', 'photoshop'),
            ('AE', 'after_effects'),
            ('Premiere Pro', 'premiere'),
            ('FCPX', 'fcp'),
            ('3ds Max', '3ds_max'),
        ]
        for input_name, expected in test_cases:
            self.assertEqual(get_dcc_icon_name(input_name), expected)

    def test_unknown_dcc(self):
        test_cases = [
            ('RandomApp', None),
            ('CoolSoftware2023', None),
            ('SomeUnknownDCC', None),
        ]
        for input_name, expected in test_cases:
            self.assertEqual(get_dcc_icon_name(input_name), expected)


class TestGetAllKnownDCCFormats(unittest.TestCase):
    """Tests for the get_all_known_dcc_formats function."""

    def test_known_formats(self):
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

    def test_type_of_result(self):
        result = get_all_known_dcc_formats()
        self.assertIsInstance(result, set)
        self.assertTrue(all(isinstance(fmt, str) for fmt in result))


if __name__ == '__main__':
    unittest.main()
