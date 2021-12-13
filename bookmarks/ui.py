import functools

from PySide2 import QtCore, QtGui, QtWidgets

from . import common
from . import images

OkButton = 'Ok'
YesButton = 'Yes'
SaveButton = 'Save'
CancelButton = 'Cancel'
NoButton = 'No'

buttons = (
    OkButton,
    YesButton,
    SaveButton,
    CancelButton,
    NoButton,
)

MESSAGE_BOX_STYLESHEET = """
QWidget {{
    color: {TEXT};
    background-color: {TRANSPARENT};
    font-family: "{FAMILY}";
    font-size: {SIZE}px;
}}"""

PUSH_BUTTON_STYLESHEET = """
QPushButton {{
    font-size: {px}px;
    color: {SELECTED_TEXT};
    border-radius: {i}px;
    margin: {i}px;
    padding: {i}px;
    background-color: {p};
}}
QPushButton:hover {{
    background-color: {pl};
}}
QPushButton:pressed {{
    background-color: {pd};
}}"""


class MessageBox(QtWidgets.QDialog):
    """Informative message box used for notifying the user of an event.

    Attributes:
        buttonClicked (Signal -> str): Emitted when the user click a button.

    """
    primary_color = common.color(common.BlueLightColor)
    secondary_color = common.color(common.BlueColor).lighter(120)
    icon = 'icon_bw'

    buttonClicked = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):

        try:
            common.message_widget.close()
            common.message_widget.deleteLater()
        except:
            pass
        finally:
            common.message_widget = None
        common.message_widget = self

        if 'parent' in kwargs:
            parent = kwargs['parent']
        else:
            parent = None

        super().__init__(parent=parent)

        if parent is None:
            common.set_custom_stylesheet(self)

        # labels
        self.no_buttons = False
        self.buttons = []
        self.primary_label = None
        self.secondary_label = None

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.NoDropShadowWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.installEventFilter(self)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )

        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self._opacity = 1.0
        self.fade_in = QtCore.QPropertyAnimation(
            effect,
            QtCore.QByteArray('opacity'.encode('utf-8'))
        )
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setDuration(200)
        self.fade_in.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self.fade_out = QtCore.QPropertyAnimation(
            effect,
            QtCore.QByteArray('opacity'.encode('utf-8'))
        )
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.setDuration(200)
        self.fade_out.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self._clicked_button = None

        self.set_labels(args)
        self.set_buttons(kwargs)

        self._create_ui()
        self._connect_signals()

    def clicked_button(self):
        return self._clicked_button

    def set_clicked_button(self, v):
        self._clicked_button = v

    def _get_label(self, parent=None, size=common.size(common.FontSizeSmall)):
        label = QtWidgets.QLabel(parent=parent)
        label.setOpenExternalLinks(True)
        label.setTextFormat(QtCore.Qt.RichText)
        label.setTextInteractionFlags(
            QtCore.Qt.LinksAccessibleByMouse |
            QtCore.Qt.LinksAccessibleByKeyboard
        )
        label.setStyleSheet('padding: 0px;')
        label.setMargin(0)
        label.setIndent(0)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        label.setMinimumWidth(common.size(common.DefaultWidth) * 0.66)
        label.setMaximumWidth(common.size(common.DefaultWidth))
        label.setStyleSheet('font-size: {}px;'.format(size))
        return label

    def _get_row(self, vertical=False, parent=None):
        row = QtWidgets.QWidget(parent=parent)
        if vertical:
            QtWidgets.QVBoxLayout(row)
        else:
            QtWidgets.QHBoxLayout(row)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)
        parent.layout().addWidget(row, 1)
        return row

    def _create_ui(self):
        stylesheet = MESSAGE_BOX_STYLESHEET.format(
            SIZE=common.size(common.FontSizeLarge),
            FAMILY=common.font_db.primary_font(
                common.size(common.FontSizeMedium)
            )[0].family(),
            TEXT=common.rgb(self.secondary_color.darker(255)),
            TRANSPARENT=common.rgb(common.color(common.Transparent)),
        )
        self.setStyleSheet(stylesheet)

        QtWidgets.QHBoxLayout(self)
        o = common.size(common.WidthMargin)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        # Main Row
        main_row = self._get_row(parent=self)
        main_row.layout().setSpacing(o)

        label = self._get_label(parent=main_row)

        pixmap = images.ImageCache.get_rsc_pixmap(
            self.icon,
            self.secondary_color.lighter(150),
            common.size(common.HeightRow)
        )
        label.setPixmap(pixmap)
        label.setFixedWidth(common.size(common.HeightRow))
        label.setFixedHeight(common.size(common.HeightRow))
        main_row.layout().addWidget(label, 0)

        # Labels and buttons
        columns = self._get_row(vertical=True, parent=main_row)
        columns.layout().setSpacing(o)

        primary_row = self._get_row(parent=columns)
        columns.layout().addWidget(primary_row, 1)

        if self.primary_label:
            primary_row.layout().addWidget(self.primary_label)

        if self.secondary_label:
            secondary_row = self._get_row(parent=columns)
            secondary_row.layout().addWidget(self.secondary_label)

        if self.no_buttons is True:
            return

        if self.buttons:
            buttons_row = self._get_row(parent=columns)
            for idx, button in enumerate(self.buttons):
                if idx == 0:
                    buttons_row.layout().addWidget(button, 2)
                else:
                    buttons_row.layout().addWidget(button, 1)

    def _connect_signals(self):
        for button in buttons:
            k = button.lower() + '_button'

            if not hasattr(self, k):
                continue

            widget = getattr(self, k)
            widget.clicked.connect(
                functools.partial(self.buttonClicked.emit, button)
            )

            if button in (OkButton, YesButton, SaveButton):
                widget.clicked.connect(
                    lambda: self.done(QtWidgets.QDialog.Accepted)
                )
            if button in (CancelButton, NoButton):
                widget.clicked.connect(
                    lambda: self.done(QtWidgets.QDialog.Rejected)
                )

        self.buttonClicked.connect(self.set_clicked_button)

    def set_labels(self, args):
        if len(args) >= 1 and isinstance(args[0], str):
            self.primary_label = self._get_label(
                parent=self, size=common.size(common.FontSizeLarge) - 2
            )
            self.primary_label.setText(args[0])
        else:
            raise ValueError('Primary Label must be {}'.format(str))
        if len(args) >= 2:
            self.secondary_label = self._get_label(parent=self)
            self.secondary_label.setText(args[1])
            self.secondary_label.setTextFormat(QtCore.Qt.PlainText)

    def set_buttons(self, kwargs):
        if 'no_buttons' in kwargs and kwargs['no_buttons'] is True:
            self.no_buttons = kwargs['no_buttons']
            self.buttons = []
            return

        color = QtGui.QColor(self.primary_color)
        color.setAlphaF(0.5)

        stylesheet = PUSH_BUTTON_STYLESHEET.format(
            px=common.size(common.FontSizeSmall),
            i=common.size(common.WidthIndicator),
            s=common.size(common.HeightSeparator),
            c=common.rgb(self.secondary_color.lighter(150)),
            p=common.rgb(color),
            pl=common.rgb(self.primary_color.lighter(120)),
            pd=common.rgb(self.primary_color.darker(120)),
            SELECTED_TEXT=common.rgb(common.color(common.TextSelectedColor)),
        )
        if 'buttons' in kwargs and isinstance(kwargs['buttons'], (tuple, list)) and \
                kwargs['buttons']:
            for k in kwargs['buttons']:
                if k not in buttons:
                    raise ValueError(f'{k} is an invalid button')
                button = QtWidgets.QPushButton(k, parent=self)
                button.setStyleSheet(stylesheet)
                button.setFixedHeight(common.size(common.HeightRow))
                self.buttons.append(button)
                setattr(self, k.lower() + '_button', button)
            return

        button = QtWidgets.QPushButton(OkButton, parent=self)
        button.setStyleSheet(stylesheet)
        self.buttons = [button, ]
        setattr(self, OkButton.lower() + '_button', button)

    def sizeHint(self):
        return QtCore.QSize(
            common.size(common.DefaultHeight),
            common.size(common.DefaultHeight) * 0.5
            )

    def eventFilter(self, widget, event):
        if widget != self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)

            pen = QtGui.QPen(QtGui.QColor(self.secondary_color).darker(250))
            pen.setWidthF(common.size(common.HeightSeparator))
            painter.setPen(pen)

            painter.setBrush(self.secondary_color)

            o = common.size(common.HeightSeparator)
            rect = self.rect().adjusted(o, o, -o, -o)
            o = common.size(common.WidthIndicator) * 2
            painter.setOpacity(0.90)
            painter.drawRoundedRect(
                rect,
                o, o
            )
            painter.end()
            return True
        return False

    def open(self):
        common.center_window(self)
        super().open()
        if self.fade_in.state() != QtCore.QAbstractAnimation.Running:
            self.fade_in.start()
        while self.fade_in.state() != QtCore.QAbstractAnimation.Stopped:
            QtCore.QCoreApplication.processEvents()

    def exec_(self):
        common.center_window(self)
        self.show()
        if self.fade_in.state() != QtCore.QAbstractAnimation.Running:
            self.fade_in.start()
        while self.fade_in.state() != QtCore.QAbstractAnimation.Stopped:
            QtCore.QCoreApplication.processEvents()
        return super().exec_()

    def done(self, result):
        if self.fade_out.state() != QtCore.QAbstractAnimation.Running:
            self.fade_out.start()
        while self.fade_out.state() != QtCore.QAbstractAnimation.Stopped:
            QtCore.QCoreApplication.processEvents()
        return super().done(result)

    def hide(self):
        if self.fade_out.state() != QtCore.QAbstractAnimation.Running:
            self.fade_out.start()
        while self.fade_out.state() != QtCore.QAbstractAnimation.Stopped:
            QtCore.QCoreApplication.processEvents()
        super().hide()


