# -*- coding: utf-8 -*-
"""QTreeView used to preview the contents of an alembic file.

Defines the helper classes and the model used used to visualise
the hierarchy.

Example:

    code-block:: python

        w = AlembicPreviewWidget('c:/path/to/my/alembic.abc')
        w.show()

"""
import alembic

from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import ui
from .. import images


instance = None


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


BG_COLOR = QtGui.QColor(0, 0, 0, 230)
TREE_STYLESHEET = """QTreeView {{
    padding: {p}px;
    border-radius: {p}px;
    border: {s}px solid black;
}}"""


class BaseNode(QtCore.QObject):
    def __init__(self, iobject, parentNode=None, parent=None):
        super(BaseNode, self).__init__(parent=parent)
        self._name = u'{}'.format(iobject)
        self.iobject = iobject
        self._children = []
        self._parentNode = parentNode

        if parentNode:
            parentNode.addChild(self)

    @property
    def name(self):
        return self._name

    @property
    def fullname(self):
        return self._name

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

    @property
    def row(self):
        """Row number of this node."""
        if self.parentNode:
            return self.parentNode.children.index(self)
        return None


class AlembicNode(BaseNode):
    """Small wrapper around the iobject hierarchy to display it in a QTreeView."""

    @property
    def name(self):
        """The name of this node."""
        props = self.iobject.getProperties()
        props.getNumProperties()
        if not self.iobject:
            return u'rootNode'
        name = self.iobject.getName()
        name = u'{}{}'.format(
            self.iobject.getName(), props.getPropertyHeader(0))
        return name

    @property
    def fullname(self):
        """The name of this node."""
        if not self.iobject:
            return u'rootNode'
        return self.iobject.getFullName()


class AlembicModel(QtCore.QAbstractItemModel):
    """Simple tree model to browse the data-structure of the alembic."""

    def __init__(self, name, node, parent=None):
        super(AlembicModel, self).__init__(parent=parent)
        self._name = name
        self._rootNode = node
        self._originalRootNode = node

    @property
    def rootNode(self):
        """ The current root node of the model """
        return self._rootNode

    @rootNode.setter
    def rootNode(self, node):
        """ The current root node of the model """
        self._rootNode = node

    @property
    def originalRootNode(self):
        """ The original root node of the model """
        return self._originalRootNode

    def rowCount(self, parent):
        """Row count."""
        if not parent.isValid():
            parentNode = self.rootNode
        else:
            parentNode = parent.internalPointer()
        return parentNode.childCount

    def columnCount(self, parent):  # pylint: disable=W0613
        """Column count."""
        return 1

    def parent(self, index):
        """The parent of the node."""
        node = index.internalPointer()
        if not node:
            return QtCore.QModelIndex()

        parentNode = node.parentNode

        if not parentNode:
            return QtCore.QModelIndex()
        elif parentNode == self.rootNode:
            return QtCore.QModelIndex()
        elif parentNode == self.originalRootNode:
            return QtCore.QModelIndex()

        return self.createIndex(parentNode.row, 0, parentNode)

    def index(self, row, column, parent):
        """Returns a QModelIndex()."""
        if not parent.isValid():
            parentNode = self.rootNode
        else:
            parentNode = parent.internalPointer()

        childItem = parentNode.getChild(row)
        if not childItem:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, childItem)

    def data(self, index, role):  # pylint: disable=W0613
        """Name data."""
        if not index.isValid():
            return None

        node = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            if u'ABC.childBnds' in node.name:
                return self._name + u'.childBnds'
            return node.name

        if role == QtCore.Qt.DecorationRole:
            if u'.childBnds' in node.name:
                return images.ImageCache.get_rsc_pixmap('abc', None, common.MARGIN(), resource=images.FormatResource)
            if u'.geom' in node.name:
                return images.ImageCache.get_rsc_pixmap('mesh', None, common.MARGIN())
            if u'.xform' in node.name:
                return images.ImageCache.get_rsc_pixmap('loc', None, common.MARGIN())

        if role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(0, common.ROW_HEIGHT())
        return None

    def headerData(self, section, orientation, role):  # pylint: disable=W0613
        """Static header data."""
        return 'Name'

    def createIndexFromNode(self, node):
        """ Creates a QModelIndex based on a Node """
        if not node.parentNode:
            return QtCore.QModelIndex()

        if node not in node.parentNode.children:
            raise ValueError('Node\'s parent doesn\'t contain the node.')

        idx = node.parentNode.children.index(node)
        return self.createIndex(idx, 0, node)


