import functools
import re

__all__ = ['get_sequence_and_shot']

sep = r'[_\-/]'
seq_min_len = 2
seq_max_len = 5
sh_min_len = 3
sh_max_len = 5

SEQUENCE_PATTERNS = [
    rf'/(?P<sequence>SQ\d{{{seq_min_len},{seq_max_len}}}){sep}?',
    # Matches SQ01, SQ0010
    rf'/(?P<sequence>SEQ\d{{{seq_min_len},{seq_max_len}}}){sep}?',
    # Matches SEQ01, SEQ0010
    rf'/(?P<sequence>SEQUENCE\d{{{seq_min_len},{seq_max_len}}}){sep}?',
    # Matches SEQUENCE01, SEQUENCE0010, SEQUENCE-01, SEQUENCE-0010
    rf'/(?P<sequence>[A-Z]{{3,4}}\d{{{seq_min_len},{seq_max_len}}}){sep}?',
    # Matches ABC01, ABC0010, ABC-01, ABC-0010, ABC_01, ABC_0010
    rf'/(?P<sequence>\d{{{seq_min_len},{seq_max_len}}}){sep}',
]

SHOT_PATTERNS = [
    rf'{sep}?(?P<shot>SH\d{{{sh_min_len},{sh_max_len}}})',
    # Matches SH010, SH0010
    rf'{sep}?(?P<shot>SHOT\d{{{sh_min_len},{sh_max_len}}})',
    # Matches SHOT010, SHOT0010
    rf'{sep}(?P<shot>\d{{{sh_min_len},{sh_max_len}}})'
    # Matches non-prefixed shots like 0010, 0100
]

# generate combinations using itertools.product
COMBINED_PATTERNS = [
    rf'/(?P<sequence>SQ\d{{{seq_min_len},{seq_max_len}}}){sep}?(?P<shot>SH\d{{3,5}})/',
    rf'/(?P<sequence>SQ\d{{{seq_min_len},{seq_max_len}}}){sep}?(?P<shot>SHOT\d{{3,5}})/',
    rf'/(?P<sequence>SQ\d{{{seq_min_len},{seq_max_len}}}){sep}(?P<shot>\d{{3,5}})/',
    rf'/(?P<sequence>SEQ\d{{{seq_min_len},{seq_max_len}}}){sep}?(?P<shot>SH\d{{3,5}})/',
    rf'/(?P<sequence>SEQ\d{{{seq_min_len},{seq_max_len}}}){sep}?(?P<shot>SHOT\d{{3,5}})/',
    rf'/(?P<sequence>SEQ\d{{{seq_min_len},{seq_max_len}}}){sep}(?P<shot>\d{{3,5}})/',
    rf'/(?P<sequence>SEQUENCE\d{{{seq_min_len},{seq_max_len}}}){sep}?(?P<shot>SH\d{{3,5}})/',
    rf'/(?P<sequence>SEQUENCE\d{{{seq_min_len},{seq_max_len}}}){sep}?(?P<shot>SHOT\d{{3,5}})/',
    rf'/(?P<sequence>SEQUENCE\d{{{seq_min_len},{seq_max_len}}}){sep}(?P<shot>\d{{3,5}})/',
    rf'/(?P<sequence>[A-Z]{{3,4}}\d{{{seq_min_len},{seq_max_len}}}){sep}?(?P<shot>SH\d{{3,5}})/',
    rf'/(?P<sequence>[A-Z]{{3,4}}\d{{{seq_min_len},{seq_max_len}}}){sep}?(?P<shot>SHOT\d{{3,5}})/',
    rf'/(?P<sequence>[A-Z]{{3,4}}\d{{{seq_min_len},{seq_max_len}}}){sep}(?P<shot>\d{{3,5}})/',
    rf'/(?P<sequence>\d{{{seq_min_len},{seq_max_len}}}){sep}?(?P<shot>SH\d{{3,5}})/',
    rf'/(?P<sequence>\d{{{seq_min_len},{seq_max_len}}}){sep}?(?P<shot>SHOT\d{{3,5}})/',
    rf'/(?P<sequence>\d{{{seq_min_len},{seq_max_len}}}){sep}(?P<shot>\d{{3,5}})/',
]


@functools.cache
def get_sequence_and_shot(path):
    """
    Parses a given path to extract sequence and shot numbers.

    Args:
        path (str): The path to be parsed.

    Returns:
        tuple: A tuple containing sequence and shot information if found, otherwise (None, None).
    """
    sequence = None
    shot = None

    # First try to match combined patterns in the path
    for pattern in COMBINED_PATTERNS:
        match = re.search(pattern, path, re.IGNORECASE)
        if match:
            sequence = match.group('sequence')
            shot = match.group('shot')
            return sequence, shot

    path_parts = path.split('/')
    path_parts = [f'/{part}/' for part in path_parts]

    # First, try to match combined patterns
    for part in path_parts:
        for pattern in COMBINED_PATTERNS:
            match = re.search(pattern, part, re.IGNORECASE)
            if match:
                sequence = match.group('sequence')
                shot = match.group('shot')
                return sequence, shot

    # Then try to match sequence and shot separately
    for part in path_parts:
        if sequence is None:
            for pattern in SEQUENCE_PATTERNS:
                match = re.search(pattern, part, re.IGNORECASE)
                if match:
                    sequence = match.group('sequence')
                    break
        if shot is None:
            for pattern in SHOT_PATTERNS:
                match = re.search(pattern, part, re.IGNORECASE)
                if match:
                    shot = match.group('shot')
                    break
        if sequence is not None and shot is not None:
            break

    return sequence, shot


import unittest


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
