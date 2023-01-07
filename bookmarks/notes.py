"""Item note editor.

The main edit widget is :class:`NoteEditor`, a 

"""
import functools
import re
import time

from PySide2 import QtWidgets, QtGui, QtCore

from . import actions
from . import common
from . import images
from . import ui


class Lockfile(QtCore.QSettings):
    """Lockfile to prevent another user from modifying the database whilst
    an edit is in progress.

    """

    def __init__(self, index, parent=None):
        self.index = index
        self.lockstamp = int(round(time.time() * 1000))
        self.read_only = False

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

    def _get_values(self):
        is_open = self.value('open')
        is_open = False if is_open is None else is_open
        is_open = is_open if isinstance(is_open, bool) else (
            False if is_open.lower() == 'false' else True)

        stamp = self.value('stamp')
        if stamp is not None:
            stamp = int(stamp)

        return is_open, stamp

    def init_lock(self):
        """Creates a lock file.

        This will prevent other sessions editing notes.

        """
        if not self.index.isValid():
            return

        is_open, stamp = self._get_values()

        if not is_open:
            self.read_only = False
            self.setValue('open', True)
            self.setValue('stamp', self.lockstamp)
            return

        if stamp == self.lockstamp:
            self.lock.setValue('stamp', self.lockstamp)
            return

        if stamp != self.lockstamp:
            self.read_only = True

    @QtCore.Slot()
    def unlock(self):
        """Removes the temporary lockfile on close"""
        if not self.index.isValid():
            return

        is_open, stamp = self._get_values()

        if is_open and stamp == self.lockstamp:
            self.setValue('stamp', None)
            self.setValue('open', False)


class SyntaxHighliter(QtGui.QSyntaxHighlighter):
    formats = {
        'bold': {
            'regex': re.compile(r'(\*\*|__)(.*?)(\*\*|__)', re.IGNORECASE),
            'flag': 0b000000,
        },
        'italic': {
            'regex': re.compile(r'(\*|_)(.*?)(\*|_)', re.IGNORECASE),
            'flag': 0b000001,
        },
        'header': {
            'regex': re.compile(r'(#+)(.*)', re.IGNORECASE),
            'flag': 0b000010,
        },
        'image': {
            'regex': re.compile(r'!\[(.*?)\]\((.*?)\)', re.IGNORECASE),
            'flag': 0b001000,
        },
        'quote': {
            'regex': re.compile(r'>\s(.*)', re.IGNORECASE),
            'flag': 0b010000,
        },
        'url': {
            'regex': re.compile(
                r'\b[\w.+-]+://[^\s]+',
                re.IGNORECASE),
            'flag': 0b100000,
        },
        'filepath': {
            'regex': re.compile(
                r'^(?:\s|^)((?:[A-Za-z]\:|(?:\/|\\))(?:[\/\\][^\/\\:*?"<>|\r\n]+)*[\/\\][^\/\\:*?"<>|\r\n]+|(?:[A-Za-z]\:|(?:\/|\\))(?:[\/\\][^\/\\:*?"<>|\r\n]+)*(?:[^\/\\:*?"<>|\r\n]+\.?)+)(?=\s|$)$',
                re.IGNORECASE | re.MULTILINE),
            'flag': 0b000000,
        },
    }

    def __init__(self, document, parent=None):
        super().__init__(document, parent=parent)

    @functools.lru_cache(maxsize=4194304)
    def _get_text_format(self, k, href):
        light_font, _ = common.font_db.light_font(common.size(common.size_font_medium))
        large_font, _ = common.font_db.bold_font(common.size(common.size_font_large))
        f = QtGui.QTextCharFormat()
        f.setFont(light_font)
        if k == 'bold':
            f.setFontWeight(QtGui.QFont.Bold)
        elif k == 'italic':
            f.setFontItalic(True)
        elif k == 'header':
            f.setFont(large_font)
            f.setFontWeight(QtGui.QFont.Bold)
            f.setForeground(common.color(common.color_blue))
        elif k == 'image':
            f.setForeground(common.color(common.color_blue))
        elif k == 'quote':
            f.setForeground(common.color(common.color_blue))
        elif k == 'url':
            f.setFontWeight(QtGui.QFont.Bold)
            f.setForeground(common.color(common.color_blue))
        elif k == 'filepath':
            f.setFontWeight(QtGui.QFont.Bold)
            f.setForeground(common.color(common.color_green))
        return f

    def highlightBlock(self, text):
        for k in self.formats:
            e = self.formats[k]['regex']
            it = e.finditer(text)

            for match in it:
                grp = match.group(0)

                index = match.span()[0]
                length = match.span()[1] - match.span()[0]
                f = self._get_text_format(k, grp)
                self.setFormat(index, length, f)


