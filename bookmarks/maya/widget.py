# -*- coding: utf-8 -*-
# pylint: disable=E0401
"""This module defines Bookmarks's ``PluginWidget``, a dockable `mayaMixin`
widget that wraps MainWidget.

Usage:

    .. code-block:: python

        import bookmarks.maya.widget as mb
        mb.show()

"""
import re
import sys
import functools
import collections

import shiboken2
from PySide2 import QtWidgets, QtGui, QtCore

import maya.app.general.mayaMixin as mayaMixin

import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMaya as OpenMaya
import maya.cmds as cmds

from .. import log
from .. import common
from .. import ui
from .. import images
from .. import contextmenu
from .. import main
from .. import settings

from . import actions as maya_actions
from . import base as maya_base


object_name = 'm{}MainButton'.format(__name__.split('.')[0])


_button_instance = None
_instance = None


def instance():
    return _instance


def button_instance():
    return _button_instance


@common.error
@common.debug
def init_tool_button(*args, **kwargs):
    """Finds the built-in Toolbox menu and embeds a custom control-button.

    """
    global _button_instance
    ptr = OpenMayaUI.MQtUtil.findControl('ToolBox')
    if ptr is None:
        _button_instance = ToolButton(common.ASSET_ROW_HEIGHT())
        _button_instance.show()
        return

    widget = shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)
    if not widget:
        return

    _button_instance = ToolButton(widget.width())
    widget.layout().addWidget(_button_instance)
    _button_instance.adjustSize()
    _button_instance.update()


@QtCore.Slot()
@common.error
def show():
    """Main function to show ``PluginWidget`` inside Maya as a dockable
    widget.

    The function will create ``PluginWidget`` if it doesn't yet exist and
    dock it to the _AttributeEditor_. If it exists it will get the existing
    instance and show it if not currently visible, hide it if visible.

    Usage

        Run the following python code inside maya:

        .. code-block:: python

            import bookmarks.maya.widget as widget
            widget.show()

    """
    app = QtWidgets.QApplication.instance()

    # We will check if there's already a _PluginWidget_ instance
    for widget in app.allWidgets():
        # Skipping workspaceControls objects, just in case there's a name conflict
        # between what the parent().objectName() and this method yields
        if re.match('{}.*WorkspaceControl'.format(common.PRODUCT), widget.objectName()):
            continue

        match = re.match('{}.*'.format(common.PRODUCT), widget.objectName())

        # Skip invalid matches
        if not match:
            continue

        # We have found our instance and now we'll restore/toggle its state

        # The widget is visible and is currently a floating window
        if not widget.parent():
            state = widget.isVisible()
            widget.setVisible(not state)
            return

        # The widget is docked with a workspace control object
        workspace_control = widget.parent().objectName()
        if cmds.workspaceControl(workspace_control, q=True, exists=True):
            visible = cmds.workspaceControl(
                workspace_control, q=True, visible=True)
            if cmds.workspaceControl(workspace_control, q=True, floating=True):
                cmds.workspaceControl(
                    workspace_control, e=True, visible=not visible)
                return
            state = cmds.workspaceControl(
                workspace_control, q=True, collapse=True)
            if state is None:
                cmds.workspaceControl(
                    workspace_control, e=True, tabToControl=('AttributeEditor', -1))
                cmds.workspaceControl(workspace_control, e=True, visible=True)
                cmds.workspaceControl(
                    workspace_control, e=True, collapse=False)
                return
            if not widget.parent().isVisible():
                cmds.workspaceControl(workspace_control, e=True, visible=True)
                cmds.workspaceControl(
                    workspace_control, e=True, collapse=False)
                return
            if state is False:
                cmds.workspaceControl('AttributeEditor', e=True, visible=True)
                cmds.workspaceControl(
                    'AttributeEditor', e=True, collapse=False)
                return
            if state is True:
                cmds.workspaceControl(
                    workspace_control, e=True, collapse=True)
            return
        else:
            # We'll toggle the visibilty
            state = widget.parent().isVisible()
            widget.setVisible(not state)
        return

    # We should only get here if no PluginWidget instances were found elsewhere
    # Initializing PluginWidget
    global _instance
    _instance = PluginWidget()
    _instance.show()


    # By default, the tab is docked just next to the attribute editor
    for widget in app.allWidgets():
        match = re.match(
            '{}.*WorkspaceControl'.format(common.PRODUCT), widget.objectName())

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
        break


