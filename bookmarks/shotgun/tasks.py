# -*- coding: utf-8 -*-
"""Module contains all widgets and utility classes used to select a Task
when publishing to shotgun.

"""
import functools
from PySide2 import QtWidgets, QtCore, QtGui

from .. import common
from .. import ui

from .. import images
from .. import contextmenu
from . import shotgun

from ..editor import base_widgets
from ..editor import base


instance = None
NoStepName = '(Tasks without Step)'


def close():
    global instance
    if instance is None:
        return
    try:
        instance.close()
        instance.deleteLater()
    except:
        pass
    instance = None


def show():
    global instance
    close()
    instance = TaskPicker()
    instance.open()
    return instance


class TaskViewContextMenu(contextmenu.BaseContextMenu):
    """The context menu associated with the AssetsWidget."""

    @common.debug
    @common.error
    def setup(self):
        self.visit_menu()

    def visit_menu(self):
        if not self.index.isValid():
            return

        entity = self.index.data(QtCore.Qt.UserRole)
        if not entity:
            return

        sg_properties = self.parent().window().sg_properties
        if not sg_properties.verify():
            return

        url = shotgun.ENTITY_URL.format(
            domain=sg_properties.domain,
            entity_type=entity['type'],
            entity_id=entity['id'],
        )
        self.menu['visit'] = {
            'text': 'View Online...',
            'action': functools.partial(QtGui.QDesktopServices.openUrl, QtCore.QUrl(url))
        }


class InteralNode(QtCore.QObject):
    """Utility class to represent a hierarchy needed by the tree view."""

    def __init__(self, data, parentNode=None, parent=None):
        super(InteralNode, self).__init__(parent=parent)
        self.data = data
        self._children = []
        self._parentNode = parentNode

        if parentNode:
            parentNode.addChild(self)

    def removeSelf(self):
        """Removes itself from the parent's children."""
        if self.parentNode:
            if self in self.parentNode.children:
                idx = self.parentNode.children.index(self)
                del self.parentNode.children[idx]

    def removeChild(self, child):
        """Remove the given node from the children."""
        if child in self.children:
            idx = self.children.index(child)
            del self.children[idx]

    def addChild(self, child):
        """Add a child node."""
        self.children.append(child)

    @property
    def children(self):
        """Children of the node."""
        return self._children

    @property
    def childCount(self):
        """Children of the this node."""
        return len(self._children)

    @property
    def parentNode(self):
        """Parent of this node."""
        return self._parentNode

    @parentNode.setter
    def parentNode(self, node):
        self._parentNode = node

    def getChild(self, row):
        """Child at the provided index/row."""
        if row < self.childCount:
            return self.children[row]
        return None

    def row(self):
        """Row number of this node."""
        if self.parentNode:
            return self.parentNode.children.index(self)
        return None


class ProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(ProxyModel, self).__init__(parent=parent)
        self.user_filter = -1
        self.asset_filter = -1

    def set_user_filter(self, v):
        self.user_filter = v

    def set_asset_filter(self, v):
        self.asset_filter = v

    def filterAcceptsColumn(self, source_column, parent=QtCore.QModelIndex()):
        return True

    def filterAcceptsRow(self, source_row, parent=QtCore.QModelIndex()):
        """Filters rows of the proxy model based on the current flags and
        filter string.

        """
        if not parent.isValid():
            return True

        if self.user_filter == -1 and self.asset_filter == -1:
            return True

        node = parent.internalPointer()
        if not node:
            return True
        entity = node.data['children'][source_row]['entity']

        if all((self._asset_filter_accepts(entity), self._user_filter_accepts(entity))):
            return True
        return False

    def _asset_filter_accepts(self, entity):
        if self.asset_filter == -1:
            return True
        elif self.asset_filter >= 0 and 'entity' in entity and entity['entity']:
            if self.asset_filter == entity['entity']['id']:
                return True
        return False

    def _user_filter_accepts(self, entity):
        if self.user_filter == -2 and ('task_assignees' not in entity or not entity['task_assignees']):
            return True
        elif self.user_filter == -1:
            return True
        elif self.user_filter >= 0 and 'task_assignees' in entity and entity['task_assignees']:
            for user in entity['task_assignees']:
                if self.user_filter == user['id']:
                    return True
        return False


