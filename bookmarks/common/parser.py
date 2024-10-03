"""This module provides the :class:`StringParser` class, which is used to parse strings containing tokens and replace
them with values from a given environment. The parser supports features such as simple token replacement, modifiers,
slicing, and generator tokens.

Features:
    - **Simple Token Replacement**: Replaces tokens with their corresponding values from the environment.
    - **Modifiers**: Applies transformations like `lower`, `upper`, and `title` to token values.
    - **Slicing**: Extracts parts of a token value based on indices.
    - **Generator Tokens**: Generates multiple strings by iterating over multiple values for tokens marked with a `*`.

Example:

    .. code-block:: python

        from tokens import StringParser

        parser = StringParser()
        parser.env = {
            'name': 'Alice',
            'greeting': 'Hello,Hi',
            'path': 'home/user/docs',
            'options': 'opt1,opt2',
        }

        # Simple replacement
        print(parser.format('Welcome, {name}!'))
        # Output: Welcome, Alice!

        # Using modifiers
        print(parser.format('Name in uppercase: {name.upper}'))
        # Output: Name in uppercase: ALICE

        # Using slicing
        print(parser.format('First directory: {path[0]}'))
        # Output: First directory: home

        # Using generator tokens
        print(parser.format('{greeting*}, {name}!'))
        # Output:
        # Hello, Alice!
        # Hi, Alice!

        # Combining slicing and modifiers with generators
        print(parser.format('Options:\n{options*.upper}'))
        # Output:
        # OPT1
        # OPT2


"""
import itertools
import re
import unittest

__all__ = ['StringParser']

from datetime import datetime

from PySide2 import QtCore

from .. import common