class PluginContextMenu(contextmenu.BaseContextMenu):
    def setup(self):
        self.apply_bookmark_settings_menu()

        self.separator()

        self.save_menu()

        self.separator()

        self.open_import_scene_menu()

        self.separator()

        self.export_sets_menu()

        self.separator()

        self.capture_menu()

    def apply_bookmark_settings_menu(self):
        server = settings.active(settings.ServerKey)
        job = settings.active(settings.JobKey)
        root = settings.active(settings.RootKey)
        asset = settings.active(settings.AssetKey)

        if not all((server, job, root, asset)):
            return

        self.menu['apply_settings'] = {
            'text': 'Apply scene settings...',
            'icon': self.get_icon('check', color=common.GREEN),
            'action': maya_actions.apply_settings
        }

    def save_menu(self):
        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

        self.menu[contextmenu.key()] = {
            'text': 'Save Scene...',
            'icon': self.get_icon('add_file', color=common.GREEN),
            'action': lambda: maya_actions.save_scene(increment=False)
        }
        if common.get_sequence(scene.fileName()):
            self.menu[contextmenu.key()] = {
                'text': 'Incremental Save...',
                'icon': self.get_icon('add_file'),
                'action': lambda: maya_actions.save_scene(increment=True)
            }

    def open_import_scene_menu(self):
        if not self.index.isValid():
            return

        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        _s = file_info.suffix().lower()
        if _s not in ('ma', 'mb', 'abc'):
            return

        maya_pixmap = self.get_icon('maya', color=None)
        maya_reference_pixmap = self.get_icon('maya_reference', color=None)

        self.menu[contextmenu.key()] = {
            'text': 'Open',
            'icon': maya_pixmap,
            'action': functools.partial(
                maya_actions.open_scene,
                file_info.filePath())
        }
        self.menu[contextmenu.key()] = {
            'text': 'Import',
            'icon': maya_pixmap,
            'action': functools.partial(
                maya_actions.import_scene,
                file_info.filePath(),
                reference=False
            )
        }
        self.menu[contextmenu.key()] = {
            'text': 'Reference',
            'icon': maya_reference_pixmap,
            'action': functools.partial(
                maya_actions.import_scene,
                file_info.filePath(),
                reference=True
            )
        }

    def export_sets_menu(self):
        formats = {
            'abc': {
                'action': maya_actions.export_set_to_abc,
            },
            'obj': {
                'action': maya_actions.export_set_to_obj,
            },
            'ass': {
                'action': maya_actions.export_set_to_ass,
            },
        }

        icon = self.get_icon('set', color=None)
        sets = maya_base.outliner_sets()
        keys = sorted(set(sets))


        kk = contextmenu.key()
        self.menu[kk] = collections.OrderedDict()
        self.menu[kk + ':icon'] = icon
        self.menu[kk + ':text'] = 'Export'

        for e in formats:
            k = contextmenu.key()
            self.menu[kk][k] = collections.OrderedDict()
            self.menu[kk][k + ':text'] = '*.{}: Export Timeline'.format(e.upper())
            for _k in keys:
                s = _k.replace(':', ' - ')
                self.menu[kk][k][contextmenu.key()] = {
                    'text': '{} ({} items)'.format(s, len(sets[_k])),
                    'icon': icon,
                    'action': functools.partial(
                        formats[e]['action'],
                        _k,
                        sets[_k],
                        frame=False
                    )
                }

            k = contextmenu.key()
            self.menu[kk][k] = collections.OrderedDict()
            self.menu[kk][k + ':icon'] = icon
            self.menu[kk][k + ':text'] = '*.{}: Export Current Frame'.format(e.upper())
            for _k in keys:
                s = _k.replace(':', ' - ')
                self.menu[kk][k][contextmenu.key()] = {
                    'text': '{} ({} items)'.format(s, len(sets[_k])),
                    'icon': icon,
                    'action': functools.partial(
                        formats[e]['action'],
                        _k,
                        sets[_k],
                        frame=True
                    )
                }

    def capture_menu(self):
        k = 'Capture Viewport'
        self.menu[k] = collections.OrderedDict()
        self.menu['{}:icon'.format(k)] = self.get_icon('capture_thumbnail')

        width = cmds.getAttr("defaultResolution.width")
        height = cmds.getAttr("defaultResolution.height")

        def size(n): return (int(int(width) * n), int(int(height) * n))

        for n in (1.0, 0.5, 0.25, 1.5, 2.0):
            self.menu[k]['capture{}'.format(n)] = {
                'text': 'Capture  |  @{}  |  {}x{}px'.format(n, *size(n)),
                'action': functools.partial(maya_actions.capture_viewport, size=n),
                'icon': self.get_icon('capture_thumbnail'),
            }

    def show_window_menu(self):
        if not hasattr(self.parent(), 'clicked'):
            return
        self.menu['show'] = {
            'icon': self.get_icon('logo_bw', color=None),
            'text': 'Toggle {}'.format(common.PRODUCT),
            'action': self.parent().clicked.emit
        }
        return


