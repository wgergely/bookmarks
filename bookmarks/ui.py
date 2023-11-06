"""Various generic utility classes and functions used to define the UI.

"""
import functools

from PySide2 import QtCore, QtGui, QtWidgets

from . import common
from . import images

BUTTONS = (
    common.OkButton,
    common.YesButton,
    common.SaveButton,
    common.CancelButton,
    common.NoButton,
)


class MessageBox(QtWidgets.QDialog):
    """Informative message box used for notifying the user.

    Attributes:
        buttonClicked (Signal -> str): Emitted when the user click a button.

    """
    buttonClicked = QtCore.Signal(str)

    def __init__(self, title=None, body='', buttons=None, icon='icon', disable_animation=False, message_type=None,
                 parent=None):
        super().__init__(parent=parent if parent else QtWidgets.QApplication.activeWindow())

        common.set_stylesheet(self)

        if message_type and message_type not in ('info', 'success', 'error'):
            raise ValueError(f'{message_type} is an invalid message type')

        if message_type:
            self.setObjectName(f'{message_type}Box')

        self.icon = icon
        self.disable_animation = disable_animation
        self.message_type = message_type
        self.buttons = buttons if buttons else []

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
        if self.buttons == []:
            self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setAutoFillBackground(True)

        self.installEventFilter(self)

        # Shadow effect
        self.effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.effect.setBlurRadius(common.size(common.size_margin) * 2)
        self.effect.setXOffset(0)
        self.effect.setYOffset(0)
        self.effect.setColor(QtGui.QColor(0, 0, 0, 200))
        self.setGraphicsEffect(self.effect)

        self.animation = QtCore.QPropertyAnimation(self, b'windowOpacity')
        self.animation.setDuration(500)  # 500 ms duration for fade in/out
        self.animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.animation.valueChanged.connect(self.update)
        self.animation.valueChanged.connect(lambda x: QtWidgets.QApplication.instance().processEvents)

        self._create_ui()
        self._connect_signals()

        self.set_labels(title, body)

    def eventFilter(self, obj, event):
        if obj == self and event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtCore.Qt.NoPen)

            rect = self.rect().adjusted(
                common.size(common.size_margin * 1.5),
                common.size(common.size_margin * 1.5),
                -common.size(common.size_margin * 1.5),
                -common.size(common.size_margin * 1.5)
            )
            o = int(common.size(common.size_indicator))

            # Get the background color set by the stylesheet
            color = self.palette().color(QtGui.QPalette.Background)
            brush = QtGui.QBrush(color)
            painter.setBrush(brush)
            painter.drawRoundedRect(
                rect,
                o,
                o
            )
            return True
        return False

    def _create_ui(self):
        self.setLayout(QtWidgets.QHBoxLayout())

        o = common.size(common.size_margin) * 2
        self.layout().setContentsMargins(o, o, o, o)

        o = common.size(common.size_margin) * 0.5
        self.layout().setSpacing(o)

        # Main Row
        main_row = QtWidgets.QWidget(parent=self)
        main_row.setLayout(QtWidgets.QHBoxLayout())
        main_row.layout().setSpacing(o)
        self.layout().addWidget(main_row, 1)

        label = QtWidgets.QLabel(parent=self)
        pixmap = images.rsc_pixmap(
            self.icon,
            self.palette().color(QtGui.QPalette.Text),
            common.size(common.size_row_height * 1.5),
            opacity=0.5
        )
        label.setPixmap(pixmap)
        label.setFixedWidth(common.size(common.size_row_height * 1.5))
        label.setFixedHeight(common.size(common.size_row_height * 1.5))

        main_row.layout().addWidget(label, 0)

        # Labels and buttons
        columns = QtWidgets.QWidget(parent=main_row)
        columns.setLayout(QtWidgets.QVBoxLayout())
        columns.layout().setSpacing(o)

        self.title_label = QtWidgets.QLabel(parent=self)
        self.title_label.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Preferred
        )
        self.title_label.setWordWrap(True)
        self.title_label.setObjectName('titleLabel')

        self.body_label = QtWidgets.QLabel(parent=self)
        self.body_label.setWordWrap(True)
        self.body_label.setObjectName('bodyLabel')
        self.body_label.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        columns.layout().addWidget(self.title_label, 1)
        columns.layout().addWidget(self.body_label, 1)
        columns.layout().addStretch()
        columns.layout().addSpacing(common.size(common.size_margin))
        main_row.layout().addWidget(columns, 1)

        if self.buttons:
            row = QtWidgets.QWidget(parent=columns)
            row.setLayout(QtWidgets.QHBoxLayout())
            row.layout().setSpacing(o * 0.5)
            row.layout().setContentsMargins(0, 0, 0, 0)
            columns.layout().addWidget(row, 1)

            for idx, k in enumerate(self.buttons):
                if k not in BUTTONS:
                    raise ValueError(f'{k} is an invalid button')
                button = QtWidgets.QPushButton(k, parent=self)

                setattr(self, k.lower() + '_button', button)

                if idx == 0:
                    row.layout().addWidget(button, 2)
                else:
                    row.layout().addWidget(button, 1)

    def _connect_signals(self):
        for button in BUTTONS:
            k = button.lower() + '_button'

            if not hasattr(self, k):
                continue

            widget = getattr(self, k)
            widget.clicked.connect(
                functools.partial(self.buttonClicked.emit, button)
            )

            if button in (common.OkButton, common.YesButton, common.SaveButton):
                widget.clicked.connect(
                    lambda: self.done(QtWidgets.QDialog.Accepted)
                )
            if button in (common.CancelButton, common.NoButton):
                widget.clicked.connect(
                    lambda: self.done(QtWidgets.QDialog.Rejected)
                )

        self.buttonClicked.connect(self.set_clicked_button)

    @QtCore.Slot(str)
    def set_clicked_button(self, button):
        self._clicked_button = button

    def set_labels(self, title, body):
        """Sets the message box's labels.

        Args:
            title (str): The message box's title.
            body (str): The message box's body.

        """
        self.title_label.setText(title)
        self.body_label.setText(body)

        QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width * 0.90),
            common.size(common.size_height * 0.66)
        )

    def showEvent(self, event):
        """Override the show event to start the fade in animation.

        """
        common.center_to_parent(self)
        common.move_widget_to_available_geo(self)

        if self.disable_animation:
            return

        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()


