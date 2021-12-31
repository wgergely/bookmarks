# -*- coding: utf-8 -*-
"""The widget used set and edit search filters.

"""
from PySide2 import QtWidgets, QtGui, QtCore

from ... import common
from ... import ui



class FilterEditor(QtWidgets.QDialog):
    """Editor widget used to set a list model's persistent text filter.

    """
    finished = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(FilterEditor, self).__init__(parent=parent)

        self.editor = None
        self.ok_button = None
        self.context_menu_open = False

        self._create_ui()
        self._connect_signals()

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(QtCore.Qt.Widget)
        self.setFocusProxy(self.editor)

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.size(common.WidthMargin) * 2
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        row = ui.add_row(
            None,
            parent=self,
            padding=0,
            height=common.size(common.HeightRow)
        )

        self.history_button = ui.ClickableIconButton(
            'filter',
            (common.color(common.TextSecondaryColor), common.color(common.TextSecondaryColor)),
            common.size(common.WidthMargin)
        )
        self.history_button.setFocusPolicy(QtCore.Qt.NoFocus)
        row.layout().addWidget(self.history_button, 0)

        self.editor = ui.LineEdit(parent=self)
        self.editor.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        row.layout().addWidget(self.editor, 1)

        self.ok_button = ui.PaintedButton('Save', parent=self)
        row.layout().addWidget(self.ok_button, 0)

        self.layout().addStretch(1)

    def _connect_signals(self):
        self.editor.returnPressed.connect(self.action)
        self.ok_button.clicked.connect(self.action)

    def set_completer(self):
        proxy = self.parent().model()
        model = proxy.sourceModel()

        v = model.get_local_setting(common.TextFilterKeyHistory)
        v = v.split(';') if v else []
        v.reverse()
        v = [f for f in v if f]

        completer = QtWidgets.QCompleter(v, parent=self.editor)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_stylesheet(completer.popup())

        self.editor.setCompleter(completer)

        self.history_button.clicked.connect(self.show_history)

    def show_history(self):
        self.editor.completer().setCompletionPrefix('')
        self.editor.completer().complete()

    def init_text(self):
        proxy = self.parent().model()
        text = proxy.filter_text()
        text = text.lower() if text else ''
        text = '' if text == '/' else text
        self.editor.setText(text)

    @QtCore.Slot()
    def action(self):
        self.finished.emit(self.editor.text())
        self.done(QtWidgets.QDialog.Accepted)

    @QtCore.Slot()
    def adjust_size(self):
        if not self.parent():
            return
        geo = self.parent().geometry()
        self.resize(geo.width(), geo.height())

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        pen = QtGui.QPen(common.color(common.SeparatorColor))
        pen.setWidthF(common.size(common.HeightSeparator))
        painter.setPen(pen)

        o = common.size(common.WidthMargin)
        i = common.size(common.WidthIndicator)
        r = common.size(common.HeightRow)

        rect = self.rect().adjusted(o, o, -o, -o)
        rect.setHeight(r + (o * 2))

        painter.setBrush(common.color(common.BackgroundDarkColor))
        painter.setOpacity(0.85)
        painter.drawRoundedRect(rect, i, i)
        painter.end()

    def showEvent(self, event):
        self.init_text()
        self.set_completer()
        self.editor.selectAll()
        self.editor.setFocus()
