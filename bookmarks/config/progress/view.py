from PySide2 import QtWidgets

from .model import TemplateModel


class TemplateView(QtWidgets.QTreeView):
    """View for displaying task templates, supports dragging."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModel(TemplateModel(parent=self))

        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(False)  # Show header to display "Templates"
        self.setRootIsDecorated(False)  # Since we have a flat list
        # self.expandAll()
