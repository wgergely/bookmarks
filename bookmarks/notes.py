"""Module contains the widgets used to add and edit item cards/notes.

"""
import functools
import os
import re
import time

from PySide2 import QtWidgets, QtGui, QtCore

from . import actions
from . import common
from . import database
from . import images
from . import log
from . import ui


def close():
    """Closes the :class:`CardsWidget` editor.

    """
    if common.notes_widget is None:
        return
    try:
        common.notes_widget.close()
        common.notes_widget.deleteLater()
    except:
        pass
    common.notes_widget = None


def show(index):
    """Shows the :class:`CardsWidget` editor.

    Args:
        index (QModelIndex): The item's
    """
    close()
    if common.notes_widget is None:
        common.notes_widget = CardsWidget(index, parent=common.widget())

    common.widget().resized.connect(common.notes_widget.setGeometry)
    common.notes_widget.setGeometry(common.widget().geometry())
    # common.notes_widget.setFocus()
    common.notes_widget.open()

    return common.notes_widget


class Lockfile(QtCore.QSettings):
    """Lockfile to prevent another user from modifying the database whilst
    an edit is in progress.

    """

    def __init__(self, index, parent=None):
        self.index = index
        self._is_locked = False

        if index.isValid():
            p = '/'.join(index.data(common.ParentPathRole)[0:3])
            f = QtCore.QFileInfo(index.data(common.PathRole))
            self.config_path = f'{p}/{common.bookmark_cache_dir}/locks/{f.baseName()}.lock'
            _dir = QtCore.QFileInfo(self.config_path).dir()
            if not _dir.exists():
                _dir.mkpath('.')
        else:
            self.config_path = '/'

        super().__init__(
            self.config_path,
            QtCore.QSettings.IniFormat,
            parent=parent
        )

        self.init_lock()

    def init_lock(self):
        """Creates a lock file.

        This will prevent others from editing the notes of this time whilst we have the
        editor open.

        """
        if not self.index.isValid():
            return

        file_info = QtCore.QFileInfo(self.config_path)
        if not file_info.exists():
            self.setValue('pid', os.getpid())
            self.sync()
            return

    @QtCore.Slot()
    def unlock(self, force=False):
        if self.is_locked() and not force:
            return

        self.deleteLater()
        if not QtCore.QFile(self.config_path).remove():
            log.error('Could not remove the lock file.')

    def is_locked(self):
        file_info = QtCore.QFileInfo(self.config_path)
        return file_info.exists() and self.value('pid') != os.getpid()


class SyntaxHighlighter(QtGui.QSyntaxHighlighter):
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
                re.IGNORECASE
            ),
            'flag': 0b100000,
        },
        'filepath': {
            'regex': re.compile(
                r'^(?:\s|^)((?:[A-Za-z]\:|(?:\/|\\))(?:[\/\\][^\/\\:*?"<>|\r\n]+)*[\/\\][^\/\\:*?"<>|\r\n]+|(?:['
                r'A-Za-z]\:|(?:\/|\\))(?:[\/\\][^\/\\:*?"<>|\r\n]+)*(?:[^\/\\:*?"<>|\r\n]+\.?)+)(?=\s|$)$',
                re.IGNORECASE | re.MULTILINE
            ),
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

        self.highlighter = SyntaxHighlighter(self.document())

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
                        QtCore.Qt.PointingHandCursor
                    )
                    return
                if k == 'filepath':
                    QtWidgets.QApplication.instance().setOverrideCursor(
                        QtCore.Qt.PointingHandCursor
                    )
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
        if common.show_message(
                'Delete note',
                body='Are you sure you want to remove this note? This action cannot be undone.',
                buttons=[common.YesButton, common.NoButton],
                message_type='error',
                modal=True,
        ) == QtWidgets.QDialog.Rejected:
            return

        parent_widget = self.parent().parent()
        parent_widget.deleteCard.emit(parent_widget)


