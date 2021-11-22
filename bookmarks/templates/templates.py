# -*- coding: utf-8 -*-
"""The `templates.py` adds the methods and widgets needed to create items based
on zip template files.

The templates are used to create a job's or an asset's folder structure.

The list of template files are stored (in Windows) in the
`%localappdata%/{product}/{mode}_template` folder. The `{mode}` can be any
arbitary string, eg. 'job', or 'asset' as defined by `JobTemplateMode` and
`AssetTemplateMode`.

"""
import zipfile
import functools

from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import ui
from .. import images
from .. import contextmenu
from .. import settings
from .. import actions
from . import actions as template_actions


JobTemplateMode = 'job'
AssetTemplateMode = 'asset'

TemplateContentsRole = QtCore.Qt.UserRole
TemplatePathRole = TemplateContentsRole + 1

TEMPLATES_DIR = '{root}/{product}/{mode}_templates'

HINT_TEXT = 'Right-click or drag\'n\'drop to add ZIP template'


def get_template_folder(mode):
    """Returns the path where the ZIP template files are stored, associated with
    the given `mode`.

    Args:
        mode (str): A template mode, eg. `JobTemplateMode`.

    Returns:
        str: Path to the folder where the template zip files are stored.

    """
    common.check_type(mode, str)

    data_location = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.GenericDataLocation
    )
    path = TEMPLATES_DIR.format(
        root=data_location,
        product=common.PRODUCT,
        mode=mode
    )
    _dir = QtCore.QDir(path)
    if _dir.exists():
        return path
    if not _dir.mkpath('.'):
        raise OSError('Failed to create template directory.')
    return path


class TemplateContextMenu(contextmenu.BaseContextMenu):

    @common.error
    @common.debug
    def setup(self):
        self.refresh_menu()
        self.separator()
        self.add_menu()
        self.separator()
        if self.index:
            self.reveal_menu()
            self.separator()
            self.remove_menu()

    def add_menu(self):
        self.menu[contextmenu.key()] = {
            'text': 'Add new {} template...'.format(self.parent().mode()),
            'action': functools.partial(
                template_actions.pick_template,
                self.parent().mode()
            ),
            'icon': self.get_icon('add', color=common.GREEN)
        }

    def remove_menu(self):
        source = self.index.data(TemplatePathRole)
        self.menu[contextmenu.key()] = {
            'text': 'Delete',
            'action': functools.partial(
                template_actions.remove_zip_template,
                source
            ),
            'icon': self.get_icon('close', color=common.RED)
        }

    def refresh_menu(self):
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'action': self.parent().init_data,
            'icon': self.get_icon('refresh')
        }

    def reveal_menu(self):
        def reveal():
            actions.reveal(self.index.data(TemplatePathRole))

        self.menu[contextmenu.key()] = {
            'text': 'Show in file explorer...',
            'icon': self.get_icon('folder'),
            'action': reveal,
        }


class TemplateListDelegate(ui.ListWidgetDelegate):
    def __init__(self, parent=None):
        super(TemplateListDelegate, self).__init__(parent=parent)

    def createEditor(self, parent, option, index):
        """Custom editor for editing the template's name."""
        editor = QtWidgets.QLineEdit(parent=parent)
        editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        editor.setStyleSheet('padding: 0px; margin: 0px; border-radius: 0px;')
        validator = QtGui.QRegExpValidator(parent=editor)
        validator.setRegExp(QtCore.QRegExp(r'[\_\-a-zA-z0-9]+'))
        editor.setValidator(validator)
        return editor