class TaskModel(QtCore.QAbstractItemModel):
    def __init__(self, entities, parent=None):
        super(TaskModel, self).__init__(parent=parent)

        self.task_icon = None
        self.step_icon = None

        self.entities = entities
        self._root_node = None
        self._original_root_node = None

        self.init_icons()
        self.init_root_node()

    @common.error
    @common.debug
    def init_root_node(self):
        root_node = self.entities_to_nodes()
        self._root_node = root_node
        self._original_root_node = root_node

    @common.error
    @common.debug
    def init_icons(self):
        pixmap1 = images.ImageCache.get_rsc_pixmap(
            'sg', common.color(common.GreenColor), common.size(common.WidthMargin))
        pixmap2 = images.ImageCache.get_rsc_pixmap(
            'check', common.color(common.TextSelectedColor), common.size(common.WidthMargin))
        icon = QtGui.QIcon()
        icon.addPixmap(pixmap1, mode=QtGui.QIcon.Normal)
        icon.addPixmap(pixmap2, mode=QtGui.QIcon.Active)
        icon.addPixmap(pixmap2, mode=QtGui.QIcon.Selected)
        self.task_icon = icon

        self.step_icon = QtGui.QIcon(images.ImageCache.get_rsc_pixmap(
            'sg', common.color(common.BlueColor), common.size(common.WidthMargin)))

    def entities_to_nodes(self):
        """Builds the internal node hierarchy base on the given entity data.

        """
        def get_children(parent_node):
            for data in parent_node.data['children']:
                node = InteralNode(data, parentNode=parent_node)
                get_children(node)

        data = {}
        for entity in self.entities:

            # Add steps
            if 'step' in entity and entity['step']:
                k = entity['step']['name']
                if k not in data:
                    data[k] = {
                        'entity': entity['step'],
                        'children': [],
                    }
            else:
                k = NoStepName
                if k not in data:
                    data[k] = {
                        'entity': {'type': 'Step', 'id': -1, 'name': NoStepName},
                        'children': [],
                    }

            task = {
                'entity': entity,
                'children': []
            }
            data[k]['children'].append(task)

        ks = sorted(data.keys())
        root_node = InteralNode(None)
        for k in ks:
            node = InteralNode(data[k], parentNode=root_node)
            get_children(node)

        return root_node

    @property
    def root_node(self):
        return self._root_node

    @root_node.setter
    def root_node(self, node):
        self._root_node = node

    @property
    def original_root_node(self):
        return self._original_root_node

    def rowCount(self, parent):
        if not parent.isValid():
            parentNode = self.root_node
        else:
            parentNode = parent.internalPointer()
        return parentNode.childCount

    def columnCount(self, parent):  # pylint: disable=W0613
        return 5

    def parent(self, index):
        node = index.internalPointer()
        if not node:
            return QtCore.QModelIndex()

        parentNode = node.parentNode

        if not parentNode:
            return QtCore.QModelIndex()
        elif parentNode == self.root_node:
            return QtCore.QModelIndex()
        elif parentNode == self.original_root_node:
            return QtCore.QModelIndex()

        return self.createIndex(parentNode.row(), 0, parentNode)

    def index(self, row, column, parent):
        if not parent.isValid():
            parentNode = self.root_node
        else:
            parentNode = parent.internalPointer()

        childItem = parentNode.getChild(row)
        if not childItem:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, childItem)

    def task_entity(self, column, entity, role):
        if role == QtCore.Qt.DisplayRole and column == 0:
            return entity['content']

        if role == QtCore.Qt.DisplayRole and column == 1:
            if 'entity' in entity and entity['entity']:
                return entity['entity']['name']
            return ''

        if role == QtCore.Qt.DisplayRole and column == 2:
            if 'task_assignees' in entity and entity['task_assignees']:
                names = []
                for user in entity['task_assignees']:
                    names.append(user['name'])
                return '; '.join(names)
            return ''

        if role == QtCore.Qt.DisplayRole and column == 3:
            if 'start_date' in entity and entity['start_date']:
                return entity['start_date']
            return ''

        if role == QtCore.Qt.DisplayRole and column == 4:
            if 'due_date' in entity and entity['due_date']:
                return entity['due_date']
            return ''

        if role == QtCore.Qt.ForegroundRole and column == 0:
            return common.color(common.TextColor)
        if role == QtCore.Qt.ForegroundRole and column > 0:
            return common.color(common.TextDisabledColor)

        if role == QtCore.Qt.FontRole and column == 0:
            font, _ = common.font_db.primary_font(
                common.size(common.FontSizeMedium))
            return font
        if role == QtCore.Qt.FontRole and column > 0:
            font, _ = common.font_db.secondary_font(
                common.size(common.FontSizeSmall))
            return font

        if role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(0, common.size(common.HeightRow))

        if role == QtCore.Qt.DecorationRole and column == 0:
            return self.task_icon

    def step_entity(self, column, entity, role):
        if column != 0:
            return None

        if role == QtCore.Qt.DisplayRole:
            return entity['name']

        if role == QtCore.Qt.ForegroundRole:
            return common.color(common.BlueColor)

        if role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(0, common.size(common.HeightRow) * 0.66)

        if role == QtCore.Qt.DecorationRole and entity['name'] != NoStepName:
            return self.step_icon

    def data(self, index, role):  # pylint: disable=W0613
        if not index.isValid():
            return None

        node = index.internalPointer()
        entity = node.data['entity']
        if role == QtCore.Qt.UserRole:
            return entity
        column = index.column()

        if entity['type'] == 'Task':
            return self.task_entity(column, entity, role)
        elif entity['type'] == 'Step':
            return self.step_entity(column, entity, role)

    def flags(self, index, parent=QtCore.QModelIndex()):
        node = index.internalPointer()
        entity = node.data['entity']

        if entity['type'] == 'Task':
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if entity['type'] == 'Step':
            return QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role):  # pylint: disable=W0613
        if role != QtCore.Qt.DisplayRole:
            return None

        if section == 0:
            return 'Task'
        if section == 1:
            return 'Asset'
        if section == 2:
            return 'Artist'
        if section == 3:
            return 'Start'
        if section == 4:
            return 'Due'
        return None

    def createIndexFromNode(self, node):
        """ Creates a QModelIndex based on a Node """
        if not node.parentNode:
            return QtCore.QModelIndex()

        if node not in node.parentNode.children:
            raise ValueError('Node\'s parent doesn\'t contain the node.')

        idx = node.parentNode.children.index(node)
        return self.createIndex(idx, 0, node)


