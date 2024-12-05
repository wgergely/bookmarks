"""This module defines :class:`MayaWidget`, Bookmarks' container widget.

"""
import functools
import re

try:
    import maya.OpenMaya as OpenMaya
    import maya.OpenMayaUI as OpenMayaUI
    import maya.app.general.mayaMixin as mayaMixin
    import maya.cmds as cmds
except ImportError:
    raise ImportError('Could not find the Maya modules.')

import shiboken2
from PySide2 import QtWidgets, QtGui, QtCore

from . import actions
from . import contextmenu
from .. import common
from .. import images
from .. import ui


@common.error
@common.debug
def init_tool_button(*args, **kwargs):
    """Finds the built-in Toolbox menu and embeds our custom control-button.

    """

    ptr = OpenMayaUI.MQtUtil.findControl('ToolBox')

    if ptr is None:
        common.maya_button_widget = MayaButtonWidget(common.Size.RowHeight(2.0))
        common.maya_button_widget.show()
        return

    parent = shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)
    if not parent:
        common.maya_button_widget = MayaButtonWidget(common.Size.RowHeight(2.0))
        common.maya_button_widget.show()
        return

    common.maya_button_widget = MayaButtonWidget(parent.width())
    parent.layout().addWidget(common.maya_button_widget, 0)
    common.maya_button_widget.adjustSize()
    common.maya_button_widget.update()
    common.maya_button_widget.show()


@QtCore.Slot()
@common.error
def show():
    """Main function to show :class:`MayaWidget` inside Maya as a dockable
    widget.

    The function will create :class:`MayaWidget` if it doesn't yet exist and dock
    it to the bar where AttributeEditor is found. If it exists it will get the
    existing instance and show it if not currently visible, hide it if visible.

    """
    # We will check if there's already a _MayaWidget_ instance
    for widget in QtWidgets.QApplication.instance().allWidgets():
        # Skipping workspaceControls objects, just in case there's a name conflict
        # between what the parent().objectName() and this method yields
        try:
            widget.objectName()
        except:
            continue

        if re.match(f'{common.product}_.*WorkspaceControl', widget.objectName()):
            continue

        match = re.match(f'{common.product}_.*', widget.objectName())
        if not match:
            continue

        # We have found our instance, and now we'll restore/toggle its state
        # The widget is visible and is currently a floating window
        if not widget.parent():
            widget.setVisible(not widget.isVisible())
            return

        # The widget is docked with a workspace control object
        workspace_control = widget.parent().objectName()
        if cmds.workspaceControl(workspace_control, q=True, exists=True):
            visible = cmds.workspaceControl(
                workspace_control, q=True, visible=True
            )
            if cmds.workspaceControl(workspace_control, q=True, floating=True):
                cmds.workspaceControl(
                    workspace_control, e=True, visible=not visible
                )
                return

            state = cmds.workspaceControl(
                workspace_control, q=True, collapse=True
            )

            if state is None:
                cmds.workspaceControl(
                    workspace_control, e=True, tabToControl=('AttributeEditor', -1)
                )
                cmds.workspaceControl(workspace_control, e=True, visible=True)
                cmds.workspaceControl(
                    workspace_control, e=True, collapse=False
                )
            elif not widget.parent().isVisible():
                cmds.workspaceControl(workspace_control, e=True, visible=True)
                cmds.workspaceControl(
                    workspace_control, e=True, collapse=False
                )
            elif state is False:
                cmds.workspaceControl('AttributeEditor', e=True, visible=True)
                cmds.workspaceControl(
                    'AttributeEditor', e=True, collapse=False
                )
            elif state is True:
                cmds.workspaceControl(
                    workspace_control, e=True, collapse=True
                )
        else:
            # We'll toggle the visibility
            state = widget.parent().isVisible()
            widget.setVisible(not state)


