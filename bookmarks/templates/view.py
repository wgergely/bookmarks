import collections
import functools
import os

from PySide2 import QtWidgets, QtCore, QtGui

from .error import *
from .lib import *
from .model import TemplatesModel
from .preview import TemplatePreviewView
from .. import actions
from .. import common
from .. import contextmenu
from .. import images
from .. import log
from .. import shortcuts
from .. import ui
from ..editor import base
from ..editor.base_widgets import ThumbnailEditorWidget
from ..links.lib import LinksAPI
from ..links.view import LinksEditor


def show():
    close()

    if common.templates_editor is None:
        common.templates_editor = TemplatesMainWidget()
    common.templates_editor.open()


def close():
    if common.templates_editor is None:
        return

    try:
        common.templates_editor.close()
        common.templates_editor.deleteLater()
        common.templates_editor = None
    except Exception as e:
        log.error(__name__, e)


class TemplatesContextMenu(contextmenu.BaseContextMenu):

    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
        self.new_template_menu()
        self.separator()
        self.template_to_folder_menu()
        self.rename_template_menu()
        self.separator()
        self.thumbnail_menu()
        self.separator()
        self.add_link_preset_menu()
        self.remove_link_preset_menu()
        self.separator()
        self.remove_template_menu()
        self.separator()
        self.remove_all_templates_menu()
        self.separator()
        self.add_view_menu()

    def new_template_menu(self):
        """Add default template menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Add New',
            'icon': ui.get_icon('add', color=common.Color.Green()),
            'action': self.parent().add_new,
            'shortcut': shortcuts.get(
                shortcuts.TemplatesViewShortcuts,
                shortcuts.NewTemplate
            ).key(),
            'description': shortcuts.hint(
                shortcuts.TemplatesViewShortcuts,
                shortcuts.NewTemplate
            )
        }

        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        # Add default template menu
        if common.active('root'):
            self.menu[contextmenu.key()] = {
                'text': 'Import Default Template',
                'icon': ui.get_icon('arrow_right', color=common.Color.Yellow()),
                'action': self.parent().add_default_template,
                'shortcut': shortcuts.get(
                    shortcuts.TemplatesViewShortcuts,
                    shortcuts.AddDefaultTemplate
                ).key(),
                'description': shortcuts.hint(
                    shortcuts.TemplatesViewShortcuts,
                    shortcuts.AddDefaultTemplate
                )
            }

    def remove_template_menu(self):
        """Add remove template menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if not node.is_leaf():
            return

        self.menu[contextmenu.key()] = {
            'text': f'Remove',
            'icon': ui.get_icon('close', color=common.Color.Red()),
            'action': self.parent().remove_template,
            'shortcut': shortcuts.get(
                shortcuts.TemplatesViewShortcuts,
                shortcuts.RemoveTemplate
            ).key(),
            'description': shortcuts.hint(
                shortcuts.TemplatesViewShortcuts,
                shortcuts.RemoveTemplate
            )
        }

    def remove_all_templates_menu(self):
        """Add remove all templates menu.

        """
        if not self.index.isValid():
            return

        self.menu[contextmenu.key()] = {
            'text': f'Remove All',
            'icon': ui.get_icon('close', color=common.Color.Red()),
            'action': self.parent().remove_all_templates,
            'shortcut': shortcuts.get(
                shortcuts.TemplatesViewShortcuts,
                shortcuts.RemoveAllTemplates
            ).key(),
            'description': shortcuts.hint(
                shortcuts.TemplatesViewShortcuts,
                shortcuts.RemoveAllTemplates
            )
        }

    def thumbnail_menu(self):
        """Add the thumbnail menu."""
        if not self.index.isValid():
            return

        if not self.index.column() == 0:
            return

        node = self.index.internalPointer()
        if not node:
            return

        if not node.is_leaf():
            return

        self.menu[contextmenu.key()] = {
            'text': 'Pick thumbnail...',
            'icon': ui.get_icon('image'),
            'action': self.parent().pick_thumbnail,
            'help': 'Set the thumbnail for the template.',
        }
        self.menu[contextmenu.key()] = {
            'text': 'Clear thumbnail',
            'icon': ui.get_icon('image'),
            'action': self.parent().clear_thumbnail,
            'help': 'Clear the thumbnail for the template.',
        }

    def add_link_preset_menu(self):
        """Add the add link preset menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if not node.is_leaf():
            return

        if not common.active('root'):
            return

        k = 'Set Link Preset'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('link')

        preset = LinksAPI.presets()
        for _k in preset:
            self.menu[k][_k] = {
                'text': _k,
                'icon': ui.get_icon('link', color=common.Color.Blue()),
                'action': functools.partial(self.parent().add_link_preset, _k),
                'description': f'Add a link preset: {_k}',
            }

    def remove_link_preset_menu(self):
        """Add the remove link preset menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if not node.is_leaf():
            return

        self.menu[contextmenu.key()] = {
            'text': 'Clear Link Preset',
            'action': self.parent().remove_link_preset,
            'help': 'Clear the link preset from the template.',
        }

    def template_to_folder_menu(self):
        """Add the extract template menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if not node.is_leaf():
            return

        self.menu[contextmenu.key()] = {
            'text': 'Extract Template...',
            'icon': ui.get_icon('add_folder', color=common.Color.Green()),
            'action': self.parent().template_to_folder,
            'help': 'Extract the template contents to a folder.',
        }

    def rename_template_menu(self):
        """Add the rename template menu.

        """
        if not self.index.isValid():
            return

        node = self.index.internalPointer()
        if not node:
            return

        if not node.is_leaf():
            return

        self.menu[contextmenu.key()] = {
            'text': 'Rename',
            'icon': ui.get_icon('todo'),
            'action': self.parent().rename_template,
            'description': 'Rename the template.',
        }

    def add_view_menu(self):
        """Add view menu.

        """
        self.menu[contextmenu.key()] = {
            'text': 'Refresh',
            'icon': ui.get_icon('refresh'),
            'action': self.parent().init_data,
            'shortcut': shortcuts.get(
                shortcuts.TemplatesViewShortcuts,
                shortcuts.ReloadTemplates
            ).key(),
            'description': shortcuts.hint(
                shortcuts.TemplatesViewShortcuts,
                shortcuts.ReloadTemplates
            ),
        }
        self.menu[contextmenu.key()] = {
            'text': 'Expand All',
            'icon': ui.get_icon('expand'),
            'action': (self.parent().expandAll),
            'help': 'Expand all items.',
        }
        self.menu[contextmenu.key()] = {
            'text': 'Collapse All',
            'icon': ui.get_icon('collapse'),
            'action': (self.parent().collapseAll),
            'help': 'Collapse all items.',
        }


class TemplateThumbnailPicker(ThumbnailEditorWidget):

    def _get_source_pixmap(self):
        return images.rsc_pixmap(
            self.fallback_thumb, None, self.rect().height()
        ), common.Color.VeryDarkBackground()


class LinksComboBox(QtWidgets.QComboBox):
    """A combo box for selecting links presets."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = QtWidgets.QListView(self)
        self.setView(view)

        self.init_data()

    def init_data(self):
        self.clear()
        self.addItem('No links preset', None)

        presets = LinksAPI.presets()
        for name in presets:
            self.addItem(name, userData=name)
            self.setItemData(self.count() - 1, presets[name], QtCore.Qt.ToolTipRole)
            self.setItemData(self.count() - 1, presets[name], QtCore.Qt.StatusTipRole)
            self.setItemData(self.count() - 1, presets[name], QtCore.Qt.WhatsThisRole)
            self.setItemData(
                self.count() - 1,
                ui.get_icon('link', color=common.Color.Blue()),
                QtCore.Qt.DecorationRole
            )


