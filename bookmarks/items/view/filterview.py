from PySide2 import QtCore, QtGui, QtWidgets

from . import buttonview
from ... import common


class FilterView(buttonview.ButtonView):
    filterRectangleEntered = QtCore.Signal(QtCore.QRect)
    filterRectangleLeft = QtCore.Signal()

    def _connect_signals(self):
        super()._connect_signals()
        self.filterRectangleEntered.connect(self.itemDelegate().set_filter_candidate_rectangle)
        self.filterRectangleLeft.connect(self.itemDelegate().clear_filter_candidate_rectangle)
        self.filterRectangleLeft.connect(common.signals.clearStatusBarMessage)

    def mouseMoveEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            super().mouseMoveEvent(event)
            return

        index = self.indexAt(event.pos())
        if not index.isValid():
            super().mouseMoveEvent(event)
            return

        if index.column() != 2:
            super().mouseMoveEvent(event)
            return

        rect, text = self.itemDelegate().get_filter_rectangle(index.data(common.IdRole), event.pos())
        if not text:
            self.filterRectangleLeft.emit()
        else:
            self.filterRectangleEntered.emit(rect)
            common.signals.showStatusTipMessage.emit(
                f'Shift-click to filter by "{text}"  |  Alt-click to exclude "{text}"')

        self.repaint(self.visualRect(index))

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            super().mouseReleaseEvent(event)
            return

        index = self.indexAt(event.pos())
        if not index.isValid():
            super().mouseReleaseEvent(event)
            return

        if index.column() == 2 and not index.flags() & common.MarkedAsArchived:
            rect, text = self.itemDelegate().get_filter_rectangle(index.data(common.IdRole), event.pos())
            if not text:
                super().mouseReleaseEvent(event)
                return

            modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
            shift_modifier = modifiers & QtCore.Qt.ShiftModifier
            alt_modifier = modifiers & QtCore.Qt.AltModifier

            if modifiers == QtCore.Qt.NoModifier:
                super().mouseReleaseEvent(event)
                return

            negative_filter_text = f'--"{text}"'
            positive_filter_text = f'"{text}"'

            if shift_modifier:  # positive filter intent
                # Remove negative filter
                if self.model().filter.has_string(negative_filter_text, negative_terms=True):
                    self.model().filter.remove_filter(negative_filter_text)

                if self.model().filter.has_string(positive_filter_text, positive_terms=True):
                    self.model().filter.remove_filter(positive_filter_text)
                else:
                    self.model().filter.add_filter(positive_filter_text)
            elif alt_modifier:  # negative filter intent
                # Remove positive filter
                if self.model().filter.has_string(positive_filter_text, positive_terms=True):
                    self.model().filter.remove_filter(positive_filter_text)
                self.model().filter.add_filter(negative_filter_text)

            self.model().set_filter_text(self.model().filter.filter_string)
            self.update(index)

            self.filterRectangleLeft.emit()

        return super().mouseReleaseEvent(event)
