import os
import shutil
import tempfile
import unittest

from . import common


class TestStringParser(unittest.TestCase):
    def setUp(self):
        # Create temporary directories for server, job, root, and asset
        self.temp_dir = tempfile.mkdtemp().replace('\\', '/')
        self.server = os.path.join(self.temp_dir, 'test_server')
        self.job = 'test_job'
        self.root = 'test_root'
        self.asset = 'test_asset'

        os.makedirs(f'{self.server}/{self.job}/{self.root}/{self.asset}', exist_ok=True)

        # Initialize the app with active overrides
        common.initialize(
            mode=common.Mode.Core,
            run_app=False,
            server=self.server,
            job=self.job,
            root=self.root,
            asset=self.asset
        )

        tokens = {
            'token': 'my/test/path',
            'token1': 'base1,base2',
            'token2': 'path1,path2',
            'token3': 'base',
            'token4': 'base1,base2,base3',
            'name': 'Alice',
            'age': '30',
            'empty_token': ''
        }
        common.parser.update_env(**tokens)

    def tearDown(self):
        # Shutdown the application environment
        common.shutdown()

        # Remove temporary directories
        shutil.rmtree(self.temp_dir)

    def test_no_tokens(self):
        input_text = 'This is a test string with no tokens.'
        expected = 'This is a test string with no tokens.'
        self.assertEqual(common.parser.format(input_text), expected)

    def test_simple_token(self):
        self.assertEqual(common.parser.format('{token}'), 'my/test/path')

    def test_multiple_tokens(self):
        input_text = 'Name: {name}, Age: {age}'
        expected = 'Name: Alice, Age: 30'
        self.assertEqual(common.parser.format(input_text), expected)

    def test_index_zero(self):
        self.assertEqual(common.parser.format('{token[0]}'), 'my')

    def test_index_negative_one(self):
        self.assertEqual(common.parser.format('{token[-1]}'), 'path')

    def test_slice_zero_to_one(self):
        self.assertEqual(common.parser.format('{token[0-1]}'), 'my/test')

    def test_slice_negative_indices(self):
        self.assertEqual(common.parser.format('{token[-2--1]}'), 'test/path')

    def test_lower_modifier(self):
        self.assertEqual(common.parser.format('{token.lower}'), 'my/test/path')

    def test_upper_modifier(self):
        self.assertEqual(common.parser.format('{token.upper}'), 'MY/TEST/PATH')

    def test_title_modifier(self):
        self.assertEqual(common.parser.format('{token.title}'), 'My/Test/Path')

    def test_combined_slice_and_modifier(self):
        self.assertEqual(common.parser.format('{token[0].upper}'), 'MY')

    def test_generator_token_single_value(self):
        self.assertEqual(common.parser.format('my/{token3*}/path'), 'my/base/path')

    def test_generator_token_multiple_values(self):
        expected = 'my/base1/path\nmy/base2/path\nmy/base3/path'
        self.assertEqual(common.parser.format('my/{token4*}/path'), expected)

    def test_multiple_generator_tokens(self):
        expected = (
            'my/base1/path1\n'
            'my/base1/path2\n'
            'my/base2/path1\n'
            'my/base2/path2'
        )
        self.assertEqual(common.parser.format('my/{token1*}/{token2*}'), expected)

    def test_generator_and_non_generator_tokens(self):
        expected = 'my/base1/base\nmy/base2/base'
        self.assertEqual(common.parser.format('my/{token1*}/{token3}'), expected)

    def test_generator_with_modifiers(self):
        expected = 'my/BASE1/path\nmy/BASE2/path'
        self.assertEqual(common.parser.format('my/{token1*.upper}/path'), expected)

    def test_invalid_syntax(self):
        with self.assertRaises(ValueError):
            common.parser.format('my/{token[}/path')

    def test_empty_generator_token(self):
        self.assertEqual(common.parser.format('value/{empty_token*}/test'), 'value//test')

    def test_slicing_out_of_range(self):
        self.assertEqual(common.parser.format('{token[10]}'), '')

    def test_modifier_on_empty_value(self):
        self.assertEqual(common.parser.format('{empty_token.upper}'), '')

    def test_nested_modifiers_and_slicing(self):
        self.assertEqual(common.parser.format('{token[0].title}'), 'My')

    def test_generator_token_with_slicing_and_modifier(self):
        common.parser.env['token1'] = 'base1/path1,base2/path2'

        expected = 'my/BASE1/path1\nmy/BASE2/path2'
        self.assertEqual(
            common.parser.format('my/{token1*[0].upper}/{token1*[1]}'),
            expected
        )

    def test_adjacent_tokens(self):
        common.parser.env['a'] = 'X,Y'
        common.parser.env['b'] = '1,2'
        expected = 'XX1\nXX2\nYY1\nYY2'  # Updated expected output
        self.assertEqual(common.parser.format('{a*}{a*}{b*}'), expected)

    def test_tokens_with_no_generator(self):
        self.assertEqual(
            common.parser.format('Hello {name}, you are {age} years old.'),
            'Hello Alice, you are 30 years old.'
        )

    def test_tokens_with_mixed_generators(self):
        common.parser.env['greeting'] = 'Hi,Hello'
        expected = 'Hi Alice\nHello Alice'
        self.assertEqual(common.parser.format('{greeting*} {name}'), expected)

    def test_token_with_no_value(self):
        common.parser.env['undefined_token'] = ''
        self.assertEqual(common.parser.format('Value: {undefined_token}'), 'Value: ')

    def test_multiple_tokens_no_generators(self):
        input_text = 'Name: {name}, Age: {age}, Location: {undefined_token}'
        expected = 'Name: Alice, Age: 30, Location: '
        self.assertEqual(common.parser.format(input_text), expected)