class AddLinkPresetEditor(QtWidgets.QDialog):
    """Dialog for adding a new links preset."""
    presetSaved = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.name_editor = None
        self.links_editor = None
        self.ok_button = None
        self.cancel_button = None

        self.setWindowTitle('New Links Preset')
        self.setWindowFlags(QtCore.Qt.Window)
        self.setModal(True)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)

        self.layout().setSpacing(common.Size.Margin())
        o = common.Size.Margin(0.66)
        self.layout().setContentsMargins(o, o, o, o)

        grp = ui.get_group(parent=self)

        row = ui.add_row('Name', height=None, parent=grp)
        self.name_editor = ui.LineEdit(required=True, parent=grp)
        self.name_editor.setPlaceholderText('Enter a name...')
        row.layout().addWidget(self.name_editor)

        row = ui.add_row('Links', height=None, parent=grp)
        self.links_editor = common.TokenEditor(parent=row)
        self.links_editor.setPlaceholderText(
            'Enter relative folder links separated by new lines, for example:\n\n'
            '\n'
            'assets/characters\n'
            'assets/props\n'
            'assets/environment\n'
        )
        row.layout().addWidget(self.links_editor, 1)

        row = ui.add_row(None, height=None, parent=self)
        self.ok_button = ui.PaintedButton('Save', parent=row)
        row.layout().addWidget(self.ok_button, 1)

        self.cancel_button = ui.PaintedButton('Cancel', parent=row)
        row.layout().addWidget(self.cancel_button, 0)

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    @common.error
    @common.debug
    @QtCore.Slot(int)
    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            return super().done(r)

        if not self.name_editor.text():
            raise ValueError('Name is required.')
        if not self.links_editor.toPlainText():
            raise ValueError('Links cannot be empty.')

        if self.name_editor.text() in LinksAPI.presets():
            raise ValueError(f'Name "{self.name_editor.text()}" already exists.')

        self.save_preset_to_database()
        self.presetSaved.emit()
        return super().done(r)

    def save_preset_to_database(self):
        name = self.name_editor.text()
        data = self.links_editor.toPlainText()
        data = data.split('\n')
        data = [line.replace('\\', '/').strip('/') for line in data if line]

        LinksAPI._save_data_to_database(name, data)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultWidth()
        )


