"""The module used to create job and asset items based on zip template files.

The template files usually contain a folder structure used to define the skeleton
of a project file structure.


The list of template files are read from/and saved to the folder returned by
:func:`get_template_folder`.

The template mode can be any arbitrary string - we're defining them as
:attr:`JobTemplateMode` and :attr:`AssetTemplateMode`.

"""
import functools
import zipfile

from PySide2 import QtCore, QtWidgets, QtGui

from . import actions
from . import common
from . import contextmenu
from . import images
from . import ui

JobTemplateMode = 'job'
AssetTemplateMode = 'asset'

TemplateContentsRole = QtCore.Qt.UserRole
TemplatePathRole = TemplateContentsRole + 1

TEMPLATES_DIR = '{root}/{product}/{mode}_templates'


def get_template_folder(mode):
    """Returns the path where the ZIP template files are stored, associated with
    the given `mode`.

    Args:
        mode (str): A template mode, e.g. `JobTemplateMode`.

    Returns:
        str: Path to the folder where the template zip files are stored.

    """
    common.check_type(mode, str)

    data_location = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.GenericDataLocation
    )
    path = TEMPLATES_DIR.format(
        root=data_location,
        product=common.product,
        mode=mode
    )
    _dir = QtCore.QDir(path)
    if _dir.exists():
        return path
    if not _dir.mkpath('.'):
        raise OSError('Failed to create template directory.')
    return path


class TemplateContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with the :class:`TemplatesWidget`.

    """

    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
        self.refresh_menu()
        self.separator()
        self.add_menu()
        self.separator()
        if self.index:
            self.reveal_menu()
            self.separator()
            self.remove_menu()

    def add_menu(self):
        """Add action menu.

        """
        self.menu[contextmenu.key()] = {
            'text': f'Add new {self.parent().mode()} template...',
            'action': functools.partial(
                actions.pick_template,
                self.parent().mode()
            ),
            'icon': ui.get_icon('add', color=common.color(common.color_green))
        }

    def remove_menu(self):
        """Remove action menu.

        """
        source = self.index.data(TemplatePathRole)
        self.menu[contextmenu.key()] = {
            'text': 'Delete',
            'action': functools.partial(
                actions.remove_zip_template,
                source
            ),
            'icon': ui.get_icon('close', color=common.color(common.color_red))
        }

    def refresh_menu(self):
        """Refresh action menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'action': self.parent().init_data,
            'icon': ui.get_icon('refresh')
        }

    def reveal_menu(self):
        """Reveal action menu.

        """

        def _reveal():
            actions.reveal(self.index.data(TemplatePathRole))

        self.menu[contextmenu.key()] = {
            'text': 'Show in file explorer...',
            'icon': ui.get_icon('folder'),
            'action': _reveal,
        }