class TaskView(QtWidgets.QTreeView):
    """Tree view used to display the current ShotGrid Steps and Tasks.

    """

    def __init__(self, parent=None):
        super(TaskView, self).__init__(parent=parent)
        if not self.parent():
            common.set_stylesheet(self)

        self.setHeaderHidden(False)
        self.setSortingEnabled(False)
        self.setItemsExpandable(True)
        self.setRootIsDecorated(True)
        self.setIndentation(common.size(common.WidthMargin))
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        header = QtWidgets.QHeaderView(QtCore.Qt.Horizontal, parent=self)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.setHeader(header)

        self.expanded.connect(lambda x: self.adjust_columns())

    def resizeEvent(self, event):
        self.adjust_columns()

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        index = self.indexAt(event.pos())
        widget = TaskViewContextMenu(index, parent=self)
        widget.move(common.cursor.pos())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def save_selection(self, current, previous):
        v = current.data(QtCore.Qt.DisplayRole)
        common.settings.setValue(
            common.PublishVersionSection,
            common.CurrentSelectionKey,
            v
        )

    def restore_selection(self):
        v = common.settings.value(
            common.PublishVersionSection,
            common.CurrentSelectionKey,
        )

        index = self.indexAt(QtCore.QPoint(0, 0))
        while index.isValid():
            index = self.indexBelow(index)

            if v == index.data(QtCore.Qt.DisplayRole):
                self.setCurrentIndex(index)
                self.scrollTo(
                    index,
                    QtWidgets.QAbstractItemView.PositionAtCenter
                )

    def adjust_columns(self):
        if not self.model():
            return

        fixed = common.size(common.DefaultWidth) * 0.3
        w = (self.rect().width() - fixed) / \
            (self.model().columnCount(QtCore.QModelIndex()) - 1)
        for x in range(self.model().columnCount(QtCore.QModelIndex())):
            if x == 0:
                self.setColumnWidth(x, fixed)
                continue
            else:
                self.setColumnWidth(x, w)

    def set_root_node(self, node):
        if not node.children:
            return

        model = self.model().sourceModel()
        index = model.createIndexFromNode(node)
        if not index.isValid():
            return

        self.setRootIndex(index)
        model.root_node = node

        index = model.createIndexFromNode(self.model().root_node)
        self.setCurrentIndex(index)

    def reset_root_node(self):
        """Resets the root node to the initial root node.

        """
        model = self.model().sourceModel()
        model.root_node = model.original_root_node

        index = model.createIndex(0, 0, model.original_root_node)
        self.setRootIndex(index)
        self.setCurrentIndex(index)


