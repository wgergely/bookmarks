import unittest

from .seqshot import get_sequence_and_shot


class TestGetSequenceAndShot(unittest.TestCase):
    def test_prefixed_sequence_and_shot(self):
        path = "/projects/production/SQ01/SH010/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("SQ01", "SH010"))

    def test_named_sequence_and_shot(self):
        path = "/projects/production/ABC01_010/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("ABC01", "010"))

    def test_non_prefixed_sequence_and_shot(self):
        path = "/projects/production/01-010/0020/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("01", "010"))

    def test_only_sequence(self):
        path = "/projects/production/SEQ01/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("SEQ01", None))

    def test_only_shot(self):
        path = "/projects/production/SH010/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), (None, "SH010"))

    def test_no_sequence_or_shot(self):
        path = "/projects/production/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), (None, None))

    def test_number_sequence_path(self):
        path = "/projects/production/invalid/1234/SH010/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("1234", "SH010"))

    def test_combined_sequence_shot_with_dash(self):
        path = "/projects/production/ABC01-0100/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("ABC01", "0100"))

    def test_combined_sequence_shot_with_underscore(self):
        path = "/projects/production/SQ02_SH020/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("SQ02", "SH020"))

    def test_sequence_and_shot_in_same_part(self):
        path = "/projects/production/XYZ03SH030/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("XYZ03", "SH030"))

    def test_numeric_sequence_and_shot(self):
        path = "/projects/production/01_0200/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("01", "0200"))

    def test_longer_shot_number(self):
        path = "/projects/production/SEQ01/SH01000/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("SEQ01", "SH01000"))

    def test_shot_number_without_prefix(self):
        path = "/projects/production/SEQ01/0100/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("SEQ01", "0100"))

    def test_sequence_with_letters_and_numbers(self):
        path = "/projects/production/ABCDEF01/1000/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("1000", "1000"))
        path = "/projects/production/ABCD01/1000/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("ABCD01", "1000"))

    def test_sequence_with_no_digits(self):
        path = "/projects/production/XYZ/SH010/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), (None, "SH010"))

    def test_sequence_and_shot_separated_by_multiple_characters(self):
        path = "/projects/production/SEQ001__SH0010/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("SEQ001", "SH0010"))

    def test_unusual_sequence_and_shot_format(self):
        path = "/projects/production/SequenceA_ShotB/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), (None, None))

    def test_sequence_and_shot_with_additional_numbers(self):
        path = "/projects/production/SQ01_extra/SH010_extra/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), ("SQ01", "SH010"))

    def test_sequence_with_special_characters(self):
        path = "/projects/production/SQ@01/SH#010/assets/character.ma"
        self.assertEqual(get_sequence_and_shot(path), (None, None))