def init_maya_widget():
    """Initializes the maya widget.
    Usually the Maya plugin will call this function.

    """
    if isinstance(common.maya_widget, MayaWidget):
        raise RuntimeError('Bookmarks is already initialized.')

    common.maya_widget = MayaWidget()
    common.maya_widget.show()

    # By default, the tab is docked just next to the attribute editor
    for widget in QtWidgets.QApplication.instance().allWidgets():
        match = re.match(
            f'{common.product}.*WorkspaceControl', widget.objectName()
        )

        if not match:
            continue

        # Defer the execution, otherwise the widget does not dock properly
        func = functools.partial(
            cmds.workspaceControl,
            widget.objectName(),
            e=True,
            tabToControl=('AttributeEditor', -1)
        )
        cmds.evalDeferred(func)
        cmds.evalDeferred(widget.raise_)
        return


class PanelPicker(QtWidgets.QDialog):
    """Modal dialog used to select a visible modelPanel in Maya.

    """

    def __init__(self, parent=None):
        super(PanelPicker, self).__init__(parent=parent)

        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_in = QtCore.QPropertyAnimation(
            effect,
            QtCore.QByteArray('opacity'.encode('utf-8'))
        )
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(0.5)
        self.fade_in.setDuration(500)
        self.fade_in.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self._mouse_pos = None
        self._click_pos = None
        self._offset_pos = None

        self._capture_rect = QtCore.QRect()

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.setMouseTracking(True)
        self.installEventFilter(self)

        self.panels = {}
        self.panel = None

        panels = cmds.lsUI(panels=True)
        if not panels:
            return

        for panel in panels:
            if not cmds.modelPanel(panel, exists=True):
                continue
            ptr = OpenMayaUI.MQtUtil.findControl(panel)
            if not ptr:
                continue
            widget = shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)
            if not widget:
                continue
            if not widget.isVisible():
                continue
            self.panels[panel] = widget

    def _fit_screen_geometry(self):
        """Compute the union of all screen geometries, and resize to fit.

        """
        app = QtWidgets.QApplication.instance()
        geo = app.primaryScreen().geometry()
        x = []
        y = []
        w = 0
        h = 0

        try:
            for screen in app.screens():
                g = screen.geometry()
                x.append(g.topLeft().x())
                y.append(g.topLeft().y())
                w += g.width()
                h += g.height()
            top_left = QtCore.QPoint(
                min(x),
                min(y)
            )
            size = QtCore.QSize(w - min(x), h - min(y))
            geo = QtCore.QRect(top_left, size)
        except:
            pass

        self.setGeometry(geo)

    def paintEvent(self, event):
        """Event handler.

        """
        # Convert click and current mouse positions to local space.
        painter = QtGui.QPainter()
        painter.begin(self)

        # Draw background. Aside from aesthetics, this makes the full
        # tool region accept mouse events.
        painter.setBrush(QtGui.QColor(0, 0, 0, 255))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())

        for panel in self.panels.values():
            cursor = QtGui.QCursor()
            _mouse_pos = panel.mapFromGlobal(cursor.pos())

            if not panel.rect().contains(_mouse_pos):
                self.setCursor(QtCore.Qt.ArrowCursor)
                continue

            self.setCursor(QtCore.Qt.PointingHandCursor)
            top_left = panel.mapToGlobal(panel.rect().topLeft())
            top_left = self.mapFromGlobal(top_left)
            bottomright = panel.mapToGlobal(panel.rect().bottomRight())
            bottomright = self.mapFromGlobal(bottomright)

            capture_rect = QtCore.QRect(top_left, bottomright)
            pen = QtGui.QPen(common.Color.Green())
            pen.setWidth(common.Size.Separator(2.0))
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(capture_rect)

            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.Color.Green())
            painter.setOpacity(0.3)
            painter.drawRect(capture_rect)

        painter.end()

    def keyPressEvent(self, event):
        """Key press event handler.

        """
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()

    def mouseReleaseEvent(self, event):
        """Event handler.

        """
        if not isinstance(event, QtGui.QMouseEvent):
            return

        for panel, widget in self.panels.items():
            mouse_pos = event.pos()
            if widget.rect().contains(mouse_pos):
                self.panel = panel
                self.done(QtWidgets.QDialog.Accepted)
                self.panel = panel
                return

        self.done(QtWidgets.QDialog.Rejected)

    def mouseMoveEvent(self, event):
        """Event handler.

        """
        self.update()

    def showEvent(self, event):
        """Event handler.

        """
        self._fit_screen_geometry()
        self.fade_in.start()