class ErrorBox(MessageBox):
    """Informative message box used for notifying the user of an error.

    """
    primary_color = common.color(common.RedLightColor)
    secondary_color = common.color(common.RedColor)
    icon = 'close'


class OkBox(MessageBox):
    """Informative message box used for notifying the user of success.

    """
    primary_color = common.color(common.GreenLightColor)
    secondary_color = common.color(common.GreenAltColor)
    icon = 'check'


class Label(QtWidgets.QLabel):
    def __init__(
            self, text, color=common.color(common.TextSecondaryColor), parent=None
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
                    common.size(common.FontSizeSmall),
                    common.font_db.secondary_font(
                        common.size(common.FontSizeMedium)
                    )[0].family()
                )
            )
        else:
            self.setStyleSheet(
                'color: {}; font-size: {}px; font-family: "{}"'.format(
                    common.rgb(self.color),
                    common.size(common.FontSizeSmall),
                    common.font_db.secondary_font(
                        common.size(common.FontSizeMedium)
                    )[0].family()
                )
            )
        self.update()

    def enterEvent(self, event):
        self._set_stylesheet(True)

    def leaveEvent(self, event):
        self._set_stylesheet(False)

    def showEvent(self, event):
        self._set_stylesheet(False)


class LineEdit(QtWidgets.QLineEdit):
    """Custom line edit widget with a single underline."""

    def __init__(self, parent=None):
        super(LineEdit, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.setAlignment(QtCore.Qt.AlignLeft)


class PaintedButton(QtWidgets.QPushButton):
    """Custom button class."""

    def __init__(
            self, text, height=common.size(common.HeightRow), width=None, parent=None
    ):
        super(PaintedButton, self).__init__(text, parent=parent)
        if height:
            self.setFixedHeight(height)
        if width:
            self.setFixedWidth(width)

    def paintEvent(self, event):
        """Paint event for smooth font display."""
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

        painter.setBrush(common.color(common.BackgroundDarkColor))
        _color = QtGui.QColor(common.color(common.SeparatorColor))
        _color.setAlpha(150)
        pen = QtGui.QPen(_color)
        pen.setWidthF(common.size(common.HeightSeparator))
        painter.setPen(pen)

        o = common.size(common.HeightSeparator)
        rect = self.rect().adjusted(o, o, -o, -o)

        o = common.size(common.WidthIndicator) * 1.5
        painter.drawRoundedRect(rect, o, o)

        if focus:
            painter.setBrush(QtCore.Qt.NoBrush)
            pen = QtGui.QPen(common.color(common.BlueColor))
            pen.setWidthF(common.size(common.HeightSeparator))
            painter.setPen(pen)
            painter.drawRoundedRect(rect, o, o)

        rect = QtCore.QRect(self.rect())
        center = rect.center()
        rect.setWidth(rect.width() - (common.size(common.WidthIndicator) * 2))
        rect.moveCenter(center)

        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.size(common.FontSizeMedium))[0],
            rect,
            self.text(),
            QtCore.Qt.AlignCenter,
            common.color(common.TextColor)
        )

        painter.end()