class AddTemplateDialog(QtWidgets.QDialog):
    """Dialog for adding a new template."""

    def __init__(self, mode=None, parent=None):
        super().__init__(parent=parent)

        self.thumbnail_editor = None
        self.name_editor = None
        self.description_editor = None
        self.folder_editor = None
        self.links_editor = None

        self._mode = mode

        self.ok_button = None
        self.cancel_button = None

        self.setWindowTitle('New Template')
        self.setWindowFlags(QtCore.Qt.Window)
        self.setModal(True)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        o = common.Size.Margin(0.66)
        self.layout().setSpacing(o)
        self.layout().setContentsMargins(o, o, o, o)

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(widget)
        widget.layout().setAlignment(QtCore.Qt.AlignCenter)
        widget.setContentsMargins(0, 0, 0, 0)
        widget.setStyleSheet(f'background-color: {common.Color.VeryDarkBackground(qss=True)};')
        self.layout().addWidget(widget)
        self.thumbnail_editor = TemplateThumbnailPicker(fallback_thumb='folder_sm', parent=self)
        widget.layout().addWidget(self.thumbnail_editor)

        main_row = ui.add_row(None, vertical=True, height=None, parent=self)
        main_row.layout().setAlignment(QtCore.Qt.AlignCenter)

        main_row.layout().addStretch(10)

        grp = ui.get_group(parent=main_row)
        row = ui.add_row('Name', height=None, parent=grp)

        self.name_editor = ui.LineEdit(required=True, parent=grp)
        self.name_editor.setValidator(base.name_validator)
        self.name_editor.setPlaceholderText('Enter a name...')

        row.layout().addWidget(self.name_editor)

        row = ui.add_row('Description', height=None, parent=grp)
        self.description_editor = ui.LineEdit(parent=row)
        self.description_editor.setPlaceholderText('Enter a description...')
        row.layout().addWidget(self.description_editor)

        grp = ui.get_group(parent=main_row)
        row = ui.add_row('Contents', height=None, parent=grp)
        self.folder_editor = ui.LineEdit(required=True, parent=grp)
        self.folder_editor.setPlaceholderText('Enter a folder path, or click to browse...')
        action = QtWidgets.QAction(self.folder_editor)
        action.setIcon(ui.get_icon('folder', color=common.Color.Text()))
        self.folder_editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

        row.layout().addWidget(self.folder_editor)
        ui.add_description(
            'The content of the template is normally a folder hierarchy. '
            'Files can be included but total template size is capped at 100MB. '
            f'If you want to use a <span style="color: {common.Color.Blue(qss=True)};">.links</span> preset for '
            f'mapping the asset paths, you can select an empty folder and select a preset below.',
            parent=grp
        )

        row = ui.add_row('Links', height=None, parent=grp)
        self.links_editor = LinksComboBox(parent=grp)
        row.layout().addWidget(self.links_editor, 1)
        self.new_preset_button = ui.PaintedButton('New Preset', parent=grp)
        row.layout().addWidget(self.new_preset_button, 0)
        ui.add_description(
            'Links are relative folder paths '
            f'stored in a <span style="color: {common.Color.Blue(qss=True)};">.links</span> file. '
            'They allow you to set asset paths for placeholder folders, '
            'which is useful when an asset contains multiple task folders.',
            parent=grp
        )

        grp = ui.get_group(parent=main_row)
        row = ui.add_row('Type', height=None, parent=grp)
        self.type_editor = QtWidgets.QComboBox(parent=grp)
        self.type_editor.setView(QtWidgets.QListView(self.type_editor))

        if self._mode == TemplateType.DatabaseTemplate or self._mode is None:
            self.type_editor.addItem(TemplateType.DatabaseTemplate, userData=TemplateType.DatabaseTemplate)

        if self._mode == TemplateType.UserTemplate or self._mode is None:
            self.type_editor.addItem(TemplateType.UserTemplate, userData=TemplateType.UserTemplate)

        ui.add_description(
            f'Select the template\'s type. '
            f'<span style="color: {common.Color.Text(qss=True)};">{TemplateType.DatabaseTemplate.value}</span> '
            f'are shared across all users. <span style="color: {common.Color.Text(qss=True)};">{TemplateType.UserTemplate.value}</span> '
            'are private to you.',
            parent=grp
        )
        row.layout().addWidget(self.type_editor, 1)

        main_row.layout().addStretch(10)

        row = ui.add_row(None, height=None, parent=main_row)
        self.ok_button = ui.PaintedButton('Save', parent=row)
        row.layout().addWidget(self.ok_button, 1)

        self.cancel_button = ui.PaintedButton('Cancel', parent=row)
        row.layout().addWidget(self.cancel_button, 0)

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.folder_editor.actions()[-1].triggered.connect(self.pick_folder)
        self.new_preset_button.clicked.connect(self.add_new_preset)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(1.4),
            common.Size.DefaultHeight(0.1)
        )

    def get_data(self):
        _type = self.type_editor.currentData()

        if _type == TemplateType.DatabaseTemplate.value:
            _type = TemplateType.DatabaseTemplate
        if _type == TemplateType.UserTemplate.value:
            _type = TemplateType.UserTemplate

        return {
            'name': self.name_editor.text(),
            'description': self.description_editor.text(),
            'folder': self.folder_editor.text(),
            'links': self.links_editor.currentData(),
            'type': _type,
            'image': self.thumbnail_editor.image()
        }

    @common.error
    @common.debug
    @QtCore.Slot()
    def pick_folder(self):
        """Pick a folder."""
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            'Select the folder hierarchy to use as the template:',
            QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DesktopLocation)
        )
        if not path:
            return
        if not os.path.exists(path):
            raise ValueError(f'Path "{path}" does not exist.')
        self.folder_editor.setText(path)

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_new_preset(self):
        """Add a new links preset."""
        dialog = AddLinkPresetEditor(parent=self)
        dialog.presetSaved.connect(self.links_editor.init_data)
        dialog.exec_()

    @common.error
    @common.debug
    @QtCore.Slot(int)
    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            return super().done(r)

        if not self.name_editor.text():
            raise ValueError('Name is required.')
        if not self.folder_editor.text():
            raise ValueError('Folder path is required.')

        return super().done(r)


class ExtractTemplateDialog(QtWidgets.QDialog):
    """Dialog for selecting a folder to extract the template to."""
    folderSelected = QtCore.Signal(str, bool)  # path, extract_to_links

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.folder_editor = None
        self.pick_folder_button = None
        self.extract_to_links_toggle = None
        self.ok_button = None
        self.cancel_button = None

        self.setWindowTitle('Extract Template')
        self.setWindowFlags(QtCore.Qt.Window)
        self.setModal(True)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.Size.Margin(0.66)
        self.layout().setSpacing(o)
        self.layout().setContentsMargins(o, o, o, o)

        grp = ui.get_group(parent=self)

        row = ui.add_row(None, height=None, parent=grp)

        self.folder_editor = ui.LineEdit(required=True, parent=grp)
        self.folder_editor.setPlaceholderText('Enter a folder path...')
        action = QtWidgets.QAction(self.folder_editor)
        icon = ui.get_icon('folder', color=common.Color.Text())
        action.setIcon(icon)
        self.folder_editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

        row.layout().addWidget(self.folder_editor, 1)

        row = ui.add_row('Extract to Links?', height=None, parent=grp)
        self.extract_to_links_toggle = QtWidgets.QCheckBox('Extract to Links', parent=grp)
        row.layout().addStretch(1)
        row.layout().addWidget(self.extract_to_links_toggle, 0)

        ui.add_description(
            f'If the <span style="color: {common.Color.Green(qss=True)};">"Extract to Links"</span> option is checked, '
            f'the contents of the template will be extracted into each folder path defined in the .links file. '
            f'Ensure the .links file is correct and the template is structured '
            f'properly before proceeding, as this action cannot be undone.',
            icon=ui.get_icon('alert', color=common.Color.SecondaryText()),
            label=None,
            parent=grp
        )

        self.layout().addStretch(1)

        row = ui.add_row(None, height=None, parent=self)
        self.ok_button = ui.PaintedButton('Extract', parent=row)
        row.layout().addWidget(self.ok_button, 1)

        self.cancel_button = ui.PaintedButton('Cancel', parent=row)
        row.layout().addWidget(self.cancel_button, 0)

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.folder_editor.actions()[-1].triggered.connect(self.pick_folder)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight(0.1)
        )

    def get_data(self):
        p = self.folder_editor.text()
        return {
            'path': p.replace('\\', '/').rstrip('/'),
            'extract_to_links': self.extract_to_links_toggle.isChecked()
        }

    @common.error
    @common.debug
    @QtCore.Slot()
    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            return super().done(r)

        if not self.folder_editor.text():
            raise ValueError('Folder path is required.')

        self.folderSelected.emit(
            self.folder_editor.text(),
            self.extract_to_links_toggle.isChecked()
        )

        return super().done(r)

    @common.error
    @common.debug
    @QtCore.Slot()
    def pick_folder(self):
        """Pick a folder."""
        p = common.active('root', path=True)

        if not p:
            p = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DesktopLocation)

        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select the folder to extract the template to:', p
        )
        if not path:
            return
        if not os.path.exists(path):
            raise ValueError(f'Path "{path}" does not exist.')
        self.folder_editor.setText(path)


