# tokeneditors.py

import copy
import functools

from PySide2 import QtWidgets, QtCore

from bookmarks import common, tokens
from bookmarks import log
from bookmarks import ui
from bookmarks.common import TokenLineEdit
from bookmarks.editor import base

MoveUp = 0
MoveDown = 1

def _set(d, keys, v):
    """Utility method for updating a value in a dict."""
    if isinstance(keys, str):
        keys = keys.split('/')
    k = keys.pop(0)
    if keys:
        if k in d:
            return _set(d[k], keys, v)
        else:
            try:
                k = int(k)
                if k in d:
                    return _set(d[k], keys, v)
            except:
                pass
    d[k] = v

class TokenEditor(QtWidgets.QDialog):
    """Popup dialog used to insert an available token to one of the file name template editors."""
    tokenSelected = QtCore.Signal(str)

    def __init__(self, server, job, root, parent=None):
        super().__init__(parent=parent)
        self.server = server
        self.job = job
        self.root = root

        self.setWindowFlags(QtCore.Qt.Popup)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, on=True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._create_ui()

    def _create_ui(self):
        common.set_stylesheet(self)
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)

        editor = ui.ListWidget(parent=self)
        editor.setSpacing(0)

        editor.itemClicked.connect(
            lambda x: self.tokenSelected.emit(x.data(QtCore.Qt.UserRole))
        )
        editor.itemClicked.connect(
            lambda x: self.done(QtWidgets.QDialog.Accepted)
        )

        self.layout().addWidget(editor, 0)

        config = tokens.get(self.server, self.job, self.root)
        v = config.get_tokens()

        for k in sorted(v.keys(), key=lambda x: x.strip('{}').lower()):
            editor.addItem(f'{k}{"    >   {}".format(v[k]) if v[k] != "{invalid_token}" else ""}')
            item = editor.item(editor.count() - 1)
            item.setFlags(QtCore.Qt.ItemIsEnabled)

            item.setData(
                QtCore.Qt.ToolTipRole,
                f'Current value: "{v[k]}"'
            )
            item.setData(
                QtCore.Qt.UserRole,
                '{{{}}}'.format(k)
            )

    def sizeHint(self):
        """Returns a size hint."""
        return QtCore.QSize(
            self.parent().geometry().width(),
            common.Size.RowHeight(7.0)
        )

    def showEvent(self, event):
        """Show event handler."""
        editor = self.parent()
        geo = editor.rect()
        pos = editor.mapToGlobal(geo.bottomLeft())

        self.move(pos)
        self.setFixedWidth(geo.width())

        self.setFocus(QtCore.Qt.PopupFocusReason)

class BaseEditor(QtWidgets.QWidget):
    """Base class for editors to reduce code redundancy."""

    def __init__(self, section, parent=None):
        super().__init__(parent=parent)
        self.section = section  # Token config section key

        self.tokens = None
        self.current_data = {}
        self.changed_data = {}
        self.init_data()
        self._create_ui()
        self._connect_signals()

    @property
    def server(self):
        return self.window().server

    @property
    def job(self):
        return self.window().job

    @property
    def root(self):
        return self.window().root

    def init_data(self):
        self.tokens = tokens.get(self.server, self.job, self.root)

    def _create_ui(self):
        # This method should be overridden by subclasses
        pass

    def _connect_signals(self):
        # This method can be overridden by subclasses if needed
        pass

    def text_changed(self, key, editor, value):
        # Common implementation
        if key not in self.current_data:
            self.current_data[key] = value

        if value != str(self.current_data[key]):
            self.changed_data[key] = value
            editor.setStyleSheet(f'color: {common.Color.Green(qss=True)};')
            return

        if key in self.changed_data:
            del self.changed_data[key]
        editor.setStyleSheet(f'color: {common.Color.Text(qss=True)};')

    def save_changes(self):
        # This method should be overridden by subclasses to save data accordingly
        pass

    def restore_defaults(self):
        if common.show_message(
                'Are you sure you want to restore the default values?',
                body='Any custom values will be permanently lost.',
                buttons=[common.YesButton, common.CancelButton],
                modal=True,
        ) == QtWidgets.QDialog.Rejected:
            return

        data = self.tokens.data(force=True)

        if self.section not in data:
            common.log.error(f'Invalid section: {self.section}. Skipping.')
            return
        if self.section not in tokens.DEFAULT_TOKEN_CONFIG:
            common.log.error(f'Invalid section: {self.section}. Skipping.')
            return

        default_section = copy.deepcopy(tokens.DEFAULT_TOKEN_CONFIG[self.section])
        data[self.section] = default_section

        self.tokens.set_data(data)
        self.refresh_ui()

    def refresh_ui(self):
        # Remove existing items and recreate them
        for i in reversed(range(self.layout().count())):
            widget = self.layout().itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self._create_ui()

