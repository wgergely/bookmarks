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
import enum
import itertools
import re
import unittest

__all__ = ['StringParser', 'TokenEditor', 'TokenLineEdit']

from datetime import datetime

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common, database


class StringParser(QtCore.QObject):
    token_pattern = re.compile(r'\{([^{}]+?)\}')
    _env = {}

    db_keys = {
        database.BookmarkTable: (
            'prefix',
            'width',
            'height',
            'framerate',
            'startframe',
            'duration'
        ),
        database.AssetTable: (
            'cut_duration',
            'cut_in',
            'cut_out',
            'edit_in',
            'edit_out',
            'asset_width',
            'asset_height',
            'asset_framerate',
        ),
    }

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._connect_signals()

    def _connect_signals(self):
        common.signals.databaseValueChanged.connect(self.update_env)
        common.signals.bookmarkItemActivated.connect(self.update_env)
        common.signals.assetItemActivated.connect(self.update_env)
        common.signals.fileItemActivated.connect(self.update_env)
        common.signals.taskFolderChanged.connect(self.update_env)
        common.signals.activeModeChanged.connect(self.update_env)
        common.signals.activeChanged.connect(self.update_env)

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
        env['today'] = datetime.now().strftime('%Y%m%d')

        env['user'] = common.get_username()
        env['platform'] = common.get_platform()

        env['#'] = '0'
        env['##'] = '00'
        env['###'] = '000'
        env['####'] = '0000'
        env['#####'] = '00000'
        env['#####'] = '000000'
        env['%01d'] = '0'
        env['%02d'] = '00'
        env['%03d'] = '000'
        env['%04d'] = '0000'
        env['%05d'] = '00000'
        env['%06d'] = '00000'

        # Set shot and sequence

        if common.active('asset', path=True):
            seq, shot = common.get_sequence_and_shot(common.active('asset', path=True))
        else:
            seq, shot = '000', '0000'

        env['sequence'] = seq
        env['seq'] = seq
        env['sq'] = env['sequence']

        env['shot'] = shot
        env['sh'] = env['shot']

        # Item properties
        properties = {}
        if common.active('root', args=True):
            db = database.get(*common.active('root', args=True))
            for k in self.db_keys[database.BookmarkTable]:
                v = db.value(db.source(), k, database.BookmarkTable)
                properties[k] = v
            if common.active('asset', args=True):
                for k in self.db_keys[database.AssetTable]:
                    v = db.value(common.active('asset', path=True), k, database.AssetTable)
                    properties[k] = v
            else:
                for k in self.db_keys[database.AssetTable]:
                    properties[k] = None
        else:
            for k in self.db_keys[database.BookmarkTable]:
                properties[k] = None
            for k in self.db_keys[database.AssetTable]:
                properties[k] = None

        env['fps'] = properties['asset_framerate'] or properties['framerate'] or '24'
        env['cut_in'] = properties['cut_in'] or properties['startframe'] or 1
        env['cut_out'] = properties['cut_out'] or properties['duration'] or 100
        env['width'] = properties['asset_width'] or properties['width'] or 1920
        env['height'] = properties['asset_height'] or properties['height'] or 1080
        env['prefix'] = properties['prefix'] or None

        # TODO: Add config values when they're implemented

        # Update env with kwargs
        env.update(kwargs)

        self._env = env

    @property
    def env(self):
        return self._env

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

    @staticmethod
    def _parse_token_expression(token_expr):
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


class EditorMode(enum.IntEnum):
    """Enumeration for different editor modes."""
    LineMode = 1
    TextMode = 2


class TokenSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_formats()

    def _init_formats(self):
        # Initialize the text formats
        self.formats = {}

        # Base color for tokens
        base_color = common.Color.Yellow()  # Gold

        # Complete token format (including braces)
        token_format = QtGui.QTextCharFormat()
        token_format.setForeground(base_color)
        token_format.setFontWeight(QtGui.QFont.Bold)
        self.formats['token'] = token_format

        # Token name format (slightly lighter shade)
        name_format = QtGui.QTextCharFormat()
        name_format.setForeground(base_color.lighter(120))  # Light gold
        name_format.setFontWeight(QtGui.QFont.Bold)
        self.formats['name'] = name_format

        # Generator marker '*' (slightly darker shade)
        generator_format = QtGui.QTextCharFormat()
        generator_format.setForeground(base_color.darker(120))  # Slightly darker gold
        generator_format.setFontWeight(QtGui.QFont.Bold)
        self.formats['generator'] = generator_format

        # Slicing '[...]' (lighter shade)
        slicing_format = QtGui.QTextCharFormat()
        slicing_format.setForeground(base_color.lighter(150))  # Very light gold
        self.formats['slicing'] = slicing_format

        # Modifiers '.modifier' (darker shade)
        modifier_format = QtGui.QTextCharFormat()
        modifier_format.setForeground(base_color.darker(150))  # Dark gold
        modifier_format.setFontWeight(QtGui.QFont.Bold)
        self.formats['modifier'] = modifier_format

    def highlightBlock(self, text):
        # Regex pattern to find tokens including incomplete ones
        token_pattern = re.compile(r'\{[^{}]*?(\}|$)')

        for match in token_pattern.finditer(text):
            start, end = match.span()
            token_text = match.group()

            # Apply the complete token format
            self.setFormat(start, end - start, self.formats['token'])

            # Now parse the token expression to highlight internal parts
            if token_text.endswith('}'):
                token_expr = token_text[1:-1]  # Remove braces
            else:
                token_expr = token_text[1:]  # Remove opening brace only

            # Regex to parse the token expression
            token_expr_pattern = re.compile(r'''
                ^([^\[\].*]+)    # Token name
                (\*)?            # Optional '*'
                (\[[^\]]*\])?    # Optional slicing
                (?:\.(.*))?      # Optional modifiers
                $''', re.VERBOSE)
            m = token_expr_pattern.match(token_expr)
            if not m:
                continue  # Skip if token expression doesn't match
            name, is_generator, slicing, modifiers = m.groups()

            # Calculate positions relative to the start of the token
            token_content_start = start + 1  # After '{'
            current_pos = token_content_start

            # Highlight token name
            name_len = len(name)
            self.setFormat(current_pos, name_len, self.formats['name'])
            current_pos += name_len

            # Highlight generator marker '*'
            if is_generator:
                self.setFormat(current_pos, len(is_generator), self.formats['generator'])
                current_pos += len(is_generator)

            # Highlight slicing '[...]'
            if slicing:
                slicing_len = len(slicing)
                self.setFormat(current_pos, slicing_len, self.formats['slicing'])
                current_pos += slicing_len

            # Highlight modifiers '.modifier'
            if modifiers:
                modifiers_with_dot = '.' + modifiers
                modifiers_len = len(modifiers_with_dot)
                self.setFormat(current_pos, modifiers_len, self.formats['modifier'])


