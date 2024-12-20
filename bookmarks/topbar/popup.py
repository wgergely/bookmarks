from PySide2 import QtWidgets, QtCore, QtGui

from .. import common


class FilterPopupDialog(QtWidgets.QDialog):
    """
    A custom popup dialog that resembles a context QMenu with a QListView.
    Features a frameless window, drop shadow, and a custom shape combining
    a rounded rectangle with a protruding upward-pointing triangle.
    """

    def __init__(self, filter_type, parent=None):
        """
        Initialize the custom popup dialog.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget.
        """
        super().__init__(parent=parent)

        self.filter_type = filter_type

        # Initialize attributes
        self._list_view = None

        # Set window flags and attributes
        self.setWindowFlags(
            QtCore.Qt.Popup |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.NoDropShadowWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        # Set up opacity effect
        self._opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0)

        # Set up animations
        duration = 300  # Duration in milliseconds
        self._fade_in_animation = QtCore.QPropertyAnimation(self._opacity_effect, b'opacity')
        self._fade_in_animation.setDuration(duration)
        self._fade_in_animation.setStartValue(0)
        self._fade_in_animation.setEndValue(1)
        self._fade_in_animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        self._fade_out_animation = QtCore.QPropertyAnimation(self._opacity_effect, b'opacity')
        self._fade_out_animation.setDuration(duration)
        self._fade_out_animation.setStartValue(1)
        self._fade_out_animation.setEndValue(0)
        self._fade_out_animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._fade_out_animation.finished.connect(self._on_fade_out_finished)

        self._create_ui()
        self._connect_signals()
        self._init_data()
        self._apply_custom_mask()

        self.setFocusProxy(self._list_view)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def _create_ui(self):
        """Set up the user interface components."""
        QtWidgets.QVBoxLayout(self)
        top_margin = common.Size.Margin(1.1)

        o = common.Size.Indicator(1.0)
        self.layout().setContentsMargins(
            o, top_margin, -o, -o
        )

        self._list_view = QtWidgets.QListView(self)
        self._list_view.setFrameShape(QtWidgets.QFrame.NoFrame)

        self._list_view.setModel(QtGui.QStandardItemModel(self._list_view))
        self.layout().addWidget(self._list_view)

    def _connect_signals(self):
        """Connect signals to slots."""
        self._list_view.clicked.connect(self._on_item_selected)

    def _init_data(self):
        """Initialize data for the list view."""
        # Example items; replace with dynamic data as needed
        self._list_view.model().clear()
        for item_text in ["Option 1", "Option 2", "Option 3"]:
            item = QtGui.QStandardItem(item_text)
            self._list_view.model().appendRow(item)

    def _apply_custom_mask(self):
        """Apply a custom mask to create a rounded rectangle with a triangle."""
        path = QtGui.QPainterPath()

        # Sizes
        triangle_height = common.Size.Indicator(2.5)  # Approx 10
        corner_radius = common.Size.Margin(0.55)  # Approx 10

        # Set fixed size of the dialog
        rect_width = common.Size.DefaultWidth(0.3)  # Approx 192
        rect_height = common.Size.DefaultHeight(0.4)  # Approx 192

        self.setFixedSize(rect_width, rect_height + triangle_height)

        # Rounded rectangle
        path.addRoundedRect(
            0, triangle_height, rect_width, rect_height, corner_radius, corner_radius
        )

        # Triangle (inverted)
        triangle = QtGui.QPolygonF([
            QtCore.QPointF(rect_width / 2 - triangle_height, triangle_height),
            QtCore.QPointF(rect_width / 2 + triangle_height, triangle_height),
            QtCore.QPointF(rect_width / 2, 0)
        ])
        path.addPolygon(triangle)

        region = QtGui.QRegion(path.simplified().toFillPolygon().toPolygon())
        self.setMask(region)

    def _start_fade_in(self):
        """Start the fade-in animation."""
        self._fade_in_animation.start()

    def _start_fade_out(self):
        """Start the fade-out animation."""
        self._fade_out_animation.start()

    def _on_fade_out_finished(self):
        """Handle the completion of the fade-out animation."""
        super().accept()

    def _on_item_selected(self, index):
        """
        Handle the selection of an item from the list view.

        Args:
            index (QtCore.QModelIndex): The index of the selected item.
        """
        selected_item = self._list_view.model().itemFromIndex(index).text()
        self.close()  # Trigger fade-out animation

    def showEvent(self, event):
        """Handle the show event to start the fade-in animation."""
        super().showEvent(event)
        self._start_fade_in()
        self._list_view.setFocus(QtCore.Qt.OtherFocusReason)

    def closeEvent(self, event):
        """Override closeEvent to start fade-out animation."""
        if self._fade_out_animation.state() == QtCore.QAbstractAnimation.Running:
            # Fade-out animation already running
            event.ignore()
        else:
            # Start fade-out animation
            event.ignore()
            self._start_fade_out()

    def keyPressEvent(self, event):
        """
        Handle key press events for keyboard navigation.

        Args:
            event (QtGui.QKeyEvent): The key event.
        """
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()  # Close the dialog on Escape key
        elif event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            current_index = self._list_view.currentIndex()
            if current_index.isValid():
                self._on_item_selected(current_index)
            else:
                self.close()  # Close if no selection
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        """
        Paint the background with rounded corners and a triangle.

        Args:
            event (QtGui.QPaintEvent): The paint event.
        """
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Create path
        path = QtGui.QPainterPath()

        # Sizes
        rect_width = self.width()
        triangle_height = common.Size.Indicator(2.5)
        rect_height = self.height() - triangle_height
        corner_radius = common.Size.Indicator(2.5)

        path.addRoundedRect(
            0, triangle_height, rect_width, rect_height, corner_radius, corner_radius
        )

        triangle = QtGui.QPolygonF([
            QtCore.QPointF(rect_width / 2 - triangle_height, triangle_height),
            QtCore.QPointF(rect_width / 2 + triangle_height, triangle_height),
            QtCore.QPointF(rect_width / 2, 0)
        ])
        path.addPolygon(triangle)

        # Fill background
        painter.fillPath(path.simplified(), common.Color.VeryDarkBackground())
        pen = QtGui.QPen(common.Color.Blue())
        pen.setWidthF(common.Size.Separator(6.0))
        painter.strokePath(path.simplified(), pen)