class PaintedLabel(QtWidgets.QLabel):
    """QLabel used for static aliased label."""

    def __init__(
            self, text, color=common.color(common.TextColor),
            size=common.size(common.FontSizeMedium),
            parent=None
    ):
        super(PaintedLabel, self).__init__(text, parent=parent)
        self._size = size
        self._color = color
        self._text = text
        self.update_size()

    def update_size(self):
        font, metrics = common.font_db.primary_font(self._size)
        self.setFixedHeight(metrics.height())
        self.setFixedWidth(
            metrics.horizontalAdvance(self._text) +
            common.size(common.WidthIndicator) * 2
            )

    def paintEvent(self, event):
        """Custom paint event to use the aliased paint method."""
        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        painter = QtGui.QPainter()
        painter.begin(self)

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        pressed = option.state & QtWidgets.QStyle.State_Sunken
        focus = option.state & QtWidgets.QStyle.State_HasFocus
        disabled = not self.isEnabled()

        o = 1.0 if hover else 0.8
        o = 0.3 if disabled else 1.0
        painter.setOpacity(o)

        rect = self.rect()
        rect.setLeft(rect.left() + common.size(common.WidthIndicator))
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(self._size)[0],
            self.rect(),
            self.text(),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            self._color
        )
        painter.end()

    def leaveEvent(self, event):
        self.update()

    def enterEvent(self, event):
        self.update()