class MayaButtonWidget(ui.ClickableIconButton):
    """A small control buttons used by the Maya plugin usually docked
    under the Maya Toolbox.

    """
    ContextMenu = contextmenu.MayaButtonWidgetContextMenu

    def __init__(self, size, parent=None):
        super().__init__(
            'icon',
            (None, None),
            size,
            description=f'Click to toggle {common.product.title()}.',
            parent=parent
        )
        self.setObjectName('BookmarksMayaButton')
        self.setAttribute(QtCore.Qt.WA_NoBackground, False)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self._connect_signals()
        self.init_shortcuts()

    def init_shortcuts(self):
        """Initializes the plugin shortcuts.

        """
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence('Ctrl+Alt+Shift+B'), self
        )
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut.activated.connect(show)

        shortcut1 = QtWidgets.QShortcut(
            QtGui.QKeySequence(f'Ctrl+Alt+Shift+1'), self
        )
        shortcut1.setAutoRepeat(False)
        shortcut1.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut1.activated.connect(
            functools.partial(actions.apply_viewport_preset, 'Show All Nodes')
        )
        shortcut2 = QtWidgets.QShortcut(
            QtGui.QKeySequence(f'Ctrl+Alt+Shift+2'), self
        )
        shortcut2.setAutoRepeat(False)
        shortcut2.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut2.activated.connect(
            functools.partial(actions.apply_viewport_preset, 'Animation Nodes')
        )
        shortcut3 = QtWidgets.QShortcut(
            QtGui.QKeySequence(f'Ctrl+Alt+Shift+3'), self
        )
        shortcut3.setAutoRepeat(False)
        shortcut3.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut3.activated.connect(
            functools.partial(actions.apply_viewport_preset, 'Show Mesh Nodes')
        )

    def _connect_signals(self):
        self.clicked.connect(show)

    def paintEvent(self, event):
        """Event handler.

        """
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 10))

        if hover:
            pixmap = images.rsc_pixmap(
                'icon', None, self.width()
            )
            painter.setOpacity(1.0)
        else:
            pixmap = images.rsc_pixmap(
                'icon_bw', None, self.width()
            )
            painter.setOpacity(0.80)

        rect = self.rect()
        center = rect.center()
        o = common.Size.Indicator(2.0)
        rect = rect.adjusted(0, 0, -o, -o)
        rect.moveCenter(center)

        painter.drawRoundRect(rect, o, o)

        painter.drawPixmap(rect, pixmap, pixmap.rect())
        painter.end()

    def enterEvent(self, event):
        """Event handler.

        """
        self.update()

    def leaveEvent(self, event):
        """Event handler.

        """
        self.update()

    def contextMenuEvent(self, event):
        """Event handler.

        """
        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier
        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit(event.pos())
            return

        widget = self.ContextMenu(parent=self)
        widget.move(self.mapToGlobal(self.rect().bottomLeft()))
        common.move_widget_to_available_geo(widget)
        widget.exec_()


