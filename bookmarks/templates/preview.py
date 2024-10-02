import io
import zipfile

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import ui


class Node:
    def __init__(self, name, is_dir=False, parent=None, is_internal_link=False, is_links_file=False):
        self.name = name
        self.is_dir = is_dir
        self.parent = parent
        self.children = []
        self.is_internal_link = is_internal_link
        self.is_links_file = is_links_file
        if parent:
            parent.children.append(self)


def build_tree_from_zip(data):
    zp = io.BytesIO(data)
    with zipfile.ZipFile(zp, 'r') as zf:

        root = Node('root', is_dir=True)
        nl = zf.namelist()
        nl = sorted(nl, key=lambda s: s.lower())

        # Build the tree from zip entries, including the .links file
        for path in nl:
            is_dir = path.endswith('/')

            path = path.rstrip('/')
            if not path:
                continue  # Skip root

            path_parts = path.split('/')
            current_node = root
            for part in path_parts[:-1]:
                child = next((x for x in current_node.children if x.name == part and x.is_dir), None)
                if not child:
                    child = Node(part, is_dir=True, parent=current_node)
                current_node = child

            file_name = path_parts[-1]
            is_links_file = path == '.links'
            if is_dir:
                Node(file_name, is_dir=True, parent=current_node)
            else:
                Node(file_name, is_dir=False, parent=current_node, is_links_file=is_links_file)

        if '.links' in nl:
            links_node = None
            for child in root.children:
                if child.name == '.links' and not child.is_dir:
                    links_node = child
                    break

            if links_node:
                with zf.open('.links') as f:
                    links_content = f.read().decode('utf-8')
                    link_paths = links_content.strip().splitlines()
                    for link_path in link_paths:
                        link_path = link_path.strip()
                        if not link_path:
                            continue

                        # Build the path in the tree, marking nodes as internal links
                        path_parts = link_path.strip('/').split('/')
                        current_node = root
                        for part in path_parts:
                            # Find or create the node
                            child = next((x for x in current_node.children if x.name == part), None)
                            if not child:
                                child = Node(part, is_dir=True, parent=current_node, is_internal_link=True)
                            else:
                                # If the node already exists, mark it as an internal link
                                if not child.is_internal_link:
                                    child.is_internal_link = True
                            current_node = child
        return root


class TreeModel(QtCore.QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_node = Node('root', is_dir=True)

    @QtCore.Slot(bytes)
    def init_data(self, data):
        """Initialize the model with the data from the zip file

        Args:
            data (bytes): The data from the zip file

        """
        if not data:
            self.beginResetModel()
            self.root_node = Node('root', is_dir=True)
            self.endResetModel()
            return

        self.beginResetModel()

        self.root_node = build_tree_from_zip(data)

        self.endResetModel()

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1  # Only one column needed

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()
        return len(parent_node.children)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()
        child_node = parent_node.children[row]
        return self.createIndex(row, column, child_node)

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        child_node = index.internalPointer()
        parent_node = child_node.parent
        if parent_node == self.root_node or parent_node is None:
            return QtCore.QModelIndex()
        grandparent_node = parent_node.parent
        row = 0
        if grandparent_node:
            row = grandparent_node.children.index(parent_node)
        return self.createIndex(row, 0, parent_node)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            return node.name
        elif role == QtCore.Qt.DecorationRole:
            if node.is_links_file:
                return ui.get_icon('link', color=common.Color.Blue())
            elif node.is_dir:
                if node.is_internal_link:
                    return ui.get_icon('link', color=common.Color.Blue())
                else:
                    return ui.get_icon('folder')
            else:
                return ui.get_icon('file')
        elif role == QtCore.Qt.ToolTipRole:
            if node.is_links_file:
                return 'This is the .links file containing internal links'
            elif node.is_internal_link:
                return 'Internal Link'
        elif role == QtCore.Qt.FontRole:
            if node.is_internal_link or node.is_links_file:
                font = QtGui.QFont()
                font.setItalic(True)
                return font
        elif role == QtCore.Qt.ForegroundRole:
            if node.is_internal_link or node.is_links_file:
                return QtGui.QBrush(QtGui.QColor('blue'))
        return None


class TemplatePreviewView(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Preview Template')

        if not parent:
            common.set_stylesheet(self)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        self.setHeaderHidden(True)

        self.setModel(TreeModel(parent=self))