class Label(QtWidgets.QLabel):
    def __init__(
            self, text, color=common.color(common.color_secondary_text), parent=None
    ):
        super().__init__(text, parent=parent)

        self.color = color
        self._color = QtGui.QColor(color)
        self._color.setAlpha(230)

        self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignJustify)
        self.setWordWrap(True)
        self.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.setOpenExternalLinks(True)

    def _set_stylesheet(self, isEnabled):
        if not isEnabled:
            self.setStyleSheet(
                'color: {}; font-size: {}px; font-family: "{}"'.format(
                    common.rgb(self._color),
                    common.size(common.size_font_small),
                    common.font_db.medium_font(
                        common.size(common.size_font_medium)
                    )[0].family()
                )
            )
        else:
            self.setStyleSheet(
                'color: {}; font-size: {}px; font-family: "{}"'.format(
                    common.rgb(self.color),
                    common.size(common.size_font_small),
                    common.font_db.medium_font(
                        common.size(common.size_font_medium)
                    )[0].family()
                )
            )
        self.update()

    def enterEvent(self, event):
        """Event handler.

        """
        self._set_stylesheet(True)

    def leaveEvent(self, event):
        """Event handler.

        """
        self._set_stylesheet(False)

    def showEvent(self, event):
        """Event handler.

        """
        self._set_stylesheet(False)


class LineEdit(QtWidgets.QLineEdit):
    """Custom line edit widget with a single underline."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.setAlignment(QtCore.Qt.AlignLeft)


class PaintedButton(QtWidgets.QPushButton):
    """Custom button class."""

    def __init__(
            self, text, height=None, width=None, parent=None
    ):
        super().__init__(text, parent=parent)
        if height:
            self.setFixedHeight(height)
        if width:
            self.setFixedWidth(width)

    def paintEvent(self, event):
        """Event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        pressed = option.state & QtWidgets.QStyle.State_Sunken
        focus = option.state & QtWidgets.QStyle.State_HasFocus
        disabled = not self.isEnabled()

        o = 1.0 if hover else 0.8
        o = 0.3 if disabled else o
        painter.setOpacity(o)

        painter.setBrush(common.color(common.color_dark_background))
        _color = QtGui.QColor(common.color(common.color_separator))
        _color.setAlpha(150)
        pen = QtGui.QPen(_color)
        pen.setWidthF(common.size(common.size_separator))
        painter.setPen(pen)

        o = common.size(common.size_separator)
        rect = self.rect().adjusted(o, o, -o, -o)

        o = common.size(common.size_indicator) * 1.5
        painter.drawRoundedRect(rect, o, o)

        if focus:
            painter.setBrush(QtCore.Qt.NoBrush)
            pen = QtGui.QPen(common.color(common.color_blue))
            pen.setWidthF(common.size(common.size_separator))
            painter.setPen(pen)
            painter.drawRoundedRect(rect, o, o)

        rect = QtCore.QRect(self.rect())
        center = rect.center()
        rect.setWidth(rect.width() - (common.size(common.size_indicator) * 2))
        rect.moveCenter(center)

        common.draw_aliased_text(
            painter,
            common.font_db.bold_font(common.size(common.size_font_medium))[0],
            rect,
            self.text(),
            QtCore.Qt.AlignCenter,
            common.color(common.color_text)
        )

        painter.end()