class MayaWidget(mayaMixin.MayaQWidgetDockableMixin, QtWidgets.QWidget):
    """The main plugin widget.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._workspacecontrol = None
        self._callbacks = []  # Maya api callbacks

        self.setWindowTitle(common.product.title())
        common.set_stylesheet(self)

        # Rename object
        o = self.objectName().replace(
            self.__class__.__name__, common.product
        )
        self.setObjectName(o)

        # Timer to update the HUD
        self.hud_update_timer = common.Timer(parent=self)
        self.hud_update_timer.setSingleShot(False)
        self.hud_update_timer.setInterval(5000)

        # Timer to set the workspace and context periodically
        self.workspace_timer = common.Timer(parent=self)
        self.workspace_timer.setSingleShot(False)
        self.workspace_timer.setInterval(10000)

        self._create_ui()

        self.setFocusProxy(common.main_widget.stacked_widget)
        common.main_widget.sizeHint = self.sizeHint

        self.workspace_timer.timeout.connect(actions.set_workspace)
        self.hud_update_timer.timeout.connect(actions.add_hud)

        # Connect signals when the main widget is initialized
        common.main_widget.initialized.connect(lambda: common.main_widget.layout().setContentsMargins(0, 0, 0, 0))
        common.main_widget.initialized.connect(self._connect_signals)
        common.main_widget.initialized.connect(self.context_callbacks)
        common.main_widget.initialized.connect(self.workspace_timer.start)
        common.main_widget.initialized.connect(self.hud_update_timer.start)

        common.main_widget.initialized.connect(actions.set_workspace)
        common.main_widget.initialized.connect(actions.set_sg_context)
        common.main_widget.initialized.connect(actions.add_hud)

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().addWidget(common.main_widget)

    @QtCore.Slot()
    def _connect_signals(self):
        common.widget(common.BookmarkTab).customContextMenuRequested.connect(
            self.customFilesContextMenuEvent
        )

        common.widget(common.AssetTab).customContextMenuRequested.connect(
            self.customFilesContextMenuEvent
        )
        common.source_model(common.AssetTab).activeChanged.connect(
            actions.set_workspace
        )

        common.widget(common.FileTab).customContextMenuRequested.connect(
            self.customFilesContextMenuEvent
        )
        common.source_model(common.FileTab).modelReset.connect(
            actions.unmark_active
        )
        common.source_model(common.FileTab).modelReset.connect(
            actions.update_active_item
        )
        common.widget(common.FileTab).activated.connect(
            actions.execute
        )

        common.widget(common.FavouriteTab).customContextMenuRequested.connect(
            self.customFilesContextMenuEvent
        )
        common.widget(common.FavouriteTab).activated.connect(
            actions.execute
        )

        common.signals.assetItemActivated.connect(actions.set_workspace)
        common.signals.assetItemActivated.connect(actions.set_sg_context)
        common.signals.assetItemActivated.connect(actions.add_hud)

    def context_callbacks(self):
        """This method is called by the Maya plug-in when initializing
        and the callback needed by the maya plugin.

        """
        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kAfterOpen, actions.update_active_item
        )
        self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeOpen, actions.unmark_active
        )
        self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeNew, actions.unmark_active
        )
        self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kAfterSave, actions.save_warning
        )
        self._callbacks.append(callback)

    def remove_context_callbacks(self):
        """This method is called by the Maya plug-in when unloading."""
        for callback in self._callbacks:
            res = OpenMaya.MMessage.removeCallback(callback)
        self._callbacks = []

    @QtCore.Slot(QtCore.QModelIndex)
    @QtCore.Slot(QtCore.QObject)
    def customFilesContextMenuEvent(self, index, parent):
        """Event handler used to show a custom context menu.

        """
        width = parent.viewport().geometry().width()
        width = (width * 0.5) if width > common.Size.DefaultWidth() else width
        width = width - common.Size.Indicator()

        widget = contextmenu.PluginContextMenu(index, parent=parent)
        if index.isValid():
            rect = parent.visualRect(index)
            widget.move(
                parent.viewport().mapToGlobal(rect.bottomLeft()).x(),
                parent.viewport().mapToGlobal(rect.bottomLeft()).y(),
            )
        else:
            cursor = QtGui.QCursor()
            widget.move(cursor.pos())

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.Size.Indicator(), widget.y())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    @common.error
    @common.debug
    def show(self, *args, **kwargs):
        """Show method override.

        """
        kwargs = {
            'dockable': True,
            'allowedArea': None,
            'retain': True,
            'width': common.Size.DefaultWidth(0.5),
            'height': common.Size.DefaultHeight(0.5)
        }

        try:
            super().show(**kwargs)
        except:
            kwargs['dockable'] = False
            super().show(**kwargs)

    def paintEvent(self, event):
        """Event handler.

        """
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(common.Color.VeryDarkBackground())
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())
        painter.end()

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.Size.DefaultWidth(0.5),
            common.Size.DefaultHeight(0.5)
        )