class RenameTemplateDialog(QtWidgets.QDialog):

    def __init__(self, name, parent=None):
        super().__init__(parent=parent)

        self._current_name = name

        self.name_editor = None
        self.ok_button = None
        self.cancel_button = None

        self.setWindowTitle('Rename Template')

        self._create_ui()
        self._connect_signals()

    @common.error
    @common.debug
    @QtCore.Slot()
    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            return super().done(r)

        if not self.name_editor.text():
            raise ValueError('Name is required.')

        return super().done(r)

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.Size.Margin(0.66)
        self.layout().setSpacing(o)
        self.layout().setContentsMargins(o, o, o, o)

        grp = ui.get_group(parent=self)

        row = ui.add_row('Name', height=None, parent=grp)
        self.name_editor = ui.LineEdit(required=True, parent=grp)
        self.name_editor.setPlaceholderText('Enter a new name...')
        self.name_editor.setValidator(base.name_validator)
        self.name_editor.setText(self._current_name)
        row.layout().addWidget(self.name_editor)

        row = ui.add_row(None, height=None, parent=self)
        self.ok_button = ui.PaintedButton('Rename', parent=row)
        row.layout().addWidget(self.ok_button, 1)

        self.cancel_button = ui.PaintedButton('Cancel', parent=row)
        row.layout().addWidget(self.cancel_button, 0)

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_data(self):
        return self.name_editor.text()


class TemplatesViewDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate class for the :class:`TemplatesView`."""

    @staticmethod
    def paintmethod(func):
        """Decorator for painting methods."""

        @functools.wraps(func)
        def wrapper(self, painter, *args, **kwargs):
            painter.save()
            try:
                return func(self, painter, *args, **kwargs)
            finally:
                painter.restore()

        return wrapper

    def paint(self, painter, option, index):
        if not index.isValid():
            return

        node = index.internalPointer()
        if not node:
            return

        self._paint_background(painter, option, index, node)

        if index.column() == 0:
            self._paint_col0(painter, option, index, node)
        elif index.column() == 1:
            self._paint_col1(painter, option, index, node)
        elif index.column() == 2:
            self._paint_col2(painter, option, index, node)
        elif index.column() == 3:
            self._paint_col3(painter, option, index, node)

        if node.is_leaf() and index.row() == 0:
            # Draw gradient from bottom to top
            rect = QtCore.QRect(option.rect)
            color = QtGui.QColor(common.Color.VeryDarkBackground())
            color.setAlpha(150)
            gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
            gradient.setColorAt(0.01, color)
            gradient.setColorAt(0.15, QtGui.QColor(color.red(), color.green(), color.blue(), 50))
            gradient.setColorAt(0.66, QtGui.QColor(color.red(), color.green(), color.blue(), 10))
            gradient.setColorAt(1.0, QtGui.QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillRect(rect, gradient)

    @paintmethod
    def _paint_background(self, painter, option, index, node):
        selected = option.state & QtWidgets.QStyle.State_Selected
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        enabled = option.state & QtWidgets.QStyle.State_Enabled
        is_open = option.state & QtWidgets.QStyle.State_Open

        color = common.Color.Background()
        color = common.Color.LightBackground() if selected else color
        color = QtCore.Qt.transparent if not enabled else color

        if hover:
            color = QtGui.QColor(color)
            color.setRgb(
                color.red() + 10,
                color.green() + 10,
                color.blue() + 10
            )

        painter.fillRect(option.rect, color)

        if not node.is_leaf() and is_open:
            color = common.Color.LightBackground()
            painter.setOpacity(0.2)
            painter.fillRect(option.rect, color)

    @paintmethod
    def _paint_col0_name(self, painter, option, index):
        # Draw icon
        thumb_rect = QtCore.QRect(option.rect)
        thumb_rect.setRight(option.rect.height())
        _center = thumb_rect.center()
        thumb_rect.setSize(
            QtCore.QSize(common.Size.Margin(),
                         common.Size.Margin())
        )
        thumb_rect.moveCenter(_center)

        color = common.Color.Text()

        is_open = option.state & QtWidgets.QStyle.State_Open
        has_children = index.model().hasChildren(index)

        if is_open:
            icon = ui.get_icon('branch_open', color=common.Color.Text())
        elif not is_open and has_children:
            icon = ui.get_icon('branch_closed', color=common.Color.SelectedText())
        else:
            icon = ui.get_icon('failed', color=common.Color.DarkBackground())
        icon.paint(painter, thumb_rect, QtCore.Qt.AlignCenter)

        # Draw the name
        font, metrics = common.Font.BoldFont(option.font.pixelSize())

        text = index.data(QtCore.Qt.DisplayRole)
        alignment = option.displayAlignment
        elide_mode = option.textElideMode
        padding = common.Size.Indicator(2.0)

        painter.setFont(font)
        painter.setPen(color)

        rect = QtCore.QRect(option.rect)
        rect.setHeight(metrics.height())
        rect.moveCenter(option.rect.center())
        rect = rect.adjusted(padding + thumb_rect.right(), 0, -padding, 0)

        text = metrics.elidedText(text, elide_mode, rect.width())
        painter.drawText(rect, alignment, text)

    @paintmethod
    def _paint_col0_thumbnail(self, painter, option, index):
        selected = option.state & QtWidgets.QStyle.State_Selected
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        opacity = 0.66
        opacity = (opacity + abs(1 - opacity)) if selected else opacity
        opacity = (opacity + (abs(1 - opacity) * 0.8)) if hover else opacity
        painter.setOpacity(opacity)

        # Draw the background
        color = common.Color.VeryDarkBackground()
        painter.fillRect(option.rect, color)

        # Draw the thumbnail
        image = index.data(QtCore.Qt.DecorationRole)
        if not image.isNull():
            painter.drawImage(option.rect, image)
            return

        pixmap = images.rsc_pixmap(
            'asset',
            common.Color.VeryDarkBackground(),
            common.Size.size(option.rect.height())
        )
        painter.drawPixmap(option.rect, pixmap)

    @paintmethod
    def _paint_col0(self, painter, option, index, node):
        if not node.is_leaf():
            self._paint_col0_name(painter, option, index)
            return

        painter.save()
        self._paint_col0_thumbnail(painter, option, index)
        painter.restore()

    @paintmethod
    def _paint_col1(self, painter, option, index, node):
        if not node.is_leaf():
            return

        is_default = (
                BuiltInTemplate.TokenConfig.value in index.data(QtCore.Qt.DisplayRole) or
                BuiltInTemplate.Empty.value in index.data(QtCore.Qt.DisplayRole)
        )

        # Paint left gradient
        rect = QtCore.QRect(option.rect)
        rect.setWidth(common.Size.Margin())
        color = common.Color.VeryDarkBackground()
        color.setAlpha(150)
        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.topRight())
        gradient.setColorAt(0.0, color)
        gradient.setColorAt(0.25, QtGui.QColor(color.red(), color.green(), color.blue(), 50))
        gradient.setColorAt(0.66, QtGui.QColor(color.red(), color.green(), color.blue(), 10))
        gradient.setColorAt(1.0, QtGui.QColor(color.red(), color.green(), color.blue(), 0))
        painter.fillRect(rect, gradient)

        # Get the text color from the option
        color = option.palette.color(QtGui.QPalette.Text)
        if is_default:
            color = common.Color.Yellow()

        font = option.font
        metrics = option.fontMetrics
        elide_mode = option.textElideMode
        alignment = option.displayAlignment
        padding = common.Size.Indicator(3.0)

        lines = index.data(QtCore.Qt.DisplayRole).split('\n')
        lines = [line for line in lines if line]

        rect = QtCore.QRect(option.rect)
        rect.setHeight(metrics.height())
        rect.moveCenter(option.rect.center())
        rect = rect.adjusted(padding, 0, -padding, 0)

        # Set the rect top based on the number of lines
        start_pos = ((option.fontMetrics.lineSpacing() * (len(lines) - 1)) * 0.5)
        rect.moveTop(rect.top() - start_pos + (metrics.descent() * 0.5))

        for idx, text in enumerate(lines):
            if idx > 0:
                font, metrics = common.Font.LightFont(font.pixelSize() * 0.95)
                color = common.Color.SecondaryText()

            if idx == 0 and is_default:
                char = text[0]
                text = text.strip(char)

            painter.setFont(font)
            painter.setPen(color)

            text = metrics.elidedText(text, elide_mode, rect.width())
            painter.drawText(rect, alignment, text)

            rect.moveTop(rect.top() + metrics.lineSpacing())

        # if edit is in progress
        if option.state & QtWidgets.QStyle.State_Editing:
            painter.fillRect(option.rect, common.Color.VeryDarkBackground())

    @paintmethod
    def _paint_col2(self, painter, option, index, node):
        if not node.is_leaf():
            return

        # Get the text color from the option
        font, metrics = common.Font.LightFont(option.font.pixelSize() * 0.95)
        elide_mode = option.textElideMode
        alignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        padding = common.Size.Indicator(3.0)
        color = common.Color.SecondaryText()

        painter.setFont(font)
        painter.setPen(color)

        lines = index.data(QtCore.Qt.DisplayRole).split('\n')

        rect = QtCore.QRect(option.rect)
        rect.setHeight(metrics.height())
        rect.moveCenter(option.rect.center())
        rect = rect.adjusted(padding, 0, -padding, 0)

        # Set the rect top based on the number of lines
        start_pos = ((option.fontMetrics.lineSpacing() * (len(lines) - 1)) * 0.5)
        rect.moveTop(rect.top() - start_pos + (metrics.descent() * 0.5))
        for line in lines:
            name = metrics.elidedText(line, elide_mode, rect.width())
            painter.drawText(rect, alignment, name)
            rect.moveTop(rect.top() + option.fontMetrics.lineSpacing())

    @paintmethod
    def _paint_col3(self, painter, option, index, node):
        # Draw the background
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        selected = option.state & QtWidgets.QStyle.State_Selected

        painter.setOpacity(0.85)
        if hover or selected:
            painter.setOpacity(1.0)

        # Draw gradient from left to right
        color = common.Color.VeryDarkBackground()
        color.setAlpha(150)

        rect = QtCore.QRect(option.rect)
        rect.setSize(QtCore.QSize(common.Size.Margin(), common.Size.Margin()))
        rect.moveCenter(option.rect.center())

        if node.is_leaf() and node.api.has_error:
            icon = ui.get_icon('close', color=common.Color.Red())
        elif node.is_leaf() and node.api.has_links:
            icon = ui.get_icon('link', color=common.Color.Blue())
        else:
            icon = None

        if icon:
            icon.paint(painter, rect, QtCore.Qt.AlignCenter)

    def createEditor(self, parent, option, index):
        """Create the editor for the given index."""
        if not index.isValid():
            return

        node = index.internalPointer()
        if not node:
            return

        if not node.is_leaf():
            return

        if index.column() == 0:
            dialog = QtWidgets.QFileDialog(parent=parent)

            dialog.setOption(QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)
            dialog.setOption(QtWidgets.QFileDialog.HideNameFilterDetails, True)

            dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)

            dialog.setNameFilter(images.get_oiio_namefilters())

            if not dialog.history():
                dialog.setDirectory(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DesktopLocation))
            else:
                dialog.setDirectory(dialog.history()[0])

            return dialog

        elif index.column() == 1:
            widget = ui.LineEdit(parent=parent)
            widget.setPlaceholderText('Edit description...')
            return widget

    def updateEditorGeometry(self, editor, option, index):
        """Update the editor's geometry."""
        if not index.isValid():
            return

        node = index.internalPointer()
        if not node:
            return

        if not node.is_leaf():
            return

        if index.column() == 0:
            return
        elif index.column() == 1:
            sibling_ = index.sibling(index.row(), index.column() + 1)
            rect_ = self.parent().visualRect(sibling_)

            rect = QtCore.QRect(option.rect)
            rect.setRight(rect_.right())
            rect.setHeight(editor.height())

            center = QtCore.QRect(option.rect).center()
            _center = rect.center()
            _center.setY(center.y())
            rect.moveCenter(_center)

            o = common.Size.Margin(0.5)
            rect = rect.adjusted(o, 0, -o, 0)

            editor.setGeometry(rect)

    def setEditorData(self, editor, index):
        """Set the editor data."""
        if not index.isValid():
            return

        node = index.internalPointer()
        if not node:
            return

        if not node.is_leaf():
            return

        if index.column() == 0:
            pass
        elif index.column() == 1:
            try:
                v = index.data(QtCore.Qt.DisplayRole)
                v = v.split('\n') if v else ('', '')
                editor.setText(v[1])
            except ValueError:
                pass

    def setModelData(self, editor, model, index):
        """Set the model data."""
        if not index.isValid():
            return

        node = index.internalPointer()
        if not node:
            return

        if not node.is_leaf():
            return

        if index.column() == 0:
            if not editor.selectedFiles():
                return
            path = editor.selectedFiles()[0]
            node.api.set_thumbnail(path)
            node.api.save(force=True)
            self.parent().update(index)

        if index.column() == 1:
            node.api.set_metadata('description', editor.text())
            node.api.save(force=True)