class StringParser(QtCore.QObject):
    token_pattern = re.compile(r'\{([^{}]+?)\}')
    _env = {}

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._connect_signals()

    def _connect_signals(self):
        common.signals.databaseValueUpdated.connect(self.update_env)
        common.signals.bookmarkItemActivated.connect(self.update_env)
        common.signals.assetItemActivated.connect(self.update_env)
        common.signals.fileItemActivated.connect(self.update_env)
        common.signals.taskFolderChanged.connect(self.update_env)
        common.signals.databaseValueUpdated.connect(self.update_env)

    @QtCore.Slot()
    def update_env(self, *args, **kwargs):
        env = {}

        # Active values
        env['server'] = common.active('server')
        env['job'] = common.active('job')
        env['root'] = common.active('root')
        env['asset'] = common.active('asset')
        env['task'] = common.active('task')

        # Bookmark values
        env['bookmark'] = common.active('root', path=True)

        # Properties
        from .. import database
        if common.active('root', args=True):
            db = database.get(*common.active('root', args=True))
            for _k in database.TABLES[database.BookmarkTable]:
                if _k == 'id':
                    continue
                if database.TABLES[database.BookmarkTable][_k]['type'] == dict:
                    continue
                _v = db.value(db.source(), _k, database.BookmarkTable)
                if not _v:
                    continue
                _k = _k.replace('bookmark_', '')
                _k = f'bookmark_{_k}'
                env[_k] = _v

        if common.active('asset', args=True):
            db = database.get(*common.active('root', args=True))
            for _k in database.TABLES[database.AssetTable]:
                if _k == 'id':
                    continue
                if database.TABLES[database.AssetTable][_k]['type'] == dict:
                    continue
                _v = db.value(common.active('asset', path=True), _k, database.AssetTable)
                if not _v:
                    continue
                _k = _k.replace('asset_', '')
                _k = f'asset_{_k}'
                env[_k] = _v

        # Misc values
        env['year'] = datetime.now().year
        env['month'] = datetime.now().month
        env['day'] = datetime.now().day
        env['hour'] = datetime.now().hour
        env['minute'] = datetime.now().minute
        env['second'] = datetime.now().second

        env['date'] = datetime.now().strftime('%Y%m%d')

        env['user'] = common.get_username()
        env['platform'] = common.get_platform()

        env['#'] = '0'
        env['##'] = '00'
        env['###'] = '000'
        env['####'] = '0000'
        env['#####'] = '00000'
        env['%01d'] = '0'
        env['%01d'] = '00'
        env['%02d'] = '000'
        env['%03d'] = '0000'
        env['%04d'] = '00000'
        env['%05d'] = '000000'

    @property
    def env(self):
        return self._env

    @env.setter
    def env(self, value):
        if not isinstance(value, dict):
            raise ValueError('Environment must be a dictionary')
        self._env.update(value)

    def format(self, text, **kwargs):
        env = self.env.copy()
        env.update(kwargs)

        for k, v in env.items():
            if v is None:
                env[k] = ''
            else:
                env[k] = str(v)

        # Find all tokens in the text
        tokens = []
        for match in self.token_pattern.finditer(text):
            start, end = match.span()
            token_expr = match.group(1)
            tokens.append({'start': start, 'end': end, 'expr': token_expr})

        if not tokens:
            return text

        # Parse all token expressions
        for token in tokens:
            token_expr = token['expr']
            parsed = self._parse_token_expression(token_expr)
            token.update(parsed)

        # Collect generator tokens by name
        generator_token_names = set()
        for token in tokens:
            if token['is_generator']:
                generator_token_names.add(token['name'])

        # Get possible values for each generator token name
        generator_token_values = {}
        for name in generator_token_names:
            value = env.get(name, '')
            values = value.split(',') if value else ['']
            generator_token_values[name] = values

        # Generate combinations over generator token names
        names = sorted(generator_token_values.keys())
        if generator_token_values:
            values_list = [generator_token_values[name] for name in names]
            combinations = list(itertools.product(*values_list))
        else:
            combinations = [()]

        results = []
        for combo in combinations:
            # Map token names to values
            token_assignments = dict(zip(names, combo))

            # Build the result string
            new_text_parts = []
            last_end = 0
            for token in tokens:
                start = token['start']
                end = token['end']
                # Append text before the token
                new_text_parts.append(text[last_end:start])

                # Get the base value
                if token['is_generator']:
                    val = token_assignments[token['name']]
                else:
                    val = env.get(token['name'], '')

                # Apply slicing and modifiers
                if token['slicing']:
                    val = self._apply_slicing(val, token['slicing'][1:-1])  # Remove '[' and ']'
                for modifier in token['modifiers']:
                    val = self._apply_modifier(val, modifier)

                # Append the token value
                new_text_parts.append(val)
                last_end = end
            # Append the text after the last token
            new_text_parts.append(text[last_end:])
            new_text = ''.join(new_text_parts)
            results.append(new_text)
        # Return the results
        return '\n'.join(results)

    def _parse_token_expression(self, token_expr):
        """
        Parses the token expression and returns a dictionary with components:
        - name: the token name
        - is_generator: whether the token is a generator (has a '*')
        - slicing: the slicing part (if any)
        - modifiers: a list of modifiers (if any)
        """
        # Regex to parse the token expression
        pattern = re.compile(r'''
            ^([^\[\].*]+)    # Token name (group 1)
            (\*)?            # Optional '*' for generator (group 2)
            (\[[^\]]+\])?    # Optional slicing (group 3)
            (?:\.(.*))?      # Optional modifiers after '.' (group 4)
            $''', re.VERBOSE)
        match = pattern.match(token_expr)
        if not match:
            raise ValueError(f"Invalid token expression '{token_expr}'")
        name, is_generator, slicing, modifiers = match.groups()
        is_generator = bool(is_generator)
        modifiers = modifiers.split('.') if modifiers else []
        return {
            'name': name,
            'is_generator': is_generator,
            'slicing': slicing,
            'modifiers': modifiers
        }

    @staticmethod
    def _apply_modifier(value, modifier):
        if modifier == 'lower':
            return value.lower()
        elif modifier == 'upper':
            return value.upper()
        elif modifier == 'title':
            return value.title()
        # Add more modifiers as needed
        return value

    @staticmethod
    def _apply_slicing(value, slice_expr):
        parts = value.split('/')
        # Match the slice expression with support for negative numbers
        match = re.match(r'^(-?\d+)(?:-(-?\d+))?$', slice_expr)
        if not match:
            raise ValueError("Invalid slice expression")
        start_str, end_str = match.groups()
        start = int(start_str)
        end = int(end_str) if end_str is not None else None

        # Adjust negative indices
        if start < 0:
            start += len(parts)
        if end is not None:
            if end < 0:
                end += len(parts)
            end += 1  # Adjust end for inclusive range
            sliced_parts = parts[start:end]
        else:
            if 0 <= start < len(parts):
                sliced_parts = [parts[start]]
            else:
                sliced_parts = []

        sliced = '/'.join(sliced_parts)
        return sliced