class MovableItemsEditor(BaseEditor):
    """Editor class for sections with movable items."""
    sections = {
        tokens.FileNameConfig: {
            'name': 'File Name Templates',
            'description': 'File name templates are used to define the names of scene files. These usually include the project\'s prefix, sequence and shot numbers, and the task name.',
        },
        tokens.PublishConfig: {
            'name': 'Publish Templates',
            'description': 'Publish templates are used to define the save location of published files.',
        },
        tokens.FFMpegTCConfig: {
            'name': 'Timecode Template',
            'description': 'The template used by ffmpeg for video text overlays and burn-ins.',
        },
    }

    def get_section_description(self):
        return self.sections[self.section]['description']

    def _create_ui(self):
        o = common.Size.Margin()
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o)

        data = self.tokens.data(force=True)
        if self.section not in data:
            common.log.error(f'Section {self.section} not found in data.')
            return

        section_data = data[self.section]

        # Create control row
        self.create_control_row()

        # Add items
        for k, v in section_data.items():
            self.create_item(k, v)

    def create_control_row(self):
        control_row = ui.add_row(
            None, height=None, parent=self
        )

        ui.add_description(
            self.get_section_description(),
            height=None,
            label=None,
            parent=control_row
        )

        add_button = ui.ClickableIconButton(
            'add',
            (common.Color.Green(), common.Color.Green()),
            common.Size.Margin(1.5),
            description='Add new item',
            parent=control_row
        )
        control_row.layout().addWidget(add_button, 0)

        add_button.clicked.connect(
            functools.partial(self.add_item, self)
        )

        reset_button = ui.PaintedButton('Revert to defaults')
        reset_button.clicked.connect(self.restore_defaults)

        control_row.layout().addWidget(reset_button, 0)

    def create_item(self, key, data):
        grp = ui.get_group(vertical=False, parent=self)
        grp.setObjectName('section_item_group')
        grp.section = self.section

        _row1 = ui.add_row(None, height=None, vertical=True, parent=grp)

        for _k in ('name', 'value', 'description'):
            row = ui.add_row(_k.title(), height=common.Size.RowHeight(), parent=_row1)

            if _k == 'value':
                editor = TokenLineEdit(parent=row)
            else:
                editor = ui.LineEdit(parent=row)
            editor.setObjectName(f'section_item_{_k}')

            editor.setAlignment(QtCore.Qt.AlignRight)
            editor.setText(data[_k])
            editor.setPlaceholderText(f'Edit {_k}...')

            row.layout().addWidget(editor, 1)

            # Save current data
            item_key = f'{self.section}/{key}/{_k}'
            self.current_data[item_key] = data[_k]

            editor.textChanged.connect(
                functools.partial(self.text_changed, item_key, editor)
            )

        _row2 = ui.add_row(None, height=None, vertical=False, parent=None)
        grp.layout().addWidget(_row2, 0)

        button = ui.ClickableIconButton(
            'add_circle',
            (common.Color.Text(), common.Color.Text()),
            common.Size.Margin(),
            description='Insert token',
            parent=_row2
        )
        _row2.layout().addWidget(button, 0)
        value_editor = [x for x in (grp.findChildren(QtWidgets.QLineEdit) + grp.findChildren(TokenLineEdit)) if x.objectName() == 'section_item_value'][0]
        button.clicked.connect(
            functools.partial(self.show_token_editor, value_editor)
        )

        button = ui.ClickableIconButton(
            'arrow_up',
            (common.Color.Text(), common.Color.Text()),
            common.Size.Margin(),
            description='Move item up',
            parent=_row2
        )
        _row2.layout().addWidget(button, 0)
        button.clicked.connect(
            functools.partial(self.move_item, grp, MoveUp)
        )

        button = ui.ClickableIconButton(
            'arrow_down',
            (common.Color.Text(), common.Color.Text()),
            common.Size.Margin(),
            description='Move item down',
            parent=_row2
        )
        _row2.layout().addWidget(button, 0)
        button.clicked.connect(
            functools.partial(self.move_item, grp, MoveDown)
        )

        button = ui.ClickableIconButton(
            'archive',
            (common.Color.Red(), common.Color.Red()),
            common.Size.Margin(),
            description='Remove item',
            parent=_row2
        )
        _row2.layout().addWidget(button, 0)
        button.clicked.connect(
            functools.partial(self.remove_item, grp)
        )

    def _connect_signals(self):
        pass

    def move_item(self, widget, direction):
        layout = widget.parent().layout()
        index = layout.indexOf(widget)

        if direction == MoveUp:
            min_index = 1  # Skip the first row as this is the control row
            new_index = index - 1
            new_index = max(min_index, new_index)
        else:
            new_index = index + 1
            new_index = min(layout.count() - 1, new_index)

        layout.insertWidget(new_index, layout.takeAt(index).widget())

    def add_item(self, parent):
        key = max([int(k) for k in self.tokens.data()[self.section].keys()] + [0]) + 1
        data = {
            'name': '',
            'value': '',
            'description': ''
        }
        self.create_item(key, data)

    def remove_item(self, widget):
        if common.show_message(
                'Are you sure you want to remove this item?',
                body='This action cannot be undone.',
                buttons=[common.YesButton, common.CancelButton],
                modal=True,
        ) == QtWidgets.QDialog.Rejected:
            return
        layout = widget.parent().layout()
        layout.removeWidget(widget)
        widget.deleteLater()

    def show_token_editor(self, editor):
        w = TokenEditor(self.server, self.job, self.root, parent=editor)
        w.tokenSelected.connect(editor.insert)
        w.exec_()

    def save_changes(self):
        # Retrieve the current data from the database
        data = self.tokens.data(force=True)

        # Update the data with the changed values
        for keys, v in self.changed_data.copy().items():
            _set(data, keys.split('/'), v)
            del self.changed_data[keys]

        # Reset the current data section and replace it with the values in the UI.
        data[self.section] = {}

        # Let's find the list of section group widgets
        items = [f for f in self.findChildren(QtWidgets.QWidget, 'section_item_group') if f.section == self.section]
        for idx, item in enumerate(items):
            name_editor = item.findChildren(QtWidgets.QLineEdit, 'section_item_name')[0]
            value_editor = (item.findChildren(QtWidgets.QLineEdit, 'section_item_value') + item.findChildren(TokenLineEdit, 'section_item_value'))[0]
            description_editor = item.findChildren(QtWidgets.QLineEdit, 'section_item_description')[0]

            if not all((name_editor.text(), value_editor.text())):
                continue

            data[self.section][idx] = {
                'name': name_editor.text(),
                'value': value_editor.text(),
                'description': description_editor.text() if description_editor.text() else '',
            }

        self.tokens.set_data(data)