class ToolButtonContextMenu(PluginContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(ToolButtonContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)


class PluginWidgetContextMenu(PluginContextMenu):
    @common.error
    @common.debug
    def setup(self):
        self.apply_bookmark_settings_menu()

        self.separator()

        self.save_menu()

        self.separator()

        self.open_import_scene_menu()

        self.separator()

        self.export_sets_menu()

        self.separator()

        self.capture_menu()


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
            pen = QtGui.QPen(common.GREEN)
            pen.setWidth(common.ROW_SEPARATOR() * 2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(capture_rect)

            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.GREEN)
            painter.setOpacity(0.3)
            painter.drawRect(capture_rect)

        painter.end()

    def keyPressEvent(self, event):
        """Cancel the capture on keypress."""
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()

    def mouseReleaseEvent(self, event):
        """Finalise the caputre"""
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



class ToolButton(ui.ClickableIconButton):
    """Small widget to embed into the context to toggle the MainWidget's visibility.

    """
    ContextMenu = ToolButtonContextMenu

    def __init__(self, size, parent=None):
        super(ToolButton, self).__init__(
            'icon',
            (None, None),
            size,
            description='Click to toggle {}.'.format(
                common.PRODUCT),
            parent=parent
        )

        self.setObjectName(object_name)
        self.setAttribute(QtCore.Qt.WA_NoBackground, False)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence('Ctrl+Alt+Shift+B'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut.activated.connect(show)

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
                'icon', None, self.width())
            painter.setOpacity(1.0)
        else:
            pixmap = images.ImageCache.get_rsc_pixmap(
                'logo_bw', None, self.width())
            painter.setOpacity(0.80)

        rect = self.rect()
        center = rect.center()
        o = common.INDICATOR_WIDTH() * 2
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


class PluginWidget(mayaMixin.MayaQWidgetDockableMixin, QtWidgets.QWidget):
    """The main wrapper-widget to be used inside maya."""

    def __init__(self, parent=None):
        super(PluginWidget, self).__init__(parent=parent)

        self._workspacecontrol = None
        self._callbacks = []  # Maya api callbacks
        self.mainwidget = None

        self.setWindowTitle(common.PRODUCT)
        common.set_custom_stylesheet(self)

        # Rename object
        _object_name = self.objectName().replace(
            self.__class__.__name__, common.PRODUCT)
        self.setObjectName(_object_name)

        self._create_UI()
        self.setFocusProxy(self.mainwidget.stackedwidget)

        self.mainwidget.sizeHint = self.sizeHint

        self.workspace_timer = common.Timer(parent=self)
        self.workspace_timer.setSingleShot(False)
        self.workspace_timer.setInterval(1000)
        self.workspace_timer.timeout.connect(maya_actions.set_workspace)

        self.mainwidget.initialized.connect(
            lambda: self.mainwidget.layout().setContentsMargins(0, 0, 0, 0))

        self.mainwidget.initialized.connect(self._connect_signals)
        self.mainwidget.initialized.connect(self.context_callbacks)
        self.mainwidget.initialized.connect(maya_actions.set_workspace)
        self.mainwidget.initialized.connect(self.workspace_timer.start)

    @QtCore.Slot()
    def active_changed(self):
        """Slot called when an active asset changes.

        """
        v = settings.instance().value(
            settings.SettingsSection,
            settings.WorksapceWarningsKey
        )
        v = QtCore.Qt.Unchecked if v is None else v

        # Do nothing if explicitly set not to show warnings
        if v == QtCore.Qt.Checked:
            return

        # We will get a warning when we change to a new bookmark item. Whilst
        # technically correct, it is counterintuitive to be warned of a direct
        # action just performed
        assets_model = self.mainwidget.assetswidget.model().sourceModel()
        if not assets_model.active_index().isValid():
            return

        workspace_info = QtCore.QFileInfo(
            cmds.workspace(q=True, expandName=True))

        ui.MessageBox(
            'Workspace changed\n The new workspace is {}'.format(
                workspace_info.path()),
            'If you didn\'t expect this message, it is possible your current project was changed by Bookmarks, perhaps in another instance of Maya.'
        ).open()

    def _add_shortcuts(self):
        """Global maya shortcut to do a save as"""

    def _create_UI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.mainwidget = main.MainWidget(parent=self)
        self.layout().addWidget(self.mainwidget)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(common.SEPARATOR)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())
        painter.end()

    def context_callbacks(self):
        """This method is called by the Maya plug-in when initializing."""

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kAfterOpen, maya_actions.update_active_item)
        self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeOpen, maya_actions.unmark_active)
        self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeNew, maya_actions.unmark_active)
        self._callbacks.append(callback)

        # callback = OpenMaya.MSceneMessage.addCallback(
        #     OpenMaya.MSceneMessage.kBeforeSave, self.save_warning)
        # self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kAfterSave, maya_actions.save_warning)
        self._callbacks.append(callback)

    def remove_context_callbacks(self):
        """This method is called by the Maya plug-in when unloading."""
        for callback in self._callbacks:
            res = OpenMaya.MMessage.removeCallback(callback)
        self._callbacks = []

    @QtCore.Slot()
    def _connect_signals(self):
        bookmarkswidget = self.mainwidget.bookmarkswidget
        assetswidget = self.mainwidget.assetswidget
        fileswidget = self.mainwidget.fileswidget
        favouriteswidget = self.mainwidget.favouriteswidget

        # Asset/project
        assetswidget.model().sourceModel().activeChanged.connect(
            maya_actions.set_workspace)

        # Context menu
        bookmarkswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)
        assetswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)
        fileswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)
        favouriteswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)

        fileswidget.activated.connect(maya_actions.execute)
        favouriteswidget.activated.connect(maya_actions.execute)
        fileswidget.model().sourceModel().modelReset.connect(maya_actions.unmark_active)
        fileswidget.model().sourceModel().modelReset.connect(
            maya_actions.update_active_item)

    @QtCore.Slot(QtCore.QModelIndex)
    @QtCore.Slot(QtCore.QObject)
    def customFilesContextMenuEvent(self, index, parent):
        """Shows the custom context menu."""
        width = parent.viewport().geometry().width()
        width = (width * 0.5) if width > common.WIDTH() else width
        width = width - common.INDICATOR_WIDTH()

        widget = PluginWidgetContextMenu(index, parent=parent)
        if index.isValid():
            rect = parent.visualRect(index)
            widget.move(
                parent.viewport().mapToGlobal(rect.bottomLeft()).x(),
                parent.viewport().mapToGlobal(rect.bottomLeft()).y(),
            )
        else:
            widget.move(common.cursor.pos())

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.INDICATOR_WIDTH(), widget.y())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    @common.error
    @common.debug
    def show(self, *args, **kwargs):
        kwargs = {
            'dockable': True,
            'allowedArea': None,
            'retain': True,
            'width': common.WIDTH() * 0.5,
            'height': common.HEIGHT() * 0.5
        }

        try:
            super(PluginWidget, self).show(**kwargs)
        except:
            kwargs['dockable'] = False
            super(PluginWidget, self).show(**kwargs)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH() * 0.5, common.HEIGHT() * 0.5)