class PaintedLabel(QtWidgets.QLabel):
    """QLabel used for static aliased label.

    """
    clicked = QtCore.Signal()

    def __init__(
            self, text, color=common.color(common.color_text),
            size=common.size(common.size_font_medium),
            parent=None
    ):
        super().__init__(text, parent=parent)

        self._size = size
        self._color = color
        self._text = text

        self.update_size()

    def setText(self, v):
        self._text = v
        self.update_size()

        super().setText(v)

    def set_color(self, v):
        self._color = v
        self.update_size()

    def update_size(self):
        font, metrics = common.font_db.bold_font(self._size)
        self.setFixedHeight(metrics.height())
        self.setFixedWidth(
            metrics.horizontalAdvance(self._text) +
            common.size(common.size_indicator) * 2
        )

    def paintEvent(self, event):
        """Event handler.

        """
        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        painter = QtGui.QPainter()
        painter.begin(self)

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        # pressed = option.state & QtWidgets.QStyle.State_Sunken
        # focus = option.state & QtWidgets.QStyle.State_HasFocus
        disabled = not self.isEnabled()

        o = 1.0 if hover else 0.8
        o = 0.3 if disabled else o
        painter.setOpacity(o)

        rect = self.rect()
        rect.setLeft(rect.left() + common.size(common.size_indicator))
        common.draw_aliased_text(
            painter,
            common.font_db.bold_font(self._size)[0],
            self.rect(),
            self.text(),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            self._color
        )
        painter.end()

    def leaveEvent(self, event):
        """Event handler.

        """
        self.update()

    def enterEvent(self, event):
        """Event handler.

        """
        self.update()

    def mouseReleaseEvent(self, event):
        """Event handler.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        # Check if the click was inside the label
        if not self.rect().contains(event.pos()):
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()


class ClickableIconButton(QtWidgets.QLabel):
    """A utility class for creating a square icon button.

    Args:
        pixmap (str): The name of the resource file without the extension.
        colors (tuple(QColor, QColor)): A tuple of QColors, for enabled and
        disabled states.
        size (int): The value for width and height.
        description (str): A user readable description of the action the button
            performs.
        state (bool): Optional button state. 'False' by default.
        parent (QObject): The widget's parent.

    Signals:
        clicked (QtCore.Signal()):
        doubleClicked (QtCore.Signal()):
        message (QtCore.Signal(str)):

    Returns:
        type: Description of returned object.

    """
    clicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()

    def __init__(
            self, pixmap, colors, size, description='', state=False, parent=None
    ):
        super().__init__(parent=parent)

        self._pixmap = pixmap
        self._size = size
        self._state = state

        self._on_color = QtGui.QColor(colors[0])
        self._off_color = QtGui.QColor(colors[1])

        self.setStatusTip(description)
        self.setToolTip(description)
        self.setWhatsThis(description)

        self.setFixedSize(QtCore.QSize(size, size))
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.setScaledContents(False)

        self.setAttribute(QtCore.Qt.WA_NoBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.clicked.connect(self.action)
        self.clicked.connect(self.update)

    @QtCore.Slot()
    def action(self):
        pass

    def mouseReleaseEvent(self, event):
        """Event handler.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        """Event handler.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.doubleClicked.emit()

    def enterEvent(self, event):
        """Event handler.

        """
        self.repaint()

    def leaveEvent(self, event):
        """Event handler.

        """
        self.repaint()

    def set_pixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def pixmap(self):
        if not self.isEnabled():
            return images.rsc_pixmap(
                self._pixmap, self._off_color, self._size
            )
        if self.state():
            return images.rsc_pixmap(
                self._pixmap, self._on_color, self._size
            )
        return images.rsc_pixmap(
            self._pixmap, self._off_color, self._size
        )

    def state(self):
        return self._state

    def contextMenuEvent(self, event):
        """Event handler.

        """
        pass

    def paintEvent(self, event):
        """Event handler.

        """
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setOpacity(0.8)
        if hover:
            painter.setOpacity(1.0)

        if not self.state():
            painter.setOpacity(0.5)

        pixmap = self.pixmap()

        # Make sure the pixmap is never stretched
        rect = self.rect()
        center = rect.center()
        if rect.width() != rect.height():
            if rect.width() > rect.height():
                rect.setWidth(rect.height())
            else:
                rect.setHeight(rect.width())
        rect.moveCenter(center)

        painter.drawPixmap(rect, pixmap, pixmap.rect())
        painter.end()


class ListOverlayWidget(QtWidgets.QWidget):
    """Widget used to display a status message over the list widget.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._message = ''

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

    @QtCore.Slot(str)
    @QtCore.Slot(str)
    def set_message(self, title, body):
        if title == self._message:
            return

        self._message = title
        self.update()

    def paintEvent(self, event):
        """Custom paint event used to paint the widget's message.

        """
        parent = self.parent().parent()

        if hasattr(parent, 'count'):
            count = parent.count()
        elif hasattr(parent, 'model'):
            model = parent.model()
            if hasattr(model, 'sourceModel'):
                count = parent.model().sourceModel().rowCount()
            else:
                count = parent.model().rowCount()
        else:
            count = 0

        if not self._message and not count:
            message = parent.default_message
        elif not self._message:
            return
        elif self._message:
            message = self._message

        painter = QtGui.QPainter()
        painter.begin(self)

        o = common.size(common.size_margin)
        rect = self.rect().adjusted(o, o, -o, -o)
        text = QtGui.QFontMetrics(self.font()).elidedText(
            message,
            QtCore.Qt.ElideMiddle,
            rect.width(),
        )

        painter.setOpacity(0.66)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(common.color(common.color_secondary_text))
        painter.drawText(
            rect,
            QtCore.Qt.AlignCenter,
            text,
        )
        painter.end()