class TestStringParser(unittest.TestCase):
    def setUp(self):
        self._env = {
            'token': 'my/test/path',
            'token1': 'base1,base2',
            'token2': 'path1,path2',
            'token3': 'base',
            'token4': 'base1,base2,base3',
            'name': 'Alice',
            'age': '30',
            'empty_token': ''
        }
        self._parser = StringParser()
        self._parser.env = self._env

    def test_no_tokens(self):
        input_text = 'This is a test string with no tokens.'
        expected = 'This is a test string with no tokens.'
        self.assertEqual(self._parser.format(input_text), expected)

    def test_simple_token(self):
        self.assertEqual(self._parser.format('{token}'), 'my/test/path')

    def test_multiple_tokens(self):
        input_text = 'Name: {name}, Age: {age}'
        expected = 'Name: Alice, Age: 30'
        self.assertEqual(self._parser.format(input_text), expected)

    def test_index_zero(self):
        self.assertEqual(self._parser.format('{token[0]}'), 'my')

    def test_index_negative_one(self):
        self.assertEqual(self._parser.format('{token[-1]}'), 'path')

    def test_slice_zero_to_one(self):
        self.assertEqual(self._parser.format('{token[0-1]}'), 'my/test')

    def test_slice_negative_indices(self):
        self.assertEqual(self._parser.format('{token[-2--1]}'), 'test/path')

    def test_lower_modifier(self):
        self.assertEqual(self._parser.format('{token.lower}'), 'my/test/path')

    def test_upper_modifier(self):
        self.assertEqual(self._parser.format('{token.upper}'), 'MY/TEST/PATH')

    def test_title_modifier(self):
        self.assertEqual(self._parser.format('{token.title}'), 'My/Test/Path')

    def test_combined_slice_and_modifier(self):
        self.assertEqual(self._parser.format('{token[0].upper}'), 'MY')

    def test_generator_token_single_value(self):
        self.assertEqual(self._parser.format('my/{token3*}/path'), 'my/base/path')

    def test_generator_token_multiple_values(self):
        expected = 'my/base1/path\nmy/base2/path\nmy/base3/path'
        self.assertEqual(self._parser.format('my/{token4*}/path'), expected)

    def test_multiple_generator_tokens(self):
        expected = (
            'my/base1/path1\n'
            'my/base1/path2\n'
            'my/base2/path1\n'
            'my/base2/path2'
        )
        self.assertEqual(self._parser.format('my/{token1*}/{token2*}'), expected)

    def test_generator_and_non_generator_tokens(self):
        expected = 'my/base1/base\nmy/base2/base'
        self.assertEqual(self._parser.format('my/{token1*}/{token3}'), expected)

    def test_generator_with_modifiers(self):
        expected = 'my/BASE1/path\nmy/BASE2/path'
        self.assertEqual(self._parser.format('my/{token1*.upper}/path'), expected)

    def test_invalid_syntax(self):
        with self.assertRaises(ValueError):
            self._parser.format('my/{token[}/path')

    def test_empty_generator_token(self):
        self.assertEqual(self._parser.format('value/{empty_token*}/test'), 'value//test')

    def test_slicing_out_of_range(self):
        self.assertEqual(self._parser.format('{token[10]}'), '')

    def test_modifier_on_empty_value(self):
        self.assertEqual(self._parser.format('{empty_token.upper}'), '')

    def test_nested_modifiers_and_slicing(self):
        self.assertEqual(self._parser.format('{token[0].title}'), 'My')

    def test_generator_token_with_slicing_and_modifier(self):
        self._parser.env['token1'] = 'base1/path1,base2/path2'
        expected = 'my/BASE1/path1\nmy/BASE2/path2'
        self.assertEqual(
            self._parser.format('my/{token1*[0].upper}/{token1*[1]}'),
            expected
        )

    def test_adjacent_tokens(self):
        self._parser.env['a'] = 'X,Y'
        self._parser.env['b'] = '1,2'
        expected = 'XX1\nXX2\nYY1\nYY2'  # Updated expected output
        self.assertEqual(self._parser.format('{a*}{a*}{b*}'), expected)

    def test_tokens_with_no_generator(self):
        self.assertEqual(
            self._parser.format('Hello {name}, you are {age} years old.'),
            'Hello Alice, you are 30 years old.'
        )

    def test_tokens_with_mixed_generators(self):
        self._parser.env['greeting'] = 'Hi,Hello'
        expected = 'Hi Alice\nHello Alice'
        self.assertEqual(self._parser.format('{greeting*} {name}'), expected)

    def test_token_with_no_value(self):
        self._parser.env['undefined_token'] = ''
        self.assertEqual(self._parser.format('Value: {undefined_token}'), 'Value: ')

    def test_multiple_tokens_no_generators(self):
        input_text = 'Name: {name}, Age: {age}, Location: {undefined_token}'
        expected = 'Name: Alice, Age: 30, Location: '
        self.assertEqual(self._parser.format(input_text), expected)
