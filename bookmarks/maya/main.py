# -*- coding: utf-8 -*-
"""This module defines :class:`MayaWidget`, Bookmarks' container widget.

"""
import functools
import re

import maya.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI
import maya.app.general.mayaMixin as mayaMixin
import maya.cmds as cmds
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
        common.maya_button_widget = MayaButtonWidget(
            common.size(common.HeightRow * 2)
        )
        common.maya_button_widget.show()
        return

    parent = shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)
    if not parent:
        common.maya_button_widget = MayaButtonWidget(
            common.size(common.HeightRow * 2)
        )
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
        if re.match(f'{common.product}_.*WorkspaceControl', widget.objectName()):
            continue

        match = re.match(f'{common.product}_.*', widget.objectName())
        if not match:
            continue

        # We have found our instance and now we'll restore/toggle its state
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
            # We'll toggle the visibilty
            state = widget.parent().isVisible()
            widget.setVisible(not state)


def init_maya_widget():
    """Initializes the maya widget.
    Usually the Maya plugin will call this method.

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
            topleft = QtCore.QPoint(
                min(x),
                min(y)
            )
            size = QtCore.QSize(w - min(x), h - min(y))
            geo = QtCore.QRect(topleft, size)
        except:
            pass

        self.setGeometry(geo)

    def paintEvent(self, event):
        """Paint the capture window."""
        # Convert click and current mouse positions to local space.
        mouse_pos = self.mapFromGlobal(common.cursor.pos())
        painter = QtGui.QPainter()
        painter.begin(self)

        # Draw background. Aside from aesthetics, this makes the full
        # tool region accept mouse events.
        painter.setBrush(QtGui.QColor(0, 0, 0, 255))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())

        for panel in self.panels.values():
            _mouse_pos = panel.mapFromGlobal(common.cursor.pos())

            if not panel.rect().contains(_mouse_pos):
                self.setCursor(QtCore.Qt.ArrowCursor)
                continue

            self.setCursor(QtCore.Qt.PointingHandCursor)
            topleft = panel.mapToGlobal(panel.rect().topLeft())
            topleft = self.mapFromGlobal(topleft)
            bottomright = panel.mapToGlobal(panel.rect().bottomRight())
            bottomright = self.mapFromGlobal(bottomright)

            capture_rect = QtCore.QRect(topleft, bottomright)
            pen = QtGui.QPen(common.color(common.GreenColor))
            pen.setWidth(common.size(common.HeightSeparator) * 2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(capture_rect)

            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.color(common.GreenColor))
            painter.setOpacity(0.3)
            painter.drawRect(capture_rect)

        painter.end()

    def keyPressEvent(self, event):
        """Cancel the capture on keypress."""
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()

    def mouseReleaseEvent(self, event):
        """Finalise the capture."""
        if not isinstance(event, QtGui.QMouseEvent):
            return

        for panel, widget in self.panels.items():
            mouse_pos = widget.mapFromGlobal(common.cursor.pos())
            if widget.rect().contains(mouse_pos):
                self.panel = panel
                self.done(QtWidgets.QDialog.Accepted)
                self.panel = panel
                return

        self.done(QtWidgets.QDialog.Rejected)

    def mouseMoveEvent(self, event):
        """Constrain and resize the capture window."""
        self.update()

    def showEvent(self, event):
        self._fit_screen_geometry()
        self.fade_in.start()


class MayaButtonWidget(ui.ClickableIconButton):
    """A small control buttons used by the Maya plugin usually docked
    under the Maya Toolbox.

    """
    ContextMenu = contextmenu.MayaButtonWidgetContextMenu

    def __init__(self, size, parent=None):
        super(MayaButtonWidget, self).__init__(
            'icon',
            (None, None),
            size,
            description=f'Click to toggle {common.product.title()}.',
            parent=parent
        )
        self.setObjectName('BookmarksMayaButton')
        self.setAutoFillBackground(False)
        self.setAttribute(QtCore.Qt.WA_NoBackground, False)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
    
        self._connect_signals()
        self.init_shortcuts()
    
    def init_shortcuts(self):
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence('Ctrl+Alt+Shift+B'), self
        )
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut.activated.connect(show)
        
        from . import viewport
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
            pixmap = images.ImageCache.get_rsc_pixmap(
                'icon', None, self.width()
            )
            painter.setOpacity(1.0)
        else:
            pixmap = images.ImageCache.get_rsc_pixmap(
                'icon_bw', None, self.width()
            )
            painter.setOpacity(0.80)

        rect = self.rect()
        center = rect.center()
        o = common.size(common.WidthIndicator) * 2
        rect = rect.adjusted(0, 0, -o, -o)
        rect.moveCenter(center)

        painter.drawRoundRect(rect, o, o)

        painter.drawPixmap(rect, pixmap, pixmap.rect())
        painter.end()

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def contextMenuEvent(self, event):
        """Context menu event."""
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

        self.setWindowTitle(common.product)
        common.set_stylesheet(self)

        # Rename object
        o = self.objectName().replace(
            self.__class__.__name__, common.product
        )
        self.setObjectName(o)

        self._create_UI()
        self.setFocusProxy(common.main_widget.stacked_widget)
        common.main_widget.sizeHint = self.sizeHint

        self.workspace_timer = common.Timer(parent=self)
        self.workspace_timer.setSingleShot(False)
        self.workspace_timer.setInterval(1000)
        self.workspace_timer.timeout.connect(actions.set_workspace)

        common.main_widget.initialized.connect(
            lambda: common.main_widget.layout().setContentsMargins(0, 0, 0, 0)
        )

        common.main_widget.initialized.connect(self._connect_signals)
        common.main_widget.initialized.connect(self.context_callbacks)
        common.main_widget.initialized.connect(actions.set_workspace)
        common.main_widget.initialized.connect(self.workspace_timer.start)

    def _create_UI(self):
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

    @QtCore.Slot()
    def active_changed(self):
        """Slot called when an active asset changes.

        """
        v = common.settings.value(
            common.SettingsSection,
            common.WorkspaceWarningsKey
        )
        v = QtCore.Qt.Unchecked if v is None else v

        # Do nothing if explicitly set not to show warnings
        if v == QtCore.Qt.Checked:
            return

        # We will get a warning when we change to a new bookmark item. Whilst
        # technically correct, it is counterintuitive to be warned of a direct
        # action just performed
        assets_model = common.main_widget.assets_widget.model().sourceModel()
        if not assets_model.active_index().isValid():
            return

        workspace_info = QtCore.QFileInfo(
            cmds.workspace(q=True, expandName=True)
        )

        ui.MessageBox(
            f'Workspace changed\n The new workspace is {workspace_info.path()}',
            'If you didn\'t expect this message, it is possible your current '
            'project was changed by Bookmarks, perhaps in another instance of Maya.'
        ).open()

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

        # callback = OpenMaya.MSceneMessage.addCallback(
        #     OpenMaya.MSceneMessage.kBeforeSave, self.save_warning)
        # self._callbacks.append(callback)

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
        """Shows the custom context menu."""
        width = parent.viewport().geometry().width()
        width = (width * 0.5) if width > common.size(common.DefaultWidth) else width
        width = width - common.size(common.WidthIndicator)

        widget = contextmenu.MayaWidgetContextMenu(index, parent=parent)
        if index.isValid():
            rect = parent.visualRect(index)
            widget.move(
                parent.viewport().mapToGlobal(rect.bottomLeft()).x(),
                parent.viewport().mapToGlobal(rect.bottomLeft()).y(),
            )
        else:
            widget.move(common.cursor.pos())

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.size(common.WidthIndicator), widget.y())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    @common.error
    @common.debug
    def show(self, *args, **kwargs):
        kwargs = {
            'dockable': True,
            'allowedArea': None,
            'retain': True,
            'width': common.size(common.DefaultWidth) * 0.5,
            'height': common.size(common.DefaultHeight) * 0.5
        }

        try:
            super().show(**kwargs)
        except:
            kwargs['dockable'] = False
            super().show(**kwargs)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(common.color(common.SeparatorColor))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())
        painter.end()

    def sizeHint(self):
        return QtCore.QSize(
            common.size(common.DefaultWidth) * 0.5,
            common.size(common.DefaultHeight) * 0.5
        )
