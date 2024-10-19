import unittest

from ..common import SyntaxFilter

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