class TemplateListWidget(ui.ListWidget):
    """Widget used to display a list of zip template files associated with
    the given `mode`.

    """

    def __init__(self, mode=JobTemplateMode, parent=None):
        super(TemplateListWidget, self).__init__(
            default_message='',
            parent=parent
        )
        self._mode = mode

        self._drag_in_progress = False

        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.installEventFilter(self)
        self.viewport().installEventFilter(self)
        self.setItemDelegate(TemplateListDelegate(parent=self))

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._connect_signals()

    def _connect_signals(self):
        self.model().dataChanged.connect(self.update_name)
        self.itemSelectionChanged.connect(self.save_selected)

        common.signals.templatesChanged.connect(self.save_selected)
        common.signals.templatesChanged.connect(self.init_data)
        common.signals.templatesChanged.connect(self.restore_selected)

    @QtCore.Slot()
    def init_data(self):
        """Loads the available zip template files from the template directory."""
        self.clear()
        self.blockSignals(True)

        dir_ = QtCore.QDir(get_template_folder(self.mode()))
        dir_.setNameFilters(['*.zip', ])

        h = common.ROW_HEIGHT()
        size = QtCore.QSize(1, h)

        off_pixmap = images.ImageCache.get_rsc_pixmap(
            'close', common.SEPARATOR, h)
        on_pixmap = images.ImageCache.get_rsc_pixmap(
            'check', common.GREEN, h)

        icon = QtGui.QIcon()
        icon.addPixmap(off_pixmap, QtGui.QIcon.Normal)
        icon.addPixmap(on_pixmap, QtGui.QIcon.Selected)

        height = self.contentsMargins().top() + self.contentsMargins().bottom()

        for f in dir_.entryList():
            if '.zip' not in f.lower():
                continue

            self.addItem(f, icon='icon')
            height += size.height() + self.spacing()

            item = self.item(self.count() - 1)
            item.setData(QtCore.Qt.DisplayRole, f.replace('.zip', ''))
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.DecorationRole, icon)

            path = '{}/{}'.format(dir_.path(), f)
            with zipfile.ZipFile(path) as zip:
                item.setData(TemplatePathRole, path)
                item.setData(TemplateContentsRole, [f.strip(
                    '/') for f in sorted(zip.namelist())])
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

            self.addItem(item)

        minheight = (size.height() + self.spacing())
        height = height if height >= minheight else minheight
        self.setFixedHeight(height)
        self.blockSignals(False)
        self.restore_selected()

    @QtCore.Slot()
    def save_selected(self):
        """Save the current selection to the local settings.

        """
        idx = self.currentRow()
        if idx < 0:
            return
        item = self.item(idx)
        if not item:
            return
        settings.instance().setValue(
            settings.UIStateSection,
            '{}/{}'.format(self.__class__.__name__, self.mode()),
            item.data(QtCore.Qt.DisplayRole)
        )

    @QtCore.Slot()
    def restore_selected(self):
        """Restore the previously selected item from the local settings.

        """
        v = settings.instance().value(
            settings.UIStateSection,
            '{}/{}'.format(self.__class__.__name__, self.mode())
        )
        if not v:
            return
        for n in range(self.count()):
            item = self.item(n)
            if v == item.data(QtCore.Qt.DisplayRole):
                self.setCurrentItem(item)
                return

    def mode(self):
        """The TemplateWidget's current mode.

        Returns:
            str: A template mode, eg. `AssetTable` or `JobTemplateMode`.

        """
        return self._mode

    @common.error
    @common.debug
    def create(self, name, destination):
        """The main method used to expand the selected zip template into a
        destination folder.

        Args:
            name (str): The name of the folder the contents of the zip archive will be saved to.
            destination (str): The destination folder where the new asset will be expanded to.

        """
        model = self.selectionModel()
        if not model.hasSelection():
            raise RuntimeError(
                'Must select a template to create a new {}'.format(self.mode()))
        index = next((f for f in model.selectedIndexes()),
                     QtCore.QModelIndex())
        if not index.isValid():
            raise RuntimeError('Invalid template selection.')

        template_actions.extract_zip_template(
            index.data(TemplatePathRole),
            destination,
            name
        )

    @QtCore.Slot(QtCore.QModelIndex)
    def update_name(self, index):
        """Updates the model data when a template's name has been edited."""
        oldpath = index.data(TemplatePathRole)
        oldname = QtCore.QFileInfo(oldpath).baseName()

        name = index.data(QtCore.Qt.DisplayRole)
        name = name.replace('.zip', '')

        newpath = '{}/{}.zip'.format(
            get_template_folder(self.mode()),
            name.replace(' ', '_')
        )
        if QtCore.QFile.rename(oldpath, newpath):
            self.model().setData(index, name, QtCore.Qt.DisplayRole)
            self.model().setData(index, newpath, TemplatePathRole)
        else:
            self.model().setData(index, oldname, QtCore.Qt.DisplayRole)
            self.model().setData(index, oldpath, TemplatePathRole)

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def dropMimeData(self, index, data, action):
        if not data.hasUrls():
            return False
        if action & self.supportedDropActions():
            return False
        return True

    def eventFilter(self, widget, event):
        if widget == self.viewport():
            if event.type() == QtCore.QEvent.DragEnter:
                if event.mimeData().hasUrls():
                    self._drag_in_progress = True
                    self.repaint()
                    event.accept()
                else:
                    event.ignore()
                return True

            if event.type() == QtCore.QEvent.DragLeave:
                self._drag_in_progress = False
                self.repaint()
                return True

            if event.type() == QtCore.QEvent.DragMove:
                if event.mimeData().hasUrls():
                    self._drag_in_progress = True
                    event.accept()
                else:
                    self._drag_in_progress = False
                    event.ignore()
                return True

            if event.type() == QtCore.QEvent.Drop:
                self._drag_in_progress = False
                self.repaint()

                # Let's copy the template file and reload the list
                for url in event.mimeData().urls():
                    source = url.toLocalFile()
                    if zipfile.is_zipfile(source):
                        template_actions.add_zip_template(source, self.mode())

                return True

        if event.type() == QtCore.QEvent.Paint:
            option = QtWidgets.QStyleOption()
            option.initFrom(self)
            hover = option.state & QtWidgets.QStyle.State_MouseOver

            painter = QtGui.QPainter()
            painter.begin(self.viewport())

            painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
            painter.setRenderHint(
                QtGui.QPainter.SmoothPixmapTransform, on=True)

            painter.setPen(common.SECONDARY_TEXT)

            _ = painter.setOpacity(0.6) if hover else painter.setOpacity(0.3)

            o = common.INDICATOR_WIDTH() * 2
            _o = common.ROW_SEPARATOR()
            rect = self.rect().adjusted(_o, _o, -_o, -_o)
            if self._drag_in_progress:
                op = painter.opacity()
                painter.setOpacity(1.0)
                pen = QtGui.QPen(common.GREEN)
                pen.setWidthF(_o)
                painter.setPen(pen)
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.drawRoundedRect(rect, o, o)
                painter.setOpacity(op)

            pen = QtGui.QPen(common.SEPARATOR)
            pen.setWidthF(common.ROW_SEPARATOR())
            painter.setPen(pen)
            painter.setBrush(common.SEPARATOR)
            painter.drawRoundedRect(rect, o, o)

            o = common.INDICATOR_WIDTH()
            painter.setPen(common.TEXT)

            if self.count() > 0:
                return False

            painter.drawText(
                rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
                HINT_TEXT,
                boundingRect=self.rect(),
            )
            painter.end()

        return False

    def showEvent(self, event):
        QtCore.QTimer.singleShot(100, self.init_data)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = TemplateContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH() * 0.15, common.WIDTH() * 0.2)


