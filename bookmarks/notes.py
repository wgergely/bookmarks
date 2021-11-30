# -*- coding: utf-8 -*-
"""Interface to add notes and todo-like annotations for an bookmark or an asset
item.

"""
import json
import base64
import time
import functools
import re

from PySide2 import QtWidgets, QtGui, QtCore

from . import log
from . import common
from . import ui
from . import database
from . import images
from . import actions


NoHighlightFlag = 0b000000
HeadingHighlight = 0b000001
QuoteHighlight = 0b000010
ItalicsHighlight = 0b001000
BoldHighlight = 0b010000
PathHighlight = 0b100000


HIGHLIGHT_RULES = {
    'url': {
        're': re.compile(
            r'((?:rvlink|file|http)[s]?:[/\\][/\\](?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        'flag': PathHighlight
    },
    'drivepath': {
        're': re.compile(
            r'((?:[a-zA-Z]{1})[s]?:[/\\](?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        'flag': PathHighlight
    },
    'uncpath': {
        're': re.compile(
            r'([/\\]{1,2}(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        'flag': PathHighlight
    },
    'heading': {
        're': re.compile(
            r'^(?<!#)#{1,2}(?!#)',
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        'flag': HeadingHighlight
    },
    'quotes': {
        're': re.compile(
            # Group(2) captures the contents
            r'([\"\'])((?:(?=(\\?))\3.)*?)\1',
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        'flag': QuoteHighlight
    },
    'italics': {
        're': re.compile(
            r'([\_])((?:(?=(\\?))\3.)*?)\1',  # Group(2) captures the contents
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        'flag': ItalicsHighlight
    },
    'bold': {
        're': re.compile(
            r'([\*])((?:(?=(\\?))\3.)*?)\1',  # Group(2) captures the contents
            flags=re.IGNORECASE | re.UNICODE | re.MULTILINE),
        'flag': BoldHighlight
    },
}


class Lockfile(QtCore.QSettings):
    """Lockfile to prevent another user from modifying the database whilst
    an edit is in progress.

    """

    def __init__(self, index, parent=None):
        if index.isValid():
            p = '/'.join(index.data(common.ParentPathRole)[0:3])
            f = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
            self.config_path = p + '/.bookmark/' + f.baseName() + '.lock'
        else:
            self.config_path = '/'

        super(Lockfile, self).__init__(
            self.config_path,
            QtCore.QSettings.IniFormat,
            parent=parent
        )


class Highlighter(QtGui.QSyntaxHighlighter):
    """Class responsible for highlighting urls"""

    def highlightBlock(self, text):
        """The highlighting cases are defined in the common module.
        In general we're tying to replicate the ``Markdown`` syntax rendering.

        Args:
            case (str): HIGHLIGHT_RULES dicy key.
            text (str): The text to assess.

        Returns:
            tuple: int, int, int

        """
        font = self.document().defaultFont()
        font.setPixelSize(common.size(common.FontSizeMedium))

        char_format = QtGui.QTextCharFormat()
        char_format.setFont(font)
        char_format.setFontWeight(QtGui.QFont.Normal)
        self.setFormat(0, len(text), char_format)

        _font = char_format.font()
        _foreground = char_format.foreground()
        _weight = char_format.fontWeight()

        flag = NoHighlightFlag
        for case in HIGHLIGHT_RULES.values():
            flag = flag | case['flag']

            if case['flag'] == HeadingHighlight:
                match = case['re'].match(text)
                if match:
                    n = 3 - len(match.group(0))
                    font.setPixelSize(font.pixelSize() + (n * 4))
                    char_format.setFont(font)
                    self.setFormat(0, len(text), char_format)

                    char_format.setForeground(QtGui.QColor(0, 0, 0, 80))
                    self.setFormat(match.start(0), len(
                        match.group(0)), char_format)

            if case['flag'] == PathHighlight:
                it = case['re'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        grp = match.group(0)
                        if grp:
                            char_format.setAnchor(True)
                            char_format.setForeground(common.color(common.GreenColor))
                            char_format.setAnchorHref(grp)
                            self.setFormat(match.start(
                                0), len(grp), char_format)

            if case['flag'] == QuoteHighlight:
                it = case['re'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        if match.group(1) in ('\'', '\"'):
                            grp = match.group(2)
                            if grp:
                                char_format.setAnchor(True)
                                char_format.setForeground(common.color(common.GreenColor))
                                char_format.setAnchorHref(grp)
                                self.setFormat(match.start(
                                    2), len(grp), char_format)

                                char_format.setForeground(
                                    QtGui.QColor(0, 0, 0, 40))
                                self.setFormat(match.start(
                                    2) - 1, 1, char_format)
                                self.setFormat(match.start(
                                    2) + len(grp), 1, char_format)

            if case['flag'] == ItalicsHighlight:
                it = case['re'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        if match.group(1) in '_':
                            grp = match.group(2)
                            if grp:
                                flag == flag | ItalicsHighlight
                                char_format.setFontItalic(True)
                                self.setFormat(match.start(
                                    2), len(grp), char_format)

                                char_format.setForeground(
                                    QtGui.QColor(0, 0, 0, 20))
                                self.setFormat(match.start(
                                    2) - 1, 1, char_format)
                                self.setFormat(match.start(
                                    2) + len(grp), 1, char_format)

            if case['flag'] == BoldHighlight:
                it = case['re'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        if match.group(1) in '*':
                            grp = match.group(2)
                            if grp:
                                char_format.setFontWeight(QtGui.QFont.Bold)
                                self.setFormat(match.start(
                                    2), len(grp), char_format)

                                char_format.setForeground(
                                    QtGui.QColor(0, 0, 0, 20))
                                self.setFormat(match.start(
                                    2) - 1, 1, char_format)
                                self.setFormat(match.start(
                                    2) + len(grp), 1, char_format)

            char_format.setFont(_font)
            char_format.setForeground(_foreground)
            char_format.setFontWeight(_weight)


class TodoItemEditor(QtWidgets.QTextBrowser):
    """Custom QTextBrowser widget for writing `Todo`'s.

    The editor automatically sets its size to accommodate the contents of the document.
    Some of the code has been lifted and implemented from Cameel's implementation.

    https://github.com/cameel/auto-resizing-text-edit/

    """

    def __init__(self, text, read_only=False, parent=None):
        super(TodoItemEditor, self).__init__(parent=parent)
        self.document().setDocumentMargin(common.size(common.WidthMargin))
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.highlighter = Highlighter(self.document())

        self.setOpenExternalLinks(True)
        self.setOpenLinks(False)
        self.setReadOnly(False)

        if read_only:
            self.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse)
        else:
            self.setTextInteractionFlags(
                QtCore.Qt.TextEditorInteraction | QtCore.Qt.LinksAccessibleByMouse)

        self.setTabStopWidth(common.size(common.WidthMargin))
        self.setUndoRedoEnabled(True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.document().setUseDesignMetrics(True)
        self.document().setHtml(text)

        self.document().contentsChanged.connect(self.contentChanged)
        self.anchorClicked.connect(self.open_url)

    @QtCore.Slot()
    def contentChanged(self):
        """Sets the height of the editor."""
        self.adjust_height()

    def adjust_height(self):
        height = self.document().size().height()
        if height > (common.size(common.HeightRow) * 2) and not self.isEnabled():
            self.setFixedHeight(common.size(common.HeightRow) * 2)
            return
        self.setFixedHeight(height)

    def get_minHeight(self):
        """Returns the desired minimum height of the editor."""
        font, metrics = common.font_db.primary_font(common.size(common.FontSizeMedium))
        line_height = (metrics.lineSpacing()) * 1  # Lines tall
        return line_height

    def get_maxHeight(self):
        """Returns the desired minimum height of the editor."""
        font, metrics = common.font_db.primary_font(common.size(common.FontSizeMedium))
        line_height = (metrics.lineSpacing()) * 35  # Lines tall
        return line_height

    def keyPressEvent(self, event):
        """I'm defining custom key events here, the default behaviour is pretty poor.

        In a dream-scenario I would love to implement most of the functions
        of how atom behaves.

        """
        cursor = self.textCursor()
        cursor.setVisualNavigation(True)

        no_modifier = event.modifiers() == QtCore.Qt.NoModifier
        control_modifier = event.modifiers() == QtCore.Qt.ControlModifier
        shift_modifier = event.modifiers() == QtCore.Qt.ShiftModifier

        if event.key() == QtCore.Qt.Key_Backtab:
            cursor.movePosition(
                QtGui.QTextCursor.Start,
                QtGui.QTextCursor.MoveAnchor,
                cursor.position(),
            )
            return
        super(TodoItemEditor, self).keyPressEvent(event)

    def dragEnterEvent(self, event):
        """Checking we can consume the content of the drag data..."""
        if not self.canInsertFromMimeData(event.mimeData()):
            return
        event.accept()

    def dropEvent(self, event):
        """Custom drop event to add content from mime-data."""
        index = self.parent().parent().parent().parent().parent().index
        if not index.isValid():
            return

        if not self.canInsertFromMimeData(event.mimeData()):
            return
        event.accept()

        mimedata = event.mimeData()
        self.insertFromMimeData(mimedata)

    def showEvent(self, event):
        # Sets the height of the todo item
        self.adjust_height()

        # Move the cursor to the end of the document
        cursor = QtGui.QTextCursor(self.document())
        cursor.movePosition(QtGui.QTextCursor.End)
        self.setTextCursor(cursor)

        # Rehighlight the document to apply the formatting
        self.highlighter.rehighlight()

    def canInsertFromMimeData(self, mimedata):
        """Checks if we can insert from the given mime-type."""
        if mimedata.hasUrls():
            return True
        if mimedata.hasHtml():
            return True
        if mimedata.hasText():
            return True
        if mimedata.hasImage():
            return True
        return False

    def open_url(self, url):
        """We're handling the clicking of anchors here manually."""
        if not url.isValid():
            return
        file_info = QtCore.QFileInfo(url.url())
        if file_info.exists():
            actions.reveal(file_info.filePath())
            QtGui.QClipboard().setText(file_info.filePath())
        else:
            QtGui.QDesktopServices.openUrl(url)


class RemoveNoteButton(ui.ClickableIconButton):
    def __init__(self, parent=None):
        super(RemoveNoteButton, self).__init__(
            'close',
            (common.color(common.RedColor), common.color(common.RedColor)),
            common.size(common.WidthMargin),
            description='Click to remove this note',
            parent=parent
        )
        self.clicked.connect(self.remove_note)

    @QtCore.Slot()
    def remove_note(self):
        mbox = ui.MessageBox(
            'Remove note?',
            buttons=[ui.YesButton, ui.NoButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return

        editors_widget = self.parent().parent()
        idx = editors_widget.items.index(self.parent())
        row = editors_widget.items.pop(idx)
        editors_widget.layout().removeWidget(row)
        row.deleteLater()


class DragIndicatorButton(QtWidgets.QLabel):
    """Dotted button indicating a draggable item.

    The button is responsible for initiating a QDrag operation and setting the
    mime data. The data is populated with the `TodoEditor`'s text and the
    custom mime type ('bookmarks/todo-drag'). The latter is needed to accept the drag operation
    in the target drop widet.
    """

    def __init__(self, parent=None):
        super(DragIndicatorButton, self).__init__(parent=parent)
        self.dragStartPosition = None

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'drag_indicator', common.color(common.TextSecondaryColor), common.size(common.WidthMargin))
        self.setPixmap(pixmap)

    def mousePressEvent(self, event):
        """Setting the starting drag position here."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.dragStartPosition = event.pos()

    def mouseMoveEvent(self, event):
        """The drag operation is initiated here."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        left_button = event.buttons() & QtCore.Qt.LeftButton
        if not left_button:
            return

        parent_widget = self.parent()
        drag = QtGui.QDrag(parent_widget)

        # Setting Mime Data
        mime_data = QtCore.QMimeData()
        mime_data.setData('bookmarks/todo-drag', QtCore.QByteArray(bytes()))
        drag.setMimeData(mime_data)

        # Drag pixmap
        # Transparent image
        pixmap = QtGui.QPixmap(parent_widget.size())
        parent_widget.render(pixmap)

        drag.setPixmap(pixmap)
        drag.setHotSpot(
            QtCore.QPoint(
                pixmap.width() - ((common.size(common.WidthMargin)) * 2),
                pixmap.height() / 2.0
            )
        )

        # Drag origin indicator
        pixmap = QtGui.QPixmap(parent_widget.size())

        painter = QtGui.QPainter()
        painter.begin(pixmap)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(200, 200, 200, 255)))
        painter.drawRect(pixmap.rect())
        painter.end()

        overlay_widget = QtWidgets.QLabel(parent=parent_widget)
        overlay_widget.setFixedSize(parent_widget.size())
        overlay_widget.setPixmap(pixmap)

        # Preparing the drag...
        parent_widget.parent().separator.setHidden(False)
        overlay_widget.show()

        # Starting the drag...
        drag.exec_(QtCore.Qt.CopyAction)

        # Cleanup after drag has finished...
        overlay_widget.close()
        overlay_widget.deleteLater()
        parent_widget.parent().separator.setHidden(True)



class Separator(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(Separator, self).__init__(parent=parent)
        pixmap = QtGui.QPixmap(QtCore.QSize(4096, common.size(common.HeightSeparator)))
        pixmap.fill(common.color(common.BlueColor))
        self.setPixmap(pixmap)

        self.setHidden(True)

        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )
        self.setFixedWidth(common.size(common.HeightSeparator))

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('bookmarks/todo-drag'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Calling the parent's drop event, when the drop is on the separator."""
        self.parent().dropEvent(event)


class TodoEditors(QtWidgets.QWidget):
    """This is a convenience widget for storing the added todo items.

    As this is the container widget, it is responsible for handling the dragging
    and setting the order of the contained child widgets.

    Attributes:
        items (list):       The added todo items.

    """

    def __init__(self, parent=None):
        super(TodoEditors, self).__init__(parent=parent)
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        o = common.size(common.WidthMargin) * 0.5
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(common.size(common.WidthIndicator) * 2)

        self.setAcceptDrops(True)

        self.separator = Separator(parent=self)
        self.drop_target_index = -1

        self.items = []

        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def dragEnterEvent(self, event):
        """Accepting the drag operation."""
        if event.mimeData().hasFormat('bookmarks/todo-drag'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Custom drag move event responsible for indicating the drop area."""
        # Move indicator
        idx, y = self._separator_pos(event)

        if y == -1:
            self.separator.setHidden(True)
            self.drop_target_index = -1
            event.ignore()
            return

        event.accept()
        self.drop_target_index = idx

        self.separator.setHidden(False)
        pos = self.mapToGlobal(QtCore.QPoint(self.geometry().x(), y))
        self.separator.move(pos)
        self.separator.setFixedWidth(self.width())

    def dropEvent(self, event):
        if self.drop_target_index == -1:
            event.ignore()
            return

        event.accept()

        # Drag from another todo list
        if event.source() not in self.items:
            text = event.source().findChild(TodoItemEditor).document().toHtml()
            self.parent().parent().parent().add_item(idx=0, text=text)
            self.separator.setHidden(True)
            return

        # Change internal order
        self.setUpdatesEnabled(False)

        self.items.insert(
            self.drop_target_index,
            self.items.pop(self.items.index(event.source()))
        )
        self.layout().removeWidget(event.source())
        self.layout().insertWidget(self.drop_target_index, event.source(), 0)

        self.setUpdatesEnabled(True)

    def _separator_pos(self, event):
        """Returns the position of"""
        idx = 0
        dis = []

        y = event.pos().y()

        # Collecting the available hot-spots for the drag operation
        lines = []
        for n in range(len(self.items)):
            if n == 0:  # first
                line = self.items[n].geometry().top()
                lines.append(line)
                continue

            line = (
                self.items[n - 1].geometry().bottom() +
                self.items[n].geometry().top()
            ) / 2.0
            lines.append(line)

            if n == len(self.items) - 1:  # last
                line = ((
                    self.items[n - 1].geometry().bottom() +
                    self.items[n].geometry().top()
                ) / 2.0)
                lines.append(line)
                line = self.items[n].geometry().bottom()
                lines.append(line)
                break

        # Finding the closest
        for line in lines:
            dis.append(y - line)

        # Cases when items is dragged from another editor instance
        if not dis:
            return 0, 0

        idx = dis.index(min(dis, key=abs))  # The selected line
        if event.source() not in self.items:
            source_idx = idx + 1
        else:
            source_idx = self.items.index(event.source())

        if idx == 0:  # first item
            return (0, lines[idx])
        elif source_idx == idx:  # order remains unchanged
            return (source_idx, lines[idx])
        elif (source_idx + 1) == idx:  # order remains unchanged
            return (source_idx, lines[idx])
        elif source_idx < idx:  # moves up
            return (idx - 1, lines[idx])
        elif source_idx > idx:  # move down
            return (idx, lines[idx])


class TodoItemWidget(QtWidgets.QWidget):
    """The item-wrapper widget for the drag indicator and editor widgets."""

    def __init__(self, parent=None):
        super(TodoItemWidget, self).__init__(parent=parent)
        self.editor = None
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._create_UI()

    def _create_UI(self):
        QtWidgets.QHBoxLayout(self)
        o = common.size(common.WidthIndicator)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(255, 255, 255, 255))
        painter.drawRoundedRect(
            self.rect(), common.size(common.WidthIndicator), common.size(common.WidthIndicator))
        painter.end()


class TodoEditorWidget(QtWidgets.QDialog):
    """Main widget used to view and edit and add Notes and Tasks."""

    def __init__(self, index, parent=None):
        super(TodoEditorWidget, self).__init__(parent=parent)
        self.todoeditors_widget = None
        self._index = index

        self.read_only = False

        self.lock = Lockfile(self.index, parent=self)
        self.destroyed.connect(self.unlock)

        self.lockstamp = int(round(time.time() * 1000))
        self.save_timer = common.Timer(parent=self)
        self.save_timer.setInterval(1000)
        self.save_timer.setSingleShot(False)
        self.save_timer.timeout.connect(self.save_settings)

        self.refresh_timer = common.Timer(parent=self)
        self.refresh_timer.setInterval(10000)  # refresh every 30 seconds
        self.refresh_timer.setSingleShot(False)
        self.refresh_timer.timeout.connect(self.refresh)

        self.setWindowTitle('Notes & Tasks')
        self.setWindowFlags(QtCore.Qt.Widget)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self._create_UI()
        self.installEventFilter(self)

        self.init_lock()


    def _create_UI(self):
        """Creates the ui layout."""
        QtWidgets.QVBoxLayout(self)
        o = common.size(common.WidthMargin)
        self.layout().setSpacing(common.size(common.WidthIndicator))
        self.layout().setContentsMargins(o, o, o, o)

        # Top row
        height = common.size(common.HeightRow) * 0.6666
        row = ui.add_row(None, height=height, parent=self)
        row.layout().addSpacing(height * 0.33)

        def paintEvent(event):
            painter = QtGui.QPainter()
            painter.begin(row)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(0, 0, 0, 255))
            rect = row.rect()
            rect.setTop(rect.bottom())
            painter.drawRect(rect)
            painter.end()

        # row.paintEvent = paintEvent
        # Thumbnail
        self.add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.GreenColor), common.color(common.GreenColor)),
            height,
            description='Click to add a new Todo item...',
            parent=self
        )
        self.add_button.clicked.connect(lambda: self.add_item(idx=0))

        # Name label
        text = 'Notes'
        label = ui.PaintedLabel(
            text, color=common.color(common.TextSecondaryColor), size=common.size(common.FontSizeLarge), parent=self)
        label.setFixedHeight(height)

        self.refresh_button = ui.ClickableIconButton(
            'refresh',
            (QtGui.QColor(0, 0, 0, 255), QtGui.QColor(0, 0, 0, 255)),
            height,
            description='Refresh...',
            parent=self
        )
        self.refresh_button.clicked.connect(self.refresh)

        self.remove_button = ui.ClickableIconButton(
            'close',
            (QtGui.QColor(0, 0, 0, 255), QtGui.QColor(0, 0, 0, 255)),
            height,
            description='Refresh...',
            parent=self
        )
        self.remove_button.clicked.connect(self.close)

        row.layout().addWidget(label)
        row.layout().addStretch(1)
        row.layout().addWidget(self.refresh_button, 0)
        row.layout().addWidget(self.remove_button, 0)

        row = ui.add_row(None, height=height, parent=self)

        text = 'Add Note'
        self.add_label = ui.PaintedLabel(text, color=common.color(common.TextSecondaryColor), parent=row)

        row.layout().addWidget(self.add_button, 0)
        row.layout().addWidget(self.add_label, 0)
        row.layout().addStretch(1)


        self.todoeditors_widget = TodoEditors(parent=self)
        self.setMinimumHeight(common.size(common.HeightRow) * 3.0)

        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setWidget(self.todoeditors_widget)

        self.scrollarea.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.scrollarea.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.layout().addWidget(self.scrollarea)

    def clear(self):
        for idx in reversed(range(len(list(self.todoeditors_widget.items)))):
            row = self.todoeditors_widget.items.pop(idx)
            for c in row.children():
                c.deleteLater()
            self.todoeditors_widget.layout().removeWidget(row)
            row.deleteLater()
            del row

    @common.error
    @common.debug
    def refresh(self):
        """Populates the list from the database.

        """
        if not self.parent():
            return
        if not self.index.isValid():
            return
        if not self.index.data(common.FileInfoLoaded):
            return

        if self.index.data(common.TypeRole) == common.FileItem:
            source = self.index.data(QtCore.Qt.StatusTipRole)
        elif self.index.data(common.TypeRole) == common.SequenceItem:
            source = common.proxy_path(self.index)

        db = database.get_db(*self.index.data(common.ParentPathRole)[0:3])
        v = db.value(source, 'notes')
        if not v:
            return

        self.clear()

        keys = sorted(v.keys())
        for k in keys:
            self.add_item(
                text=v[k]['text']
            )

    @property
    def index(self):
        """The path used to initialize the widget."""
        return self._index

    def eventFilter(self, widget, event):
        """Using  the custom event filter to paint the background."""
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            font = common.font_db.secondary_font(
                common.size(common.FontSizeMedium))[0]
            painter.setFont(font)
            painter.setRenderHints(QtGui.QPainter.Antialiasing)

            o = common.size(common.WidthIndicator)
            rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
            painter.setBrush(QtGui.QColor(250, 250, 250, 255))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(rect, o * 2, o * 2)

            center = rect.center()
            rect.setWidth(rect.width() - common.size(common.WidthMargin))
            rect.setHeight(rect.height() - common.size(common.WidthMargin))
            rect.moveCenter(center)

            text = 'Click the plus icon on the top to add a note'
            text = text if not len(self.todoeditors_widget.items) else ''
            common.draw_aliased_text(
                painter, font, rect, text, QtCore.Qt.AlignCenter, common.color(common.BackgroundDarkColor))
            painter.end()
        return False

    def _get_next_enabled(self, n):
        hasEnabled = False
        for i in range(len(self.todoeditors_widget.items)):
            item = self.todoeditors_widget.items[i]
            editor = item.findChild(TodoItemEditor)
            if editor.isEnabled():
                hasEnabled = True
                break

        if not hasEnabled:
            return -1

        # Finding the next enabled editor
        for _ in range(len(self.todoeditors_widget.items) - n):
            n += 1
            if n >= len(self.todoeditors_widget.items):
                return self._get_next_enabled(-1)
            item = self.todoeditors_widget.items[n]
            editor = item.findChild(TodoItemEditor)
            if editor.isEnabled():
                return n

    def key_tab(self):
        """Defining tabbing forward between items."""
        if not self.todoeditors_widget.items:
            return

        n = 0
        for n, item in enumerate(self.todoeditors_widget.items):
            editor = item.findChild(TodoItemEditor)
            if editor.hasFocus():
                break

        n = self._get_next_enabled(n)
        if n > -1:
            item = self.todoeditors_widget.items[n]
            editor = item.findChild(TodoItemEditor)
            editor.setFocus()
            self.scrollarea.ensureWidgetVisible(
                editor, ymargin=editor.height())

    def key_return(self,):
        for item in self.todoeditors_widget.items:
            editor = item.findChild(TodoItemEditor)

            if not editor.hasFocus():
                continue

            if editor.document().toPlainText():
                continue

            idx = self.todoeditors_widget.items.index(editor.parent())
            row = self.todoeditors_widget.items.pop(idx)
            self.todoedfitors_widget.layout().removeWidget(row)
            row.deleteLater()

            break

    def keyPressEvent(self, event):
        """Custom keypresses."""
        control_modifier = event.modifiers() == QtCore.Qt.ControlModifier
        shift_modifier = event.modifiers() == QtCore.Qt.ShiftModifier

        if event.key() == QtCore.Qt.Key_Escape:
            self.close()

        if shift_modifier:
            if event.key() == QtCore.Qt.Key_Tab:
                return True
            if event.key() == QtCore.Qt.Key_Backtab:
                return True

        if control_modifier:
            if event.key() == QtCore.Qt.Key_S:
                self.save_settings()
                return True
            elif event.key() == QtCore.Qt.Key_N:
                self.add_button.clicked.emit()
                return True
            elif event.key() == QtCore.Qt.Key_Tab:
                self.key_tab()
                return True
            elif event.key() == QtCore.Qt.Key_Return:
                self.key_return()

    def add_item(self, idx=None, text=None):
        """Creates a new widget containing the editor and drag widgets.

        The method is responsible for adding the item the EditorsWidget layout
        and the EditorsWidget.items property.

        """
        item = TodoItemWidget(parent=self)

        editor = TodoItemEditor(
            text, read_only=self.read_only, parent=item)
        editor.setFocusPolicy(QtCore.Qt.StrongFocus)
        item.layout().addWidget(editor, 1)

        drag = DragIndicatorButton(parent=item)
        drag.setFocusPolicy(QtCore.Qt.NoFocus)

        item.layout().addWidget(drag)
        if self.read_only:
            drag.setDisabled(True)

        if not self.read_only:
            remove = RemoveNoteButton(parent=item)
            remove.setFocusPolicy(QtCore.Qt.NoFocus)
            item.layout().addWidget(remove)

        if idx is None:
            self.todoeditors_widget.layout().addWidget(item, 0)
            self.todoeditors_widget.items.append(item)
        else:
            self.todoeditors_widget.layout().insertWidget(idx, item, 0)
            self.todoeditors_widget.items.insert(idx, item)

        editor.setFocus()
        item.editor = editor
        return item

    @QtCore.Slot()
    def save_settings(self):
        """Saves the current list of todo items to the assets configuration file."""
        if not self.index.isValid():
            return

        data = {}
        for n in range(len(self.todoeditors_widget.items)):
            item = self.todoeditors_widget.items[n]
            editor = item.findChild(TodoItemEditor)
            if not editor.document().toPlainText():
                continue
            data[n] = {
                'text': editor.document().toHtml(),
            }

        if self.index.data(common.TypeRole) == common.FileItem:
            source = self.index.data(QtCore.Qt.StatusTipRole)
        elif self.index.data(common.TypeRole) == common.SequenceItem:
            source = common.proxy_path(self.index)

        db = database.get_db(*self.index.data(common.ParentPathRole)[0:3])
        with db.connection():
            db.setValue(source, 'notes', data)

    def init_lock(self):
        """Creates a lock on the current file so it can't be edited by other users.
        It will also start the auto-save timer.
        """
        if not self.parent():
            return
        if not self.index.isValid():
            return

        v = self.lock.value('open')
        v = False if v is None else v
        v = v if isinstance(v, bool) else (
            False if v.lower() == 'false' else True)
        is_open = v

        stamp = self.lock.value('stamp')
        if stamp is not None:
            stamp = int(stamp)

        if not is_open:
            self.read_only = False
            self.add_button.show()
            self.add_label.show()
            self.refresh_button.hide()
            self.save_timer.start()
            self.refresh_timer.stop()

            self.lock.setValue('open', True)
            self.lock.setValue('stamp', self.lockstamp)
            return

        if stamp == self.lockstamp:
            self.read_only = False
            self.add_label.show()
            self.add_button.show()
            self.refresh_button.hide()
            self.save_timer.start()
            self.refresh_timer.stop()

            self.lock.setValue('stamp', self.lockstamp)
            return

        if stamp != self.lockstamp:
            self.read_only = True
            self.add_button.hide()
            self.add_label.hide()
            self.refresh_button.show()
            self.save_timer.stop()
            self.refresh_timer.start()

    @QtCore.Slot()
    def unlock(self):
        """Removes the temporary lockfile on close"""
        if not self.parent():
            return
        if not self.index.isValid():
            return

        v = self.lock.value('open')
        v = False if v is None else v
        v = v if isinstance(v, bool) else (
            False if v.lower() == 'false' else True)
        is_open = v

        stamp = self.lock.value('stamp')
        if stamp is not None:
            stamp = int(stamp)

        if is_open and stamp == self.lockstamp:
            self.lock.setValue('stamp', None)
            self.lock.setValue('open', False)

    def showEvent(self, event):
        if self.parent():
            geo = self.parent().viewport().rect()
            self.resize(geo.width(), geo.height())
        self.setFocus(QtCore.Qt.OtherFocusReason)
        self.refresh()

    def hideEvent(self, event):
        if not self.read_only:
            self.save_settings()
        self.unlock()

    def sizeHint(self):
        """Custom size."""
        return QtCore.QSize(common.size(common.DefaultWidth), common.size(common.DefaultHeight))