class ListWidgetDelegate(QtWidgets.QStyledItemDelegate):
    """Custom delegate to display label-like QListWidgetItems.

    """

    def paint(self, painter, option, index):
        checked = index.data(QtCore.Qt.CheckStateRole) == QtCore.Qt.Checked

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        selected = option.state & QtWidgets.QStyle.State_Selected
        focus = option.state & QtWidgets.QStyle.State_HasFocus
        opened = option.state & QtWidgets.QStyle.State_Open
        checkable = index.flags() & QtCore.Qt.ItemIsUserCheckable
        decoration = index.data(QtCore.Qt.DecorationRole)

        text = index.data(QtCore.Qt.DisplayRole)
        disabled = index.flags() == QtCore.Qt.NoItemFlags

        painter.setRenderHint(
            QtGui.QPainter.Antialiasing, on=True
        )
        painter.setRenderHint(
            QtGui.QPainter.SmoothPixmapTransform, on=True
        )

        o = common.size(common.size_indicator)
        rect = option.rect.adjusted(o * 0.3, o * 0.3, -o * 0.3, -o * 0.3)

        # Background
        if index.column() == 0:
            _o = 0.6 if hover else 0.2
            _o = 0.1 if disabled else _o
            _o = 1.0 if selected else _o
            painter.setOpacity(_o)
            painter.setPen(QtCore.Qt.NoPen)

            if selected or hover:
                color = common.color(common.color_light_background)
            elif opened:
                color = common.color(common.color_separator)
            else:
                color = QtGui.QColor(0, 0, 0, 0)

            painter.setBrush(color)
            painter.drawRoundedRect(rect, o, o)

            if focus:
                painter.setBrush(QtCore.Qt.NoBrush)
                pen = QtGui.QPen(common.color(common.color_blue))
                pen.setWidthF(common.size(common.size_separator))
                painter.setPen(pen)
                painter.drawRoundedRect(rect, o, o)

        # image rectangle
        painter.setPen(QtCore.Qt.NoPen)
        _ = painter.setOpacity(1.0) if hover else painter.setOpacity(0.9)

        rect = QtCore.QRect(option.rect)
        rect.setWidth(rect.height())
        center = rect.center()

        h = common.size(common.size_margin)
        rect.setSize(QtCore.QSize(h, h))
        rect.moveCenter(center)

        if checkable and checked:
            pixmap = images.rsc_pixmap(
                'check', common.color(common.color_green), rect.height()
            )
            painter.drawPixmap(rect, pixmap)
        elif checkable and not checked:
            pixmap = images.rsc_pixmap(
                'close', common.color(common.color_background), rect.height()
            )
            painter.drawPixmap(rect, pixmap)
        elif not checkable and decoration and isinstance(decoration, QtGui.QPixmap):
            painter.drawPixmap(rect, decoration)
        elif not checkable and decoration and isinstance(decoration, QtGui.QIcon):
            mode = QtGui.QIcon.Normal
            if not option.state & QtWidgets.QStyle.State_Enabled:
                mode = QtGui.QIcon.Disabled
            elif option.state & QtWidgets.QStyle.State_Selected:
                mode = QtGui.QIcon.Selected
            decoration.paint(
                painter,
                rect,
                QtCore.Qt.AlignCenter,
                mode,
                QtGui.QIcon.On
            )

        _fg = index.data(QtCore.Qt.ForegroundRole)
        color = _fg if _fg else common.color(common.color_text)
        color = common.color(common.color_selected_text) if selected else color
        color = common.color(common.color_text) if checked else color
        color = common.color(common.color_selected_text) if opened else color
        painter.setBrush(color)

        # Label
        padding = common.size(common.size_indicator) * 2
        x = rect.right() + padding

        font, metrics = common.font_db.bold_font(
            common.size(common.size_font_small)
        )

        width = option.rect.width() - (rect.right() - option.rect.left()) - padding * 2
        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            width
        )

        y = option.rect.center().y() + (metrics.ascent() / 2.0)

        path = QtGui.QPainterPath()
        path.addText(x, y, font, text)

        if checkable and not checked:
            painter.setOpacity(0.5)
        painter.drawPath(path)

    def sizeHint(self, option, index):
        opened = option.state & QtWidgets.QStyle.State_Open
        x = 1 if not opened else 1.4

        if index.isValid() and index.data(QtCore.Qt.SizeHintRole):
            height = index.data(QtCore.Qt.SizeHintRole).height() * x
        else:
            height = common.size(common.size_row_height) * x

        padding = common.size(common.size_indicator) * 2
        if index.data(QtCore.Qt.DisplayRole):
            _, metrics = common.font_db.bold_font(common.size(common.size_font_small))
            text_width = metrics.boundingRect(index.data(QtCore.Qt.DisplayRole)).width()
            width = padding + common.size(common.size_margin) + padding + text_width + padding
        else:
            width = 0
        return QtCore.QSize(width, height)

    def createEditor(self, parent, option, index):
        """Custom editor for editing the template's name.

        """
        editor = LineEdit(parent=parent)
        editor.setWindowFlags(QtCore.Qt.Widget)
        editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        editor.setStyleSheet(
            f'background-color: {common.rgb(common.color_separator)};'
            f'height: {option.rect.height()}px;'
        )
        return editor

    def updateEditorGeometry(self, editor, option, index):
        """Updates the size of the editor widget.

        """
        editor.setGeometry(option.rect)


