# -*- coding: utf-8 -*-
"""Widget used to edit the description of an item.

"""
from PySide2 import QtCore

from ... import common
from ... import database
from ... import ui
from ...items import delegate


class DescriptionEditorWidget(ui.LineEdit):
    """The editor used to edit the desciption of items."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.installEventFilter(self)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.setPlaceholderText('Edit description...')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._connect_signals()

    def _connect_signals(self):
        self.editingFinished.connect(self.action)
        self.parent().verticalScrollBar().valueChanged.connect(self.hide)
        if self.parent():
            self.parent().resized.connect(self.update_editor)

    def action(self):
        index = common.get_selected_index(self.parent())
        if not index.isValid():
            self.hide()
            return

        text = f'{index.data(common.DescriptionRole)}'
        if text.lower() == self.text().lower():
            self.hide()
            return

        source_path = index.data(common.ParentPathRole)
        if not source_path:
            self.hide()
            return

        p = index.data(common.PathRole)
        if common.is_collapsed(p):
            k = common.proxy_path(index)
        else:
            k = p

        # Set the database value
        db = database.get_db(*source_path[0:3])
        with db.connection():
            db.setValue(k, 'description', self.text())

        # Repaint the index
        source_index = index.model().mapToSource(index)
        data = source_index.model().model_data()
        idx = source_index.row()

        data[idx][common.DescriptionRole] = self.text()
        self.parent().update(source_index)
        self.hide()

    def update_editor(self):
        """Sets the editor widget's size, position and text contents."""
        index = common.get_selected_index(self.parent())
        if not index.isValid():
            self.hide()
            return

        rect = self.parent().visualRect(index)
        rectangles = delegate.get_rectangles(
            rect, self.parent().inline_icons_count())
        description_rect = self.parent().itemDelegate(
        ).get_description_rect(rectangles, index)

        # Won't be showing the editor if there's no appropriate description area
        # provided by the delegate (e.g. the bookmark items don't have this)
        if not description_rect:
            self.hide()
            return

        # Let's set the size based on the size provided by the delegate
        self.setStyleSheet(f'height: {rectangles[delegate.DataRect].height()}px;')
        self.setGeometry(rectangles[delegate.DataRect])

        # Set the text and select it
        v = index.data(common.DescriptionRole)
        v = v if v else ''
        self.setText(v)
        self.selectAll()

    def showEvent(self, event):
        index = common.get_selected_index(self.parent())
        if not index.isValid():
            self.hide()
            return None

        if not index.data(common.FileInfoLoaded):
            self.hide()
            return

        self.update_editor()
        self.setFocus()

    def eventFilter(self, widget, event):
        """We're filtering the enter key event here, otherwise, the
        list widget would close open finishing editing.

        """
        if not event.type() == QtCore.QEvent.KeyPress:
            return False

        event.accept()

        shift = event.modifiers() == QtCore.Qt.ShiftModifier

        escape = event.key() == QtCore.Qt.Key_Escape

        tab = event.key() == QtCore.Qt.Key_Tab
        backtab = event.key() == QtCore.Qt.Key_Backtab

        return_ = event.key() == QtCore.Qt.Key_Return
        enter = event.key() == QtCore.Qt.Key_Enter

        if escape:
            self.hide()
            return True

        if enter or return_:
            self.action()
            return True

        if not shift and tab:
            self.action()
            self.parent().key_down()
            self.parent().key_tab()
            self.show()

            return True

        if (shift and tab) or backtab:
            self.action()
            self.parent().key_up()
            self.parent().key_tab()
            self.show()
            return True

        return False

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.hide()