class DragIndicatorButton(QtWidgets.QLabel):
    """Dotted button indicating a draggable item.
|
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
        pixmap = images.rsc_pixmap(
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

    It has a title and a main note editor. Use :meth:`set_card_data` to set,
    and :meth:`get_card_data` to retrieve the card contents.

    """
    deleteCard = QtCore.Signal(QtWidgets.QWidget)
    beginDrag = QtCore.Signal(QtWidgets.QWidget)
    endDrag = QtCore.Signal(QtWidgets.QWidget)
    resized = QtCore.Signal(QtCore.QRect)

    def __init__(self, extra_data, read_only=False, parent=None):
        super().__init__(parent=parent)
        self.extra_data = extra_data
        self.read_only = read_only

        self.title_editor = None
        self.body_editor = None
        self.fold_button = None
        self.remove_button = None
        self.move_button = None
        self.overlay_widget = None

        self.installEventFilter(self)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum,
        )

        self._create_ui()
        self._connect_signals()

        if 'fold' in extra_data and extra_data['fold']:
            self.fold_card()

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
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
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
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum,
        )

        info = f'<span style="font-size:{int(common.size_font_small)}px;">'
        if 'created_by' in self.extra_data:
            info += f'Added by <span style="color:{common.rgb(common.color_green)};">' \
                    f'{self.extra_data["created_by"]}</span>'
        if 'created_at' in self.extra_data:
            info += f' at <span style="color:{common.rgb(common.color_green)};">' \
                    f'{self.extra_data["created_at"]}</span>'
        info += '</span>'
        label = QtWidgets.QLabel(info, parent=self)

        _widget = QtWidgets.QWidget(parent=self)
        _widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        QtWidgets.QHBoxLayout(_widget)
        _widget.layout().setContentsMargins(0, 0, 0, 0)
        _widget.layout().setSpacing(0)
        _widget.layout().addWidget(self.fold_button, 0)
        _widget.layout().addWidget(self.title_editor, 1)
        _widget.layout().addWidget(label, 0)

        _widget.layout().addWidget(self.body_editor, 1)

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

        if self.read_only:
            self.body_editor.setReadOnly(True)
            self.body_editor.setFocusPolicy(QtCore.Qt.NoFocus)
            self.title_editor.setReadOnly(True)
            self.title_editor.setFocusPolicy(QtCore.Qt.NoFocus)
            self.remove_button.setDisabled(True)
            self.move_button.setDisabled(True)

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
            self.setSizePolicy(
                QtWidgets.QSizePolicy.MinimumExpanding,
                QtWidgets.QSizePolicy.Maximum,
            )
        else:
            self.fold_button.set_pixmap('branch_open')
            self.setSizePolicy(
                QtWidgets.QSizePolicy.MinimumExpanding,
                QtWidgets.QSizePolicy.Minimum,
            )

    def eventFilter(self, widget, event):
        if widget != self:
            return False
        if event.type() != QtCore.QEvent.Resize:
            return False
        self.resized.emit(self.rect())
        return False

    def set_card_data(self, title='', body='', extra_data={}):
        """Sets the note contents and extra data.

        Args:
            title (str): The note's title.
            body (str): The note's content.
            extra_data (dict): Extra data about the note.

        """
        if title:
            self.title_editor.setText(title)
        if body:
            self.body_editor.setPlainText(body)
        if extra_data:
            self.extra_data.update(extra_data)

    def get_card_data(self):
        """Returns the title and note of the card.

        Returns:
            dict: Title, body and extra data of the card.

        """
        data = {
            'title': self.title_editor.text(),
            'body': self.body_editor.toPlainText(),
            'extra_data': self.extra_data
        }
        data['extra_data']['fold'] = self.body_editor.isHidden()
        return data


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

    def add_card(self, title, body, extra_data={}, read_only=False):
        """Add a new :class:`CardWidget` to the list.

        Args:
            title (str): Title of the note.
            body (str): Note.

        """
        widget = CardWidget(extra_data, read_only=read_only, parent=self)
        widget.set_card_data(title=title, body=body, extra_data=extra_data)
        widget.beginDrag.connect(self.begin_drag)
        widget.endDrag.connect(self.end_drag)
        widget.deleteCard.connect(self.delete_card)

        self.widget().layout().insertWidget(0, widget)
        return widget

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
            f for f in widget.children() if f.objectName() == 'card_container_widget'
        )
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
            f for f in children if child_at in f.findChildren(type(child_at), None)
        )
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