class ListWidget(QtWidgets.QListWidget):
    """A custom list widget used to display selectable item.

    """
    progressUpdate = QtCore.Signal(str, str)
    resized = QtCore.Signal(QtCore.QSize)

    def __init__(self, default_message='No items', default_icon='icon', parent=None):
        super().__init__(parent=parent)
        if not self.parent():
            common.set_stylesheet(self)

        self.default_message = default_message
        self.default_icon = default_icon

        self.server = None
        self.job = None
        self.root = None

        self.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed
        )
        self.setAcceptDrops(False)
        self.setDragEnabled(False)
        self.setSpacing(0)

        self.setItemDelegate(ListWidgetDelegate(parent=self))

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self.overlay = ListOverlayWidget(parent=self.viewport())
        self.overlay.show()

        self.installEventFilter(self)

    def eventFilter(self, widget, event):
        """Event filter handler.

        """
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            paint_background_icon(self.default_icon, widget)
            return True
        return False

    def _connect_signals(self):
        self.resized.connect(self.overlay.resize)

        self.progressUpdate.connect(self.overlay.set_message)
        self.progressUpdate.connect(lambda x, y: common.signals.showStatusTipMessage.emit(x))

        self.itemEntered.connect(
            lambda item: common.signals.showStatusTipMessage.emit(
                item.data(QtCore.Qt.DisplayRole)
            )
        )

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def toggle(self, item):
        if not item.flags() & QtCore.Qt.ItemIsUserCheckable:
            return
        if item.checkState() == QtCore.Qt.Unchecked:
            item.setCheckState(QtCore.Qt.Checked)
            return
        item.setCheckState(QtCore.Qt.Unchecked)

    def addItem(
            self, label, icon=None, color=common.color(common.color_secondary_text)
    ):
        if isinstance(label, QtWidgets.QListWidgetItem):
            return super().addItem(label)

        _, metrics = common.font_db.bold_font(
            common.size(common.size_font_small)
        )
        width = metrics.horizontalAdvance(
            label
        ) + common.size(common.size_row_height) + common.size(common.size_margin)
        item = QtWidgets.QListWidgetItem(label)

        size = QtCore.QSize(width, common.size(common.size_row_height))
        item.setData(QtCore.Qt.SizeHintRole, size)

        if icon:
            item.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            )
            pixmap = images.rsc_pixmap(
                icon,
                color,
                common.size(common.size_row_height) -
                (common.size(common.size_indicator) * 2)
            )
            item.setData(QtCore.Qt.DecorationRole, pixmap)
        else:
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsUserCheckable
            )

        item.setCheckState(QtCore.Qt.Unchecked)
        return super().addItem(item)

    def resizeEvent(self, event):
        self.resized.emit(event.size())


