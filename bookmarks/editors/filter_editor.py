# -*- coding: utf-8 -*-
"""Contains the definition for the widget used set and edit list model filters.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from .. import common
from .. import ui


class FilterEditor(QtWidgets.QDialog):
    """Editor widget used to set a persistent text filter for list models.

    """
    finished = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(FilterEditor, self).__init__(parent=parent)

        self.editor = None
        self.context_menu_open = False

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.setWindowFlags(QtCore.Qt.Widget)
        self._create_ui()
        self._connect_signals()

        self.setFocusProxy(self.editor)

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN() * 2
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        row = ui.add_row(
            None, parent=self, padding=0, height=common.ROW_HEIGHT())
        icon = ui.ClickableIconButton(
            u'filter',
            (common.RED, common.RED),
            common.ROW_HEIGHT()
        )

        label = u'Search'
        label = ui.PaintedLabel(label, parent=self)
        row.layout().addWidget(icon, 0)
        row.layout().addWidget(label, 0)

        self.editor = ui.LineEdit(parent=self)
        self.editor.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        row.layout().addWidget(self.editor, 1)
        self.layout().addStretch(1)

    def _connect_signals(self):
        self.editor.returnPressed.connect(self.action)
        self.finished.connect(
            lambda _: self.done(QtWidgets.QDialog.Accepted))

    @QtCore.Slot()
    def action(self):
        self.finished.emit(self.editor.text())

    @QtCore.Slot()
    def adjust_size(self):
        if not self.parent():
            return
        self.resize(
            self.parent().geometry().width(),
            self.parent().geometry().height())

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)

        o = common.MARGIN()
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
        rect.setHeight(common.ROW_HEIGHT() + (common.MARGIN() * 2))
        painter.setBrush(common.DARK_BG)
        painter.setOpacity(0.9)
        painter.drawRoundedRect(
            rect, common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())
        painter.end()

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.close()

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            if self.context_menu_open:
                return
            self.close()

    def showEvent(self, event):
        text = self.parent().model().filter_text()
        text = text.lower() if text else u''
        text = u'' if text == u'/' else text

        self.editor.setText(text)
        self.editor.selectAll()
        self.editor.setFocus()