class TextEditor(QtWidgets.QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.highlighter = SyntaxHighliter(self.document())

        self.document().setUseDesignMetrics(True)
        self.document().setDocumentMargin(common.size(common.size_margin))

        self.setTabStopWidth(common.size(common.size_margin))

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.setUndoRedoEnabled(True)
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.setReadOnly(False)
        self.setTextInteractionFlags(
            QtCore.Qt.TextEditorInteraction |
            QtCore.Qt.LinksAccessibleByMouse
        )

        self.setAcceptRichText(False)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._connect_signals()

    def _connect_signals(self):
        pass

    def mouseMoveEvent(self, event):
        QtWidgets.QApplication.instance().restoreOverrideCursor()
        super().mouseMoveEvent(event)

        if self.textCursor().selectedText():
            return
        if not self.underMouse():
            return

        pos = event.pos()
        cursor = self.cursorForPosition(pos)
        block = cursor.block()
        text = block.text()
        idx = cursor.positionInBlock()

        for k in ('url', 'filepath'):
            e = self.highlighter.formats[k]['regex']
            it = e.finditer(text)

            for match in it:
                grp = match.group(0)

                index = match.span()[0]
                length = match.span()[1] - match.span()[0]

                # Match anchor based on cursor position
                if not (index <= idx <= index + length):
                    continue

                _rect = self.cursorRect(cursor)
                _center = _rect.center()
                _rect.setWidth(common.size(common.size_margin))
                _rect.moveCenter(_center)

                if not _rect.contains(pos):
                    continue

                if k == 'url':
                    QtWidgets.QApplication.instance().setOverrideCursor(
                        QtCore.Qt.PointingHandCursor)
                    return
                if k == 'filepath':
                    QtWidgets.QApplication.instance().setOverrideCursor(
                        QtCore.Qt.PointingHandCursor)
                    return

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        if self.textCursor().selectedText():
            return
        if not self.underMouse():
            return

        pos = event.pos()
        cursor = self.cursorForPosition(pos)
        block = cursor.block()
        text = block.text()
        idx = cursor.positionInBlock()

        for k in ('url', 'filepath'):
            e = self.highlighter.formats[k]['regex']
            it = e.finditer(text)

            for match in it:
                grp = match.group(0)

                index = match.span()[0]
                length = match.span()[1] - match.span()[0]

                # Match anchor based on cursor position
                if not (index <= idx <= index + length):
                    continue

                _rect = self.cursorRect(cursor)
                _center = _rect.center()
                _rect.setWidth(common.size(common.size_margin))
                _rect.moveCenter(_center)

                if not _rect.contains(pos):
                    continue

                if k == 'url':
                    url = QtCore.QUrl(grp)
                    QtGui.QDesktopServices.openUrl(url)
                    return
                if k == 'filepath':
                    fpath = QtCore.QFileInfo(grp).filePath()
                    actions.reveal(fpath)

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

    def showEvent(self, event):
        """Event handler.

        """
        # Move the cursor to the end of the document
        cursor = QtGui.QTextCursor(self.document())
        cursor.movePosition(QtGui.QTextCursor.End)
        self.setTextCursor(cursor)

        # Rehighlight the document to apply the formatting
        self.highlighter.rehighlight()


class RemoveNoteButton(ui.ClickableIconButton):
    """Button used to remove a note item.

    """

    def __init__(self, parent=None):
        super().__init__(
            'close',
            (common.color(common.color_red), common.color(common.color_red)),
            common.size(common.size_margin) * 1.2,
            description='Delete note',
            parent=parent
        )

    @QtCore.Slot()
    def action(self):
        """Remove note item action.

        """
        mbox = ui.MessageBox(
            'Remove note?',
            buttons=[ui.YesButton, ui.NoButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return

        parent_widget = self.parent().parent()
        parent_widget.deleteCard.emit(parent_widget)


class DragIndicatorButton(QtWidgets.QLabel):
    """Dotted button indicating a draggable item.

    The button is responsible for initiating a QDrag operation and setting the mime
    data. The data is populated with the `TodoEditor`'s text and the custom mime type.
    The latter is needed to accept the drag operation in the target drop widget.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.dragStartPosition = None

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        pixmap = images.ImageCache.rsc_pixmap(
            'drag_indicator', common.color(common.color_dark_background),
            common.size(common.size_margin) * 1.2
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

        parent_widget = self.parent().parent()
        parent_widget.clearFocus()
        parent_widget.title_editor.clearFocus()
        parent_widget.body_editor.clearFocus()

        # Setting Mime Data
        drag = QtGui.QDrag(parent_widget)
        mime_data = QtCore.QMimeData()
        mime_data.setData('application/todo-drag', QtCore.QByteArray(bytes()))
        drag.setMimeData(mime_data)

        # Drag pixmap
        pixmap = QtGui.QPixmap(parent_widget.size())
        parent_widget.render(pixmap)

        pos = self.mapTo(parent_widget, event.pos())
        drag.setPixmap(pixmap)
        drag.setHotSpot(pos)

        # Starting the drag...
        parent_widget.beginDrag.emit(parent_widget)
        drag.exec_(QtCore.Qt.CopyAction)
        parent_widget.endDrag.emit(parent_widget)


class OverlayWidget(QtWidgets.QWidget):
    """Widget responsible for indicating files are being loaded."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._drag = False

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setWindowFlags(QtCore.Qt.Widget)

    def paintEvent(self, event):
        if not self._drag:
            return

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.color_dark_background))
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        o = common.size(common.size_margin) * 0.2
        painter.drawRoundedRect(self.rect(), o, o)

    def begin_drag(self):
        self._drag = True

    def end_drag(self):
        self._drag = False


class DragOverlayWidget(OverlayWidget):
    """Widget responsible for indicating files are being loaded."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def paintEvent(self, event):
        widget = self.parent().widget()
        idx = self.parent().drag_item_properties['current_idx']
        _idx = self.parent().drag_item_properties['original_idx']
        if idx == -1 or idx == _idx:
            return

        card_widget = widget.layout().itemAt(idx).widget()

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.color_blue))
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        o = common.size(common.size_margin) * 0.2
        painter.setOpacity(0.5)
        painter.drawRoundedRect(card_widget.geometry(), o, o)


class CardWidget(QtWidgets.QWidget):
    """Card widget represents a single note item.

    It has a title and a main note editor. Use :meth:`set_data` to set,
    and :meth:`get_data` to retrieve the card contents.

    """
    deleteCard = QtCore.Signal(QtWidgets.QWidget)
    beginDrag = QtCore.Signal(QtWidgets.QWidget)
    endDrag = QtCore.Signal(QtWidgets.QWidget)
    resized = QtCore.Signal(QtCore.QRect)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.title_editor = None
        self.body_editor = None
        self.fold_button = None
        self.remove_button = None
        self.move_button = None
        self.overlay_widget = None

        self.installEventFilter(self)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)

        o = common.size(common.size_margin)
        _o = o / 2.0

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.title_editor = QtWidgets.QLineEdit(parent=self)
        self.title_editor.setStyleSheet(
            f'QLineEdit {{ background-color: transparent;'
            f'font-size: {int(common.size(common.size_font_large))}px;}}'
        )
        self.title_editor.setPlaceholderText('Edit title...')
        self.title_editor.setStatusTip('Edit title...')
        self.title_editor.setWhatsThis('Edit title...')
        self.title_editor.setToolTip('Edit title...')

        self.body_editor = TextEditor(parent=self)
        self.body_editor.setPlaceholderText('Edit note...')
        self.body_editor.setStatusTip('Edit note...')
        self.body_editor.setWhatsThis('Edit note...')
        self.body_editor.setToolTip('Edit note...')
        self.body_editor.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.title_editor.setStatusTip('Edit note')
        self.title_editor.setWhatsThis('Edit note')
        self.title_editor.setToolTip('Edit note')

        h = common.size(common.size_margin) * 1.3
        self.fold_button = ui.ClickableIconButton(
            'branch_open',
            (common.color(common.color_text),
             common.color(common.color_text)),
            h,
            description='Fold/Unfold the note',
            state=True,
            parent=self
        )

        widget = ui.get_group(parent=self, margin=o / 4.0)
        widget.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        _widget = QtWidgets.QWidget(parent=self)
        _widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        QtWidgets.QHBoxLayout(_widget)
        _widget.layout().setContentsMargins(0, 0, 0, 0)
        _widget.layout().setSpacing(0)
        _widget.layout().addWidget(self.fold_button, 0)
        _widget.layout().addWidget(self.title_editor, 0)

        widget.layout().addWidget(_widget)
        widget.layout().addWidget(self.body_editor, 1)
        self.layout().addWidget(widget, 1)

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(widget)
        widget.layout().setContentsMargins(_o, _o, _o, _o)
        widget.layout().setSpacing(_o)

        self.remove_button = RemoveNoteButton(parent=self)
        self.move_button = DragIndicatorButton(parent=self)

        widget.layout().addWidget(self.remove_button, 0)
        widget.layout().addWidget(self.move_button, 0)

        self.layout().addWidget(widget)

        self.overlay_widget = OverlayWidget(parent=self)

    def _connect_signals(self):
        self.beginDrag.connect(self.overlay_widget.begin_drag)
        self.endDrag.connect(self.overlay_widget.end_drag)
        self.resized.connect(self.overlay_widget.setGeometry)
        self.fold_button.clicked.connect(self.fold_card)

    @QtCore.Slot()
    def fold_card(self):
        self.body_editor.setHidden(not self.body_editor.isHidden())

        if self.body_editor.isHidden():
            self.fold_button.set_pixmap('branch_closed')
        else:
            self.fold_button.set_pixmap('branch_open')
    def eventFilter(self, widget, event):
        if widget != self:
            return False
        if event.type() != QtCore.QEvent.Resize:
            return False
        self.resized.emit(self.rect())
        return False

    def set_data(self, title, note):
        """Set the data for the note.

        Args:
            title (str): Title of the note.
            note (str): Note.

        """
        if title:
            self.title_editor.setText(title)
        if note:
            self.body_editor.setPlainText(note)

    def get_data(self):
        """Returns the title and note of the card.

        Returns:
            dict: Title and note of the card.

        """
        return {
            'title': self.title_editor.text(),
            'note': self.body_editor.toPlainText(),
        }


class CardsScrollWidget(QtWidgets.QScrollArea):
    """Widget used to store a list of :class:`CardWidget`s.

    The widget implements user sorting by custom drag and drop
    mechanisms.

    """
    cardAdded = QtCore.Signal(QtWidgets.QWidget)
    cardRemoved = QtCore.Signal(QtWidgets.QWidget)
    resized = QtCore.Signal(QtCore.QRect)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setWidgetResizable(True)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)

        self.overlay_widget = None

        self.drag_item_properties = {
            'original_height': -1,
            'original_max_height': -1,
            'original_idx': -1,
            'current_idx': -1,
        }

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        widget = QtWidgets.QWidget(parent=self)
        widget.setObjectName('card_container_widget')
        widget.setMouseTracking(True)

        QtWidgets.QVBoxLayout(widget)
        widget.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)

        o = common.size(common.size_margin) * 0.5
        widget.layout().setContentsMargins(o, o, o, o)
        widget.layout().setSpacing(common.size(common.size_indicator) * 2)

        self.setWidget(widget)

        self.overlay_widget = DragOverlayWidget(parent=self)

    def _connect_signals(self):
        self.resized.connect(self.overlay_widget.setGeometry)

    def add_card(self, title, note, fold):
        """Add a new :class:`CardWidget` to the list.

        Args:
            title (str): Title of the note.
            note (str): Note.

        """
        widget = CardWidget(parent=self)
        widget.set_data(title, note)
        widget.beginDrag.connect(self.begin_drag)
        widget.endDrag.connect(self.end_drag)
        widget.deleteCard.connect(self.delete_card)
        if fold:
            widget.fold_card()

        self.widget().layout().insertWidget(0, widget)

        # widget.title_editor.setFocus()

    def _reset_drag_item_properties(self):
        self.drag_item_properties = {
            'original_height': -1,
            'original_max_height': -1,
            'original_idx': -1,
            'current_idx': -1,
        }

    @QtCore.Slot(QtWidgets.QWidget)
    def delete_card(self, widget):
        # Find the index of the widget we want to move
        animation = QtCore.QPropertyAnimation(widget, b'maximumHeight', parent=widget)
        animation.setEasingCurve(QtCore.QEasingCurve.OutQuart)
        animation.setDuration(300)
        animation.setStartValue(widget.rect().height())
        animation.setEndValue(0)

        def _remove(widget):
            idx = self.widget().layout().indexOf(widget)
            w = self.widget().layout().takeAt(idx).widget()
            w.deleteLater()

        animation.finished.connect(lambda: _remove(widget))
        animation.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    @QtCore.Slot(QtWidgets.QWidget)
    def begin_drag(self, widget):
        self.drag_item_properties['original_height'] = widget.rect().height()
        self.drag_item_properties['original_max_height'] = widget.maximumHeight()
        self.drag_item_properties['original_idx'] = self.widget().layout().indexOf(widget)

    @QtCore.Slot(QtWidgets.QWidget)
    def end_drag(self, widget):
        idx = self.drag_item_properties['current_idx']
        _idx = self.drag_item_properties['original_idx']

        widget = self.widget().layout().takeAt(_idx).widget()
        self.widget().layout().insertWidget(idx, widget)

        self._reset_drag_item_properties()
        self.overlay_widget.update()
    def eventFilter(self, widget, event):
        """Custom event filter.

        """
        if widget.objectName() != 'qt_scrollarea_viewport':
            return False
        if event.type() == QtCore.QEvent.Resize:
            self.resized.emit(self.rect())
        if event.type() != QtCore.QEvent.DragMove:
            return False

        container = next(
            f for f in widget.children() if f.objectName() == 'card_container_widget')
        child_at = container.childAt(event.pos())
        if not child_at:
            return False

        children = [
            container.layout().itemAt(idx).widget() for idx in
            range(container.layout().count())
        ]
        if not children:
            return False
        child = next(
            f for f in children if child_at in f.findChildren(type(child_at), None))
        if not child:
            return False

        idx = container.layout().indexOf(child)
        self.drag_item_properties['current_idx'] = idx
        self.overlay_widget.update()
        return False

    def dragEnterEvent(self, event):
        """Event handler.

        """
        if not event.mimeData().hasFormat('application/todo-drag'):
            event.ignore()
            return
        event.accept()


class CardsWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_button = None
        self.refresh_button = None
        self.save_button = None

        self.container_widget = None

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        common.set_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QHBoxLayout(widget)
        self.layout().addWidget(widget, 0)

        h = common.size(common.size_margin) * 1.3
        self.add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.color_green),
             common.color(common.color_selected_text)),
            h,
            description='Click to add a new note',
            state=True,
            parent=self
        )
        self.refresh_button = ui.PaintedButton('Refresh', parent=self)
        self.close_button = ui.PaintedButton('Close', parent=self)

        widget.layout().addWidget(self.add_button, 0)
        widget.layout().addStretch(1)
        widget.layout().addWidget(self.refresh_button, 0)
        widget.layout().addWidget(self.close_button, 0)

        self.container_widget = CardsScrollWidget(parent=self)
        self.layout().addWidget(self.container_widget, 1)

    def _connect_signals(self):
        self.add_button.clicked.connect(self.add_new_note)

    @QtCore.Slot()
    def add_new_note(self):
        self.container_widget.add_card('', '', False)

# class NoteEditor(QtWidgets.QDialog):
#     """Main widget used to view and edit and add Notes and Tasks."""
#
#     def __init__(self, index, parent=None):
#         super().__init__(parent=parent)
#         self.note_container_widget = None
#         self._index = index
#
#         self.read_only = False
#
#         self.lock = Lockfile(self.index, parent=self)
#         self.destroyed.connect(self.unlock)
#
#         self.lockstamp = int(round(time.time() * 1000))
#         self.save_timer = common.Timer(parent=self)
#         self.save_timer.setInterval(1000)
#         self.save_timer.setSingleShot(False)
#         self.save_timer.timeout.connect(self.save_settings)
#
#         self.refresh_timer = common.Timer(parent=self)
#         self.refresh_timer.setInterval(10000)  # refresh every 30 seconds
#         self.refresh_timer.setSingleShot(False)
#         self.refresh_timer.timeout.connect(self.refresh)
#
#         self.setWindowTitle('Notes & Tasks')
#         self.setWindowFlags(QtCore.Qt.Widget)
#         self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
#
#         self._create_ui()
#         self.installEventFilter(self)
#
#         self.init_lock()
#
#     def _create_ui(self):
#         """Creates the ui layout."""
#         QtWidgets.QVBoxLayout(self)
#         o = common.size(common.size_margin)
#         self.layout().setSpacing(common.size(common.size_indicator))
#         self.layout().setContentsMargins(o, o, o, o)
#
#         # Top row
#         height = common.size(common.size_row_height) * 0.6666
#         row = ui.add_row(None, height=height, parent=self)
#         row.layout().addSpacing(height * 0.33)
#
#         # Thumbnail
#         self.add_button = ui.ClickableIconButton(
#             'add',
#             (common.color(common.color_green), common.color(common.color_green)),
#             height,
#             description='Click to add a new Todo item...',
#             parent=self
#         )
#         self.add_button.clicked.connect(lambda: self.add_item(idx=0))
#
#         # Name label
#         text = 'Notes'
#         label = ui.PaintedLabel(
#             text, color=common.color(common.color_dark_background),
#             size=common.size(common.size_font_large), parent=self
#         )
#         label.setFixedHeight(height)
#
#         self.refresh_button = ui.ClickableIconButton(
#             'refresh',
#             (QtGui.QColor(0, 0, 0, 255), QtGui.QColor(0, 0, 0, 255)),
#             height,
#             description='Refresh...',
#             parent=self
#         )
#         self.refresh_button.clicked.connect(self.refresh)
#
#         self.remove_button = ui.ClickableIconButton(
#             'close',
#             (QtGui.QColor(0, 0, 0, 255), QtGui.QColor(0, 0, 0, 255)),
#             height,
#             description='Refresh...',
#             parent=self
#         )
#         self.remove_button.clicked.connect(self.close)
#
#         row.layout().addWidget(label)
#         row.layout().addStretch(1)
#         row.layout().addWidget(self.refresh_button, 0)
#         row.layout().addWidget(self.remove_button, 0)
#
#         row = ui.add_row(None, height=height, parent=self)
#
#         text = 'Add Note'
#         self.add_label = ui.PaintedLabel(
#             text, color=common.color(common.color_dark_background),
#             parent=row
#         )
#
#         row.layout().addWidget(self.add_button, 0)
#         row.layout().addWidget(self.add_label, 0)
#         row.layout().addStretch(1)
#
#         self.note_container_widget = NoteContainerWidget(parent=self)
#         self.setMinimumHeight(common.size(common.size_row_height) * 3.0)
#
#         self.scroll_area = QtWidgets.QScrollArea(parent=self)
#         self.scroll_area.setWidgetResizable(True)
#         self.scroll_area.setWidget(self.note_container_widget)
#
#         self.scroll_area.setAttribute(QtCore.Qt.WA_NoSystemBackground)
#         self.scroll_area.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#
#         self.layout().addWidget(self.scroll_area)
#
#     def clear(self):
#         """Deletes all note item editors.
#
#         """
#         for idx in reversed(range(len(list(self.note_container_widget.items)))):
#             row = self.note_container_widget.items.pop(idx)
#             for c in row.children():
#                 c.deleteLater()
#             self.note_container_widget.layout().removeWidget(row)
#             row.deleteLater()
#             del row
#
#     @common.error
#     @common.debug
#     def refresh(self):
#         """Populates the list from the database.
#
#         """
#         if not self.parent():
#             return
#         if not self.index.isValid():
#             return
#         if not self.index.data(common.FileInfoLoaded):
#             return
#
#         if self.index.data(common.TypeRole) == common.FileItem:
#             source = self.index.data(common.PathRole)
#         elif self.index.data(common.TypeRole) == common.SequenceItem:
#             source = common.proxy_path(self.index)
#
#         db = database.get_db(*self.index.data(common.ParentPathRole)[0:3])
#         v = db.value(source, 'notes', database.AssetTable)
#         if not v:
#             return
#
#         self.clear()
#
#         keys = sorted(v.keys())
#         for k in keys:
#             self.add_item(
#                 text=v[k]['text']
#             )
#
#     @property
#     def index(self):
#         """The path used to initialize the widget.
#
#         """
#         return self._index
#
#     def eventFilter(self, widget, event):
#         """Event filter handler.
#
#         """
#         if event.type() == QtCore.QEvent.Paint:
#             painter = QtGui.QPainter()
#             painter.begin(self)
#             font = common.font_db.medium_font(
#                 common.size(common.size_font_medium)
#             )[0]
#             painter.setFont(font)
#             painter.setRenderHints(QtGui.QPainter.Antialiasing)
#
#             o = common.size(common.size_indicator)
#             rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
#             painter.setBrush(QtGui.QColor(250, 250, 250, 255))
#             painter.setPen(QtCore.Qt.NoPen)
#             painter.drawRoundedRect(rect, o * 2, o * 2)
#
#             center = rect.center()
#             rect.setWidth(rect.width() - common.size(common.size_margin))
#             rect.setHeight(rect.height() - common.size(common.size_margin))
#             rect.moveCenter(center)
#
#             text = 'Click the plus icon on the top to add a note'
#             text = text if not len(self.note_container_widget.items) else ''
#             common.draw_aliased_text(
#                 painter, font, rect, text, QtCore.Qt.AlignCenter,
#                 common.color(common.color_dark_background)
#             )
#             painter.end()
#         return False
#
#     def _get_next_enabled(self, n):
#         hasEnabled = False
#         for i in range(len(self.note_container_widget.items)):
#             item = self.note_container_widget.items[i]
#             editor = item.findChild(NoteTextEditor)
#             if editor.isEnabled():
#                 hasEnabled = True
#                 break
#
#         if not hasEnabled:
#             return -1
#
#         # Finding the next enabled editor
#         for _ in range(len(self.note_container_widget.items) - n):
#             n += 1
#             if n >= len(self.note_container_widget.items):
#                 return self._get_next_enabled(-1)
#             item = self.note_container_widget.items[n]
#             editor = item.findChild(NoteTextEditor)
#             if editor.isEnabled():
#                 return n
#
#     def key_tab(self):
#         """Custom key action.
#
#         """
#         if not self.note_container_widget.items:
#             return
#
#         n = 0
#         for n, item in enumerate(self.note_container_widget.items):
#             editor = item.findChild(NoteTextEditor)
#             if editor.hasFocus():
#                 break
#
#         n = self._get_next_enabled(n)
#         if n > -1:
#             item = self.note_container_widget.items[n]
#             editor = item.findChild(NoteTextEditor)
#             editor.setFocus()
#             self.scroll_area.ensureWidgetVisible(
#                 editor, ymargin=editor.height()
#             )
#
#     def key_return(self, ):
#         """Custom key action.
#
#         """
#         for item in self.note_container_widget.items:
#             editor = item.findChild(NoteTextEditor)
#
#             if not editor.hasFocus():
#                 continue
#
#             if editor.document().toPlainText():
#                 continue
#
#             idx = self.note_container_widget.items.index(editor.parent())
#             row = self.note_container_widget.items.pop(idx)
#             self.todoedfitors_widget.layout().removeWidget(row)
#             row.deleteLater()
#
#             break
#
#     def keyPressEvent(self, event):
#         """Key press event handler.
#
#         """
#         control_modifier = event.modifiers() == QtCore.Qt.ControlModifier
#         shift_modifier = event.modifiers() == QtCore.Qt.ShiftModifier
#
#         if event.key() == QtCore.Qt.Key_Escape:
#             self.close()
#
#         if shift_modifier:
#             if event.key() == QtCore.Qt.Key_Tab:
#                 return True
#             if event.key() == QtCore.Qt.Key_Backtab:
#                 return True
#
#         if control_modifier:
#             if event.key() == QtCore.Qt.Key_S:
#                 self.save_settings()
#                 return True
#             elif event.key() == QtCore.Qt.Key_N:
#                 self.add_button.clicked.emit()
#                 return True
#             elif event.key() == QtCore.Qt.Key_Tab:
#                 self.key_tab()
#                 return True
#             elif event.key() == QtCore.Qt.Key_Return:
#                 self.key_return()
#
#     def add_item(self, idx=None, text=None):
#         """Creates a new :class:`NoteItemWidget`editor and adds it to
#         :meth:`NoteContainerWidget.items`.
#
#         Args:
#             idx (int): The index of the item to be added. Optional.
#             text (str): The text of the item to be added. Optional.
#
#         """
#         item = NoteItemWidget(parent=self)
#
#         editor = NoteTextEditor(
#             text,
#             read_only=self.read_only,
#             parent=item
#         )
#         editor.setFocusPolicy(QtCore.Qt.StrongFocus)
#         item.layout().addWidget(editor, 1)
#
#         drag = DragIndicatorButton(parent=item)
#         drag.setFocusPolicy(QtCore.Qt.NoFocus)
#
#         item.layout().addWidget(drag)
#         if self.read_only:
#             drag.setDisabled(True)
#
#         if not self.read_only:
#             remove = RemoveNoteButton(parent=item)
#             remove.setFocusPolicy(QtCore.Qt.NoFocus)
#             item.layout().addWidget(remove)
#
#         if idx is None:
#             self.note_container_widget.layout().addWidget(item, 0)
#             self.note_container_widget.items.append(item)
#         else:
#             self.note_container_widget.layout().insertWidget(idx, item, 0)
#             self.note_container_widget.items.insert(idx, item)
#
#         editor.setFocus()
#         item.editor = editor
#         return item
#
#     @QtCore.Slot()
#     def save_settings(self):
#         """Saves the current list of note items to the assets configuration file."""
#         if not self.index.isValid():
#             return
#
#         data = {}
#         for n in range(len(self.note_container_widget.items)):
#             item = self.note_container_widget.items[n]
#             editor = item.findChild(NoteTextEditor)
#             if not editor.document().toPlainText():
#                 continue
#             data[n] = {
#                 'text': editor.document().toHtml(),
#             }
#
#         if self.index.data(common.TypeRole) == common.FileItem:
#             source = self.index.data(common.PathRole)
#         elif self.index.data(common.TypeRole) == common.SequenceItem:
#             source = common.proxy_path(self.index)
#
#         db = database.get_db(*self.index.data(common.ParentPathRole)[0:3])
#         db.setValue(source, 'notes', data)
#
#     def init_lock(self):
#         """Creates a lock file.
#
#         This will prevent other sessions editing notes.
#
#         """
#         if not self.parent():
#             return
#         if not self.index.isValid():
#             return
#
#         v = self.lock.value('open')
#         v = False if v is None else v
#         v = v if isinstance(v, bool) else (
#             False if v.lower() == 'false' else True)
#         is_open = v
#
#         stamp = self.lock.value('stamp')
#         if stamp is not None:
#             stamp = int(stamp)
#
#         if not is_open:
#             self.read_only = False
#             self.add_button.show()
#             self.add_label.show()
#             self.refresh_button.hide()
#             self.save_timer.start()
#             self.refresh_timer.stop()
#
#             self.lock.setValue('open', True)
#             self.lock.setValue('stamp', self.lockstamp)
#             return
#
#         if stamp == self.lockstamp:
#             self.read_only = False
#             self.add_label.show()
#             self.add_button.show()
#             self.refresh_button.hide()
#             self.save_timer.start()
#             self.refresh_timer.stop()
#
#             self.lock.setValue('stamp', self.lockstamp)
#             return
#
#         if stamp != self.lockstamp:
#             self.read_only = True
#             self.add_button.hide()
#             self.add_label.hide()
#             self.refresh_button.show()
#             self.save_timer.stop()
#             self.refresh_timer.start()
#

#
#     def showEvent(self, event):
#         """Event handler.
#
#         """
#         if self.parent():
#             geo = self.parent().viewport().rect()
#             self.resize(geo.width(), geo.height())
#         self.setFocus(QtCore.Qt.OtherFocusReason)
#         self.refresh()
#
#     def hideEvent(self, event):
#         """Hide event handler.
#
#         """
#         if not self.read_only:
#             self.save_settings()
#         self.unlock()
#
#     def sizeHint(self):
#         """Returns a size hint.
#
#         """
#         return QtCore.QSize(
#             common.size(common.size_width),
#             common.size(common.size_height)
#         )
