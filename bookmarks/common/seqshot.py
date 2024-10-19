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