class TaskPicker(QtWidgets.QDialog):
    """The main dialog used to select a task entity.

     The task is to associate a file publish, or a version when publishing to
     ShotGrid.

    """
    sgEntitySelected = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super(TaskPicker, self).__init__(parent=parent)
        if not self.parent():
            common.set_stylesheet(self)

        self.sg_properties = None
        self.user_editor = None
        self.asset_editor = None
        self.task_editor = None

        self.ok_button = None

        self._message = 'No task was found.'
        self.installEventFilter(self)
        self._create_ui()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.size(common.WidthMargin)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        grp = base.add_section(
            'sg', 'Select Task', self, color=None
        )

        self.user_editor = base_widgets.BaseComboBox(parent=self)
        self.user_editor.setDuplicatesEnabled(False)
        self.asset_editor = base_widgets.BaseComboBox(parent=self)
        self.asset_editor.setDuplicatesEnabled(False)

        filter_row = ui.add_row(None, parent=grp)

        label = ui.PaintedLabel('Filter by User')
        filter_row.layout().addWidget(label, 0)
        filter_row.layout().addWidget(self.user_editor, 1)

        filter_row.layout().addSpacing(o)

        label = ui.PaintedLabel('Filter by Asset')
        filter_row.layout().addWidget(label, 0)
        filter_row.layout().addWidget(self.asset_editor, 1)

        self.task_editor = TaskView(parent=self)
        grp.layout().addWidget(self.task_editor)

        self.ok_button = ui.PaintedButton('Done')
        grp.layout().addWidget(self.ok_button, 1)

    def _connect_signals(self):
        self.user_editor.currentIndexChanged.connect(
            lambda: self.task_editor.model().set_user_filter(self.user_editor.currentData()))
        self.user_editor.currentIndexChanged.connect(
            lambda x: self.task_editor.model().invalidateFilter())

        self.user_editor.currentTextChanged.connect(
            functools.partial(self.save_selection, self.user_editor, common.CurrentUserKey))

        self.asset_editor.currentIndexChanged.connect(
            lambda: self.task_editor.model().set_asset_filter(self.asset_editor.currentData()))
        self.asset_editor.currentIndexChanged.connect(
            lambda x: self.task_editor.model().invalidateFilter())

        self.asset_editor.currentTextChanged.connect(
            functools.partial(self.save_selection, self.asset_editor, common.CurrentAssetKey))

        self.task_editor.selectionModel().currentChanged.connect(
            self.task_editor.save_selection)
        self.ok_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

        self.task_editor.doubleClicked.connect(self.double_clicked)

    @common.error
    @common.debug
    def init_items(self):
        sg_properties = shotgun.ShotgunProperties(active=True)
        sg_properties.init()
        if not sg_properties.verify(bookmark=True):
            raise ValueError('Bookmark not configured.')

        self.sg_properties = sg_properties

        with shotgun.connection(sg_properties) as sg:
            entities = sg.find(
                'Task',
                [
                    ['project', 'is', {'type': 'Project',
                                       'id': sg_properties.bookmark_id}]
                ],
                fields=shotgun.fields['Task']
            )

        model = TaskModel(entities, parent=self)

        proxy = ProxyModel(parent=self)
        proxy.setSourceModel(model)

        self.task_editor.setModel(proxy)
        self.task_editor.set_root_node(model.root_node)
        self.task_editor.expandAll()
        self.task_editor.restore_selection()

        self.init_users(entities)
        self.init_assets(entities)

        self._connect_signals()

        self.restore_selection(self.user_editor, common.CurrentUserKey)
        self.restore_selection(self.asset_editor, common.CurrentAssetKey)

    def init_users(self, entities):
        self.user_editor.clear()

        self.user_editor.addItem('Show All', userData=-1)
        self.user_editor.addItem('Show Unassigned', userData=-2)
        self.user_editor.insertSeparator(self.user_editor.count())

        for entity in entities:
            if 'task_assignees' not in entity or not entity['task_assignees']:
                continue

            for user in entity['task_assignees']:
                if self.user_editor.findData(user['id'], role=QtCore.Qt.UserRole) >= 0:
                    continue
                self.user_editor.addItem(user['name'], userData=user['id'])

    def init_assets(self, entities):
        self.asset_editor.clear()

        self.asset_editor.addItem('Show All', userData=-1)
        self.asset_editor.insertSeparator(self.asset_editor.count())

        for entity in entities:
            if 'entity' not in entity or not entity['entity']:
                continue

            _entity = entity['entity']
            if self.asset_editor.findData(_entity['id'], role=QtCore.Qt.UserRole) >= 0:
                continue
            self.asset_editor.addItem(_entity['name'], userData=_entity['id'])

    @common.error
    @common.debug
    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            super(TaskPicker, self).done(result)
            return

        index = common.get_selected_index(self.task_editor)
        if not index.isValid():
            self.sgEntitySelected.emit(None)
            super(TaskPicker, self).done(result)
            return

        entity = index.data(QtCore.Qt.UserRole)
        if not entity:
            self.sgEntitySelected.emit(None)
            super(TaskPicker, self).done(result)
            return

        self.sgEntitySelected.emit(entity)
        super(TaskPicker, self).done(result)

    def save_selection(self, editor, k, v):
        common.settings.setValue(
            common.PublishVersionSection,
            k,
            v
        )

    def restore_selection(self, k, v):
        v = common.settings.value(
            common.PublishVersionSection,
            k,
        )
        if isinstance(v, str):
            self.setCurrentText(v)

    def double_clicked(self, index):
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.UserRole):
            return
        self.done(QtWidgets.QDialog.Accepted)

    def showEvent(self, event):
        common.center_window(self)
        QtCore.QTimer.singleShot(100, self.init_items)

    def sizeHint(self):
        return QtCore.QSize(common.size(common.DefaultWidth) * 1.5, common.size(common.DefaultHeight) * 1.3)
