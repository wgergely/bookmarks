import functools
import re
import shlex
import unittest
from types import NoneType

__all__ = [
    'SyntaxFilter', 'FilterSyntaxHighlighter'
]

from PySide2 import QtGui


class SyntaxFilter:
    _syntax_markers = (
        '--',
        '--(',
        '--("',
        "'",
        '"',
        ')"',
        ")'",
    )

    # re.split to split by spaces but keep quoted strings intact
    regex_split = re.compile(r'(?<!\\)"[^"]*"|\S+')


    def __init__(self, filter_string='', case_sensitive=True):
        """
        Initializes the SyntaxFilter with a filter string and case sensitivity option.

        Args:
            filter_string: The filter string to parse and use for matching.
            case_sensitive: Boolean indicating if matching should be case-sensitive.

        """
        if not isinstance(filter_string, str):
            raise TypeError('Filter must be a string')
        if not isinstance(case_sensitive, bool):
            raise TypeError('case_sensitive must be a boolean')

        self.negative_regex_patterns = []
        self.positive_regex_patterns = []
        self.invalid_regex_patterns = []

        self.negative_terms = []
        self.positive_terms = []

        self._filter_string = ''
        self.case_sensitive = case_sensitive

        self.set_filter_string(filter_string)

    @property
    def filter_string(self):
        return self._filter_string

    @staticmethod
    @functools.lru_cache(maxsize=4194304)
    def parse_filter_string(filter_string, case_sensitive):
        """
        Parses the filter string into positive and negative patterns and terms.

        Args:
            filter_string: The filter string to parse.
            case_sensitive: Boolean indicating if matching should be case-sensitive.

        """
        positive_terms = []
        negative_terms = []
        positive_regex_patterns = []
        negative_regex_patterns = []
        invalid_regex_patterns = []

        try:
            tokens = shlex.split(filter_string)
        except ValueError:
            # Handle unmatched quotes
            return (
                positive_terms,
                negative_terms,
                positive_regex_patterns,
                negative_regex_patterns,
                invalid_regex_patterns
            )

        for token in tokens:
            is_negative = False
            if token.startswith('--'):
                is_negative = True
                token = token[2:]  # Remove the '--' prefix

            # Check if the token is a regular expression pattern enclosed in parentheses
            if token.startswith('(') and token.endswith(')'):
                pattern_str = token[1:-1]  # Remove the parentheses
                try:
                    if case_sensitive is False:
                        pattern = re.compile(pattern_str, flags=re.IGNORECASE)
                    else:
                        pattern = re.compile(pattern_str)
                except re.error as e:
                    # Handle invalid regular expression patterns
                    invalid_regex_patterns.append(pattern_str)
                    continue
                if is_negative:
                    negative_regex_patterns.append(pattern)
                else:
                    positive_regex_patterns.append(pattern)
            else:
                # Treat token as plain text term - could be quoted or unquoted
                if not case_sensitive:
                    token = token.lower()
                if is_negative:
                    negative_terms.append(token)
                else:
                    positive_terms.append(token)

        return (
            positive_terms,
            negative_terms,
            positive_regex_patterns,
            negative_regex_patterns,
            invalid_regex_patterns
        )

    @functools.lru_cache(maxsize=4194304)
    def _match_string(self, _, full_path):
        """
        Determines if a given full path matches the filter criteria.

        Args:
            full_path: The full path string to match against the filter.

        Returns:
            True if the path matches the filter, False otherwise.
        """
        # Adjust for case sensitivity
        path_str = full_path.replace('\\', '/').rstrip('/')
        if not self.case_sensitive:
            path_str = path_str.lower()

        segments = [f for f in path_str.split('/') if f]

        if not self.case_sensitive:
            path_str = path_str.lower()

        # Check negative regular expression patterns first
        for pattern in self.negative_regex_patterns:
            if self._match_regex_pattern(pattern, segments, path_str, self._filter_string):
                return False

        # Check negative plain terms
        for term in self.negative_terms:
            if not self.case_sensitive:
                term = term.lower()
            if self._match_plain_term(term, segments, path_str, self._filter_string):
                return False

        # If there are no positive patterns, accept the item
        if not (self.positive_terms or self.positive_regex_patterns):
            return True

        # Check if all positive regular expression patterns match
        for pattern in self.positive_regex_patterns:
            if not self._match_regex_pattern(pattern, segments, path_str, self._filter_string):
                return False

        # Check if all positive plain terms matches
        for term in self.positive_terms:
            if not self.case_sensitive:
                term = term.lower()
            if not self._match_plain_term(term, segments, path_str, self._filter_string):
                return False

        return True

    @staticmethod
    def _match_regex_pattern(pattern, segments, path_str, filter_string):
        """
        Checks if a regular expression pattern matches any segment or the full path.

        Args:
            pattern: The compiled regular expression pattern.
            segments: The list of path segments.
            path_str: The full path string.
            filter_string: The original filter string.

        Returns:
            True if the pattern matches, False otherwise.
        """
        for segment in segments:
            if pattern.search(segment):
                return True
        if pattern.search(path_str):
            return True
        return False

    @staticmethod
    def _match_plain_term(term, segments, path_str, filter_string):
        """
        Checks if a plain term matches any segment or the full path.

        Args:
            term: The plain text term to match.
            segments: The list of path segments.
            path_str: The full path string.
            filter_string: The original filter string.

        Returns:
            True if the term matches, False otherwise.
        """
        is_strict = f'"{term}"' in filter_string

        # First, check for exact folder name matches
        if term in segments:
            return True

        # Then, check segment matches
        for segment in segments:
            if is_strict:
                # check for equality if the term is quoted
                if term == segment:
                    return True
            else:
                # check for substring match if the term isn't quoted
                if term in segment:
                    return True

        # Then check if the term is a substring of the full path
        if not is_strict:
            if term in path_str:
                return True

        # Finally, check if the term spans multiple segments
        _terms = term.split('/')
        if len(_terms) > 1:
            _s_terms = set(_terms)
            _s_segments = set(segments)

            if _s_terms.issubset(_s_segments):
                return True

        return False

    @property
    def syntax_markers(self):
        return self._syntax_markers

    def set_filter_string(self, filter_string, case_sensitive=None):
        """
        Sets a new filter string and parses it.

        Args:
            filter_string: The new filter string to use.
            case_sensitive: Boolean indicating if matching should be case-sensitive.

        """
        if not isinstance(filter_string, str):
            raise TypeError('Filter must be a string')
        if not isinstance(case_sensitive, (bool, NoneType)):
            raise TypeError('case_sensitive must be a boolean')

        # Sanitize quotes
        filter_string = filter_string.replace('\'', '"')
        if not filter_string.replace('"', '').strip():
            filter_string = ''
        self._filter_string = filter_string

        if isinstance(case_sensitive, bool):
            self.case_sensitive = case_sensitive

        self.negative_regex_patterns = None
        self.positive_regex_patterns = None
        self.invalid_regex_patterns = None

        self.negative_terms = None
        self.positive_terms = None

        (
            self.positive_terms,
            self.negative_terms,
            self.positive_regex_patterns,
            self.negative_regex_patterns,
            self.invalid_regex_patterns
        ) = self.parse_filter_string(filter_string, self.case_sensitive)

    def match_string(self, full_path):
        if not self._filter_string:
            return True
        key = f'{self._filter_string}:{self.case_sensitive}'
        return self._match_string(key, full_path)

    def has_invalid_regex(self):
        return bool(self.invalid_regex_patterns)

    def get_invalid_regex(self):
        return self.invalid_regex_patterns

    def add_filter(self, string):
        if not isinstance(string, str):
            raise TypeError('Filter must be a string')

        # Temporarily append new filter string to existing filter string
        self._filter_string += ' ' + string

        # Include list
        (
            positive_terms,
            negative_terms,
            positive_regex_patterns,
            negative_regex_patterns,
            invalid_regex_patterns
        ) = self.parse_filter_string(string, self.case_sensitive)

        tokens = self.regex_split.findall(self._filter_string)

        # Update existing filter
        if positive_terms:
            self.positive_terms = sorted(set(self.positive_terms + positive_terms))
        if negative_terms:
            self.negative_terms = sorted(set(self.negative_terms + negative_terms))
        if positive_regex_patterns:
            self.positive_regex_patterns = sorted(set(self.positive_regex_patterns + positive_regex_patterns))
        if negative_regex_patterns:
            self.negative_regex_patterns = sorted(set(self.negative_regex_patterns + negative_regex_patterns))

        all_terms = (
                sorted([f'"{f}"' if f'"{f}"' in tokens else f for f in self.positive_terms]) +
                sorted([f'--"{f}"' if f'--"{f}"' in tokens else f for f in self.negative_terms]) +
                sorted([f'"({f})"' for f in self.positive_regex_patterns]) +
                sorted([f'--"({f})"' for f in self.negative_regex_patterns]) +
                sorted([f'"({f})"' for f in self.invalid_regex_patterns])
        )
        all_terms = set(all_terms)
        self._filter_string = ' '.join(all_terms)

    def remove_filter(self, string):
        string = string.replace("'", '"')
        if string not in self._filter_string:
            return

        tokens = self.regex_split.findall(self._filter_string)

        _f = lambda f: f'"{f}"' if f'"{f}"' in tokens else f
        __f = lambda f: True if f'"{f}"' in tokens else False

        _f_ = lambda f: f'--"{f}"' if f'--"{f}"' in tokens else f
        __f_ = lambda f: True if f'--"{f}"' in tokens else False

        _positive_terms = sorted([_f(f) for f in self.positive_terms if __f(f)])
        _negative_terms = sorted([_f_(f) for f in self.negative_terms if __f_(f)])
        _positive_regex_patterns = sorted([f'"({f})"' for f in self.positive_regex_patterns])
        _negative_regex_patterns = sorted([f'--"({f})"' for f in self.negative_regex_patterns])
        _invalid_regex_patterns = sorted([f'"({f})"' for f in self.invalid_regex_patterns])

        tokens = self.regex_split.findall(self._filter_string)
        if string in tokens:
            tokens.remove(string)
        else:
            if string in _positive_terms:
                tokens.remove(string)
            if string in _negative_terms:
                tokens.remove(string)
            if string in _positive_regex_patterns:
                tokens.remove(string)
            if string in _negative_regex_patterns:
                tokens.remove(string)
            if string in _invalid_regex_patterns:
                tokens.remove(string)

        _filter_string = ' '.join(set(tokens))
        self._filter_string = _filter_string
        (
            self.positive_terms,
            self.negative_terms,
            self.positive_regex_patterns,
            self.negative_regex_patterns,
            self.invalid_regex_patterns
        ) = self.parse_filter_string(_filter_string, self.case_sensitive)

    def has_string(
            self,
            string,
            positive_terms=False,
            negative_terms=False,
            positive_regex_patterns=False,
            negative_regex_patterns=False,
            invalid_regex_patterns=False
    ):
        if not self._filter_string:
            return False

        tokens = self.regex_split.findall(self._filter_string)

        all_terms = []
        if positive_terms:
            all_terms += sorted([f'"{f}"' if f'"{f}"' in tokens else f for f in self.positive_terms])
        if negative_terms:
            all_terms += sorted(
                [f'--"{f}"' if f'--"{f}"' in tokens else f'--{f}' for f in self.negative_terms])
        if positive_regex_patterns:
            all_terms += sorted([f'"({f})"' for f in self.positive_regex_patterns])
        if negative_regex_patterns:
            all_terms += sorted([f'--"({f})"' for f in self.negative_regex_patterns])
        if invalid_regex_patterns:
            all_terms += sorted([f'"({f})"' for f in self.invalid_regex_patterns])

        all_terms = set(all_terms)
        string = string.replace("'", '"')
        return string in all_terms



class FilterSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(FilterSyntaxHighlighter, self).__init__(parent)
        self.initializeFormats()

    def initializeFormats(self):
        # Define formats for different term types
        self.formats = {}

        # Positive partial term
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor("#A8FF60"))  # Greenish
        self.formats['positive_partial'] = fmt

        # Positive exact term
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor("#B5FFD1"))  # Lighter green
        self.formats['positive_exact'] = fmt

        # Positive regex term
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor("#99FF99"))  # Another shade of green
        self.formats['positive_regex'] = fmt

        # Negative partial term
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor("#FF6E64"))  # Reddish
        self.formats['negative_partial'] = fmt

        # Negative exact term
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor("#FFAFAF"))  # Lighter red
        self.formats['negative_exact'] = fmt

        # Negative regex term
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor("#FF9999"))  # Another shade of red
        self.formats['negative_regex'] = fmt

        # Invalid term
        fmt = QtGui.QTextCharFormat()
        fmt.setUnderlineColor(QtGui.QColor("#FFA500"))  # Orange
        fmt.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
        self.formats['invalid'] = fmt

    def highlightBlock(self, text):
        length = len(text)
        i = 0
        while i < length:
            if text[i:].startswith('--'):
                # Negative term
                start = i
                i += 2
                if i < length:
                    if text[i] == '"':
                        # Negative quoted term
                        i += 1
                        start_quote = i
                        while i < length and text[i] != '"':
                            i += 1
                        if i < length and text[i] == '"':
                            # Found closing quote
                            i += 1
                            self.setFormat(start, i - start, self.formats['negative_exact'])
                        else:
                            # Unterminated quote
                            i = length
                            self.setFormat(start, i - start, self.formats['invalid'])
                    elif text[i] == '(':
                        # Negative regex term
                        i += 1
                        start_paren = i
                        while i < length and text[i] != ')':
                            i += 1
                        if i < length and text[i] == ')':
                            # Found closing parenthesis
                            i += 1
                            self.setFormat(start, i - start, self.formats['negative_regex'])
                        else:
                            # Unterminated parenthesis
                            i = length
                            self.setFormat(start, i - start, self.formats['invalid'])
                    else:
                        # Negative partial term
                        start_term = i
                        while i < length and not text[i].isspace():
                            i += 1
                        self.setFormat(start, i - start, self.formats['negative_partial'])
                else:
                    # Just '--' at end of text
                    self.setFormat(start, i - start, self.formats['invalid'])
            elif text[i] == '"':
                # Positive quoted term
                start = i
                i += 1
                while i < length and text[i] != '"':
                    i += 1
                if i < length and text[i] == '"':
                    # Found closing quote
                    i += 1
                    self.setFormat(start, i - start, self.formats['positive_exact'])
                else:
                    # Unterminated quote
                    i = length
                    self.setFormat(start, i - start, self.formats['invalid'])
            elif text[i] == '(':
                # Positive regex term
                start = i
                i += 1
                while i < length and text[i] != ')':
                    i += 1
                if i < length and text[i] == ')':
                    # Found closing parenthesis
                    i += 1
                    self.setFormat(start, i - start, self.formats['positive_regex'])
                else:
                    # Unterminated parenthesis
                    i = length
                    self.setFormat(start, i - start, self.formats['invalid'])
            elif text[i].isspace():
                # Skip whitespace
                i += 1
            else:
                # Positive partial term
                start = i
                while i < length and not text[i].isspace():
                    if text[i] in '"()':
                        break
                    i += 1
                self.setFormat(start, i - start, self.formats['positive_partial'])