class CardsWidget(QtWidgets.QDialog):
    """This is the main cards/notes widget.

    """

    def __init__(self, index, parent=None):
        super().__init__(parent=parent)
        self._index = index

        self.add_button = None
        self.save_button = None
        self.cards_widget = None

        self.setWindowTitle('Notes')
        self.setWindowFlags(QtCore.Qt.Widget)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.lock = Lockfile(index)
        self.autosave_timer = common.Timer(parent=self)
        self.autosave_timer.setInterval(5000)
        self.autosave_timer.timeout.connect(self.save)

        self._create_ui()
        self._connect_signals()

        QtCore.QTimer.singleShot(100, self.init_data)
        QtCore.QTimer.singleShot(1000, self.autosave_timer.start)

    def _create_ui(self):
        common.set_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QHBoxLayout(widget)
        self.layout().addWidget(widget, 0)

        h = common.size(common.size_margin) * 1.4
        self.add_button = ui.ClickableIconButton(
            'add',
            (common.color(common.color_green),
             common.color(common.color_selected_text)),
            h,
            description='Click to add a new note',
            state=True,
            parent=self
        )
        self.save_button = ui.PaintedButton('Save', parent=self)
        self.close_button = ui.PaintedButton('Close', parent=self)

        pixmap, color = images.get_thumbnail(
            self.index.data(common.ParentPathRole)[0],
            self.index.data(common.ParentPathRole)[1],
            self.index.data(common.ParentPathRole)[2],
            self.index.data(common.PathRole),
            size=common.size(common.size_row_height)
        )
        if not pixmap.isNull():
            label = QtWidgets.QLabel(parent=self)
            label.setPixmap(pixmap)
        widget.layout().addWidget(label, 0)

        info = ''
        info = f'<span style="font-size:{int(common.size_font_large)}px;">'
        info += f'{self.index.data(QtCore.Qt.DisplayRole)}'
        info += f'<span style="color:{common.rgb(common.color_secondary_text)};">'
        info += ' notes'
        if self.lock.is_locked():
            info += ' (read-only)'

        info += '</span></span>'
        label = QtWidgets.QLabel(info, parent=self)
        widget.layout().addWidget(label, 0)

        widget.layout().addStretch(1)
        widget.layout().addWidget(self.add_button, 0)
        widget.layout().addWidget(self.save_button, 0)
        widget.layout().addWidget(self.close_button, 0)

        # Separator pixmap
        pixmap = images.rsc_pixmap(
            'gradient2', None, common.size(common.size_row_height), opacity=0.5
        )
        separator = QtWidgets.QLabel(parent=self)
        separator.setScaledContents(True)
        separator.setFixedHeight(common.size(common.size_row_height))
        separator.setPixmap(pixmap)
        self.layout().addWidget(separator, 1)

        self.cards_widget = CardsScrollWidget(parent=self)
        self.layout().addWidget(self.cards_widget, 1)

        if self.lock.is_locked():
            self.add_button.setHidden(True)
            self.save_button.setHidden(True)

    def _connect_signals(self):
        self.add_button.clicked.connect(self.add_new_note)
        self.close_button.clicked.connect(lambda: self.done(QtWidgets.QDialog.Accepted))
        self.save_button.clicked.connect(self.save)
        self.destroyed.connect(self.autosave_timer.stop)

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width),
            common.size(common.size_height)
        )

    @property
    def index(self):
        """The QModelIndex of the current item.

        """
        return self._index

    @QtCore.Slot()
    def add_new_note(self, title='', body='', extra_data={}):
        extra_data.update(
            {
                'created_by': common.get_username(),
                'created_at': time.strftime('%d/%m/%Y %H:%M'),
                'fold': False
            }
        )
        widget = self.cards_widget.add_card(
            title,
            body,
            extra_data=extra_data,
            read_only=self.lock.is_locked()
        )
        widget.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Minimum,
        )

    def add_card(self, *args, **kwargs):
        return self.cards_widget.add_card(*args, **kwargs)

    def get_cards_data(self):
        """Get all cards data.

        Returns:
            dict: A dictionary of each card item's data.

        """
        data = {}
        container = self.cards_widget.widget()
        for idx in range(container.layout().count()):
            widget = container.layout().itemAt(idx).widget()
            data[idx] = widget.get_card_data()
        return data

    @common.error
    @common.debug
    @QtCore.Slot()
    def init_data(self):
        """Load cards data stored in the database.

        """
        if not self.index.isValid():
            return False
        if not self.index.data(common.FileInfoLoaded):
            return False

        if self.index.data(common.DataTypeRole) == common.FileItem:
            source = self.index.data(common.PathRole)
        elif self.index.data(common.DataTypeRole) == common.SequenceItem:
            source = common.proxy_path(self.index)

        db = database.get(*self.index.data(common.ParentPathRole)[0:3])
        v = db.value(source, 'notes', database.AssetTable)
        if not v:
            return False

        for idx in sorted(v.keys(), reverse=True):
            # Let's do some data sanity checks and ignore invalid items
            if not isinstance(v[idx], dict):
                continue
            if set(v[idx].keys()) != set(['title', 'body', 'extra_data']):
                continue

            self.add_card(
                title=v[idx]['title'],
                body=v[idx]['body'],
                extra_data=v[idx]['extra_data'],
                read_only=self.lock.is_locked()
            )
        return True

    @QtCore.Slot()
    def done(self, r):
        """Close the window.

        """
        if r == QtWidgets.QDialog.Accepted:
            self.save()
            self.lock.unlock()
        return super().done(r)

    @QtCore.Slot()
    def save(self):
        """Save the note items to the database.

        """
        if not self.index.isValid():
            return
        if self.lock.is_locked():
            return

        if self.index.data(common.DataTypeRole) == common.FileItem:
            source = self.index.data(common.PathRole)
        elif self.index.data(common.DataTypeRole) == common.SequenceItem:
            source = common.proxy_path(self.index)

        db = database.get(*self.index.data(common.ParentPathRole)[0:3])
        db.set_value(source, 'notes', self.get_cards_data(), database.AssetTable)