class NumberBar(QtWidgets.QWidget):
    """A custom widget that displays line numbers for a text editor."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.parent().blockCountChanged.connect(self.update_width)
        self.parent().updateRequest.connect(self.update_contents)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        if not self.parent().toPlainText():
            alpha = 0
        else:
            alpha = 20

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, alpha))
        painter.drawRoundedRect(
            event.rect(),
            common.Size.Indicator(),
            common.Size.Indicator()
        )

        block = self.parent().firstVisibleBlock()

        font = self.parent().font()
        metrics = self.parent().fontMetrics()

        # Iterate over all visible text blocks in the document.
        while block.isValid():
            block_number = block.blockNumber()
            block_top = self.parent().blockBoundingGeometry(block).translated(self.parent().contentOffset()).top()

            # Check if the position of the block is outside the visible area.
            if not block.isVisible() or block_top >= event.rect().bottom():
                break

            # We want the line number for the selected line to be bold.
            if block_number == self.parent().textCursor().blockNumber():
                painter.setPen(common.Color.Blue())
            else:
                painter.setPen(common.Color.LightBackground())
            painter.setFont(font)

            # Draw the line number right justified at the position of the line.
            paint_rect = QtCore.QRect(
                0,
                block_top,
                self.width() - (common.Size.Indicator(2.0)),
                metrics.height()
            )

            if self.parent().toPlainText():
                painter.drawText(
                    paint_rect,
                    QtCore.Qt.AlignRight,
                    f'{block_number + 1}'
                )

            block = block.next()

        painter.end()

        super().paintEvent(event)

    def get_width(self):
        metrics = self.parent().fontMetrics()

        count = self.parent().blockCount()
        width = metrics.width(f'{count}') + common.Size.Margin()
        return width

    def update_width(self):
        width = self.get_width()
        if self.width() != width:
            self.setFixedWidth(width)
            self.parent().setViewportMargins(width, 0, 0, 0)

    def update_contents(self, rect, scroll):
        font = self.parent().font()

        if scroll:
            self.scroll(0, scroll)
        else:
            self.update(0, rect.y(), self.width(), rect.height())

        if rect.contains(self.parent().viewport().rect()):
            font_size = self.parent().currentCharFormat().font().pointSize()
            font.setPointSize(font_size)
            font.setStyle(QtGui.QFont.StyleNormal)
            self.update_width()


class TokenEditor(QtWidgets.QPlainTextEdit):
    """A text editor with syntax highlighting, mode-based configurations, and optional line numbering.

    Can operate in either line mode or text mode, adjusting size constraints and displaying line numbers accordingly.

    Signals:
        returnPressed: Emitted when the Return key is pressed.
        textChanged(str): Emitted when the text is changed.
    """

    returnPressed = QtCore.Signal()
    textChanged = QtCore.Signal(str)

    def __init__(self, parent=None, mode=EditorMode.TextMode):
        """Initialize the TokenEditor with the specified mode.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
            mode (EditorMode, optional): The mode of the editor. Defaults to EditorMode.LineMode.
        """
        super().__init__(parent)
        self.mode = mode
        self.highlighter = TokenSyntaxHighlighter(self.document())

        self.completer = QtWidgets.QCompleter(self)
        common.set_stylesheet(self.completer.popup())
        self.completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.modifiers = [
            'upper', 'lower', 'title'
        ]

        self.completer.activated.connect(self.insert_completion)
        super().textChanged.connect(lambda: self.textChanged.emit(self.toPlainText()))

        self._number_bar = None
        self._init_mode()

    @property
    def tokens(self):
        """Available tokens for autocompletion."""
        return list(common.parser.env.keys())

    def text(self):
        """Get the text content."""
        return self.toPlainText()

    def set_text(self, text):
        """Set the text content.

        Args:
            text (str): The text to set.
        """
        self.setPlainText(text)

    def insert_completion(self, completion):
        """Insert the selected completion into the text.

        Args:
            completion (str): The completion string.
        """
        tc = self.textCursor()
        extra = completion[len(self.completer.completionPrefix()):]
        tc.insertText(extra)
        self.setTextCursor(tc)
        self.completer.popup().hide()

    def focusInEvent(self, event):
        """Handle focus in events to notify the completer.

        Args:
            event (QtGui.QFocusEvent): The focus event.
        """
        if self.completer:
            self.completer.setWidget(self)
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        """Handle key press events for custom behavior.

        Args:
            event (QtGui.QKeyEvent): The key event.
        """
        if event.key() == QtCore.Qt.Key_Tab:
            self.move_to_next_token_or_word()
            event.accept()
            return
        elif event.key() == QtCore.Qt.Key_Backtab:
            self.move_to_previous_token_or_word()
            event.accept()
            return

        if self.completer and self.completer.popup().isVisible():
            if event.key() in (
                    QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return,
                    QtCore.Qt.Key_Escape,
            ):
                event.ignore()
                return

        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.returnPressed.emit()
            event.accept()
            return

        if event.text() == '{':
            super().keyPressEvent(event)
            self.insertPlainText('name}')
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Left)
            self.setTextCursor(cursor)
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor, len('name'))
            self.setTextCursor(cursor)
            self.update_completer_model(self.tokens)
            self.show_completer()
        elif (event.key() == QtCore.Qt.Key_Period or event.text() == '.') and self.is_inside_token():
            super().keyPressEvent(event)
            self.update_completer_model(self.modifiers)
            self.show_completer()
        elif (event.key() == QtCore.Qt.Key_BracketLeft or event.text() == '[') and self.is_inside_token():
            super().keyPressEvent(event)
            self.insertPlainText('0]')
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Left)
            self.setTextCursor(cursor)
            cursor.movePosition(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)
        else:
            super().keyPressEvent(event)
            if self.is_inside_token():
                self.update_completer()
            elif self.is_completer_visible():
                self.completer.popup().hide()

    def move_to_next_token_or_word(self):
        """Move the cursor to the next token or word."""
        cursor = self.textCursor()
        pos = cursor.position()
        text = self.toPlainText()
        text_length = len(text)

        search_pos = pos + 1 if pos + 1 < text_length else pos
        next_brace_pos = text.find('{', search_pos)
        if next_brace_pos != -1:
            cursor.setPosition(next_brace_pos)
        else:
            pattern = re.compile(r'\b\w', re.UNICODE)
            match = pattern.search(text, search_pos)
            if match:
                cursor.setPosition(match.start())
            else:
                cursor.movePosition(QtGui.QTextCursor.End)
        self.setTextCursor(cursor)

    def move_to_previous_token_or_word(self):
        """Move the cursor to the previous token or word."""
        cursor = self.textCursor()
        pos = cursor.position()
        text = self.toPlainText()

        search_pos = pos - 1 if pos > 0 else pos
        prev_brace_pos = text.rfind('{', 0, search_pos)
        if prev_brace_pos != -1:
            cursor.setPosition(prev_brace_pos)
        else:
            pattern = re.compile(r'\b\w', re.UNICODE)
            matches = list(pattern.finditer(text, 0, search_pos))
            if matches:
                cursor.setPosition(matches[-1].start())
            else:
                cursor.movePosition(QtGui.QTextCursor.Start)
        self.setTextCursor(cursor)

    def is_completer_visible(self):
        """Check if the completer popup is visible.

        Returns:
            bool: True if visible, False otherwise.
        """
        return self.completer.popup().isVisible()

    def is_inside_token(self):
        """Determine if the cursor is inside a token.

        Returns:
            bool: True if inside a token, False otherwise.
        """
        cursor = self.textCursor()
        pos = cursor.position()
        text = self.toPlainText()

        brace_start = text.rfind('{', 0, pos)
        brace_end = text.find('}', brace_start)

        if brace_start == -1:
            return False
        if brace_end != -1 and pos > brace_end:
            return False
        return True

    def show_completer(self):
        """Display the completer popup at the current cursor position."""
        self.completer.popup().setCurrentIndex(
            self.completer.completionModel().index(0, 0)
        )

        rect = self.cursorRect()
        rect.setWidth(
            self.completer.popup().sizeHintForColumn(0) +
            self.completer.popup().verticalScrollBar().sizeHint().width()
        )
        self.completer.complete(rect)

    def update_completer(self):
        """Update the completer's current index."""
        self.completer.popup().setCurrentIndex(
            self.completer.completionModel().index(0, 0)
        )

    def update_completer_model(self, suggestions):
        """Update the completer model with new suggestions.

        Args:
            suggestions (List[str]): The list of suggestion strings.
        """
        model = QtCore.QStringListModel(suggestions, parent=self.completer)
        model.setStringList(suggestions)
        self.completer.setModel(model)

    def focusOutEvent(self, event):
        """Handle focus out events to hide the completer.

        Args:
            event (QtGui.QFocusEvent): The focus event.
        """
        if self.completer:
            self.completer.popup().hide()
        super().focusOutEvent(event)

    def _init_mode(self):
        """Initialize mode-specific configurations, including size constraints and line numbering."""
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)

        if self.mode == EditorMode.LineMode:
            self.setFixedHeight(common.Size.RowHeight(0.8))
        elif self.mode == EditorMode.TextMode:

            self._number_bar = NumberBar(parent=self)
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Minimum,
                QtWidgets.QSizePolicy.MinimumExpanding
            )

    def sizeHint(self):
        """Provide a recommended size for the editor.

        Returns:
            QtCore.QSize: The recommended size.
        """
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight(0.5)
        )

    def minimumSizeHint(self):
        """Provide a minimum recommended size for the editor.

        Returns:
            QtCore.QSize: The minimum recommended size.
        """
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight(0.1)
        )

    def resizeEvent(self, event):
        """Handle resize events to adjust the NumberBar geometry.

        Args:
            event (QtGui.QResizeEvent): The resize event.
        """
        if self.mode == EditorMode.TextMode and self._number_bar:
            cr = self.contentsRect()
            rec = QtCore.QRect(
                cr.left(),
                cr.top(),
                self._number_bar.get_width(),
                cr.height()
            )
            self._number_bar.setGeometry(rec)
        super().resizeEvent(event)


class TokenLineEdit(TokenEditor):

    def __init__(self, parent=None):
        super().__init__(parent=parent, mode=EditorMode.LineMode)