class TestSyntaxFilter(unittest.TestCase):

    def test_plain_positive_term(self):
        """Test matching with a single positive plain term."""
        filter_string = 'folder'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/folder'))
        self.assertTrue(filter.match_string('/folder/subfolder'))
        self.assertFalse(filter.match_string('/path/to/another'))

        filter_string = 'TestAsset3'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('TestClient/TestJob/data/asset/TestAsset3'))

        filter_string = '"TestAsset3"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('TestClient/TestJob/data/asset/TestAsset3'))

    def test_plain_positive_terms(self):
        """Test matching with a multiple positive plain term."""
        filter_string = '"folder" "to"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/folder'))
        self.assertFalse(filter.match_string('/subfolder/subfolder/to'))
        self.assertFalse(filter.match_string('/path/to/another'))

        filter_string = '"to" "folder"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/folder'))
        self.assertFalse(filter.match_string('/subfolder/subfolder/to'))
        self.assertFalse(filter.match_string('/path/to/another'))

        filter_string = 'folder to'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/folder'))
        self.assertTrue(filter.match_string('/folder/subfolder/to'))
        self.assertFalse(filter.match_string('/path/to/another'))

    def test_plain_positive_nested_folder(self):
        """Test matching with a nested folder structure."""
        filter_string = 'to/include'
        filter = SyntaxFilter(filter_string)
        self.assertFalse(filter.match_string('/path/to/exclude'))
        self.assertTrue(filter.match_string('/path/to/include'))

        filter_string = 'to/include'
        filter = SyntaxFilter(filter_string)
        self.assertFalse(filter.match_string('/path/into/exclude'))
        self.assertTrue(filter.match_string('/path/into/include'))

        filter_string = '"to/include"'
        filter = SyntaxFilter(filter_string)
        self.assertFalse(filter.match_string('/path/to/exclude'))
        self.assertTrue(filter.match_string('/path/to/include'))

        filter_string = '"to/include"'
        filter = SyntaxFilter(filter_string)
        self.assertFalse(filter.match_string('/path/into/exclude'))
        self.assertFalse(filter.match_string('/path/into/include'))

    def test_plain_negative_term(self):
        """Test matching with a single negative plain term."""
        filter_string = '--exclude'
        filter = SyntaxFilter(filter_string)
        self.assertFalse(filter.match_string('/path/to/exclude'))
        self.assertTrue(filter.match_string('/path/to/include'))

    def test_positive_and_negative_terms(self):
        """Test matching with both positive and negative plain terms."""
        filter_string = 'folder --exclude'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/folder'))
        self.assertFalse(filter.match_string('/path/to/folder/exclude'))
        self.assertFalse(filter.match_string('/exclude/folder'))

    def test_positive_regex_pattern(self):
        """Test matching with a positive regex pattern."""
        filter_string = '(folder\\d+)'
        filter = SyntaxFilter(filter_string)
        self.assertFalse(filter.match_string('/path/to/folder1'))
        self.assertFalse(filter.match_string('/folder2/subfolder'))
        self.assertFalse(filter.match_string('/path/to/folderA'))

        filter_string = '"(folder\\d+)"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/folder1'))
        self.assertTrue(filter.match_string('/folder2/subfolder'))
        self.assertFalse(filter.match_string('/path/to/folderA'))

        filter_string = '\'(folder\\d+)\''
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/folder1'))
        self.assertTrue(filter.match_string('/folder2/subfolder'))
        self.assertFalse(filter.match_string('/path/to/folderA'))

    def test_negative_regex_pattern(self):
        """Test matching with a negative regex pattern."""
        filter_string = '--(exclude\\d+)'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/exclude1'))
        self.assertTrue(filter.match_string('/exclude2/path'))
        self.assertTrue(filter.match_string('/path/to/include1'))

        filter_string = '--"(exclude\\d+)"'
        filter = SyntaxFilter(filter_string)
        self.assertFalse(filter.match_string('/path/to/exclude1'))
        self.assertFalse(filter.match_string('/exclude2/path'))
        self.assertTrue(filter.match_string('/path/to/include1'))

        filter_string = '--\'(exclude\\d+)\''
        filter = SyntaxFilter(filter_string)
        self.assertFalse(filter.match_string('/path/to/exclude1'))
        self.assertFalse(filter.match_string('/exclude2/path'))
        self.assertTrue(filter.match_string('/path/to/include1'))

    def test_combined_terms_and_patterns(self):
        """Test matching with combined positive and negative terms and patterns."""
        filter_string = 'folder "(file\\d+)" --exclude --"(temp\\d+)"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/folder/file1'))
        self.assertFalse(filter.match_string('/folder/exclude/file1'))
        self.assertFalse(filter.match_string('/folder/file1/temp1'))
        self.assertFalse(filter.match_string('/folder/temp2/file2'))
        self.assertFalse(filter.match_string('/exclude/folder/file1'))

    def test_case_insensitive_matching(self):
        """Test case-insensitive matching."""
        filter_string = 'Folder'
        filter = SyntaxFilter(filter_string, case_sensitive=False)
        self.assertTrue(filter.match_string('/path/to/folder'))
        # self.assertTrue(filter.match_string('/path/to/FOLDER'))
        # self.assertTrue(filter.match_string('/path/to/FoLdEr'))
        # self.assertFalse(filter.match_string('/path/to/another'))

    def test_case_sensitive_matching(self):
        """Test case-sensitive matching."""
        filter_string = 'Folder'
        filter = SyntaxFilter(filter_string, case_sensitive=True)
        self.assertTrue(filter.match_string('/path/to/Folder'))
        self.assertFalse(filter.match_string('/path/to/folder'))
        self.assertFalse(filter.match_string('/path/to/FOLDER'))

    def test_empty_filter_accepts_all(self):
        """Test that an empty filter accepts all paths."""
        filter_string = ''
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/any/path'))
        self.assertTrue(filter.match_string('/another/path'))

    def test_invalid_regex_pattern(self):
        """Test handling of invalid regex patterns."""
        filter_string = '"(invalid[)"'
        filter = SyntaxFilter(filter_string)
        # Should have an invalid regular expression pattern recorded
        self.assertTrue(filter.has_invalid_regex())
        self.assertIn('invalid[', filter.get_invalid_regex())
        # No valid positive patterns, so accept all paths
        self.assertTrue(filter.match_string('/path/to/something'))
        self.assertTrue(filter.match_string('/another/path'))

    def test_caching_behavior(self):
        """Test that caching is functioning without affecting correctness."""
        filter_string = 'folder'
        filter = SyntaxFilter(filter_string)
        # First call to match_string (cache miss)
        self.assertTrue(filter.match_string('/path/to/folder'))
        # Second call with the same arguments (should be a cache hit)
        self.assertTrue(filter.match_string('/path/to/folder'))

    def test_set_filter_string(self):
        """Test updating the filter string."""
        filter = SyntaxFilter('folder')
        self.assertTrue(filter.match_string('/path/to/folder'))
        filter.set_filter_string('--folder')
        self.assertFalse(filter.match_string('/path/to/folder'))
        self.assertTrue(filter.match_string('/path/to/another'))

    def test_match_string_different_filters(self):
        """Test different instances with different filter strings."""
        filter1 = SyntaxFilter('folder')
        filter2 = SyntaxFilter('--folder')
        self.assertTrue(filter1.match_string('/path/to/folder'))
        self.assertFalse(filter2.match_string('/path/to/folder'))

    def test_complex_filter_with_quotes(self):
        """Test filters with quoted phrases and regex patterns."""
        filter_string = '"special folder" "(file\\s+\\d+)" --"temporary files" --"(exclude\\d+)"'
        filter = SyntaxFilter(filter_string, case_sensitive=False)
        self.assertTrue(filter.match_string('/path/to/special folder/file 123'))
        self.assertFalse(filter.match_string('/path/to/special folder/temporary files/file 123'))
        self.assertFalse(filter.match_string('/path/to/special folder/file 123/exclude1'))

    def test_no_positive_patterns(self):
        """Test when only negative patterns are provided."""
        filter_string = '--exclude --"(temp\\d+)"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/include'))
        self.assertFalse(filter.match_string('/path/to/exclude'))
        self.assertFalse(filter.match_string('/path/to/temp1'))

    def test_only_positive_patterns(self):
        """Test when only positive patterns are provided."""
        filter_string = 'include "(file\\d+)"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/include/file1'))
        self.assertFalse(filter.match_string('/path/to/include/fileA'))
        self.assertFalse(filter.match_string('/path/to/another'))

    def test_edge_cases(self):
        """Test various edge cases."""
        # Empty path
        filter = SyntaxFilter('folder')
        self.assertFalse(filter.match_string(''))
        # Path with only slashes
        self.assertFalse(filter.match_string('///'))
        # Path with special characters
        filter = SyntaxFilter('"(foo\\$bar)"')
        self.assertTrue(filter.match_string('/path/to/foo$bar'))
        self.assertFalse(filter.match_string('/path/to/foobar'))

    def test_handling_of_single_and_double_quotes(self):
        """Test handling of single and double quotes in filter strings."""
        filter_string = "'folder name' \"another folder\""
        filter = SyntaxFilter(filter_string)
        self.assertFalse(filter.match_string('/path/to/folder name'))
        self.assertFalse(filter.match_string('/path/to/another folder'))
        self.assertTrue(filter.match_string('/path/to/folder name/another folder'))
        self.assertTrue(filter.match_string('/path/to/another folder/folder name'))
        self.assertFalse(filter.match_string('/path/to/different folder'))

    def test_negations_with_quotes_and_whitespace(self):
        """Test negations with quotes and whitespace handling."""
        filter_string = 'include --"exclude folder"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/include'))
        self.assertFalse(filter.match_string('/path/to/include/exclude folder'))
        self.assertFalse(filter.match_string('/path/to/exclude folder'))

    def test_multiple_whitespace(self):
        """Test filter strings with multiple whitespaces and tabs."""
        filter_string = '  include    "(file\\d+)"   --exclude\t--"(temp\\d+)" '
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/include/file1'))
        self.assertFalse(filter.match_string('/include/file1/temp1'))
        self.assertFalse(filter.match_string('/include/exclude/file1'))
        self.assertFalse(filter.match_string('/include/fileA'))

    def test_non_string_filter(self):
        """Test that non-string filter strings raise TypeError."""
        with self.assertRaises(TypeError):
            SyntaxFilter(filter_string=123)

    def test_non_boolean_case_sensitive(self):
        """Test that non-boolean case_sensitive raises TypeError."""
        with self.assertRaises(TypeError):
            SyntaxFilter(filter_string='folder', case_sensitive='yes')

    def test_invalid_regex_in_filter_string(self):
        """Test invalid regex patterns in the filter string."""
        filter_string = '"(invalid[)"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.has_invalid_regex())
        self.assertIn('invalid[', filter.get_invalid_regex())
        # Since the regex is invalid and no valid positive patterns, accept all
        self.assertTrue(filter.match_string('/path/to/anything'))

    def test_nested_quotes_in_filter_string(self):
        """Test filter strings with nested quotes."""
        filter_string = '"a \'quoted\' word"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/a quoted word'))
        self.assertFalse(filter.match_string('/path/to/another word'))

    def test_escaped_quotes_in_filter_string(self):
        """Test filter strings with escaped quotes."""
        filter_string = '"folder \\"name\\""'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/folder "name"'))
        self.assertFalse(filter.match_string('/path/to/folder name'))

    def test_filter_string_with_only_whitespace(self):
        """Test that a filter string with only whitespace accepts all paths."""
        filter_string = '   '
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/anything'))

    def test_whitespace_in_terms(self):
        """Test that whitespace within terms is handled correctly."""
        filter_string = '"folder   name"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/folder   name'))
        self.assertFalse(filter.match_string('/path/to/folder name'))

    def test_has_invalid_regex_method(self):
        """Test the has_invalid_regex method."""
        filter_string = '(valid_regex)'
        filter = SyntaxFilter(filter_string)
        self.assertFalse(filter.has_invalid_regex())  # No invalid regex patterns

        filter_string = '"(invalid[)"'
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.has_invalid_regex())

    def test_get_invalid_regex(self):
        """Test the get_invalid_regex method."""
        filter_string = '"(invalid[)"'
        filter = SyntaxFilter(filter_string)
        invalid_patterns = filter.get_invalid_regex()
        self.assertIn('invalid[', invalid_patterns)

    def test_filter_with_no_tokens(self):
        """Test filter strings that result in no tokens after parsing."""
        filter_string = '"" \'\''
        filter = SyntaxFilter(filter_string)
        self.assertTrue(filter.match_string('/path/to/anything'))