class ListViewWidget(QtWidgets.QListView):
    """A custom list widget used to display selectable item.

    """
    progressUpdate = QtCore.Signal(str, str)
    resized = QtCore.Signal(QtCore.QSize)
    itemEntered = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, default_message='No items', default_icon='icon', parent=None):
        super().__init__(parent=parent)
        if not self.parent():
            common.set_stylesheet(self)

        self.default_message = default_message
        self.default_icon = default_icon

        self.server = None
        self.job = None
        self.root = None

        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed
        )
        self.setAcceptDrops(False)
        self.setDragEnabled(False)
        self.setSpacing(0)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setItemDelegate(ListWidgetDelegate(parent=self))
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setModel(QtCore.QSortFilterProxyModel(parent=self))
        self.model().setSourceModel(QtGui.QStandardItemModel(parent=self))
        self.model().sourceModel().setColumnCount(1)
        self.model().setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.overlay = ListOverlayWidget(parent=self.viewport())
        self.overlay.show()

        self.installEventFilter(self)

    def eventFilter(self, widget, event):
        """Event filter handler.

        """
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            paint_background_icon(self.default_icon, widget)
            return True
        return False

    def _connect_signals(self):
        self.resized.connect(self.overlay.resize)
        self.progressUpdate.connect(self.overlay.set_message)
        self.progressUpdate.connect(lambda x, y: common.signals.showStatusTipMessage.emit(x))

        self.itemEntered.connect(
            lambda item: common.signals.showStatusTipMessage.emit(
                item.data(QtCore.Qt.DisplayRole)
            )
        )

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        pos = self.mapFromGlobal(common.cursor.pos())
        if self.rect().contains(pos):
            index = self.indexAt(pos)
            if not index.isValid():
                return
            self.itemEntered.emit(index)

    @QtCore.Slot(QtGui.QStandardItem)
    def toggle(self, item):
        if not item.flags() & QtCore.Qt.ItemIsUserCheckable:
            return
        if item.checkState() == QtCore.Qt.Unchecked:
            item.setCheckState(QtCore.Qt.Checked)
            return
        item.setCheckState(QtCore.Qt.Unchecked)

    def addItem(self, v, icon=None, color=common.color(common.color_secondary_text)):
        common.check_type(v, (str, QtGui.QStandardItem))
        common.check_type(icon, (QtGui.QPixmap, QtGui.QIcon, str, None))
        common.check_type(color, (QtGui.QColor, None))

        if isinstance(v, QtGui.QStandardItem):
            self.model().sourceModel().appendRow(v)
            return

        _, metrics = common.font_db.bold_font(
            common.size(common.size_font_small)
        )
        width = metrics.horizontalAdvance(v) + common.size(
            common.size_row_height
        ) + common.size(common.size_margin)

        item = QtGui.QStandardItem(v)

        size = QtCore.QSize(width, common.size(common.size_row_height))
        item.setData(size, role=QtCore.Qt.SizeHintRole)

        if isinstance(icon, str):
            item.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            )
            pixmap = images.rsc_pixmap(
                icon,
                color,
                common.size(common.size_row_height) -
                (common.size(common.size_indicator) * 2)
            )
            item.setData(pixmap, role=QtCore.Qt.DecorationRole)
        elif isinstance(icon, (QtGui.QIcon, QtGui.QPixmap)):
            item.setData(icon, role=QtCore.Qt.DecorationRole)
        else:
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsUserCheckable
            )

        item.setCheckState(QtCore.Qt.Unchecked)
        self.model().sourceModel().appendRow(item)

    def resizeEvent(self, event):
        self.resized.emit(event.size())


def get_icon(
        name,
        color=common.color(common.color_disabled_text),
        size=common.size(common.size_row_height) * 2,
        opacity=1.0,
        resource=common.GuiResource
):
    """Utility method for retuning a QIcon to use in the context menu.

    Args:
        name (str): The name of the icon.
        color (QColor or None): The color of the icon.
        size (QtGui.QSize or None): The size of the icon.
        opacity (float): The opacity of the icon.
        resource (str): The resource source for the icon.

    Returns:
        QtGui.QIcon: The QIcon.

    """
    k = f'{name}/{color}/{size}/{opacity}/{resource}'

    if k in common.image_cache[images.IconType]:
        return common.image_cache[images.IconType][k]

    icon = QtGui.QIcon()

    pixmap = images.rsc_pixmap(
        name, color, size, opacity=opacity, resource=resource
    )
    icon.addPixmap(pixmap, mode=QtGui.QIcon.Normal)

    _c = common.color(common.color_selected_text) if color else None
    pixmap = images.rsc_pixmap(
        name, _c, size, opacity=opacity, resource=resource
    )
    icon.addPixmap(pixmap, mode=QtGui.QIcon.Active)
    icon.addPixmap(pixmap, mode=QtGui.QIcon.Selected)

    _c = common.color(common.color_separator) if color else None
    pixmap = images.rsc_pixmap(
        'close', _c, size, opacity=0.5, resource=common.GuiResource
    )

    icon.addPixmap(pixmap, mode=QtGui.QIcon.Disabled)

    common.image_cache[images.IconType][k] = icon
    return common.image_cache[images.IconType][k]


def get_group(parent=None, vertical=True, margin=common.size(common.size_margin)):
    """Utility method for creating a group widget.

    Returns:
        QGroupBox: group widget.

    """
    grp = QtWidgets.QGroupBox(parent=parent)
    grp.setMinimumWidth(common.size(common.size_width) * 0.3)

    if vertical:
        QtWidgets.QVBoxLayout(grp)
    else:
        QtWidgets.QHBoxLayout(grp)

    grp.setSizePolicy(
        QtWidgets.QSizePolicy.Minimum,
        QtWidgets.QSizePolicy.Maximum,
    )

    grp.layout().setContentsMargins(margin, margin, margin, margin)
    grp.layout().setSpacing(margin * 0.5)
    parent.layout().addWidget(grp, 1)

    return grp


