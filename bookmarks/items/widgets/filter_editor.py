"""The widget used set the text search filter of
:class:`~bookmarks.items.models.FilterProxyModel`.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from ... import common
from ... import ui


class TextFilterEditor(QtWidgets.QWidget):
    """Editor widget used to set a list model's persistent text filter.

    """
    finished = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.editor = None
        self.ok_button = None
        self.context_menu_open = False

        self.installEventFilter(self)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(QtCore.Qt.Widget)

        # Shadow effect
        self.effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.effect.setBlurRadius(common.size(common.size_margin))
        self.effect.setXOffset(0)
        self.effect.setYOffset(0)
        self.effect.setColor(QtGui.QColor(0, 0, 0, 255))
        self.setGraphicsEffect(self.effect)

        self._opacity = 0.0
        self.animation = QtCore.QPropertyAnimation(self, b'_opacity')
        self.animation.setDuration(300)  # 500 ms duration for fade in/out
        self.animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.animation.valueChanged.connect(self.set_opacity)

        self.setFocusProxy(self.editor)

        self._create_ui()
        self._connect_signals()

    def set_opacity(self, value):
        self._opacity = value
        self.setWindowOpacity(value)
        self.repaint()
        QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyRelease:
            if event.key() in [QtCore.Qt.Key_Escape, ]:
                self.close()
                return True
            if event.key() in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
                self.finished.emit(self.editor.text())
                self.close()
                return True
        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            rect = self._get_rect()
            if not rect.contains(event.pos()):
                self.close()
                return True
        return super().eventFilter(source, event)

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.size(common.size_margin) * 2
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        row = ui.add_row(
            None,
            parent=self,
            height=common.size(common.size_row_height)
        )

        self.history_button = ui.ClickableIconButton(
            'filter',
            (common.color(common.color_secondary_text),
             common.color(common.color_secondary_text)),
            common.size(common.size_margin)
        )
        self.history_button.setFocusPolicy(QtCore.Qt.NoFocus)
        row.layout().addWidget(self.history_button, 0)

        self.editor = ui.LineEdit(parent=self)
        self.editor.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.editor.setPlaceholderText('Enter filter, e.g. "maya" or --"SH010"')
        row.layout().addWidget(self.editor, 1)

        self.ok_button = ui.PaintedButton('Save', parent=self)
        row.layout().addWidget(self.ok_button, 0)

        self.layout().addStretch(1)

    def _connect_signals(self):
        self.editor.returnPressed.connect(lambda: self.finished.emit(self.editor.text()))
        self.ok_button.clicked.connect(lambda: self.finished.emit(self.editor.text()))
        self.finished.connect(self.close)

        common.signals.jobAdded.connect(self.close)
        common.signals.assetAdded.connect(self.close)
        common.signals.fileAdded.connect(self.close)
        common.signals.bookmarksChanged.connect(self.close)
        common.signals.tabChanged.connect(self.close)
        common.signals.switchViewToggled.connect(self.close)
        common.signals.taskFolderChanged.connect(self.close)
        common.signals.bookmarkActivated.connect(self.close)
        common.signals.assetActivated.connect(self.close)
        common.signals.fileActivated.connect(self.close)

    def set_completer(self):
        """Sets the editor's completer.

        """
        model = common.source_model()

        v = model.get_filter_setting('filters/text_history')
        v = v.split(';') if v else []
        v.reverse()
        v = [f for f in v if f]

        completer = QtWidgets.QCompleter(v, parent=self.editor)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_stylesheet(completer.popup())

        self.editor.setCompleter(completer)

        self.history_button.clicked.connect(self.show_history)

    def show_history(self):
        """Shows the editor's completer.

        """
        self.editor.completer().setCompletionPrefix('')
        self.editor.completer().complete()

    def init_text(self):
        """Sets the current filter text to the editor.

        """
        proxy = common.model()
        text = proxy.filter_text()
        text = text.lower() if text else ''
        text = '' if text == '/' else text
        self.editor.setText(text)

    def _get_rect(self):
        o = common.size(common.size_margin)
        r = common.size(common.size_row_height)

        rect = self.rect().adjusted(o, o, -o, -o)
        rect.setHeight(r + (o * 2))
        return rect

    def paintEvent(self, event):
        """Event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)

        rect = common.widget().rect()
        painter.setBrush(QtGui.QColor(0, 0, 0, 150))
        painter.setPen(QtCore.Qt.NoPen)
        painter.setOpacity(self._opacity * 0.3)
        painter.drawRect(rect)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        pen = QtGui.QPen(common.color(common.color_separator))
        pen.setWidthF(common.size(common.size_separator))
        painter.setPen(pen)

        i = common.size(common.size_indicator)
        rect = self._get_rect()
        painter.setBrush(common.color(common.color_dark_background))
        painter.setOpacity(self._opacity)
        painter.drawRoundedRect(rect, i, i)

        painter.end()

    def showEvent(self, event):
        """Event handler."""
        global_position = common.widget().mapToGlobal(QtCore.QPoint(0, 0))
        local_position = self.parent().mapFromGlobal(global_position)
        self.setGeometry(QtCore.QRect(local_position, common.widget().size()))

        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

        self.init_text()
        self.set_completer()
        self.editor.selectAll()

        # Set focus to the editor when shown
        self.editor.setFocus()