class TasksConfigEditor(MovableItemsEditor):
    """Editor for the TasksConfig section."""

    def __init__(self, parent=None):
        super().__init__(tokens.TasksConfig, parent=parent)

class FileNameConfigEditor(MovableItemsEditor):
    """Editor for the FileNameConfig section."""

    def __init__(self, parent=None):
        super().__init__(tokens.FileNameConfig, parent=parent)

class PublishConfigEditor(MovableItemsEditor):
    """Editor for the PublishConfig section."""

    def __init__(self, parent=None):
        super().__init__(tokens.PublishConfig, parent=parent)

class FFMpegTCConfigEditor(MovableItemsEditor):
    """Editor for the FFMpegTCConfig section."""

    def __init__(self, parent=None):
        super().__init__(tokens.FFMpegTCConfig, parent=parent)

class FormatEditor(QtWidgets.QDialog):
    """Popup widget used to set the acceptable file formats for a task folder."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_widget = None

        self.setWindowTitle('Edit Formats')
        self._create_ui()

    def _create_ui(self):
        o = common.Size.Margin()
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        self.list_widget = ui.ListWidget(parent=self)
        self.list_widget.setWrapping(False)
        self.list_widget.setSpacing(0)
        self.list_widget.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.list_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.list_widget.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.list_widget.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.layout().addWidget(self.list_widget, 1)
        self.list_widget.itemClicked.connect(self.list_widget.toggle)

        self.save_button = ui.PaintedButton('Save')
        self.cancel_button = ui.PaintedButton('Cancel')

        row = ui.add_row(
            None, height=common.Size.RowHeight(), parent=self
        )
        row.layout().addWidget(self.save_button, 1)
        row.layout().addWidget(self.cancel_button, 0)

        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted)
        )
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected)
        )

class SubfolderEditor(QtWidgets.QDialog):
    """A popup editor used to edit the subfolders of a task folder."""

    def __init__(self, section, key, data, parent=None):
        super().__init__(parent=parent)
        self.section = section
        self.key = key
        self.data = data

        self.setWindowTitle('Edit Sub-folders')
        self._create_ui()

    def _create_ui(self):
        o = common.Size.Margin()
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        main_grp = base.add_section('', 'Edit Sub-folders', self)
        grp = ui.get_group(parent=main_grp)

        for _k, _v in self.data['subfolders'].items():
            if not isinstance(_v, dict):
                log.error(f'Invalid data. Key: {_k}, Value: {_v}')
                continue

            _row = ui.add_row(_v['name'], parent=grp)
            editor = ui.LineEdit(parent=_row)
            editor.setText(_v['value'])

            key = f'{self.section}/{self.key}/subfolders/{_k}/value'
            self.parent().current_data[key] = _v['value']

            editor.textChanged.connect(
                functools.partial(self.parent().text_changed, key, editor)
            )

            _row.layout().addWidget(editor, 1)
            _row.setStatusTip(_v['description'])
            _row.setWhatsThis(_v['description'])
            _row.setToolTip(_v['description'])

        self.save_button = ui.PaintedButton('Save')
        self.cancel_button = ui.PaintedButton('Cancel')

        row = ui.add_row(
            None, height=common.Size.RowHeight(), parent=self
        )
        row.layout().addWidget(self.save_button, 1)
        row.layout().addWidget(self.cancel_button, 0)

        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted)
        )
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected)
        )

class AssetFolderConfigEditor(BaseEditor):
    """Editor for the AssetFolderConfig section."""

    def __init__(self, parent=None):
        super().__init__(tokens.AssetFolderConfig, parent=parent)

    def get_section_description(self):
        return 'Common folders that define the principal folders of an asset item. These values are used when browsing files, saving scene files and publishing items.'

    def _create_ui(self):
        o = common.Size.Margin()
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o)

        data = self.tokens.data(force=True)
        section_data = data.get(self.section, {})

        # Create control row
        self.create_control_row()

        # Add items
        for k, v in section_data.items():
            self.create_item(k, v)

    def create_control_row(self):
        control_row = ui.add_row(
            None, height=None, parent=self
        )

        ui.add_description(
            self.get_section_description(),
            height=None,
            label=None,
            parent=control_row
        )

        reset_button = ui.PaintedButton('Revert to defaults')
        reset_button.clicked.connect(self.restore_defaults)

        control_row.layout().addWidget(reset_button, 0)

    def create_item(self, key, data):
        h = common.Size.RowHeight()
        _name = data['name'].title()
        row = ui.add_row(_name, height=h, parent=self)

        row.setStatusTip(data['description'])
        row.setWhatsThis(data['description'])
        row.setToolTip(data['description'])
        row.setAccessibleDescription(data['description'])

        editor = ui.LineEdit(parent=row)
        editor.setAlignment(QtCore.Qt.AlignRight)
        editor.setText(data['value'])

        row.layout().addWidget(editor, 1)

        # Save current data
        value_key = f'{self.section}/{key}/value'
        self.current_data[value_key] = data['value']

        editor.textChanged.connect(
            functools.partial(self.text_changed, value_key, editor)
        )

        # 'Formats' button
        button = ui.PaintedButton('Formats', parent=row)
        row.layout().addWidget(button, 0)
        if 'filter' in data:
            filter_key = f'{self.section}/{key}/filter'
            self.current_data[filter_key] = data['filter']
            button.clicked.connect(
                functools.partial(self.show_filter_editor, filter_key, data)
            )
        else:
            button.setDisabled(True)

        # 'Subfolders' button
        button = ui.PaintedButton('Subfolders', parent=row)
        row.layout().addWidget(button, 0)
        if 'subfolders' in data and isinstance(data['subfolders'], dict):
            button.clicked.connect(
                functools.partial(
                    self.show_subfolders_editor, key, data
                )
            )
        else:
            button.setDisabled(True)

    def show_filter_editor(self, key, data):
        editor = FormatEditor(parent=self)
        editor.list_widget.itemClicked.connect(
            functools.partial(self.filter_changed, key, editor)
        )

        format_data = self.tokens.data()[tokens.FileFormatConfig]
        for _v in format_data.values():
            editor.list_widget.addItem(_v['name'])

            item = editor.list_widget.item(editor.list_widget.count() - 1)
            item.setData(QtCore.Qt.UserRole, _v['flag'])
            item.setData(common.PathRole, _v['description'])
            item.setData(QtCore.Qt.ToolTipRole, _v['description'])
            item.setData(QtCore.Qt.AccessibleDescriptionRole, _v['description'])
            item.setData(QtCore.Qt.WhatsThisRole, _v['description'])

            if _v['flag'] & data['filter']:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)

        editor.finished.connect(
            lambda x: self.save_changes(
            ) if x == QtWidgets.QDialog.Accepted else None
        )
        editor.exec_()

    def filter_changed(self, key, editor, *args):
        v = 0
        for n in range(editor.list_widget.count()):
            item = editor.list_widget.item(n)
            if item.checkState() == QtCore.Qt.Checked:
                v |= item.data(QtCore.Qt.UserRole)
        self.changed_data[key] = v

    def show_subfolders_editor(self, key, data):
        editor = SubfolderEditor(self.section, key, data, parent=self)
        editor.finished.connect(
            lambda x: self.save_changes(
            ) if x == QtWidgets.QDialog.Accepted else None
        )
        editor.exec_()

    def save_changes(self):
        # Retrieve the current data from the database
        data = self.tokens.data(force=True)

        # Update the data with the changed values
        for keys, v in self.changed_data.copy().items():
            _set(data, keys, v)
            del self.changed_data[keys]

        self.tokens.set_data(data)

class FileFormatConfigEditor(BaseEditor):
    """Editor for the FileFormatConfig section."""

    def __init__(self, parent=None):
        super().__init__(tokens.FileFormatConfig, parent=parent)

    def get_section_description(self):
        return 'The list of file formats that are allowed to be shown.'

    def _create_ui(self):
        o = common.Size.Margin()
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o)

        data = self.tokens.data(force=True)
        section_data = data.get(self.section, {})

        # Create control row
        self.create_control_row()

        # Add items
        for k, v in section_data.items():
            self.create_item(k, v)

    def create_control_row(self):
        control_row = ui.add_row(
            None, height=None, parent=self
        )

        ui.add_description(
            self.get_section_description(),
            height=None,
            label=None,
            parent=control_row
        )

        add_button = ui.ClickableIconButton(
            'add',
            (common.Color.Green(), common.Color.Green()),
            common.Size.Margin(1.5),
            description='Add new format',
            parent=control_row
        )
        control_row.layout().addWidget(add_button, 0)

        add_button.clicked.connect(
            functools.partial(self.add_item, self)
        )

        reset_button = ui.PaintedButton('Revert to defaults')
        reset_button.clicked.connect(self.restore_defaults)

        control_row.layout().addWidget(reset_button, 0)

    def create_item(self, key, data):
        # We will exclude the 'flag' field from the UI and remove movable functionality
        grp = ui.get_group(vertical=False, parent=self)
        grp.setObjectName('section_item_group')
        grp.section = self.section

        _row1 = ui.add_row(None, height=None, vertical=True, parent=grp)

        for _k in ('name', 'value', 'description'):
            row = ui.add_row(_k.title(), height=common.Size.RowHeight(), parent=_row1)
            editor = ui.LineEdit(parent=row)
            editor.setObjectName(f'section_item_{_k}')

            editor.setAlignment(QtCore.Qt.AlignRight)
            editor.setText(str(data[_k]))
            editor.setPlaceholderText(f'Edit {_k}...')

            if _k in ('name', 'description'):
                editor.setReadOnly(True)
                editor.setDisabled(True)

            row.layout().addWidget(editor, 1)

            # Save current data
            item_key = f'{self.section}/{key}/{_k}'
            self.current_data[item_key] = data[_k]

            editor.textChanged.connect(
                functools.partial(self.text_changed, item_key, editor)
            )

        # No action buttons (no move up/down, no remove)

    def add_item(self, parent):
        key = max([int(k) for k in self.tokens.data()[self.section].keys()] + [0]) + 1
        data = {
            'name': '',
            'value': '',
            'description': '',
            'flag': 0  # Default flag value
        }
        self.create_item(key, data)

    def save_changes(self):
        # We need to preserve the 'flag' values even though they are not editable
        data = self.tokens.data(force=True)

        # Update the data with the changed values
        for keys, v in self.changed_data.copy().items():
            _set(data, keys.split('/'), v)
            del self.changed_data[keys]

        # Reset the current data section and replace it with the values in the UI
        original_data = data[self.section]
        data[self.section] = {}

        items = [f for f in self.findChildren(QtWidgets.QWidget, 'section_item_group') if
                 f.section == self.section]
        for idx, item in enumerate(items):
            name_editor = item.findChildren(QtWidgets.QLineEdit, 'section_item_name')[0]
            value_editor = (item.findChildren(QtWidgets.QLineEdit, 'section_item_value') + item.findChildren(TokenLineEdit, 'section_item_value'))[0]
            description_editor = item.findChildren(QtWidgets.QLineEdit, 'section_item_description')[0]

            if not all((name_editor.text(), value_editor.text())):
                continue

            # Get the original 'flag' value
            try:
                original_flag = original_data[str(idx)]['flag']
            except KeyError:
                original_flag = 0  # Default value if not found

            data[self.section][idx] = {
                'name': name_editor.text(),
                'value': value_editor.text(),
                'description': description_editor.text() if description_editor.text() else '',
                'flag': original_flag
            }

        self.tokens.set_data(data)