def add_row(
        label,
        color=common.color(common.color_secondary_text),
        height=common.size(common.size_row_height),
        cls=None,
        vertical=False,
        parent=None,
):
    """Utility method for creating a row widget.

    Returns:
        QWidget:    The newly created row.

    """
    if cls:
        w = cls(parent=parent)
    else:
        w = QtWidgets.QWidget(parent=parent)

    if vertical:
        QtWidgets.QVBoxLayout(w)
    else:
        QtWidgets.QHBoxLayout(w)

    w.layout().setContentsMargins(0, 0, 0, 0)
    w.layout().setSpacing(common.size(common.size_indicator))
    w.layout().setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

    w.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.Expanding,
    )
    if height:
        w.setFixedHeight(height)

    w.setAttribute(QtCore.Qt.WA_NoBackground)
    w.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    if label:
        l = PaintedLabel(
            label,
            size=common.size(common.size_font_small),
            color=color,
            parent=parent
        )
        l.setFixedWidth(common.size(common.size_margin) * 8.6667)
        w.layout().addWidget(l, 1)

    if parent:
        parent.layout().addWidget(w, 1)

    return w


def add_label(text, parent=None):
    """Utility method for creating a label.

    Returns:
        QLabel: label widget.

    """
    label = QtWidgets.QLabel(text, parent=parent)
    label.setFixedHeight(common.size(common.size_row_height))
    label.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.Expanding
    )
    label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
    parent.layout().addWidget(label, 0)


def add_line_edit(label, parent=None):
    """Utility method for adding a line editor.

    Returns:
        QLineEdit: line editor widget.

    """
    w = LineEdit(parent=parent)
    w.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
    w.setPlaceholderText(label)
    parent.layout().addWidget(w, 1)
    return w


def add_description(
        text, label=' ', height=None, color=common.color(common.color_secondary_text), parent=None
):
    """Utility method for adding a description field.

    Returns:
        QLabel: the added QLabel.

    """
    row = add_row(label, height=height, parent=parent)
    row.layout().setSpacing(0)

    label = Label(text, color=color, parent=parent)
    row.layout().addWidget(label, 1)
    parent.layout().addWidget(row, 1)
    row.setFocusPolicy(QtCore.Qt.NoFocus)
    label.setFocusPolicy(QtCore.Qt.NoFocus)
    return row


def paint_background_icon(name, widget):
    """Paints a decorative background icon to the middle of the given widget.

    Args:
        name (str): The image's name.
        widget (QWidget): The widget to paint on.

    """
    painter = QtGui.QPainter()
    painter.begin(widget)

    pixmap = images.rsc_pixmap(
        name,
        common.color(common.color_opaque),
        common.size(common.size_row_height) * 3
    )
    rect = pixmap.rect()
    rect.moveCenter(widget.rect().center())
    painter.drawPixmap(rect, pixmap, pixmap.rect())
    painter.end()


class GalleryItem(QtWidgets.QLabel):
    """Custom QLabel used by the GalleryWidget to display an image.

    Args:
        label (str): An informative label.
        data (str): The item's data. This will be emitted by the clicked signal.
        thumbnail (str): Path to an image file.
        height (int or float, optional): The item's width/height in pixels.

    """
    clicked = QtCore.Signal(str)

    def __init__(
            self, label, data, thumbnail, height=common.size(common.size_row_height) * 2,
            parent=None
    ):
        super().__init__(parent=parent)

        common.check_type(label, str)
        common.check_type(data, str)
        common.check_type(thumbnail, str)
        common.check_type(height, (int, float))

        self._pixmap = None
        self._label = label
        self._data = data
        self._thumbnail = thumbnail
        self._height = height

        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setScaledContents(False)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self.setMinimumSize(QtCore.QSize(self._height, self._height))

    def resizeEvent(self, event):
        h = self.sizeHint().height()
        self.setFixedSize(QtCore.QSize(h, h))

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def mouseReleaseEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.clicked.emit(self._data)

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        o = 1.0 if hover else 0.7
        painter.setOpacity(o)

        if not self._pixmap:
            self._pixmap = images.ImageCache.get_pixmap(
                self._thumbnail,
                self._height,
                force=True
            )
            if not self._pixmap:
                return

        s = float(min((self.rect().height(), self.rect().width())))
        longest_edge = float(max((self._pixmap.width(), self._pixmap.height())))
        ratio = s / longest_edge
        w = self._pixmap.width() * ratio
        h = self._pixmap.height() * ratio
        _rect = QtCore.QRect(0, 0, w, h)
        _rect.moveCenter(self.rect().center())
        painter.drawPixmap(
            _rect,
            self._pixmap,
        )

        if not hover:
            painter.end()
            return

        # Paint the item's label when the mouse is over it
        painter.setPen(common.color(common.color_text))
        rect = self.rect()
        rect.moveTopLeft(rect.topLeft() + QtCore.QPoint(1, 1))

        font, _ = common.font_db.bold_font(common.size(common.size_font_medium))

        common.draw_aliased_text(
            painter,
            font,
            rect,
            self._label,
            QtCore.Qt.AlignCenter,
            QtGui.QColor(0, 0, 0, 255),
        )

        rect = self.rect()
        common.draw_aliased_text(
            painter,
            font,
            rect,
            self._label,
            QtCore.Qt.AlignCenter,
            common.color(common.color_selected_text),
        )

        painter.end()


