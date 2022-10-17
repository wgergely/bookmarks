"""Item note editor.

The main edit widget is :class:`NoteEditor`, a 

"""
import re
import time

from PySide2 import QtWidgets, QtGui, QtCore

from . import actions
from . import common
from . import database
from . import images
from . import ui

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
            flags=re.IGNORECASE | re.MULTILINE
        ),
        'flag': PathHighlight
    },
    'drivepath': {
        're': re.compile(
            r'((?:[a-zA-Z]{1})[s]?:[/\\](?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            flags=re.IGNORECASE | re.MULTILINE
        ),
        'flag': PathHighlight
    },
    'uncpath': {
        're': re.compile(
            r'([/\\]{1,2}(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            flags=re.IGNORECASE | re.MULTILINE
        ),
        'flag': PathHighlight
    },
    'heading': {
        're': re.compile(
            r'^(?<!#)#{1,2}(?!#)',
            flags=re.IGNORECASE | re.MULTILINE
        ),
        'flag': HeadingHighlight
    },
    'quotes': {
        're': re.compile(
            # Group(2) captures the contents
            r'([\"\'])((?:(?=(\\?))\3.)*?)\1',
            flags=re.IGNORECASE | re.MULTILINE
        ),
        'flag': QuoteHighlight
    },
    'italics': {
        're': re.compile(
            r'([\_])((?:(?=(\\?))\3.)*?)\1',  # Group(2) captures the contents
            flags=re.IGNORECASE | re.MULTILINE
        ),
        'flag': ItalicsHighlight
    },
    'bold': {
        're': re.compile(
            r'([\*])((?:(?=(\\?))\3.)*?)\1',  # Group(2) captures the contents
            flags=re.IGNORECASE | re.MULTILINE
        ),
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
            f = QtCore.QFileInfo(index.data(common.PathRole))
            self.config_path = f'{p}/{common.bookmark_cache_dir}/{f.baseName()}.lock'
        else:
            self.config_path = '/'

        super().__init__(
            self.config_path,
            QtCore.QSettings.IniFormat,
            parent=parent
        )


class Highlighter(QtGui.QSyntaxHighlighter):
    """Class responsible for highlighting urls"""

    def highlightBlock(self, text):
        """Highlights the given text.

        Args:
            text (str): The text to assess.

        Returns:
            tuple: int, int, int

        """
        font = self.document().defaultFont()
        font.setPixelSize(common.size(common.size_font_medium))

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
                    self.setFormat(
                        match.start(0), len(
                            match.group(0)
                        ), char_format
                    )

            if case['flag'] == PathHighlight:
                it = case['re'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        grp = match.group(0)
                        if grp:
                            char_format.setAnchor(True)
                            char_format.setForeground(
                                common.color(common.color_green)
                            )
                            char_format.setAnchorHref(grp)
                            self.setFormat(
                                match.start(
                                    0
                                ), len(grp), char_format
                            )

            if case['flag'] == QuoteHighlight:
                it = case['re'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        if match.group(1) in ('\'', '\"'):
                            grp = match.group(2)
                            if grp:
                                char_format.setAnchor(True)
                                char_format.setForeground(
                                    common.color(common.color_green)
                                )
                                char_format.setAnchorHref(grp)
                                self.setFormat(
                                    match.start(
                                        2
                                    ), len(grp), char_format
                                )

                                char_format.setForeground(
                                    QtGui.QColor(0, 0, 0, 40)
                                )
                                self.setFormat(
                                    match.start(
                                        2
                                    ) - 1, 1, char_format
                                )
                                self.setFormat(
                                    match.start(
                                        2
                                    ) + len(grp), 1, char_format
                                )

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
                                self.setFormat(
                                    match.start(
                                        2
                                    ), len(grp), char_format
                                )

                                char_format.setForeground(
                                    QtGui.QColor(0, 0, 0, 20)
                                )
                                self.setFormat(
                                    match.start(
                                        2
                                    ) - 1, 1, char_format
                                )
                                self.setFormat(
                                    match.start(
                                        2
                                    ) + len(grp), 1, char_format
                                )

            if case['flag'] == BoldHighlight:
                it = case['re'].finditer(text)
                for match in it:
                    groups = match.groups()
                    if groups:
                        if match.group(1) in '*':
                            grp = match.group(2)
                            if grp:
                                char_format.setFontWeight(QtGui.QFont.Bold)
                                self.setFormat(
                                    match.start(
                                        2
                                    ), len(grp), char_format
                                )

                                char_format.setForeground(
                                    QtGui.QColor(0, 0, 0, 20)
                                )
                                self.setFormat(
                                    match.start(
                                        2
                                    ) - 1, 1, char_format
                                )
                                self.setFormat(
                                    match.start(
                                        2
                                    ) + len(grp), 1, char_format
                                )

            char_format.setFont(_font)
            char_format.setForeground(_foreground)
            char_format.setFontWeight(_weight)


class NoteTextEditor(QtWidgets.QTextBrowser):
    """Custom QTextBrowser widget for writing note items.

    The editor automatically sets its size to accommodate the contents of the
    document.

    """

    def __init__(self, text, read_only=False, parent=None):
        super().__init__(parent=parent)

        self.document().setDocumentMargin(common.size(common.size_margin))
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.highlighter = Highlighter(self.document())

        self.setOpenExternalLinks(True)
        self.setOpenLinks(False)
        self.setReadOnly(False)

        if read_only:
            self.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse
            )
        else:
            self.setTextInteractionFlags(
                QtCore.Qt.TextEditorInteraction | QtCore.Qt.LinksAccessibleByMouse
            )

        self.setTabStopWidth(common.size(common.size_margin))
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
        """Slot used to set the editor height based on the current item contents.

        """
        height = self.document().size().height()
        if height > (common.size(common.size_row_height) * 2) and not self.isEnabled():
            self.setFixedHeight(common.size(common.size_row_height) * 2)
            return
        self.setFixedHeight(height)

    def keyPressEvent(self, event):
        """Key press event handler.

        """
        cursor = self.textCursor()
        cursor.setVisualNavigation(True)

        if event.key() == QtCore.Qt.Key_Backtab:
            cursor.movePosition(
                QtGui.QTextCursor.Start,
                QtGui.QTextCursor.MoveAnchor,
                cursor.position(),
            )
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        """Event handler.

        """
        if not self.canInsertFromMimeData(event.mimeData()):
            return
        event.accept()

    def dropEvent(self, event):
        """Event handler.

        """
        index = self.parent().parent().parent().parent().parent().index
        if not index.isValid():
            return

        if not self.canInsertFromMimeData(event.mimeData()):
            return
        event.accept()

        mimedata = event.mimeData()
        self.insertFromMimeData(mimedata)

    def showEvent(self, event):
        """Event handler.

        """
        # Sets the height of the note item
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
            QtWidgets.QApplication.clipboard().setText(
                file_info.filePath()
            )
        else:
            QtGui.QDesktopServices.openUrl(url)


class RemoveNoteButton(ui.ClickableIconButton):
    """Button used to remove a note item.

    """

    def __init__(self, parent=None):
        super().__init__(
            'close',
            (common.color(common.color_red), common.color(common.color_red)),
            common.size(common.size_margin),
            description='Click to remove this note',
            parent=parent
        )
        self.clicked.connect(self.remove_note)

    @QtCore.Slot()
    def remove_note(self):
        """Remove note item action.

        """
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
    custom mime type ('bookmarks/todo-drag'). The latter is needed to accept the
    drag operation
    in the target drop widet.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.dragStartPosition = None

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        pixmap = images.ImageCache.rsc_pixmap(
            'drag_indicator', common.color(common.color_dark_background),
            common.size(common.size_margin)
        )
        self.setPixmap(pixmap)

    def mousePressEvent(self, event):
        """Event handler.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.dragStartPosition = event.pos()

    def mouseMoveEvent(self, event):
        """Event handler.

        """
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
                pixmap.width() - ((common.size(common.size_margin)) * 2),
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
    """A custom label used as an item separator.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        pixmap = QtGui.QPixmap(
            QtCore.QSize(4096, common.size(common.size_separator))
        )
        pixmap.fill(common.color(common.color_blue))
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
        self.setFixedWidth(common.size(common.size_separator))

    def dragEnterEvent(self, event):
        """Event handler.

        """
        if event.mimeData().hasFormat('bookmarks/todo-drag'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Event handler.

        """
        self.parent().dropEvent(event)


class NoteContainerWidget(QtWidgets.QWidget):
    """This widget for storing the added note items.

    As this is the container widget, it is responsible for handling the dragging
    and setting the order of the contained child widgets.

    Attributes:
        items (list): The added note items.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        o = common.size(common.size_margin) * 0.5
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(common.size(common.size_indicator) * 2)

        self.setAcceptDrops(True)

        self.separator = Separator(parent=self)
        self.drop_target_index = -1

        self.items = []

        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def dragEnterEvent(self, event):
        """Event handler.

        """
        if event.mimeData().hasFormat('bookmarks/todo-drag'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Event handler.

        """
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
        """Event handler.

        """
        if self.drop_target_index == -1:
            event.ignore()
            return

        event.accept()

        # Drag from another todo list
        if event.source() not in self.items:
            text = event.source().findChild(NoteTextEditor).document().toHtml()
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

        # Case when items is dragged from another editor instance
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


class NoteItemWidget(QtWidgets.QWidget):
    """The item-wrapper widget for the drag indicator and editor widgets."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.editor = None
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._create_ui()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        o = common.size(common.size_indicator)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o)

    def paintEvent(self, event):
        """Event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(255, 255, 255, 255))
        painter.drawRoundedRect(
            self.rect(), common.size(common.size_indicator),
            common.size(common.size_indicator)
        )
        painter.end()


class NoteEditor(QtWidgets.QDialog):
    """Main widget used to view and edit and add Notes and Tasks."""

    def __init__(self, index, parent=None):
        super().__init__(parent=parent)
        self.note_container_widget = None
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

        self._create_ui()
        self.installEventFilter(self)

        self.init_lock()

    def _create_ui(self):
        """Creates the ui layout."""
        QtWidgets.QVBoxLayout(self)
        o = common.size(common.size_margin)
        self.layout().setSpacing(common.size(common.size_indicator))
        self.layout().setContentsMargins(o, o, o, o)

        # Top row
        height = common.size(common.size_row_height) * 0.6666
        row = ui.add_row(None, height=height, parent=self)
        row.layout().addSpacing(height * 0.33)

        # Thumbnail
        self.add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.color_green), common.color(common.color_green)),
            height,
            description='Click to add a new Todo item...',
            parent=self
        )
        self.add_button.clicked.connect(lambda: self.add_item(idx=0))

        # Name label
        text = 'Notes'
        label = ui.PaintedLabel(
            text, color=common.color(common.color_dark_background),
            size=common.size(common.size_font_large), parent=self
        )
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
        self.add_label = ui.PaintedLabel(
            text, color=common.color(common.color_dark_background),
            parent=row
        )

        row.layout().addWidget(self.add_button, 0)
        row.layout().addWidget(self.add_label, 0)
        row.layout().addStretch(1)

        self.note_container_widget = NoteContainerWidget(parent=self)
        self.setMinimumHeight(common.size(common.size_row_height) * 3.0)

        self.scroll_area = QtWidgets.QScrollArea(parent=self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.note_container_widget)

        self.scroll_area.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.scroll_area.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.layout().addWidget(self.scroll_area)

    def clear(self):
        """Deletes all note item editors.

        """
        for idx in reversed(range(len(list(self.note_container_widget.items)))):
            row = self.note_container_widget.items.pop(idx)
            for c in row.children():
                c.deleteLater()
            self.note_container_widget.layout().removeWidget(row)
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
            source = self.index.data(common.PathRole)
        elif self.index.data(common.TypeRole) == common.SequenceItem:
            source = common.proxy_path(self.index)

        db = database.get_db(*self.index.data(common.ParentPathRole)[0:3])
        v = db.value(source, 'notes', database.AssetTable)
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
        """The path used to initialize the widget.

        """
        return self._index

    def eventFilter(self, widget, event):
        """Event filter handler.

        """
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            font = common.font_db.medium_font(
                common.size(common.size_font_medium)
            )[0]
            painter.setFont(font)
            painter.setRenderHints(QtGui.QPainter.Antialiasing)

            o = common.size(common.size_indicator)
            rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
            painter.setBrush(QtGui.QColor(250, 250, 250, 255))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(rect, o * 2, o * 2)

            center = rect.center()
            rect.setWidth(rect.width() - common.size(common.size_margin))
            rect.setHeight(rect.height() - common.size(common.size_margin))
            rect.moveCenter(center)

            text = 'Click the plus icon on the top to add a note'
            text = text if not len(self.note_container_widget.items) else ''
            common.draw_aliased_text(
                painter, font, rect, text, QtCore.Qt.AlignCenter,
                common.color(common.color_dark_background)
            )
            painter.end()
        return False

    def _get_next_enabled(self, n):
        hasEnabled = False
        for i in range(len(self.note_container_widget.items)):
            item = self.note_container_widget.items[i]
            editor = item.findChild(NoteTextEditor)
            if editor.isEnabled():
                hasEnabled = True
                break

        if not hasEnabled:
            return -1

        # Finding the next enabled editor
        for _ in range(len(self.note_container_widget.items) - n):
            n += 1
            if n >= len(self.note_container_widget.items):
                return self._get_next_enabled(-1)
            item = self.note_container_widget.items[n]
            editor = item.findChild(NoteTextEditor)
            if editor.isEnabled():
                return n

    def key_tab(self):
        """Custom key action.

        """
        if not self.note_container_widget.items:
            return

        n = 0
        for n, item in enumerate(self.note_container_widget.items):
            editor = item.findChild(NoteTextEditor)
            if editor.hasFocus():
                break

        n = self._get_next_enabled(n)
        if n > -1:
            item = self.note_container_widget.items[n]
            editor = item.findChild(NoteTextEditor)
            editor.setFocus()
            self.scroll_area.ensureWidgetVisible(
                editor, ymargin=editor.height()
            )

    def key_return(self, ):
        """Custom key action.

        """
        for item in self.note_container_widget.items:
            editor = item.findChild(NoteTextEditor)

            if not editor.hasFocus():
                continue

            if editor.document().toPlainText():
                continue

            idx = self.note_container_widget.items.index(editor.parent())
            row = self.note_container_widget.items.pop(idx)
            self.todoedfitors_widget.layout().removeWidget(row)
            row.deleteLater()

            break

    def keyPressEvent(self, event):
        """Key press event handler.

        """
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
        """Creates a new :class:`NoteItemWidget`editor and adds it to
        :meth:`NoteContainerWidget.items`.

        Args:
            idx (int): The index of the item to be added. Optional.
            text (str): The text of the item to be added. Optional.

        """
        item = NoteItemWidget(parent=self)

        editor = NoteTextEditor(
            text,
            read_only=self.read_only,
            parent=item
        )
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
            self.note_container_widget.layout().addWidget(item, 0)
            self.note_container_widget.items.append(item)
        else:
            self.note_container_widget.layout().insertWidget(idx, item, 0)
            self.note_container_widget.items.insert(idx, item)

        editor.setFocus()
        item.editor = editor
        return item

    @QtCore.Slot()
    def save_settings(self):
        """Saves the current list of note items to the assets configuration file."""
        if not self.index.isValid():
            return

        data = {}
        for n in range(len(self.note_container_widget.items)):
            item = self.note_container_widget.items[n]
            editor = item.findChild(NoteTextEditor)
            if not editor.document().toPlainText():
                continue
            data[n] = {
                'text': editor.document().toHtml(),
            }

        if self.index.data(common.TypeRole) == common.FileItem:
            source = self.index.data(common.PathRole)
        elif self.index.data(common.TypeRole) == common.SequenceItem:
            source = common.proxy_path(self.index)

        db = database.get_db(*self.index.data(common.ParentPathRole)[0:3])
        with db.connection():
            db.setValue(source, 'notes', data)

    def init_lock(self):
        """Creates a lock file.

        This will prevent other sessions editing notes.

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
        """Event handler.

        """
        if self.parent():
            geo = self.parent().viewport().rect()
            self.resize(geo.width(), geo.height())
        self.setFocus(QtCore.Qt.OtherFocusReason)
        self.refresh()

    def hideEvent(self, event):
        """Hide event handler.

        """
        if not self.read_only:
            self.save_settings()
        self.unlock()

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width),
            common.size(common.size_height)
        )