class AlembicTree(QtWidgets.QTreeView):
    """Custom QTreeView responsible for rendering the contents of an
    Alembic archive."""

    def __init__(self, path, parent=None):
        super(AlembicTree, self).__init__(parent=parent)
        path = path.encode('utf-8')
        file_info = QtCore.QFileInfo(path)

        self._abc = None
        try:
            self._abc = alembic.Abc.IArchive(path)
            node = self.alembic_to_nodes()
            model = AlembicModel(file_info.fileName(), node)
        except Exception as e:
            root_node = BaseNode(u'rootNode')
            node = BaseNode(u'Error reading alembic: {}'.format(
                e), parentNode=root_node)
            model = AlembicModel(file_info.fileName(), root_node)

        self.setHeaderHidden(False)
        self.setSortingEnabled(False)
        self.setItemsExpandable(True)
        self.setRootIsDecorated(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setModel(model)
        self.set_root_node(model.rootNode)

        self.expandAll()

    def alembic_to_nodes(self):
        """Builds the internalPointer structure needed to represent the alembic archive."""
        def _get_children(node):
            for idx in xrange(node.iobject.getNumChildren()):
                child = node.iobject.getChild(idx)
                nnode = AlembicNode(child, parentNode=node)
                _get_children(nnode)

        rootNode = AlembicNode('rootNode')

        if not self._abc.valid():
            return rootNode

        node = AlembicNode(self._abc.getTop(), parentNode=rootNode)

        # Info
        _get_children(node)
        return rootNode

    def set_root_node(self, node):
        """ Sets the given Node as the root """
        if not node.children:
            return

        index = self.model().createIndexFromNode(node)
        if not index.isValid():
            return

        self.setRootIndex(index)
        self.model().rootNode = node

        index = self.model().createIndexFromNode(self.model().rootNode)
        self.setCurrentIndex(index)

    def reset_root_node(self):
        """Resets the root node to the initial node."""
        node = self.model().originalRootNode
        index = self.model().createIndex(0, 0, node)
        self.setRootIndex(index)
        self.setCurrentIndex(index)
        self.model().rootNode = self.model().originalRootNode

    def alembic_to_plaintext(self, abc):
        """Parses the alembic structure and returns a string representation of it."""
        def _get_children(parent, text, numchildren):
            if not parent.valid():
                return text

            for idx in xrange(numchildren):
                child = parent.getChild(idx)
                childnumchildren = child.getNumChildren()
                name = child.getName().split(':')[-1]
                if idx != (numchildren - 1):
                    if childnumchildren:
                        text += u'├── {}/\n|   '.format(name)
                    else:
                        text += u' └── {}/\n'.format(name)
                else:
                    if childnumchildren:
                        text += u'└── {}\n   '.format(name)
                    else:
                        text += u' └── {}\n'.format(name)
                text = _get_children(child, text, child.getNumChildren())
            return text
        if not abc.valid():
            return u'{} is not valid.'.format(abc)

        text = u'{}/\n'.format(QtCore.QFileInfo(abc.getName()).fileName())
        text = _get_children(abc.getTop(), text,
                             abc.getTop().getNumChildren())
        return text.encode('utf-8')

    def keyPressEvent(self, event):
        event.ignore()


class AlembicPreviewWidget(QtWidgets.QWidget):
    """Widget used  to display the contents of an alembic archive.

    """

    def __init__(self, path, parent=None):
        global instance
        instance = self

        super(AlembicPreviewWidget, self).__init__(parent=parent)
        if not isinstance(path, unicode):
            raise ValueError(
                u'Expected {}, got {}'.format(unicode, type(path)))

        if not self.parent():
            common.set_custom_stylesheet(self)

        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            raise RuntimeError('{} does not exists.'.format(path))

        self.path = path
        self.view = AlembicTree(path, parent=self)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )

        self._create_ui()
        self.view.setStyleSheet(
            TREE_STYLESHEET.format(
                p=common.INDICATOR_WIDTH() * 2,
                s=common.ROW_SEPARATOR()
            )
        )

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        self.layout().setSpacing(o)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        row = ui.add_row(None, parent=self)
        label = ui.PaintedLabel(self.path, parent=row)
        row.layout().addWidget(label)

        row = ui.add_row(None, height=None, parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.view, 1)
        row.layout().addStretch(1)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(BG_COLOR)
        painter.drawRect(self.rect())
        painter.end()

    def mousePressEvent(self, event):
        event.accept()
        self.close()
        self.deleteLater()

    def keyPressEvent(self, event):
        """We're mapping the key press events to the parent list."""
        if self.parent():
            if event.key() == QtCore.Qt.Key_Down:
                self.parent().key_down()
                self.parent().key_space()
            elif event.key() == QtCore.Qt.Key_Up:
                self.parent().key_up()
                self.parent().key_space()
            elif event.key() == QtCore.Qt.Key_Tab:
                self.parent().key_up()
                self.parent().key_space()
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.parent().key_down()
                self.parent().key_space()

        self.deleteLater()
        self.close()

    def showEvent(self, event):
        common.fit_screen_geometry(self)