class TemplatesPreviewWidget(QtWidgets.QListWidget):
    """List widget used to peak into the contents of a zip template file.

    """

    def __init__(self, parent=None):
        super(TemplatesPreviewWidget, self).__init__(parent=parent)
        self.installEventFilter(self)

    @QtCore.Slot(tuple)
    def init_data(self, files):
        """Slot responsible for displaying a list of file names.

        Args:
            files (tuple): A list of file names.

        """
        self.clear()

        size = QtCore.QSize(0, common.ROW_HEIGHT() * 0.8)

        folder_pixmap = images.ImageCache.get_rsc_pixmap(
            'folder', common.SECONDARY_TEXT, common.MARGIN())
        folder_icon = QtGui.QIcon()
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Normal)
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Selected)
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Disabled)

        file_pixmap = images.ImageCache.get_rsc_pixmap(
            'file', common.GREEN, common.MARGIN(), opacity=0.5)
        file_icon = QtGui.QIcon()
        file_icon.addPixmap(file_pixmap, QtGui.QIcon.Normal)
        file_icon.addPixmap(file_pixmap, QtGui.QIcon.Selected)
        file_icon.addPixmap(file_pixmap, QtGui.QIcon.Disabled)

        for f in files:
            if QtCore.QFileInfo(f).suffix():
                icon = file_icon
            else:
                icon = folder_icon

            item = QtWidgets.QListWidgetItem(parent=self)
            item.setData(QtCore.Qt.FontRole, common.font_db.secondary_font(
                common.SMALL_FONT_SIZE())[0])
            item.setData(QtCore.Qt.DisplayRole, f)
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.DecorationRole, icon)
            item.setFlags(QtCore.Qt.ItemIsSelectable)

            self.addItem(item)

    def eventFilter(self, widget, event):
        if widget is not self:
            return False

        if event.type() is QtCore.QEvent.Paint:
            if self.model().rowCount():
                return False
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setBrush(common.DARK_BG)
            painter.setPen(QtCore.Qt.NoPen)

            painter.setFont(common.font_db.secondary_font(
                common.SMALL_FONT_SIZE())[0])
            painter.drawRect(self.rect())
            o = common.MEDIUM_FONT_SIZE()
            rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
            painter.drawText(
                rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
                'Template preview',
                boundingRect=self.rect(),
            )
            painter.end()
            return True
        return False

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH() * 0.15, common.WIDTH() * 0.2)


class TemplatesWidget(QtWidgets.QSplitter):

    def __init__(self, mode, parent=None):
        super(TemplatesWidget, self).__init__(parent=parent)
        self._mode = mode

        self.template_list_widget = None
        self.template_contents_widget = None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMaximumHeight(common.WIDTH() * 0.3)

        self._create_UI()
        self._connect_signals()

    def mode(self):
        return self._mode

    def _create_UI(self):
        if not self.parent():
            common.set_custom_stylesheet(self)
        self.template_list_widget = TemplateListWidget(self._mode, parent=self)
        self.template_contents_widget = TemplatesPreviewWidget(parent=self)
        self.addWidget(self.template_list_widget)
        self.addWidget(self.template_contents_widget)
        self.setSizes((common.WIDTH(), 0))

    def _connect_signals(self):
        model = self.template_list_widget.selectionModel()
        model.selectionChanged.connect(self.itemActivated)

    @QtCore.Slot()
    def itemActivated(self, selectionList):
        """Slot called when a template was selected by the user.

        It will load and display the contents of the zip file in the
        `template_contents_widget`.

        Args:
            selectionList (QItemSelection): A QItemSelection instance of QModelIndexes.

        """
        if not selectionList:
            self.template_contents_widget.clear()
            return
        index = selectionList.first().topLeft()
        if not index.isValid():
            self.template_contents_widget.clear()
            return

        self.template_contents_widget.init_data(
            index.data(TemplateContentsRole))

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH(), common.HEIGHT())
