"""Various widgets used to edit token values.

See the :mod:`bookmarks.tokens.tokens` for the interface details.

"""
import copy
import functools

from PySide2 import QtWidgets, QtCore

from . import tokens
from .. import common
from .. import log
from .. import ui
from ..editor import base

MoveUp = 0
MoveDown = 1

SECTIONS = {
    tokens.FileNameConfig: {
        'name': 'File Name Templates',
        'description': 'File name templates are used to define the names scene files. These usually include the '
                       'project\'s prefix, sequence and shot numbers, and the task name.',
    },
    tokens.PublishConfig: {
        'name': 'Publish Templates',
        'description': 'Publish templates are used to define the save location of published files.',
    },
    tokens.FFMpegTCConfig: {
        'name': 'Timecode Template',
        'description': 'The template used by ffmpeg for video text overlays and burn-ins.',
    },
    tokens.AssetFolderConfig: {
        'name': 'Asset Folders',
        'description': 'Common folders that define the principal folders of an asset item. These values are'
                       'used when browsing files, saving scene files and publishing items.',
    },
    tokens.FileFormatConfig: {
        'name': 'Format Whitelist',
        'description': 'The list of file formats that are allowed to be shown.',

    },
}


def _set(d, keys, v):
    """Utility method for updating a value in a dict.

    """
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
    """Popup dialog used to insert an available token to one of the file
    name template editors.

    """
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
        """Returns a size hint.

        """
        return QtCore.QSize(
            self.parent().geometry().width(),
            common.size(common.size_row_height) * 7
        )

    def showEvent(self, event):
        """Show event handler.

        """
        editor = self.parent()
        geo = editor.rect()
        pos = editor.mapToGlobal(geo.bottomLeft())

        self.move(pos)
        self.setFixedWidth(geo.width())

        self.setFocus(QtCore.Qt.PopupFocusReason)