class TemplateListDelegate(ui.ListWidgetDelegate):
    """Delegate associated with :class:`TemplateListWidget`.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def createEditor(self, parent, option, index):
        """Custom editor for editing the template's name.

        """
        editor = super().createEditor(parent, option, index)
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
            default_message='Right-click or drag\'n\'drop to add ZIP template',
            default_icon='folder',
            parent=parent,
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
        super()._connect_signals()

        self.model().dataChanged.connect(self.update_name)
        self.selectionModel().selectionChanged.connect(
            functools.partial(
                common.save_selection,
                self,
            )
        )
        common.signals.templatesChanged.connect(self.init_data)

    @QtCore.Slot()
    def init_data(self):
        """Loads the available zip template files from the template directory.

        """
        selected_index = common.get_selected_index(self)
        selected_name = selected_index.data(
            QtCore.Qt.DisplayRole
        ) if selected_index.isValid() else None

        self.selectionModel().blockSignals(True)

        self.clear()

        dir_ = QtCore.QDir(get_template_folder(self.mode()))
        dir_.setNameFilters(['*.zip', ])

        h = common.size(common.size_row_height)
        size = QtCore.QSize(1, h)

        off_pixmap = images.ImageCache.rsc_pixmap(
            'close', common.color(common.color_separator), h)
        on_pixmap = images.ImageCache.rsc_pixmap(
            'check', common.color(common.color_green), h)

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

            path = f'{dir_.path()}/{f}'
            with zipfile.ZipFile(path) as zip:
                item.setData(TemplatePathRole, path)
                item.setData(TemplateContentsRole, [f.strip(
                    '/') for f in sorted(zip.namelist())])
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

            self.addItem(item)

        if selected_name:
            for idx in range(self.model().rowCount()):
                index = self.model().index(idx, 0)
                if index.data(QtCore.Qt.DisplayRole) == selected_name:
                    self.selectionModel().select(
                        index, QtCore.QItemSelectionModel.ClearAndSelect
                    )

        self.selectionModel().blockSignals(False)

        common.restore_selection(self)
        self.progressUpdate.emit('')

    def mode(self):
        """The TemplateWidget's current mode.

        Returns:
            str: A template mode, e.g. `AssetTable` or `JobTemplateMode`.

        """
        return self._mode

    def create(self, name, destination):
        """The main method used to expand the selected zip template into a
        destination folder.

        Args:
            name (str): The name of the folder the contents of the zip archive will be saved to.
            destination (str): The destination folder where the new asset will be expanded to.

        """
        index = common.get_selected_index(self)
        if not index.isValid():
            raise RuntimeError(f'Select a template to add a new {self.mode()}')

        actions.extract_zip_template(
            index.data(TemplatePathRole),
            destination,
            name
        )

    @QtCore.Slot(QtCore.QModelIndex)
    def update_name(self, index):
        """Updates the model data when a template's name has been edited.

        """
        if not index.isValid():
            return

        previous_path = index.data(TemplatePathRole)
        if not previous_path:
            return
        previous_name = QtCore.QFileInfo(previous_path).baseName()

        name = index.data(QtCore.Qt.DisplayRole)
        name = name.replace('.zip', '')

        new_path = '{}/{}.zip'.format(
            get_template_folder(self.mode()),
            name.replace(' ', '_')
        )

        if not new_path:
            return

        if QtCore.QFile.rename(previous_path, new_path):
            self.model().setData(index, name, QtCore.Qt.DisplayRole)
            self.model().setData(index, new_path, TemplatePathRole)
        else:
            self.model().setData(index, previous_name, QtCore.Qt.DisplayRole)
            self.model().setData(index, previous_path, TemplatePathRole)

    def supportedDropActions(self):
        """Returns the supported drop actions.

        """
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def dropMimeData(self, index, data, action):
        """Returns the drop mime data.

        """
        if not data.hasUrls():
            return False
        if action & self.supportedDropActions():
            return False
        return True

    def eventFilter(self, widget, event):
        """Event filter handler.

        """
        super().eventFilter(widget, event)

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
                        actions.add_zip_template(source, self.mode())

                return True

        if event.type() == QtCore.QEvent.Paint:
            if widget != self.viewport():
                return False
            option = QtWidgets.QStyleOption()
            option.initFrom(self)
            hover = option.state & QtWidgets.QStyle.State_MouseOver

            painter = QtGui.QPainter()
            painter.begin(self.viewport())

            painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
            painter.setRenderHint(
                QtGui.QPainter.SmoothPixmapTransform, on=True)

            painter.setPen(common.color(common.color_secondary_text))

            _ = painter.setOpacity(0.6) if hover else painter.setOpacity(0.3)

            o = common.size(common.size_indicator) * 2
            _o = common.size(common.size_separator)
            rect = self.rect().adjusted(_o, _o, -_o, -_o)
            if self._drag_in_progress:
                op = painter.opacity()
                painter.setOpacity(1.0)
                pen = QtGui.QPen(common.color(common.color_green))
                pen.setWidthF(_o)
                painter.setPen(pen)
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.drawRoundedRect(rect, o, o)
                painter.setOpacity(op)

            pen = QtGui.QPen(common.color(common.color_separator))
            pen.setWidthF(common.size(common.size_separator))
            painter.setPen(pen)
            painter.setBrush(common.color(common.color_separator))
            painter.drawRoundedRect(rect, o, o)

        return False

    def showEvent(self, event):
        """Event handler.

        """
        QtCore.QTimer.singleShot(100, self.init_data)

    def contextMenuEvent(self, event):
        """Event handler.

        """
        item = self.itemAt(event.pos())
        menu = TemplateContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width) * 0.15,
            common.size(common.size_width) * 0.2
        )


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

        size = QtCore.QSize(0, common.size(common.size_row_height) * 0.8)

        folder_pixmap = images.ImageCache.rsc_pixmap(
            'folder', common.color(common.color_secondary_text),
            common.size(common.size_margin))
        folder_icon = QtGui.QIcon()
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Normal)
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Selected)
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Disabled)

        file_pixmap = images.ImageCache.rsc_pixmap(
            'file', common.color(common.color_green), common.size(common.size_margin),
            opacity=0.5)
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
                common.size(common.size_font_small))[0])
            item.setData(QtCore.Qt.DisplayRole, f)
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.DecorationRole, icon)
            item.setFlags(QtCore.Qt.ItemIsSelectable)

            self.addItem(item)

    def eventFilter(self, widget, event):
        """Event filter handler.

        """
        if widget is not self:
            return False

        if event.type() is QtCore.QEvent.Paint:
            if self.model().rowCount():
                return False
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setBrush(common.color(common.color_dark_background))
            painter.setPen(QtCore.Qt.NoPen)

            painter.setFont(
                common.font_db.secondary_font(common.size(common.size_font_small))[0])
            painter.drawRect(self.rect())
            o = common.size(common.size_font_medium)
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
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width) * 0.15,
            common.size(common.size_width) * 0.2
        )


class TemplatesWidget(QtWidgets.QSplitter):
    """Main template list with a template content preview widget.

    """

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
        self.setMaximumHeight(common.size(common.size_width) * 0.3)

        self._create_ui()
        self._connect_signals()

    def mode(self):
        """The current template mode.

        """
        return self._mode

    def _create_ui(self):
        if not self.parent():
            common.set_stylesheet(self)
        self.template_list_widget = TemplateListWidget(self._mode, parent=self)
        self.template_contents_widget = TemplatesPreviewWidget(parent=self)
        self.addWidget(self.template_list_widget)
        self.addWidget(self.template_contents_widget)
        self.setSizes((1, 0))

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
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width),
            common.size(common.size_height)
        )