class TemplatesView(QtWidgets.QTreeView):
    """
    A view class for displaying and interacting with asset links.
    """
    templateDataSelected = QtCore.Signal(bytes)

    def __init__(self, mode=None, parent=None):

        super().__init__(parent=parent)
        self.setWindowTitle('Templates')

        self.setHeaderHidden(True)
        self.setUniformRowHeights(False)

        self.setRootIsDecorated(False)
        self.setIndentation(0)
        self.header().setStretchLastSection(False)

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed
        )

        self.setItemDelegate(TemplatesViewDelegate(self))

        self._selected_node = (None, None)
        self._mode = mode

        self._init_shortcuts()
        self._init_model()
        self._connect_signals()

    def _init_shortcuts(self):
        """Initializes shortcuts.

        """
        shortcuts.add_shortcuts(self, shortcuts.TemplatesViewShortcuts)
        connect = functools.partial(
            shortcuts.connect, shortcuts.TemplatesViewShortcuts
        )
        connect(shortcuts.AddDefaultTemplate, self.add_default_template)
        connect(shortcuts.NewTemplate, self.add_new)
        connect(shortcuts.RemoveTemplate, self.remove_template)
        connect(shortcuts.RemoveAllTemplates, self.remove_all_templates)
        connect(shortcuts.ReloadTemplates, self.init_data)

    def _init_model(self):
        self.setModel(TemplatesModel(mode=self._mode, parent=self))

    def _connect_signals(self):
        self.selectionModel().selectionChanged.connect(self.emit_template_data_selected)
        self.model().modelAboutToBeReset.connect(
            lambda: self.emit_template_data_selected(QtCore.QModelIndex(), QtCore.QModelIndex())
        )

        self.selectionModel().selectionChanged.connect(self.save_selected_node)
        self.model().modelAboutToBeReset.connect(self.save_selected_node)

        self.model().modelReset.connect(self.restore_selected_node)
        self.expanded.connect(self.restore_selected_node)

    @QtCore.Slot(QtCore.QModelIndex, QtCore.QModelIndex)
    def emit_template_data_selected(self, current, previous, *args, **kwargs):
        if isinstance(current, QtCore.QItemSelection):
            index = next(iter(current.indexes()), QtCore.QModelIndex())
        elif isinstance(current, QtCore.QModelIndex):
            index = current
        else:
            index = QtCore.QModelIndex()

        if not index.isValid():
            self.templateDataSelected.emit(b'')
            return

        node = index.internalPointer()
        if not node:
            self.templateDataSelected.emit(b'')
            return

        if not node.is_leaf():
            self.templateDataSelected.emit(b'')
            return

        self.templateDataSelected.emit(node.api.template)

    def contextMenuEvent(self, event):
        """Context menu event."""
        index = self.indexAt(event.pos())
        menu = TemplatesContextMenu(index, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(),
            common.Size.DefaultHeight()
        )

    def get_selection_node_type(self):
        if not self.selectionModel().hasSelection():
            return None

        index = next(iter(self.selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return None

        _type = None
        p_parent_index = self.model().index(0, 0, QtCore.QModelIndex())
        m_parent_index = self.model().index(1, 0, QtCore.QModelIndex())

        if index.parent() == QtCore.QModelIndex():
            if index.row() == 0:
                _type = TemplateType.DatabaseTemplate
            elif index.row() == 1:
                _type = TemplateType.UserTemplate
        else:

            if index.parent() == p_parent_index:
                _type = TemplateType.DatabaseTemplate
            elif index.parent() == m_parent_index:
                _type = TemplateType.UserTemplate

        if _type is None:
            raise ValueError('Invalid template type.')

        node = index.internalPointer()
        if node.is_leaf() and _type != index.internalPointer().api.type:
            raise ValueError('Invalid template type.')

        return _type

    def get_node_from_selection(self):
        """
        Get the internal node from the current selection.

        """
        if not self.selectionModel().hasSelection():
            return None

        index = next(iter(self.selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return None

        node = index.internalPointer()
        if not node:
            return None

        if not node.is_leaf():
            return None

        return node

    @QtCore.Slot()
    def save_selected_node(self, *args, **kwargs):
        """Save the selected node."""
        node = self.get_node_from_selection()
        if not node:
            return

        if not node.is_leaf():
            return

        self._selected_node = (node.api['name'], node.api.type)

    @QtCore.Slot()
    def restore_selected_node(self):
        """Restore the selected node."""

        def _it_children(_parent_index):
            for i in range(self.model().rowCount(parent=_parent_index)):
                _index = self.model().index(i, 0, _parent_index)
                if not _index.isValid():
                    continue

                yield _index
                yield from _it_children(_index)

        for index in _it_children(QtCore.QModelIndex()):
            node = index.internalPointer()
            if not node:
                continue

            if not node.is_leaf():
                continue

            if self._selected_node == (node.api['name'], node.api.type if hasattr(node.api, 'type') else None):
                self.selectionModel().select(index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.setCurrentIndex(index)
                self.scrollTo(index)
                break

    def resize_columns(self):
        """
        Resize the columns.

        """
        if not self.model():
            return

        self.setFirstColumnSpanned(0, QtCore.QModelIndex(), True)
        self.setFirstColumnSpanned(1, QtCore.QModelIndex(), True)

        self.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.header().setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)

        self.header().resizeSection(0, common.Size.RowHeight(1.5))

        root_index = QtCore.QModelIndex()
        model = self.model()
        if model.hasChildren(root_index):
            parent_index = model.index(0, 0, root_index)
            if model.hasChildren(parent_index):
                index = model.index(0, 2, parent_index)
                v = index.data(QtCore.Qt.DisplayRole)
                v = max(v.split('\n'), key=len)
                font, metrics = common.Font.LightFont(self.font().pixelSize() * 0.95)
                self.header().resizeSection(2, metrics.width(v) + common.Size.Indicator(8.0))

        self.header().resizeSection(3, common.Size.RowHeight(1))

    @common.error
    @common.debug
    @QtCore.Slot()
    def init_data(self):
        """
        Initialize the data.

        """
        self.model().init_data()
        self.resize_columns()
        self.expandAll()

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_default_template(self):
        """
        Add a default template.

        """
        _type = self.get_selection_node_type()
        if _type is None:
            return

        d_parent_index = self.model().index(0, 0, QtCore.QModelIndex())
        m_parent_index = self.model().index(1, 0, QtCore.QModelIndex())
        parent_index = d_parent_index if _type == TemplateType.DatabaseTemplate else m_parent_index

        for i in range(self.model().rowCount(parent=parent_index)):
            index = self.model().index(i, 0, parent_index)
            if not index.isValid():
                continue

            node = index.internalPointer()
            if not node:
                continue

            if not node.is_leaf():
                continue

            if node.api.is_builtin():
                if common.show_message(
                        'Default Template Exists',
                        body='The default template already exists. Do you want to update/overwrite it?',
                        buttons=[common.YesButton, common.NoButton],
                        modal=True,
                ) == QtWidgets.QDialog.Rejected:
                    return

                item = TemplateItem()
                item.type = _type
                item.save(force=True)

                item = TemplateItem(empty=True)
                item.type = _type
                item.save(force=True)
                break

        self.init_data()

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_new(self):
        """
        Add a new template.

        """
        dialog = AddTemplateDialog(mode=self._mode, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        data = dialog.get_data()
        if data['type'] == TemplateType.UserTemplate:
            path = TemplateItem.get_save_path(data['name'])

        item = TemplateItem(path=path)

        if not data['name']:
            raise ValueError('Name cannot be empty.')

        if data['type'] == TemplateType.DatabaseTemplate:
            parent_index = self.model().index(0, 0, QtCore.QModelIndex())
        elif data['type'] == TemplateType.UserTemplate:
            parent_index = self.model().index(1, 0, QtCore.QModelIndex())
        else:
            raise ValueError('Invalid template type.')

        # Check uniqueness
        for i in range(self.model().rowCount(parent=parent_index)):
            index = self.model().index(i, 0, parent_index)
            if not index.isValid():
                raise ValueError('Invalid index.')

            node = index.internalPointer()
            if not node:
                raise ValueError('Invalid node.')

            if node.api['name'] == data['name']:
                raise ValueError(f'Template name "{data["name"]}" already exists.')

        item['name'] = data['name']

        if data['description']:
            item['description'] = data['description']

        if data['image'] and not data['image'].isNull():
            item.qimage = data['image']

        if not data['folder'] or not os.path.exists(data['folder']):
            raise ValueError('Folder path cannot be empty.')
        item.template_from_folder(data['folder'])

        if data['links']:
            try:
                item.set_link_preset(data['links'])
            except TemplateLinkExistsError:
                if common.show_message(
                        'Link preset already exists',
                        body='The template already contains a link preset. Are you sure you want to overwrite it?',
                        buttons=[common.YesButton, common.NoButton],
                        modal=True,
                ) == QtWidgets.QDialog.Accepted:
                    item.set_link_preset(data['links'], force=True)

        # Save
        try:
            item.save()
        except:
            if common.show_message(
                    'Template Exists',
                    body='The template already exists. Do you want to update/overwrite it?',
                    buttons=[common.YesButton, common.NoButton],
                    modal=True,
            ) == QtWidgets.QDialog.Rejected:
                return
            item.save(force=True)

        # Reload the model
        self.init_data()

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_template(self):
        """Remove the selected template."""
        node = self.get_node_from_selection()
        if not node:
            return

        if not node.is_leaf():
            return

        if common.show_message(
                'Delete Template',
                body=f'Are you sure you want to delete the template "{node.api["name"]}"? This action cannot be undone.',
                buttons=[common.YesButton, common.NoButton],
                modal=True,
        ) == QtWidgets.QDialog.Rejected:
            return

        node.api.delete()
        self.init_data()

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_all_templates(self):
        """Remove all templates."""
        if not self.selectionModel().hasSelection():
            return
        index = next(iter(self.selectionModel().selectedIndexes()), QtCore.QModelIndex())
        if not index.isValid():
            return

        p_parent_index = self.model().index(0, 0, QtCore.QModelIndex())
        m_parent_index = self.model().index(1, 0, QtCore.QModelIndex())

        _type = self.get_selection_node_type()
        if _type is None:
            return

        if common.show_message(
                'Delete All Templates',
                body=f'Are you sure you want to delete all  {_type.value}s? This action cannot be undone.',
                buttons=[common.YesButton, common.NoButton],
                modal=True,
        ) == QtWidgets.QDialog.Rejected:
            return

        parent_index = p_parent_index if _type == TemplateType.DatabaseTemplate else m_parent_index
        for i in range(self.model().rowCount(parent=parent_index)):
            index = self.model().index(i, 0, parent_index)
            node = index.internalPointer()
            if not node:
                continue

            if not node.is_leaf():
                raise RuntimeError('Unexpected node type.')

            try:
                node.api.delete()
            except Exception as e:
                log.error(f'Error deleting template: {e}')

                pass

        self.init_data()

    @common.error
    @common.debug
    @QtCore.Slot()
    def pick_thumbnail(self):
        """Pick a thumbnail."""
        node = self.get_node_from_selection()
        if not node:
            return

        path = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Select the thumbnail image:',
            QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DesktopLocation),
            images.get_oiio_namefilters(),
            options=QtWidgets.QFileDialog.DontUseCustomDirectoryIcons | QtWidgets.QFileDialog.HideNameFilterDetails
        )[0]

        if not path:
            return

        node.api.set_thumbnail(path)
        node.api.save(force=True)

        self.update(self.currentIndex())

    @common.error
    @common.debug
    @QtCore.Slot()
    def clear_thumbnail(self):
        """Clear the thumbnail."""
        node = self.get_node_from_selection()
        if not node:
            return

        node.api.clear_thumbnail()
        node.api.save(force=True)

        self.update(self.currentIndex())

    @common.error
    @common.debug
    @QtCore.Slot()
    def add_link_preset(self, preset):
        """Add a link preset.

        Args:
            preset (str): The preset to add to the selected template.

        """
        node = self.get_node_from_selection()
        if not node:
            return

        if not node.is_leaf():
            return

        if node.api.is_builtin():
            raise ValueError('Cannot modify built-in template')

        try:
            node.api.set_link_preset(preset)
        except TemplateLinkExistsError:
            if common.show_message(
                    'Link preset already exists',
                    body='The template already contains a link preset. Are you sure you want to overwrite it?',
                    buttons=[common.YesButton, common.NoButton],
                    modal=True,
            ) == QtWidgets.QDialog.Rejected:
                return

        node.api.set_link_preset(preset, force=True)
        node.api.save(force=True)
        self.init_data()

    @common.error
    @common.debug
    @QtCore.Slot()
    def remove_link_preset(self):
        """Remove the link preset from the selected template."""
        node = self.get_node_from_selection()
        if not node:
            return

        if not node.is_leaf():
            return

        if node.api.is_builtin():
            raise ValueError('Cannot remove link preset from the default template.')

        if common.show_message(
                'Remove Link Preset',
                body='Are you sure you want to remove the link preset from the template?',
                buttons=[common.YesButton, common.NoButton],
                modal=True,
        ) == QtWidgets.QDialog.Rejected:
            return

        node.api.remove_link_preset()
        node.api.save(force=True)
        self.init_data()

    @common.error
    @common.debug
    @QtCore.Slot()
    def template_to_folder(self):
        """Extract the selected template."""
        node = self.get_node_from_selection()
        if not node:
            return

        if not node.is_leaf():
            return

        dialog = ExtractTemplateDialog(parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        data = dialog.get_data()
        node.api.template_to_folder(data['path'], data['extract_to_links'])
        actions.reveal(data['path'])

    @common.error
    @common.debug
    @QtCore.Slot()
    def rename_template(self):
        """Rename the selected template."""
        node = self.get_node_from_selection()
        if not node:
            return

        if not node.is_leaf():
            return

        if node.api.is_builtin():
            raise ValueError('Cannot modify built-in template')

        dialog = RenameTemplateDialog(node.api['name'], parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        name = dialog.get_data()
        node.api.rename(name)
        self.init_data()


class TemplatesEditor(QtWidgets.QSplitter):
    """The widget containing :class:`TemplatesView` and :class:`TemplatePreviewView`."""

    def __init__(self, mode=TemplateType.UserTemplate, parent=None):
        super().__init__(parent=parent)

        if not parent:
            common.set_stylesheet(self)

        self.setWindowTitle('Asset Links Editor')

        self._templates_view_widget = None
        self._templates_editor_widget = None
        self._mode = mode

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        self.setContentsMargins(0, 0, 0, 0)

        widget = QtWidgets.QWidget(parent=self)
        widget.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        QtWidgets.QVBoxLayout(widget)

        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().setSpacing(common.Size.Margin(0.5))

        self.addWidget(widget)

        self._templates_view_widget = TemplatesView(mode=self._mode, parent=self)
        widget.layout().addWidget(self._templates_view_widget)

        self._templates_editor_widget = TemplatePreviewView(parent=self)
        self.addWidget(self._templates_editor_widget)

    def _connect_signals(self):
        self._templates_view_widget.templateDataSelected.connect(
            self._templates_editor_widget.model().init_data)

    def init_data(self):
        self._templates_view_widget.init_data()


class TemplatesMainWidget(QtWidgets.QDialog):
    """The main widget for managing templates."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle('Asset Templates')

        if not self.parent():
            common.set_stylesheet(self)

        self._tabs_widget = None

        self._add_asset_widget = None
        self._asset_templates_widget = None
        self._asset_links_widget = None

        self._name_editor = None
        self._create_asset_button = None
        self._done_button = None

        self._create_ui()
        self._connect_signals()

        QtCore.QTimer.singleShot(200, self.init_data)

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)

        o = common.Size.Margin(0.66)
        self.layout().setSpacing(common.Size.Margin(1.5))
        self.layout().setContentsMargins(o, o, o, o)

        self._tabs_widget = QtWidgets.QTabWidget(parent=self)
        self._tabs_widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self.layout().addWidget(self._tabs_widget, 1)

        self._asset_links_widget = LinksEditor(parent=self)
        self._tabs_widget.addTab(self._asset_links_widget, 'Asset Links')

        self._asset_templates_widget = TemplatesEditor(parent=self)
        self._tabs_widget.addTab(self._asset_templates_widget, 'Asset Templates')

        self.layout().addStretch(1)

        row = ui.add_row(None, height=None, parent=self)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        self._done_button = ui.PaintedButton('Done', parent=row)
        self._done_button.setMaximumWidth(common.Size.Margin(30))
        row.layout().addWidget(self._done_button, 1)

    def _connect_signals(self):
        self._asset_templates_widget._templates_view_widget.model().modelReset.connect(
            lambda: self._asset_links_widget._asset_templates_widget.init_data(force=True))
        self._done_button.clicked.connect(self.accept)

        common.signals.bookmarkItemActivated.connect(self.close)
        common.signals.assetItemActivated.connect(self.close)

    @common.error
    @common.debug
    @QtCore.Slot()
    def init_data(self):
        if not common.active('root'):
            raise ValueError('This widget requires a root item to be active prior to initialization.')

        # Let's make sure the default database template is created automatically
        if not builtin_template_exists(_type=TemplateType.DatabaseTemplate):
            item = TemplateItem()
            item.type = TemplateType.DatabaseTemplate
            item.save(force=True)

            item = TemplateItem(empty=True)
            item.type = TemplateType.DatabaseTemplate
            item.save(force=True)

        # Initializes the asset links editor data
        self._asset_links_widget._links_view_widget.add_paths_from_active()
        self._asset_templates_widget.init_data()