class FormatEditor(QtWidgets.QDialog):
    """Popup widget used to set the acceptable file formats for a task folder.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.listwidget = None

        self.setWindowTitle('Edit Formats')
        self._create_ui()

    def _create_ui(self):
        o = common.size(common.size_margin)
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        self.listwidget = ui.ListWidget(parent=self)
        self.listwidget.setWrapping(False)
        self.listwidget.setSpacing(0)
        self.listwidget.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.listwidget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.listwidget.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.listwidget.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.layout().addWidget(self.listwidget, 1)
        self.listwidget.itemClicked.connect(self.listwidget.toggle)

        self.save_button = ui.PaintedButton('Save')
        self.cancel_button = ui.PaintedButton('Cancel')

        row = ui.add_row(
            None, height=common.size(
                common.size_row_height
            ), parent=self
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
    """A popup editor used to edit the sub-folders of a task folder.

    """

    def __init__(self, section, k, v, data, parent=None):
        super().__init__(parent=parent)
        self.section = section
        self.k = k
        self.v = v
        self.data = data

        self.setWindowTitle('Edit Sub-folders')
        self._create_ui()

    def _create_ui(self):
        o = common.size(common.size_margin)
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        main_grp = base.add_section('', 'Edit Sub-folders', self)
        grp = ui.get_group(parent=main_grp)

        for _k, _v in self.v['subfolders'].items():
            if not isinstance(_v, dict):
                log.error(f'Invalid data. Key: {_k}, Value: {_v}')
                continue

            _row = ui.add_row(_v['name'], parent=grp)
            editor = ui.LineEdit(parent=_row)
            editor.setText(_v['value'])

            key = f'{self.section}/{self.k}/subfolders/{_k}/value'
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
            None, height=common.size(
                common.size_row_height
            ), parent=self
        )
        row.layout().addWidget(self.save_button, 1)
        row.layout().addWidget(self.cancel_button, 0)

        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted)
        )
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected)
        )


class TokenConfigEditor(QtWidgets.QWidget):
    """The widget used to display and edit a bookmark's token configuration.

    """

    def __init__(self, server, job, root, parent=None):
        super().__init__(parent=parent)
        self.server = server
        self.job = job
        self.root = root

        self.tokens = None
        self.current_data = {}
        self.changed_data = {}

        self.header_buttons = []
        self.scroll_area = None
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.init_data()

        self.ui_groups = {}

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        common.set_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        o = common.size(common.size_margin)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o)

        # Re-fetch the config data from the database

        for k in SECTIONS:
            self._add_section(k)

    def _add_section_item(self, parent, section, data):
        """Adds a new item to a section.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
            section (str): The section to add the item to.
            data (dict): The data to add.

        Returns:
            QtWidgets.QWidget: The widget that was added.

        """
        grp = ui.get_group(vertical=False, parent=parent)
        grp.setObjectName('section_item_group')
        grp.section = section

        _row1 = ui.add_row(None, height=None, vertical=True, parent=grp)

        for _k in ('name', 'value', 'description'):
            row = ui.add_row(_k.title(), height=common.size(common.size_row_height), parent=_row1)
            editor = ui.LineEdit(parent=row)
            editor.setObjectName(f'section_item_{_k}')

            editor.setAlignment(QtCore.Qt.AlignRight)
            editor.setText(data[_k])
            editor.setPlaceholderText(f'Edit {_k}...')

            if _k in ('name', 'description'):
                editor.setStyleSheet(
                    f'color: {common.rgb(common.color_secondary_text)};'
                )
            else:
                editor.setStyleSheet(
                    f'color: {common.rgb(common.color_text)};'
                )
            row.layout().addWidget(editor, 1)

        _row2 = ui.add_row(None, height=None, vertical=False, parent=None)
        grp.layout().addWidget(_row2, 0)

        button = ui.ClickableIconButton(
            'add_circle',
            (common.color(common.color_text), common.color(common.color_text)),
            common.size(common.size_margin),
            description='Insert token',
            parent=_row2
        )
        _row2.layout().addWidget(button, 0)
        value_editor = [x for x in grp.findChildren(QtWidgets.QLineEdit) if x.objectName() == 'section_item_value'][0]
        button.clicked.connect(
            functools.partial(self.show_token_editor, value_editor)
        )

        button = ui.ClickableIconButton(
            'arrow_up',
            (common.color(common.color_text), common.color(common.color_text)),
            common.size(common.size_margin),
            description='Move item up',
            parent=_row2
        )
        _row2.layout().addWidget(button, 0)
        button.clicked.connect(
            functools.partial(self.move_item, grp, MoveUp)
        )

        button = ui.ClickableIconButton(
            'arrow_down',
            (common.color(common.color_text), common.color(common.color_text)),
            common.size(common.size_margin),
            description='Move item down',
            parent=_row2
        )
        _row2.layout().addWidget(button, 0)
        button.clicked.connect(
            functools.partial(self.move_item, grp, MoveDown)
        )

        button = ui.ClickableIconButton(
            'archive',
            (common.color(common.color_red), common.color(common.color_red)),
            common.size(common.size_margin),
            description='Remove item',
            parent=_row2
        )
        _row2.layout().addWidget(button, 0)
        button.clicked.connect(
            functools.partial(self.remove_item, grp)
        )

        return grp

    def _add_section(self, section):
        # Re-fetch the config data from the database
        data = self.tokens.data(force=True)

        if section not in data:
            print(f'Invalid section: {section}. Skipping.')
            return

        if not isinstance(data[section], dict):
            log.error('Invalid data.')
            return

        for k, v in data[section].items():
            if not isinstance(
                    v, dict
            ) or 'name' not in v or 'description' not in v:
                log.error(f'Invalid data. Key: {k}, value: {v}')
                return

        h = common.size(common.size_row_height)

        main_grp = base.add_section(
            'file',
            SECTIONS[section]['name'],
            self,
            color=common.color(common.color_dark_background)
        )

        self.ui_groups[section] = main_grp
        self.header_buttons.append((SECTIONS[section]['name'], main_grp))

        _grp = ui.get_group(parent=main_grp)

        # Control buttons
        control_row = ui.add_row(
            None, height=None, parent=_grp
        )

        ui.add_description(
            SECTIONS[section]['description'],
            height=None,
            label=None,
            parent=control_row
        )
        control_row.layout().addStretch(1)

        if section in (tokens.PublishConfig, tokens.FFMpegTCConfig, tokens.FileNameConfig):
            add_button = ui.ClickableIconButton(
                'add',
                (common.color(common.color_green), common.color(common.color_green)),
                common.size(common.size_margin) * 1.5,
                description='Add new item',
                parent=control_row
            )
            control_row.layout().addWidget(add_button, 0)

            add_button.clicked.connect(
                functools.partial(self.add_item, _grp, section)
            )

        reset_button = ui.PaintedButton('Revert to defaults')
        reset_button.clicked.connect(functools.partial(self.restore_defaults, section))

        control_row.layout().addWidget(reset_button, 0)

        for k, v in data[section].items():

            if section in (tokens.PublishConfig, tokens.FFMpegTCConfig, tokens.FileNameConfig):
                grp = self._add_section_item(_grp, section, v)
            else:
                _name = v['name'].title()
                row = ui.add_row(_name, height=h, parent=_grp)

                row.setStatusTip(v['description'])
                row.setWhatsThis(v['description'])
                row.setToolTip(v['description'])
                row.setAccessibleDescription(v['description'])

                editor = ui.LineEdit(parent=row)
                editor.setAlignment(QtCore.Qt.AlignRight)
                editor.setText(v['value'])

                row.layout().addWidget(editor, 1)

                # Save current data
                key = f'{section}/{k}/value'
                self.current_data[key] = v['value']

                editor.textChanged.connect(
                    functools.partial(self.text_changed, key, editor)
                )

                if section == tokens.AssetFolderConfig:
                    button = ui.PaintedButton('Formats', parent=row)
                    row.layout().addWidget(button, 0)
                    if 'filter' in v:
                        key = f'{section}/{k}/filter'
                        self.current_data[key] = v['filter']
                        button.clicked.connect(
                            functools.partial(self.show_filter_editor, key, v, data)
                        )
                    else:
                        button.setDisabled(True)

                    button = ui.PaintedButton('Subfolders', parent=row)
                    row.layout().addWidget(button, 0)
                    if 'subfolders' in v and isinstance(v['subfolders'], dict):
                        button.clicked.connect(
                            functools.partial(
                                self.show_subfolders_editor, section, k, v, data
                            )
                        )
                    else:
                        button.setDisabled(True)

    def init_data(self):
        """Initializes data.

        """
        self.tokens = tokens.get(self.server, self.job, self.root)

    @QtCore.Slot(QtWidgets.QWidget)
    @QtCore.Slot(int)
    def move_item(self, widget, direction):
        """Moves an item up or down in its own section.

        Args:
            widget (QtWidgets.QWidget): The widget to move.
            direction (int): The direction to move the widget in.

        """
        # Get the layout index of the widget
        layout = widget.parent().layout()
        index = layout.indexOf(widget)

        # Get the new index
        if direction == MoveUp:
            min_index = 1  # Skip the first row as this is the control row
            new_index = index - 1
            new_index = min_index if new_index < min_index else new_index
        else:
            new_index = index + 1
            new_index = layout.count() - 1 if new_index >= layout.count() else new_index

        # Set the new layout index
        layout.insertWidget(new_index, layout.takeAt(index).widget())

    @QtCore.Slot(QtWidgets.QWidget)
    @QtCore.Slot(str)
    @common.error
    def add_item(self, parent, section):
        """Adds a new item to a section.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
            section (str): The section to add the item to.

        """
        grp = self._add_section_item(
            parent, section, {
                'name': '',
                'value': '',
                'description': ''
            }
        )

        # Find the value editor
        editor = next(
            (x for x in grp.findChildren(QtWidgets.QLineEdit) if x.objectName() == 'section_item_value'),
            None
        )
        if not editor:
            raise RuntimeError('Unable to find the value editor.')
        editor.setFocus(QtCore.Qt.PopupFocusReason)
        self.window().scroll_to_section(grp)

    @QtCore.Slot(QtWidgets.QWidget)
    def remove_item(self, widget):
        """Removes an item from a section.

        Args:
            widget (QtWidgets.QWidget): The widget to remove.

        """
        # Prompt the user for confirmation
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

    @QtCore.Slot(str)
    def restore_defaults(self, section):
        """Restores the default values for a given section.

        Args:
            section (str): The section to restore.

        """
        if common.show_message(
                'Are you sure you want to restore the default values?',
                body='Any custom values will be permanently lost.',
                buttons=[common.YesButton, common.CancelButton],
                modal=True,
        ) == QtWidgets.QDialog.Rejected:
            return False

        if section not in self.ui_groups:
            print(f'Invalid section: {section}. Skipping.')
            return

        if section not in self.tokens.data():
            print(f'Invalid section: {section}. Skipping.')
            return

        if not self.ui_groups[section]:
            print(f'Invalid section: {section}. Skipping.')
            return

        if not self.write_default_to_database(section):
            return

        for k in SECTIONS:
            self.ui_groups[k].deleteLater()
            self.ui_groups[k] = None
            del self.ui_groups[k]

            self._add_section(k)

    @QtCore.Slot(str)
    @QtCore.Slot(dict)
    @QtCore.Slot(dict)
    def show_filter_editor(self, key, v, data):
        editor = FormatEditor(parent=self)
        editor.listwidget.itemClicked.connect(
            functools.partial(self.filter_changed, key, editor)
        )

        for _v in data[tokens.FileFormatConfig].values():
            editor.listwidget.addItem(_v['name'])

            item = editor.listwidget.item(editor.listwidget.count() - 1)
            item.setData(QtCore.Qt.UserRole, _v['flag'])
            item.setData(common.PathRole, _v['description'])
            item.setData(QtCore.Qt.ToolTipRole, _v['description'])
            item.setData(QtCore.Qt.AccessibleDescriptionRole, _v['description'])
            item.setData(QtCore.Qt.WhatsThisRole, _v['description'])

            if _v['flag'] & v['filter']:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)

        editor.finished.connect(
            lambda x: self.save_changes(
            ) if x == QtWidgets.QDialog.Accepted else None
        )
        editor.exec_()

    def write_default_to_database(self, section):
        """Restore the default values for a given section and write them to the database.

        Args:
            section (str): The section to restore.

        Returns:
            bool: True if successful.

        """
        data = self.tokens.data(force=True)
        if section not in data:
            print(f'Invalid section: {section}. Skipping.')
            return False
        if section not in tokens.DEFAULT_TOKEN_CONFIG:
            print(f'Invalid section: {section}. Skipping.')
            return False

        default_section = copy.deepcopy(tokens.DEFAULT_TOKEN_CONFIG[section])
        data[section] = default_section

        self.tokens.set_data(data)
        return True

    @QtCore.Slot(str)
    @QtCore.Slot(dict)
    @QtCore.Slot(dict)
    def show_subfolders_editor(self, section, k, v, data):
        editor = SubfolderEditor(section, k, v, data, parent=self)
        editor.finished.connect(
            lambda x: self.save_changes(
            ) if x == QtWidgets.QDialog.Accepted else None
        )
        editor.exec_()

    @QtCore.Slot(QtWidgets.QWidget)
    def show_token_editor(self, editor):
        """Shows the token editor.

        Args:
            editor (QtWidgets.QWidget): The editor to insert the token into.

        """
        w = TokenEditor(self.server, self.job, self.root, parent=editor)
        w.tokenSelected.connect(editor.insert)
        w.exec_()

    @QtCore.Slot(str)
    @QtCore.Slot(str)
    @QtCore.Slot(QtWidgets.QWidget)
    def filter_changed(self, key, editor, *args):
        v = 0
        for n in range(editor.listwidget.count()):
            item = editor.listwidget.item(n)
            if item.checkState() == QtCore.Qt.Checked:
                v |= item.data(QtCore.Qt.UserRole)
        self.changed_data[key] = v

    @QtCore.Slot(str)
    @QtCore.Slot(str)
    @QtCore.Slot(QtWidgets.QWidget)
    def text_changed(self, key, editor, v):
        """Slot responsible for marking an entry as changed.

        """
        if key not in self.current_data:
            self.current_data[key] = v

        if v != self.current_data[key]:
            self.changed_data[key] = v
            editor.setStyleSheet(f'color: {common.rgb(common.color_green)};')
            return

        if key in self.changed_data:
            del self.changed_data[key]
        editor.setStyleSheet(f'color: {common.rgb(common.color_text)};')

    @QtCore.Slot()
    def save_changes(self):
        """Saves changes.

        """
        # Retrieve the current data from the database
        data = self.tokens.data(force=True)

        # Update the data with the changed values
        for keys, v in self.changed_data.copy().items():
            _set(data, keys, v)
            del self.changed_data[keys]

        for section in (tokens.PublishConfig, tokens.FFMpegTCConfig, tokens.FileNameConfig):
            if section not in data:
                print(f'"{section}" not found in data! Skipping.')

            # Reset the current data section and replace it with the values in the UI.
            data[section] = {}

            # Let's find the list of section group widgets
            items = [f for f in self.findChildren(QtWidgets.QWidget, 'section_item_group') if f.section == section]
            for item in items:

                name_editor = item.findChildren(QtWidgets.QWidget, 'section_item_name')[0]
                value_editor = item.findChildren(QtWidgets.QWidget, 'section_item_value')[0]
                description_editor = item.findChildren(QtWidgets.QWidget, 'section_item_description')[0]

                if not all((name_editor.text(), value_editor.text())):
                    continue

                data[section][len(data[section])] = {
                    'name': name_editor.text(),
                    'value': value_editor.text(),
                    'description': description_editor.text() if description_editor.text() else '',
                }

        self.tokens.set_data(data)

    def _connect_signals(self):
        pass
