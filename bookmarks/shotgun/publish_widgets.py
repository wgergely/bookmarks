# -*- coding: utf-8 -*-
"""Tree view and model used to display Shotgun Steps and Tasks.

"""
from PySide2 import QtWidgets, QtCore, QtGui

from .. import common

from .. import images
from . import shotgun
from . import actions as sg_actions


NOT_SELECTED = 'Not selected...'
NOT_CONFIGURED = 'Not configured'


class DropWidget(QtWidgets.QWidget):
    """Widget used to proved an area to drop a file onto.

    """
    clicked = QtCore.Signal()
    fileSelected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(DropWidget, self).__init__(parent=parent)

        self._drag_in_progress = False
        self._path = None
        self._placeholder_text = None

        self.setAcceptDrops(True)
        self.setFixedHeight(common.size(common.HeightRow) * 4)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Fixed
        )

        self.clicked.connect(self.pick)

    def setPlaceholderText(self, v):
        self._placeholder_text = v
        self.update()

    def path(self):
        return self._path

    def set_path(self, v):
        self._path = v
        self._placeholder_text = v
        self.update()

    def statusTip(self):
        if self._path:
            return self._path
        return self._placeholder_text

    def toolTip(self):
        if self._path:
            return self._path
        return self._placeholder_text

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        pressed = option.state & QtWidgets.QStyle.State_Sunken
        focus = option.state & QtWidgets.QStyle.State_HasFocus

        # Background
        painter.save()
        self._draw_background(painter, hover)
        painter.restore()

        painter.save()
        self._draw_placeholder_text(painter, hover)
        painter.restore()

        painter.save()
        self._draw_background_icon(painter, hover)
        painter.restore()

        painter.end()

    def _draw_background(self, painter, hover):
        painter.setOpacity(0.55 if hover else 0.45)

        o = common.size(common.WidthIndicator) * 1.5
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.color(common.SeparatorColor))
        painter.drawRoundedRect(self.rect(), o, o)

        if self._path:
            return

        rect = self.rect().adjusted(o, o, -o, -o)

        color = common.color(common.GreenColor) if hover else common.color(common.SeparatorColor)
        pen = QtGui.QPen(color)
        pen.setWidthF(common.size(common.HeightSeparator) * 2)
        pen.setStyle(QtCore.Qt.DashLine)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)

        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(rect, o / 2, o / 2)

    def _draw_placeholder_text(self, painter, hover):
        if not self._placeholder_text:
            return

        v = QtCore.QFileInfo(self._placeholder_text).fileName()
        if self._drag_in_progress:
            v = 'Drop here to add file'

        painter.setOpacity(1.0 if hover else 0.8)

        o = common.size(common.WidthMargin) * 1.5

        color = common.color(common.GreenColor) if hover else common.color(common.TextSecondaryColor)
        color = common.color(common.TextSelectedColor) if self._path else color
        color = common.color(common.GreenColor) if self._drag_in_progress else color

        if self._path:
            rect = self.rect().adjusted(o * 3, o, -o, -o)
        else:
            rect = self.rect().adjusted(o, o, -o, -o)

        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(font_size=common.size(common.FontSizeLarge))[0],
            rect,
            v,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
            color,
        )

    def _draw_background_icon(self, painter, hover):
        if self._drag_in_progress:
            icon = 'add_file'
        else:
            icon = 'file'

        if hover:
            color = common.color(common.GreenColor)
        else:
            color = common.color(common.TextDisabledColor)

        if self._path:
            icon = 'check'
            color = common.color(common.GreenColor)

        if self._drag_in_progress:
            icon = 'add_file'
            color = common.color(common.GreenColor)

        h = common.size(common.WidthMargin)
        pixmap = images.ImageCache.get_rsc_pixmap(icon, color, h)

        prect = pixmap.rect()
        prect.moveCenter(self.rect().center())
        prect.moveLeft(common.size(common.WidthMargin) * 2)

        painter.drawPixmap(prect, pixmap, pixmap.rect())

    def enterEvent(self, event):
        app = QtWidgets.QApplication.instance()
        if app.overrideCursor():
            app.changeOverrideCursor(
                QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        else:
            app.restoreOverrideCursor()
            app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.update()
        super(DropWidget, self).enterEvent(event)

    def leaveEvent(self, event):
        app = QtWidgets.QApplication.instance()
        if app.overrideCursor():
            app.restoreOverrideCursor()
        self.update()
        super(DropWidget, self).leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.rect().contains(event.pos()):
            self.clicked.emit()
        super(DropWidget, self).mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self._drag_in_progress = True
            self.repaint()
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            self._drag_in_progress = True
            event.accept()
            return

        self._drag_in_progress = False
        event.ignore()

    def dragLeaveEvent(self, event):
        self._drag_in_progress = False
        self.repaint()
        return True

    def dropEvent(self, event):
        self._drag_in_progress = False
        self.repaint()

        for url in event.mimeData().urls():
            s = url.toLocalFile()
            self.fileSelected.emit(s)
            break

        self.repaint()

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def pick(self):
        widget = PickFile(parent=self)
        widget.open()
        widget.fileSelected.connect(self.fileSelected)


class ProjectEntityEditor(shotgun.EntityComboBox):
    """Displays the current project entity."""

    def __init__(self, parent=None):
        super(ProjectEntityEditor, self).__init__(
            [self.entity(), ],
            parent=None
        )
        self.model().set_entity_type(None)
        self.setCurrentIndex(0)

    @common.error
    @common.debug
    def entity(self):
        sg_properties = shotgun.ShotgunProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(bookmark=True):
            return NOT_CONFIGURED
        entity = {
            'id': sg_properties.bookmark_id,
            'name': sg_properties.bookmark_name,
            'type': sg_properties.bookmark_type,
        }
        return entity


class AssetEntityEditor(shotgun.EntityComboBox):
    """Displays the current asset entity."""

    def __init__(self, parent=None):
        super(AssetEntityEditor, self).__init__(
            [self.entity(), ],
            parent=None
        )
        self.model().set_entity_type(None)
        self.setCurrentIndex(0)

    @common.error
    @common.debug
    def entity(self):
        sg_properties = shotgun.ShotgunProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(asset=True):
            return NOT_CONFIGURED
        entity = {
            'id': sg_properties.asset_id,
            'name': sg_properties.asset_name,
            'type': sg_properties.asset_type,
        }
        return entity


class StatusEditor(shotgun.EntityComboBox):
    """Lets the user select a status code."""

    def __init__(self, parent=None):
        super(StatusEditor, self).__init__([NOT_SELECTED, ], parent=parent)
        self.init_data()
        self.model().sourceModel().entityDataReceived.connect(self.select_default)

    def init_data(self):
        """Request Status entity data.

        """
        model = self.model().sourceModel()

        # Disable filtering
        self.model().set_entity_type(None)

        # 'Status' entities are retrieved by `sg_actions.get_status_codes`,
        # which use our arguments here and so we don't have to pass anything
        # apart from the # entity type and the server, job, root names.
        model.entityDataRequested.emit(
            model.uuid,
            common.active(common.ServerKey),
            common.active(common.JobKey),
            common.active(common.RootKey),
            None,
            'Status',
            [],
            [],
        )

    def select_default(self):
        """Select the default status code, if a 'default' value is found in
        the entity list.

        """
        for idx in range(self.count()):
            entity = self.itemData(idx, role=shotgun.EntityRole)
            if not entity:
                continue
            k = 'default'
            if k in entity and entity[k]:
                self.setCurrentIndex(idx)
                return
        self.setCurrentIndex(0)


class TaskEditor(shotgun.EntityComboBox):
    """Lets the user selet a Shotgun task."""

    def __init__(self, parent=None):
        super(TaskEditor, self).__init__(
            [NOT_SELECTED, 'Open Task Browser...', ], parent=parent)
        self.init_data()

        self.model().sourceModel().entityDataReceived.connect(self.restore_selection)
        self.activated.connect(self.open_editor)
        self.currentIndexChanged.connect(self.save_selection)
        common.signals.entitySelected.connect(self.select_entity)

    @common.error
    @common.debug
    def init_data(self):
        """Request Status entity data.

        """
        model = self.model().sourceModel()

        # Set filtering
        self.model().set_entity_type('Task')

        sg_properties = shotgun.ShotgunProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(bookmark=True):
            return

        model.entityDataRequested.emit(
            model.uuid,
            sg_properties.server,
            sg_properties.job,
            sg_properties.root,
            sg_properties.asset,
            'Task',
            [
                ['project', 'is', {'type': 'Project',
                                   'id': sg_properties.bookmark_id}],
            ],
            shotgun.fields['Task'],
        )

    @common.error
    @common.debug
    def open_editor(self, idx):
        if idx == 1:
            sg_actions.show_task_picker()

    @common.error
    @common.debug
    def save_selection(self, idx):
        if idx < 2:
            return
        entity = self.itemData(idx, role=shotgun.EntityRole)
        if not entity:
            return
        k = 'content'
        if k in entity and entity[k]:
            common.settings.setValue(
                common.UIStateSection,
                common.PublishTask,
                entity[k]
            )

    @common.error
    @common.debug
    def restore_selection(self, *args, **kwargs):
        v = common.settings.value(
            common.UIStateSection,
            common.PublishTask
        )
        if not v:
            self.setCurrentIndex(0)
            return

        for idx in range(self.count()):
            entity = self.itemData(idx, role=shotgun.EntityRole)
            if not entity:
                continue
            k = 'content'
            if k in entity and entity[k]:
                if v == entity[k]:
                    self.setCurrentIndex(idx)
                    return

        self.setCurrentIndex(0)

    @common.error
    @common.debug
    def select_entity(self, entity):
        if not entity:
            return

        for idx in range(self.count()):
            _entity = self.itemData(idx, role=shotgun.EntityRole)
            if not _entity:
                continue

            k = 'content'

            if k in entity and entity[k] and k in _entity and _entity[k]:
                if entity[k] == _entity[k]:
                    self.setCurrentIndex(idx)
                    return

        self.append_entity(entity)


class LocalStorageEditor(shotgun.EntityComboBox):
    """Lets the user selet a Shotgun task."""

    def __init__(self, parent=None):
        super(LocalStorageEditor, self).__init__(
            [NOT_SELECTED, ], parent=parent)
        self.init_data()
        self.model().sourceModel().entityDataReceived.connect(self.select_entity)

    @common.error
    @common.debug
    def init_data(self):
        """Request Status entity data.

        """
        model = self.model().sourceModel()

        # Set filtering
        self.model().set_entity_type('LocalStorage')

        sg_properties = shotgun.ShotgunProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(connection=True):
            return

        model.entityDataRequested.emit(
            model.uuid,
            sg_properties.server,
            sg_properties.job,
            sg_properties.root,
            sg_properties.asset,
            'LocalStorage',
            [],
            shotgun.fields['LocalStorage'],
        )

    def select_entity(self):
        server = common.active(common.ServerKey)
        file_info = QtCore.QFileInfo(server)
        apath = file_info.absoluteFilePath()

        for idx in range(self.count()):
            entity = self.itemData(idx, role=shotgun.EntityRole)
            if not entity:
                continue

            k = 'mac_path'
            if k in entity and entity[k]:
                _file_info = QtCore.QFileInfo(entity[k])
                if apath == _file_info.absoluteFilePath():
                    self.setCurrentIndex(idx)
                    return

            k = 'windows_path'
            if k in entity and entity[k]:
                _file_info = QtCore.QFileInfo(entity[k])
                if apath == _file_info.absoluteFilePath():
                    self.setCurrentIndex(idx)
                    return

            k = 'linux_path'
            if k in entity and entity[k]:
                _file_info = QtCore.QFileInfo(entity[k])
                if apath == _file_info.absoluteFilePath():
                    self.setCurrentIndex(idx)
                    return


class PublishedFileTypeEditor(shotgun.EntityComboBox):
    """Lets the user selet a Shotgun task."""

    def __init__(self, parent=None):
        super(PublishedFileTypeEditor, self).__init__(
            [NOT_SELECTED, ], parent=parent)
        self.init_data()
        self.model().sourceModel().entityDataReceived.connect(self.restore_selection)
        self.currentIndexChanged.connect(self.save_selection)

    @common.error
    @common.debug
    def init_data(self):
        """Request Status entity data.

        """
        model = self.model().sourceModel()

        # Set filtering
        self.model().set_entity_type('PublishedFileType')

        sg_properties = shotgun.ShotgunProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(bookmark=True):
            return

        model.entityDataRequested.emit(
            model.uuid,
            sg_properties.server,
            sg_properties.job,
            sg_properties.root,
            sg_properties.asset,
            'PublishedFileType',
            [],
            shotgun.fields['PublishedFileType'],
        )

    @common.error
    @common.debug
    def open_editor(self, idx):
        if idx == 1:
            sg_actions.show_task_picker()

    @common.error
    @common.debug
    def save_selection(self, idx):
        if idx < 1:
            return
        entity = self.itemData(idx, role=shotgun.EntityRole)
        if not entity:
            return
        k = 'code'
        if k in entity and entity[k]:
            common.settings.setValue(
                common.UIStateSection,
                common.PublishFileType,
                entity[k]
            )

    @common.error
    @common.debug
    def restore_selection(self, *args, **kwargs):
        v = common.settings.value(
            common.UIStateSection,
            common.PublishFileType
        )
        if not v:
            self.setCurrentIndex(0)
            return

        for idx in range(self.count()):
            entity = self.itemData(idx, role=shotgun.EntityRole)
            if not entity:
                continue
            k = 'code'
            if k in entity and entity[k]:
                if v == entity[k]:
                    self.setCurrentIndex(idx)
                    return

        self.setCurrentIndex(0)

    @common.error
    @common.debug
    def select_entity(self, entity):
        if not entity:
            return

        for idx in range(self.count()):
            _entity = self.itemData(idx, role=shotgun.EntityRole)
            if not _entity:
                continue

            k = 'content'

            if k in entity and entity[k] and k in _entity and _entity[k]:
                if entity[k] == _entity[k]:
                    self.setCurrentIndex(idx)
                    return

        self.append_entity(entity)


class PickFile(QtWidgets.QFileDialog):
    def __init__(self, parent=None):
        super(PickFile, self).__init__(parent=parent)

        self.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        self.setViewMode(QtWidgets.QFileDialog.List)
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)

        self.setFilter(
            QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot
        )
        self.setLabelText(
            QtWidgets.QFileDialog.Accept,
            'Pick a file to publish'
        )

        args = (
            common.active(common.ServerKey),
            common.active(common.JobKey),
            common.active(common.RootKey),
            common.active(common.AssetKey),
            common.active(common.TaskKey),
        )
        if not all(args):
            args = (
                common.active(common.ServerKey),
                common.active(common.JobKey),
                common.active(common.RootKey),
                common.active(common.AssetKey),
            )
        if not all(args):
            return
        path = '/'.join(args)
        self.setDirectory(path)

    def _connect_signals(self):
        pass