class GalleryWidget(QtWidgets.QDialog):
    """A generic gallery widget used to let the user pick an item.

    Attributes:
        itemSelected (Signal -> str): Emitted when the user clicks the item.

    """
    itemSelected = QtCore.Signal(str)

    def __init__(
            self, label, columns=5, item_height=common.size(common.size_row_height) * 2,
            parent=None
    ):
        super().__init__(parent=parent)

        self.anim = None
        self.scroll_area = None
        self.columns = columns
        self._label = label
        self._item_height = item_height

        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowOpacity(0.95)

        self.installEventFilter(self)

        self._create_ui()
        self.init_data()

    def eventFilter(self, widget, event):
        if event.type() == QtCore.QEvent.WindowDeactivate:
            self.close()
            return True
        return False

    def _create_ui(self):
        if not self.parent():
            common.set_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        o = common.size(common.size_margin) * 2

        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        label = PaintedLabel(
            self._label,
            color=common.color(common.color_text),
            size=common.size(common.size_font_large),
            parent=self
        )
        self.layout().addWidget(label)
        self.layout().addSpacing(common.size(common.size_margin) * 1.5)

        _width = (
                (common.size(common.size_indicator) * 2) +
                (common.size(common.size_margin) * 4) +
                (common.size(common.size_indicator) * (self.columns - 1)) +
                self._item_height * self.columns
        )

        self.setMinimumWidth(_width)
        self.setMaximumWidth(_width)

        self.setMinimumHeight(
            (common.size(common.size_indicator) * 2) +
            (common.size(common.size_margin) * 4) +
            self._item_height
        )
        self.setMaximumHeight(
            (common.size(common.size_indicator) * 2) +
            (common.size(common.size_margin) * 4) +
            (common.size(common.size_indicator) * 9) +
            (self._item_height * 10)
        )

        widget = QtWidgets.QWidget(parent=self)
        widget.eventFilter = self.eventFilter

        QtWidgets.QGridLayout(widget)
        widget.layout().setAlignment(QtCore.Qt.AlignCenter)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().setSpacing(common.size(common.size_indicator))

        self.scroll_area = QtWidgets.QScrollArea(parent=self)
        self.scroll_area.setStyleSheet('border:none;')
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(widget)

        self.layout().addWidget(self.scroll_area, 1)
        self.setFocusProxy(self.scroll_area.widget())

    def init_data(self):
        """Initializes data.

        """
        row = 0
        idx = 0

        for label, path, thumbnail in self.item_generator():
            item = GalleryItem(
                label, path, thumbnail, height=self._item_height, parent=self
            )

            column = idx % self.columns
            if column == 0:
                row += 1

            self.scroll_area.widget().layout().addWidget(item, row, column)
            item.clicked.connect(self.itemSelected)
            item.clicked.connect(self.close)

            idx += 1

    def item_generator(self):
        """Abstract method used to generate the values needed to display items.

        Yields:
            tuple (str, str, str): An informative label, user data and thumbnail
            image path.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    def focusOutEvent(self, event):
        self.accept()  # or self.reject()

    def showEvent(self, event):
        """Show event handler.

        """
        common.center_to_parent(self, common.main_widget)
        common.move_widget_to_available_geo(self)

        self.anim = QtCore.QPropertyAnimation(self, b'windowOpacity')
        self.anim.setDuration(500)  # Animation duration in milliseconds
        self.anim.setStartValue(0)
        self.anim.setEndValue(0.95)
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

        self.anim.finished.connect(self.raise_)
        self.anim.finished.connect(lambda: self.setFocus(QtCore.Qt.PopupFocusReason))

    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            self.anim = QtCore.QPropertyAnimation(self, b'windowOpacity')
            self.anim.setDuration(500)  # Animation duration in milliseconds
            self.anim.setStartValue(0.95)
            self.anim.setEndValue(0.0)
            self.anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
            self.anim.start()
            self.anim.finished.connect(lambda: super(GalleryWidget, self).done(r))
        else:
            super().done(r)


class AbstractListModel(QtCore.QAbstractListModel):
    """Generic list model used to store custom data.

    """

    row_size = QtCore.QSize(1, common.size(common.size_row_height))

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._data = {}
        self.reset_data()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._data)

    def display_name(self, v):
        return v.replace('/', '  |   ')

    def reset_data(self):
        """Resets the model's data."""
        self.beginResetModel()
        self.init_data()
        self.endResetModel()

    def init_data(self, *args, **kwargs):
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    def index(self, row, column, parent=QtCore.QModelIndex()):
        return self.createIndex(row, 0, parent=parent)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        idx = index.row()
        if idx not in self._data:
            return None
        if role not in self._data[idx]:
            return None
        return self._data[idx][role]

    def flags(self, index):
        v = self.data(index, role=common.FlagsRole)
        if v is not None:
            return v
        return (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable
        )

    def _add_separator(self, label):
        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: label,
            QtCore.Qt.DecorationRole: None,
            QtCore.Qt.ForegroundRole: common.color(common.color_disabled_text),
            QtCore.Qt.SizeHintRole: self.row_size,
            QtCore.Qt.UserRole: None,
            common.FlagsRole: QtCore.Qt.NoItemFlags
        }