class ClickableIconButton(QtWidgets.QLabel):
    """A utility class for creating a square icon button.

    Args:
        pixmap (str): The name of the resource file without the extension.
        colors (tuple(QColor, QColor)): A tuple of QColors, for enabled and
        disabled states.
        size (int): The value for width and height.
        description (str): A user readable description of the action the button
        performs.
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
        super(ClickableIconButton, self).__init__(parent=parent)

        self._pixmap = pixmap
        self._size = size
        self._state = state

        self._on_color = colors[0]
        self._off_color = colors[1]

        self.setStatusTip(description)
        self.setToolTip(description)
        self.setWhatsThis(description)

        self.setFixedSize(QtCore.QSize(size, size))
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.setAttribute(QtCore.Qt.WA_NoBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.clicked.connect(self.action)
        self.clicked.connect(self.update)

    @QtCore.Slot()
    def action(self):
        pass

    def mouseReleaseEvent(self, event):
        """Only triggered when the left buttons is pressed."""
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        self.doubleClicked.emit()

    def enterEvent(self, event):
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def pixmap(self):
        if not self.isEnabled():
            return images.ImageCache.get_rsc_pixmap(
                self._pixmap, self._off_color, self._size
            )
        if self.state():
            return images.ImageCache.get_rsc_pixmap(
                self._pixmap, self._on_color, self._size
            )
        return images.ImageCache.get_rsc_pixmap(
            self._pixmap, self._off_color, self._size
        )

    def state(self):
        return self._state

    def contextMenuEvent(self, event):
        pass

    def paintEvent(self, event):
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
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
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
    def set_message(self, message):
        if message == self._message:
            return

        self._message = message
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

        o = common.size(common.WidthMargin)
        rect = self.rect().adjusted(o, o, -o, -o)
        text = QtGui.QFontMetrics(self.font()).elidedText(
            message,
            QtCore.Qt.ElideMiddle,
            rect.width(),
        )
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.SeparatorColor))
        painter.setOpacity(0.5)
        painter.drawRect(self.rect())

        painter.setOpacity(1.0)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(common.color(common.TextSecondaryColor))
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

        o = common.size(common.WidthIndicator)
        rect = option.rect.adjusted(o * 0.5, o * 0.5, -o * 0.5, -o * 0.5)

        # Background
        _o = 0.6 if hover else 0.2
        _o = 0.1 if disabled else _o
        _o = 1.0 if selected else _o
        painter.setOpacity(_o)
        painter.setPen(QtCore.Qt.NoPen)

        if selected or hover:
            painter.setBrush(common.color(common.BackgroundLightColor))
        else:
            painter.setBrush(common.color(common.SeparatorColor))
        painter.drawRoundedRect(rect, o, o)

        if focus:
            painter.setBrush(QtCore.Qt.NoBrush)
            pen = QtGui.QPen(common.color(common.BlueColor))
            pen.setWidthF(common.size(common.HeightSeparator))
            painter.setPen(pen)
            painter.drawRoundedRect(rect, o, o)

        # Checkbox
        rect = QtCore.QRect(rect)
        rect.setWidth(rect.height())
        center = rect.center()
        h = common.size(common.WidthMargin)
        rect.setSize(QtCore.QSize(h, h))
        rect.moveCenter(center)

        h = rect.height() / 2.0
        painter.setPen(QtCore.Qt.NoPen)

        _ = painter.setOpacity(1.0) if hover else painter.setOpacity(0.9)

        if checkable and checked:
            pixmap = images.ImageCache.get_rsc_pixmap(
                'check', common.color(common.GreenColor), rect.height()
            )
            painter.drawPixmap(rect, pixmap)
        elif checkable and not checked:
            pixmap = images.ImageCache.get_rsc_pixmap(
                'close', common.color(common.BackgroundColor), rect.height()
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
        else:
            rect.setWidth(o * 2)

        # Label
        font, metrics = common.font_db.primary_font(
            common.size(common.FontSizeSmall)
        )

        color = common.color(common.TextColor)
        color = common.color(common.TextSelectedColor) if selected else color
        color = common.color(common.TextColor) if checked else color

        painter.setBrush(color)

        x = rect.right() + common.size(common.WidthIndicator) * 3
        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            option.rect.width() - x - common.size(common.WidthIndicator),
        )

        y = option.rect.center().y() + (metrics.ascent() / 2.0)

        path = QtGui.QPainterPath()
        path.addText(x, y, font, text)

        if checkable and not checked:
            painter.setOpacity(0.5)
        painter.drawPath(path)


class ListWidget(QtWidgets.QListWidget):
    """A custom list widget used to display selectable item.

    """
    progressUpdate = QtCore.Signal(str)
    resized = QtCore.Signal(QtCore.QSize)

    def __init__(self, default_message='No items', parent=None):
        super().__init__(parent=parent)
        if not self.parent():
            common.set_custom_stylesheet(self)

        self.default_message = default_message

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
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self.overlay = ListOverlayWidget(parent=self.viewport())
        self.overlay.show()

    def _connect_signals(self):
        self.resized.connect(self.overlay.resize)
        self.progressUpdate.connect(self.overlay.set_message)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def toggle(self, item):
        if not item.flags() & QtCore.Qt.ItemIsUserCheckable:
            return
        if item.checkState() == QtCore.Qt.Unchecked:
            item.setCheckState(QtCore.Qt.Checked)
            return
        item.setCheckState(QtCore.Qt.Unchecked)

    def addItem(
            self, label, icon=None, color=common.color(common.TextSecondaryColor)
    ):
        if isinstance(label, QtWidgets.QListWidgetItem):
            return super().addItem(label)

        _, metrics = common.font_db.primary_font(
            common.size(common.FontSizeSmall)
        )
        width = metrics.horizontalAdvance(
            label
        ) + common.size(common.HeightRow) + common.size(common.WidthMargin)
        item = QtWidgets.QListWidgetItem(label)

        size = QtCore.QSize(width, common.size(common.HeightRow))
        item.setData(QtCore.Qt.SizeHintRole, size)

        if icon:
            item.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            )
            pixmap = images.ImageCache.get_rsc_pixmap(
                icon,
                color,
                common.size(common.HeightRow) -
                (common.size(common.WidthIndicator) * 2)
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
    progressUpdate = QtCore.Signal(str)
    resized = QtCore.Signal(QtCore.QSize)

    def __init__(self, default_message='No items', parent=None):
        super().__init__(parent=parent)
        if not self.parent():
            common.set_custom_stylesheet(self)

        self.default_message = default_message

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
        self.setItemDelegate(ListWidgetDelegate(parent=self))
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self.setModel(QtCore.QSortFilterProxyModel(parent=self))
        self.model().setSourceModel(QtGui.QStandardItemModel(parent=self))
        self.model().sourceModel().setColumnCount(1)
        self.model().setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.overlay = ListOverlayWidget(parent=self.viewport())
        self.overlay.show()

    def _connect_signals(self):
        self.resized.connect(self.overlay.resize)
        self.progressUpdate.connect(self.overlay.set_message)

    @QtCore.Slot(QtGui.QStandardItem)
    def toggle(self, item):
        if not item.flags() & QtCore.Qt.ItemIsUserCheckable:
            return
        if item.checkState() == QtCore.Qt.Unchecked:
            item.setCheckState(QtCore.Qt.Checked)
            return
        item.setCheckState(QtCore.Qt.Unchecked)

    def addItem(self, v, icon=None, color=common.color(common.TextSecondaryColor)):
        common.check_type(v, (str, QtGui.QStandardItem))
        common.check_type(icon, (QtGui.QPixmap, QtGui.QIcon, str, None))
        common.check_type(color, (QtGui.QColor, None))

        if isinstance(v, QtGui.QStandardItem):
            self.model().sourceModel().appendRow(v)
            return

        _, metrics = common.font_db.primary_font(
            common.size(common.FontSizeSmall)
        )
        width = metrics.horizontalAdvance(v) + common.size(
            common.HeightRow
        ) + common.size(common.WidthMargin)

        item = QtGui.QStandardItem(v)

        size = QtCore.QSize(width, common.size(common.HeightRow))
        item.setData(size, role=QtCore.Qt.SizeHintRole)

        if isinstance(icon, str):
            item.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            )
            pixmap = images.ImageCache.get_rsc_pixmap(
                icon,
                color,
                common.size(common.HeightRow) -
                (common.size(common.WidthIndicator) * 2)
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
        color=common.color(common.TextDisabledColor),
        size=common.size(common.HeightRow),
        opacity=1.0,
        resource=common.GuiResource
):
    """Utility method for retuning a QIcon to use in the context menu.

    Args:
        name (str): The name of the icon.
        color (QtGui.QColor): The color of the icon.
        size (QtGui.QSize): The size of the icon.
        opacity (float): The opacity of the icon.
        resource (str): The resource source for the icon.

    Returns:
        QtGui.QIcon: The QIcon.

    """
    k = f'{name}/{color}/{size}/{opacity}/{resource}'

    if k in common.image_cache[images.IconType]:
        return common.image_cache[images.IconType][k]

    icon = QtGui.QIcon()

    pixmap = images.ImageCache.get_rsc_pixmap(
        name, color, size, opacity=opacity, resource=resource
    )
    icon.addPixmap(pixmap, mode=QtGui.QIcon.Normal)

    _c = common.color(common.TextSelectedColor) if color else None
    pixmap = images.ImageCache.get_rsc_pixmap(
        name, _c, size, opacity=opacity, resource=resource
    )
    icon.addPixmap(pixmap, mode=QtGui.QIcon.Active)
    icon.addPixmap(pixmap, mode=QtGui.QIcon.Selected)

    _c = common.color(common.SeparatorColor) if color else None
    pixmap = images.ImageCache.get_rsc_pixmap(
        'close', _c, size, opacity=0.5, resource=common.GuiResource
    )

    icon.addPixmap(pixmap, mode=QtGui.QIcon.Disabled)

    common.image_cache[images.IconType][k] = icon
    return common.image_cache[images.IconType][k]


def get_group(parent=None, vertical=True, margin=common.size(common.WidthMargin)):
    """Utility method for creating a group widget.

    Returns:
        QGroupBox: group widget.

    """
    grp = QtWidgets.QGroupBox(parent=parent)
    grp.setMinimumWidth(common.size(common.DefaultWidth) * 0.3)

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
        label, color=common.color(common.TextSecondaryColor), parent=None,
        padding=common.size(common.WidthMargin),
        height=common.size(common.HeightRow), cls=None,
        vertical=False
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
    w.layout().setSpacing(common.size(common.WidthIndicator))
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
            size=common.size(common.FontSizeSmall),
            color=color,
            parent=parent
        )
        l.setFixedWidth(common.size(common.WidthMargin) * 8.6667)
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
    label.setFixedHeight(common.size(common.HeightRow))
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
        text, label=' ', color=common.color(common.TextSecondaryColor),
        padding=common.size(common.WidthMargin), parent=None
):
    """Utility method for adding a description field.

    Returns:
        QLabel: the added QLabel.

    """
    row = add_row(label, padding=padding, height=None, parent=parent)
    row.layout().setSpacing(0)

    label = Label(text, color=color, parent=parent)
    row.layout().addWidget(label, 1)
    parent.layout().addWidget(row, 1)
    return row


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
            self, label, data, thumbnail, height=common.size(common.HeightRow) * 2,
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
        self.setScaledContents(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self.setMinimumSize(QtCore.QSize(self._height, self._height))

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
        painter.setPen(common.color(common.TextColor))
        rect = self.rect()
        rect.moveTopLeft(rect.topLeft() + QtCore.QPoint(1, 1))

        font, _ = common.font_db.primary_font(common.size(common.FontSizeMedium))

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
            common.color(common.TextSelectedColor),
        )

        painter.end()


class GalleryWidget(QtWidgets.QDialog):
    """A generic gallery widget used to let the user pick an item.

    Attributes:
        itemSelected (Signal -> str): Emitted when the user clicks the item.

    """
    itemSelected = QtCore.Signal(str)

    def __init__(
            self, columns=5, item_height=common.size(common.HeightRow) * 2,
            parent=None
    ):
        super().__init__(parent=parent)

        self.scroll_area = None
        self.columns = columns
        self._item_height = item_height

        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Select Item')

        self._create_ui()
        self.init_data()

    def _create_ui(self):
        if not self.parent():
            common.set_custom_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        o = common.size(common.WidthMargin)

        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        row = add_row(
            None, height=common.size(common.HeightRow), padding=None, parent=self
        )
        label = PaintedLabel(
            'Select an item',
            color=common.color(common.TextColor),
            size=common.size(common.FontSizeLarge),
            parent=self
        )
        row.layout().addWidget(label)

        widget = QtWidgets.QWidget(parent=self)
        widget.setStyleSheet(
            'background-color: {}'.format(
                common.rgb(common.color(common.SeparatorColor))
            )
        )

        self.setMinimumWidth(
            (common.size(common.WidthIndicator) * 2) +
            (common.size(common.WidthMargin) * 2) +
            (common.size(common.WidthIndicator) * (self.columns - 1)) +
            self._item_height * self.columns
        )
        self.setMaximumWidth(
            (common.size(common.WidthIndicator) * 2) +
            (common.size(common.WidthMargin) * 2) +
            (common.size(common.WidthIndicator) * (self.columns - 1)) +
            self._item_height * self.columns
        )
        self.setMinimumHeight(
            (common.size(common.WidthIndicator) * 2) +
            (common.size(common.WidthMargin) * 2) +
            self._item_height
        )
        self.setMaximumHeight(
            (common.size(common.WidthIndicator) * 2) +
            (common.size(common.WidthMargin) * 2) +
            (common.size(common.WidthIndicator) * 9) +
            (self._item_height * 10)
        )

        QtWidgets.QGridLayout(widget)
        widget.layout().setAlignment(QtCore.Qt.AlignCenter)
        widget.layout().setContentsMargins(
            common.size(common.WidthIndicator),
            common.size(common.WidthIndicator),
            common.size(common.WidthIndicator),
            common.size(common.WidthIndicator)
        )
        widget.layout().setSpacing(common.size(common.WidthIndicator))

        self.scroll_area = QtWidgets.QScrollArea(parent=self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(widget)

        self.layout().addWidget(self.scroll_area, 1)

    def init_data(self):
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

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(common.color(common.SeparatorColor))
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 150))
        pen.setWidth(common.size(common.HeightSeparator))
        painter.setPen(pen)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        o = common.size(common.WidthIndicator) * 2.0
        painter.drawRoundedRect(
            self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o)),
            o, o
        )
        painter.end()

    def showEvent(self, event):
        if not self.parent():
            common.center_window(self)
