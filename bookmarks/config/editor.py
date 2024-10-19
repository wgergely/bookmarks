# editor.py

import copy
import enum
import functools

from PySide2 import QtWidgets, QtCore

from .lib import *
from .. import common, tokens
from .. import log
from .. import ui
from ..common import TokenLineEdit
from ..editor import base

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



class Field(enum.StrEnum):
    Name = 'name'
    Value = 'value'
    Description = 'description'
    Flag = 'flag'
    Status = 'status'
    Icon = 'icon'


class FlagEditorWrapper(QtWidgets.QWidget):
    """
    A wrapper widget for editing flags interactively.

    This widget includes a toggle button that switches between 'Edit Flags' and 'Done'.
    The flag editor allows users to select or deselect flags, computes the aggregate flag
    value using bitwise OR, and supports toggling flags via double-click. It automatically
    collapses when focus is lost, with smooth animations for expanding and collapsing.

    Signals:
        valueChanged(int): Emitted when the aggregate flag value changes.
    """

    valueChanged = QtCore.Signal(int)

    def __init__(self, flag_enum):
        """
        Initialize the FlagEditorWrapper widget.

        Args:
            flag_enum (enum.IntFlag): An enumeration class defining the available flags.
        """
        super().__init__()
        self.toggle_button = None
        self.collapsible_widget = None
        self.list_widget = None
        self.result_label = None
        self.animation = None
        self.flags = {name: member.value for name, member in flag_enum.__members__.items()}
        self.result = 0
        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        """
        Set up the user interface components.
        """
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.toggle_button = QtWidgets.QPushButton('Edit Flags')
        layout.addWidget(self.toggle_button)

        self.collapsible_widget = QtWidgets.QWidget()
        self.collapsible_widget.setMaximumHeight(0)
        self.collapsible_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        collapsible_layout = QtWidgets.QVBoxLayout()
        self.collapsible_widget.setLayout(collapsible_layout)

        self.list_widget = QtWidgets.QListWidget()
        for flag_name in self.flags:
            item = QtWidgets.QListWidgetItem(flag_name)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            self.list_widget.addItem(item)
        collapsible_layout.addWidget(self.list_widget)

        self.result_label = QtWidgets.QLabel('Resulting Flag Value: 0x00')
        collapsible_layout.addWidget(self.result_label)

        layout.addWidget(self.collapsible_widget)

        self.animation = QtCore.QPropertyAnimation(self.collapsible_widget, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

    def _connect_signals(self):
        """
        Connect signals to their respective slots.
        """
        self.toggle_button.clicked.connect(self._toggle_flag_editor)
        self.list_widget.itemChanged.connect(self._compute_flags)
        self.list_widget.itemDoubleClicked.connect(self._toggle_flag_on_double_click)
        QtWidgets.QApplication.instance().focusChanged.connect(self._on_focus_changed)

    @QtCore.Slot()
    def _toggle_flag_editor(self):
        """
        Toggle the visibility of the flag editor with animation.

        Switches the button text between 'Edit Flags' and 'Done'.
        """
        if self.animation.state() == QtCore.QAbstractAnimation.Running:
            return

        if self.collapsible_widget.isVisible() and self.collapsible_widget.maximumHeight() > 0:
            self.toggle_button.setEnabled(False)
            self.animation.setStartValue(self.collapsible_widget.height())
            self.animation.setEndValue(0)
            self.animation.start()
            self.animation.finished.connect(self._on_collapse_finished)
        else:
            self.collapsible_widget.setVisible(True)
            self.collapsible_widget.setMaximumHeight(0)
            self.collapsible_widget.adjustSize()
            target_height = self.collapsible_widget.sizeHint().height()

            self.toggle_button.setEnabled(False)
            self.animation.setStartValue(0)
            self.animation.setEndValue(target_height)
            self.animation.start()
            self.animation.finished.connect(self._on_expand_finished)

    @QtCore.Slot()
    def _on_expand_finished(self):
        self.toggle_button.setText('Done')
        self.animation.finished.disconnect(self._on_expand_finished)
        self.toggle_button.setEnabled(True)
        self.valueChanged.emit(self.result)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            self.list_widget.item(0).setSelected(True)
            self.list_widget.setFocus()

    @QtCore.Slot()
    def _on_collapse_finished(self):
        self.collapsible_widget.setVisible(False)
        self.toggle_button.setText('Edit Flags')
        self.animation.finished.disconnect(self._on_collapse_finished)
        self.toggle_button.setEnabled(True)
        self.valueChanged.emit(self.result)
        self.toggle_button.setFocus()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def _compute_flags(self, item):
        """
        Compute the aggregate flag value based on selected flags using bitwise OR.

        Args:
            item (QListWidgetItem): The item that was changed.
        """
        result = 0
        for index in range(self.list_widget.count()):
            current_item = self.list_widget.item(index)
            if current_item.checkState() == QtCore.Qt.Checked:
                result |= self.flags.get(current_item.text(), 0)
        self.result = result
        self.result_label.setText(f'Resulting Flag Value: 0x{self.result:02X}')
        self.valueChanged.emit(self.result)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def _toggle_flag_on_double_click(self, item):
        """
        Toggle the check state of a flag item upon double-click.

        Args:
            item (QListWidgetItem): The item that was double-clicked.
        """
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
        else:
            item.setCheckState(QtCore.Qt.Checked)

    @QtCore.Slot(QtWidgets.QWidget, QtWidgets.QWidget)
    def _on_focus_changed(self, old, now):
        """
        Automatically collapse the flag editor if focus is lost.

        Args:
            old (QWidget): The widget that lost focus.
            now (QWidget): The widget that gained focus.
        """
        if not self._is_ancestor_of(now):
            if self.collapsible_widget.isVisible() and self.collapsible_widget.maximumHeight() > 0:
                self.animation.setStartValue(self.collapsible_widget.height())
                self.animation.setEndValue(0)
                self.animation.start()
                self.animation.finished.connect(self._on_collapse_finished)

    def _is_ancestor_of(self, widget):
        """
        Check if the current widget is an ancestor of the given widget.

        Args:
            widget (QWidget): The widget to check.

        Returns:
            bool: True if self is an ancestor of widget, False otherwise.
        """
        parent = widget
        while parent is not None:
            if parent == self:
                return True
            parent = parent.parentWidget()
        return False

    @QtCore.Slot(int)
    def init_value(self, value):
        """
        Initialize the flag editor with a given aggregate flag value.

        This method sets the check state of each flag item based on the bits set in the provided value.

        Args:
            value (int): The aggregate flag value to initialize the editor with.
        """
        self.blockSignals(True)
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            flag_name = item.text()
            flag_value = self.flags.get(flag_name, 0)
            if value & flag_value:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
        self.blockSignals(False)
        self._compute_flags(None)

    def value(self):
        """
        Get the current aggregate flag value.

        Returns:
            int: The resulting flag value.
        """
        return self.result


class FlagEditor(QtWidgets.QWidget):
    """
    A wrapper widget for editing flags interactively.

    This widget includes a toggle button that switches between 'Edit Flags' and 'Done'.
    The flag editor allows users to select or deselect flags, computes the aggregate flag
    value using bitwise OR, and supports toggling flags via double-click. It automatically
    collapses when focus is lost, with smooth animations for expanding and collapsing.

    Signals:
        valueChanged(int): Emitted when the aggregate flag value changes.
    """

    valueChanged = QtCore.Signal(int)

    def __init__(self, flag_enum):
        """
        Initialize the FlagEditorWrapper widget.

        Args:
            flag_enum (enum.IntFlag): An enumeration class defining the available flags.
        """
        super().__init__()
        self.toggle_button = None
        self.collapsible_widget = None
        self.list_widget = None
        self.result_label = None
        self.animation = None
        self.flags = {name: member.value for name, member in flag_enum.__members__.items()}
        self.result = 0
        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        """
        Set up the user interface components.
        """
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.toggle_button = QtWidgets.QPushButton('Edit Flags')
        layout.addWidget(self.toggle_button)

        self.collapsible_widget = QtWidgets.QWidget()
        self.collapsible_widget.setMaximumHeight(0)
        self.collapsible_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        collapsible_layout = QtWidgets.QVBoxLayout()
        self.collapsible_widget.setLayout(collapsible_layout)

        self.list_widget = QtWidgets.QListWidget()
        for flag_name in self.flags:
            item = QtWidgets.QListWidgetItem(flag_name)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            self.list_widget.addItem(item)
        collapsible_layout.addWidget(self.list_widget)

        self.result_label = QtWidgets.QLabel('Resulting Flag Value: 0x00')
        collapsible_layout.addWidget(self.result_label)

        layout.addWidget(self.collapsible_widget)

        self.animation = QtCore.QPropertyAnimation(self.collapsible_widget, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

    def _connect_signals(self):
        """
        Connect signals to their respective slots.
        """
        self.toggle_button.clicked.connect(self._toggle_flag_editor)
        self.list_widget.itemChanged.connect(self._compute_flags)
        self.list_widget.itemDoubleClicked.connect(self._toggle_flag_on_double_click)
        QtWidgets.QApplication.instance().focusChanged.connect(self._on_focus_changed)

    @QtCore.Slot()
    def _toggle_flag_editor(self):
        """
        Toggle the visibility of the flag editor with animation.

        Switches the button text between 'Edit Flags' and 'Done'.
        """
        if self.animation.state() == QtCore.QAbstractAnimation.Running:
            return

        if self.collapsible_widget.isVisible() and self.collapsible_widget.maximumHeight() > 0:
            self.toggle_button.setEnabled(False)
            self.animation.setStartValue(self.collapsible_widget.height())
            self.animation.setEndValue(0)
            self.animation.start()
            self.animation.finished.connect(self._on_collapse_finished)
        else:
            self.collapsible_widget.setVisible(True)
            self.collapsible_widget.setMaximumHeight(0)
            self.collapsible_widget.adjustSize()
            target_height = self.collapsible_widget.sizeHint().height()

            self.toggle_button.setEnabled(False)
            self.animation.setStartValue(0)
            self.animation.setEndValue(target_height)
            self.animation.start()
            self.animation.finished.connect(self._on_expand_finished)

    @QtCore.Slot()
    def _on_expand_finished(self):
        self.toggle_button.setText('Done')
        self.animation.finished.disconnect(self._on_expand_finished)
        self.toggle_button.setEnabled(True)
        self.valueChanged.emit(self.result)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            self.list_widget.item(0).setSelected(True)
            self.list_widget.setFocus()

    @QtCore.Slot()
    def _on_collapse_finished(self):
        self.collapsible_widget.setVisible(False)
        self.toggle_button.setText('Edit Flags')
        self.animation.finished.disconnect(self._on_collapse_finished)
        self.toggle_button.setEnabled(True)
        self.valueChanged.emit(self.result)
        self.toggle_button.setFocus()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def _compute_flags(self, item):
        """
        Compute the aggregate flag value based on selected flags using bitwise OR.

        Args:
            item (QListWidgetItem): The item that was changed.
        """
        result = 0
        for index in range(self.list_widget.count()):
            current_item = self.list_widget.item(index)
            if current_item.checkState() == QtCore.Qt.Checked:
                result |= self.flags.get(current_item.text(), 0)
        self.result = result
        self.result_label.setText(f'Resulting Flag Value: 0x{self.result:02X}')
        self.valueChanged.emit(self.result)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def _toggle_flag_on_double_click(self, item):
        """
        Toggle the check state of a flag item upon double-click.

        Args:
            item (QListWidgetItem): The item that was double-clicked.
        """
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
        else:
            item.setCheckState(QtCore.Qt.Checked)

    @QtCore.Slot(QtWidgets.QWidget, QtWidgets.QWidget)
    def _on_focus_changed(self, old, now):
        """
        Automatically collapse the flag editor if focus is lost.

        Args:
            old (QWidget): The widget that lost focus.
            now (QWidget): The widget that gained focus.
        """
        if not self._is_ancestor_of(now):
            if self.collapsible_widget.isVisible() and self.collapsible_widget.maximumHeight() > 0:
                self.animation.setStartValue(self.collapsible_widget.height())
                self.animation.setEndValue(0)
                self.animation.start()
                self.animation.finished.connect(self._on_collapse_finished)

    def _is_ancestor_of(self, widget):
        """
        Check if the current widget is an ancestor of the given widget.

        Args:
            widget (QWidget): The widget to check.

        Returns:
            bool: True if self is an ancestor of widget, False otherwise.
        """
        parent = widget
        while parent is not None:
            if parent == self:
                return True
            parent = parent.parentWidget()
        return False

    @QtCore.Slot(int)
    def init_value(self, value):
        """
        Initialize the flag editor with a given aggregate flag value.

        This method sets the check state of each flag item based on the bits set in the provided value.

        Args:
            value (int): The aggregate flag value to initialize the editor with.
        """
        self.blockSignals(True)
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            flag_name = item.text()
            flag_value = self.flags.get(flag_name, 0)
            if value & flag_value:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
        self.blockSignals(False)
        self._compute_flags(None)

    def value(self):
        """
        Get the current aggregate flag value.

        Returns:
            int: The resulting flag value.
        """
        return self.result




class ConfigItem(QtWidgets.QWidget):

    fields = {
        Field.Name: {
            'type': str,
            'editor': TokenLineEdit,
        },
        Field.Value: {
            'type': str,
            'editor': TokenLineEdit,
        },
        Field.Description: {
            'type': str,
            'editor': TokenLineEdit,
        },
        Field.Flag: {
            'type': int,
            'editor': FlagEditor,
        },
        Field.Status: {
            'type': dict,
            'editor': TokenLineEdit,
        },
        Field.Icon: {
            'type': str,
            'editor': TokenLineEdit,
        },
    }

    _editors = {
        Field.Name: TokenLineEdit,
        Field.Value: TokenLineEdit,
        Field.Description: TokenLineEdit,
        Field.Flag: FlagEditor,
        Field.Status: TokenLineEdit,
        Field.Icon: TokenLineEdit,
    }

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent)

        for k in Field:
            setattr(self, f'_{k}', None)
            setattr(self, f'{k}_editor', None)

        self._create_ui()
        self._connect_signals()

        # Some config fields are optional, others are read-only.
        # Hide or disable them based on the supplied kwargs
        for k in Field:
            if f'hide_{k}' in kwargs:
                getattr(self, f'{k}_editor').hide()
            if f'disable_{k}' in kwargs:
                getattr(self, f'{k}_editor').setDisabled(True)

    def data(self):
        data = {}
        for k in Field:
            editor = getattr(self, f'{k}_editor')
            if editor is None:
                raise ValueError(f'Editor for field {k} is not defined.')

            if editor.isHidden() or editor.isDisabled():
                continue

            if isinstance(editor, TokenLineEdit):
                data[k] = editor.text()
            elif isinstance(editor, FlagEditor):
                data[k] = editor.value()

        return data


class ConfigSectionEditor(QtWidgets.QWidget):
    """The editor widget responsible for editing a bookmark configuration section.

    The editor is made up of a series of ConfigItem widgets, each representing a dict entry in the section.

    """

    def __init__(self, section, parent=None):
        super().__init__(parent=parent)
        if section not in Section:
            raise ValueError(f'Invalid section: {section}, expected one of {Section}')

        self._section = section
        self._original_data = None

        self._create_ui()
        self._connect_signals()

        self.init_data()

    @property
    def server(self):
        return self.window().server

    @property
    def job(self):
        return self.window().job

    @property
    def root(self):
        return self.window().root

    @property
    def current_data(self):
        return self.current_data

    @property
    def section(self):
        return self._section

    # @property
    # def items(self):
    #

    def init_data(self):
        config = Config(
            server=self.server,
            job=self.job,
            root=self.root,
        )
        self._original_data = copy.deepcopy(config.data(self.section, force=True))

        # data = self.tokens.data(force=True)
        # if self.section not in data:
        #     common.log.error(f'Section {self.section} not found in data.')
        #     return
        #
        # section_data = data[self.section]
        #
        # # Create control row
        # self.create_control_row()
        #
        # # Add items
        # for k, v in section_data.items():
        #     self.create_item(k, v)

    def _create_ui(self):
        o = common.Size.Margin()
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o)

    def _connect_signals(self):
        pass

    @QtCore.Slot(str, QtWidgets.QWidget, str)
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
                widget.deleteLater()
        self._create_ui()

    def get_section_description(self):
        return self.sections[self.section]['description']

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
            value_editor = (
                    item.findChildren(QtWidgets.QLineEdit, 'section_item_value') + item.findChildren(TokenLineEdit,
                                                                                                     'section_item_value'))[
                0]
            description_editor = item.findChildren(QtWidgets.QLineEdit, 'section_item_description')[0]

            if not all((name_editor.text(), value_editor.text())):
                continue

            data[self.section][idx] = {
                'name': name_editor.text(),
                'value': value_editor.text(),
                'description': description_editor.text() if description_editor.text() else '',
            }

        self.tokens.set_data(data)

#
# class TasksConfigEditor(MovableItemsEditor):
#     """Editor for the TasksConfig section."""
#
#     def __init__(self, parent=None):
#         super().__init__(tokens.TasksConfig, parent=parent)
#
#
# class FileNameConfigEditor(MovableItemsEditor):
#     """Editor for the FileNameConfig section."""
#
#     def __init__(self, parent=None):
#         super().__init__(tokens.FileNameConfig, parent=parent)
#
#
# class PublishConfigEditor(MovableItemsEditor):
#     """Editor for the PublishConfig section."""
#
#     def __init__(self, parent=None):
#         super().__init__(tokens.PublishConfig, parent=parent)
#
#
# class FFMpegTCConfigEditor(MovableItemsEditor):
#     """Editor for the FFMpegTCConfig section."""
#
#     def __init__(self, parent=None):
#         super().__init__(tokens.FFMpegTCConfig, parent=parent)
#
#
# class FormatEditor(QtWidgets.QDialog):
#     """Popup widget used to set the acceptable file formats for a task folder."""
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.list_widget = None
#
#         self.setWindowTitle('Edit Formats')
#         self._create_ui()
#
#     def _create_ui(self):
#         o = common.Size.Margin()
#         QtWidgets.QVBoxLayout(self)
#         self.layout().setContentsMargins(o, o, o, o)
#         self.layout().setSpacing(o)
#
#         self.list_widget = ui.ListWidget(parent=self)
#         self.list_widget.setWrapping(False)
#         self.list_widget.setSpacing(0)
#         self.list_widget.setAttribute(QtCore.Qt.WA_NoSystemBackground)
#         self.list_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
#         self.list_widget.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
#         self.list_widget.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
#
#         self.layout().addWidget(self.list_widget, 1)
#         self.list_widget.itemClicked.connect(self.list_widget.toggle)
#
#         self.save_button = ui.PaintedButton('Save')
#         self.cancel_button = ui.PaintedButton('Cancel')
#
#         row = ui.add_row(
#             None, height=common.Size.RowHeight(), parent=self
#         )
#         row.layout().addWidget(self.save_button, 1)
#         row.layout().addWidget(self.cancel_button, 0)
#
#         self.save_button.clicked.connect(
#             lambda: self.done(QtWidgets.QDialog.Accepted)
#         )
#         self.cancel_button.clicked.connect(
#             lambda: self.done(QtWidgets.QDialog.Rejected)
#         )
#
#
# class SubfolderEditor(QtWidgets.QDialog):
#     """A popup editor used to edit the subfolders of a task folder."""
#
#     def __init__(self, section, key, data, parent=None):
#         super().__init__(parent=parent)
#         self.section = section
#         self.key = key
#         self.data = data
#
#         self.setWindowTitle('Edit Sub-folders')
#         self._create_ui()
#
#     def _create_ui(self):
#         o = common.Size.Margin()
#         QtWidgets.QVBoxLayout(self)
#         self.layout().setContentsMargins(o, o, o, o)
#         self.layout().setSpacing(o)
#
#         main_grp = base.add_section('', 'Edit Sub-folders', self)
#         grp = ui.get_group(parent=main_grp)
#
#         for _k, _v in self.data['subfolders'].items():
#             if not isinstance(_v, dict):
#                 log.error(f'Invalid data. Key: {_k}, Value: {_v}')
#                 continue
#
#             _row = ui.add_row(_v['name'], parent=grp)
#             editor = ui.LineEdit(parent=_row)
#             editor.setText(_v['value'])
#
#             key = f'{self.section}/{self.key}/subfolders/{_k}/value'
#             self.parent().current_data[key] = _v['value']
#
#             editor.textChanged.connect(
#                 functools.partial(self.parent().text_changed, key, editor)
#             )
#
#             _row.layout().addWidget(editor, 1)
#             _row.setStatusTip(_v['description'])
#             _row.setWhatsThis(_v['description'])
#             _row.setToolTip(_v['description'])
#
#         self.save_button = ui.PaintedButton('Save')
#         self.cancel_button = ui.PaintedButton('Cancel')
#
#         row = ui.add_row(
#             None, height=common.Size.RowHeight(), parent=self
#         )
#         row.layout().addWidget(self.save_button, 1)
#         row.layout().addWidget(self.cancel_button, 0)
#
#         self.save_button.clicked.connect(
#             lambda: self.done(QtWidgets.QDialog.Accepted)
#         )
#         self.cancel_button.clicked.connect(
#             lambda: self.done(QtWidgets.QDialog.Rejected)
#         )
#
#
# class AssetFolderConfigEditor(BaseEditor):
#     """Editor for the AssetFolderConfig section."""
#
#     def __init__(self, parent=None):
#         super().__init__(tokens.AssetFolderConfig, parent=parent)
#
#     def get_section_description(self):
#         return 'Common folders that define the principal folders of an asset item. These values are used when browsing files, saving scene files and publishing items.'
#
#     def _create_ui(self):
#         o = common.Size.Margin()
#         QtWidgets.QVBoxLayout(self)
#         self.layout().setContentsMargins(0, 0, 0, 0)
#         self.layout().setSpacing(o)
#
#         data = self.tokens.data(force=True)
#         section_data = data.get(self.section, {})
#
#         # Create control row
#         self.create_control_row()
#
#         # Add items
#         for k, v in section_data.items():
#             self.create_item(k, v)
#
#     def create_control_row(self):
#         control_row = ui.add_row(
#             None, height=None, parent=self
#         )
#
#         ui.add_description(
#             self.get_section_description(),
#             height=None,
#             label=None,
#             parent=control_row
#         )
#
#         reset_button = ui.PaintedButton('Revert to defaults')
#         reset_button.clicked.connect(self.restore_defaults)
#
#         control_row.layout().addWidget(reset_button, 0)
#
#     def create_item(self, key, data):
#         h = common.Size.RowHeight()
#         _name = data['name'].title()
#         row = ui.add_row(_name, height=h, parent=self)
#
#         row.setStatusTip(data['description'])
#         row.setWhatsThis(data['description'])
#         row.setToolTip(data['description'])
#         row.setAccessibleDescription(data['description'])
#
#         editor = ui.LineEdit(parent=row)
#         editor.setAlignment(QtCore.Qt.AlignRight)
#         editor.setText(data['value'])
#
#         row.layout().addWidget(editor, 1)
#
#         # Save current data
#         value_key = f'{self.section}/{key}/value'
#         self.current_data[value_key] = data['value']
#
#         editor.textChanged.connect(
#             functools.partial(self.text_changed, value_key, editor)
#         )
#
#         # 'Formats' button
#         button = ui.PaintedButton('Formats', parent=row)
#         row.layout().addWidget(button, 0)
#         if 'filter' in data:
#             filter_key = f'{self.section}/{key}/filter'
#             self.current_data[filter_key] = data['filter']
#             button.clicked.connect(
#                 functools.partial(self.show_filter_editor, filter_key, data)
#             )
#         else:
#             button.setDisabled(True)
#
#         # 'Subfolders' button
#         button = ui.PaintedButton('Subfolders', parent=row)
#         row.layout().addWidget(button, 0)
#         if 'subfolders' in data and isinstance(data['subfolders'], dict):
#             button.clicked.connect(
#                 functools.partial(
#                     self.show_subfolders_editor, key, data
#                 )
#             )
#         else:
#             button.setDisabled(True)
#
#     def show_filter_editor(self, key, data):
#         editor = FormatEditor(parent=self)
#         editor.list_widget.itemClicked.connect(
#             functools.partial(self.filter_changed, key, editor)
#         )
#
#         format_data = self.tokens.data()[tokens.FileFormatConfig]
#         for _v in format_data.values():
#             editor.list_widget.addItem(_v['name'])
#
#             item = editor.list_widget.item(editor.list_widget.count() - 1)
#             item.setData(QtCore.Qt.UserRole, _v['flag'])
#             item.setData(common.PathRole, _v['description'])
#             item.setData(QtCore.Qt.ToolTipRole, _v['description'])
#             item.setData(QtCore.Qt.AccessibleDescriptionRole, _v['description'])
#             item.setData(QtCore.Qt.WhatsThisRole, _v['description'])
#
#             if _v['flag'] & data['filter']:
#                 item.setCheckState(QtCore.Qt.Checked)
#             else:
#                 item.setCheckState(QtCore.Qt.Unchecked)
#
#         editor.finished.connect(
#             lambda x: self.save_changes(
#             ) if x == QtWidgets.QDialog.Accepted else None
#         )
#         editor.exec_()
#
#     def filter_changed(self, key, editor, *args):
#         v = 0
#         for n in range(editor.list_widget.count()):
#             item = editor.list_widget.item(n)
#             if item.checkState() == QtCore.Qt.Checked:
#                 v |= item.data(QtCore.Qt.UserRole)
#         self.changed_data[key] = v
#
#     def show_subfolders_editor(self, key, data):
#         editor = SubfolderEditor(self.section, key, data, parent=self)
#         editor.finished.connect(
#             lambda x: self.save_changes(
#             ) if x == QtWidgets.QDialog.Accepted else None
#         )
#         editor.exec_()
#
#     def save_changes(self):
#         # Retrieve the current data from the database
#         data = self.tokens.data(force=True)
#
#         # Update the data with the changed values
#         for keys, v in self.changed_data.copy().items():
#             _set(data, keys, v)
#             del self.changed_data[keys]
#
#         self.tokens.set_data(data)
#
#
# class FileFormatConfigEditor(BaseEditor):
#     """Editor for the FileFormatConfig section."""
#
#     def __init__(self, parent=None):
#         super().__init__(tokens.FileFormatConfig, parent=parent)
#
#     def get_section_description(self):
#         return 'The list of file formats that are allowed to be shown.'
#
#     def _create_ui(self):
#         o = common.Size.Margin()
#         QtWidgets.QVBoxLayout(self)
#         self.layout().setContentsMargins(0, 0, 0, 0)
#         self.layout().setSpacing(o)
#
#         data = self.tokens.data(force=True)
#         section_data = data.get(self.section, {})
#
#         # Create control row
#         self.create_control_row()
#
#         # Add items
#         for k, v in section_data.items():
#             self.create_item(k, v)
#
#     def create_control_row(self):
#         control_row = ui.add_row(
#             None, height=None, parent=self
#         )
#
#         ui.add_description(
#             self.get_section_description(),
#             height=None,
#             label=None,
#             parent=control_row
#         )
#
#         add_button = ui.ClickableIconButton(
#             'add',
#             (common.Color.Green(), common.Color.Green()),
#             common.Size.Margin(1.5),
#             description='Add new format',
#             parent=control_row
#         )
#         control_row.layout().addWidget(add_button, 0)
#
#         add_button.clicked.connect(
#             functools.partial(self.add_item, self)
#         )
#
#         reset_button = ui.PaintedButton('Revert to defaults')
#         reset_button.clicked.connect(self.restore_defaults)
#
#         control_row.layout().addWidget(reset_button, 0)
#
#     def create_item(self, key, data):
#         # We will exclude the 'flag' field from the UI and remove movable functionality
#         grp = ui.get_group(vertical=False, parent=self)
#         grp.setObjectName('section_item_group')
#         grp.section = self.section
#
#         _row1 = ui.add_row(None, height=None, vertical=True, parent=grp)
#
#         for _k in ('name', 'value', 'description'):
#             row = ui.add_row(_k.title(), height=common.Size.RowHeight(), parent=_row1)
#             editor = ui.LineEdit(parent=row)
#             editor.setObjectName(f'section_item_{_k}')
#
#             editor.setAlignment(QtCore.Qt.AlignRight)
#             editor.setText(str(data[_k]))
#             editor.setPlaceholderText(f'Edit {_k}...')
#
#             if _k in ('name', 'description'):
#                 editor.setReadOnly(True)
#                 editor.setDisabled(True)
#
#             row.layout().addWidget(editor, 1)
#
#             # Save current data
#             item_key = f'{self.section}/{key}/{_k}'
#             self.current_data[item_key] = data[_k]
#
#             editor.textChanged.connect(
#                 functools.partial(self.text_changed, item_key, editor)
#             )
#
#         # No action buttons (no move up/down, no remove)
#
#     def add_item(self, parent):
#         key = max([int(k) for k in self.tokens.data()[self.section].keys()] + [0]) + 1
#         data = {
#             'name': '',
#             'value': '',
#             'description': '',
#             'flag': 0  # Default flag value
#         }
#         self.create_item(key, data)
#
#     def save_changes(self):
#         # We need to preserve the 'flag' values even though they are not editable
#         data = self.tokens.data(force=True)
#
#         # Update the data with the changed values
#         for keys, v in self.changed_data.copy().items():
#             _set(data, keys.split('/'), v)
#             del self.changed_data[keys]
#
#         # Reset the current data section and replace it with the values in the UI
#         original_data = data[self.section]
#         data[self.section] = {}
#
#         items = [f for f in self.findChildren(QtWidgets.QWidget, 'section_item_group') if
#                  f.section == self.section]
#         for idx, item in enumerate(items):
#             name_editor = item.findChildren(QtWidgets.QLineEdit, 'section_item_name')[0]
#             value_editor = (
#                     item.findChildren(QtWidgets.QLineEdit, 'section_item_value') + item.findChildren(TokenLineEdit,
#                                                                                                      'section_item_value'))[
#                 0]
#             description_editor = item.findChildren(QtWidgets.QLineEdit, 'section_item_description')[0]
#
#             if not all((name_editor.text(), value_editor.text())):
#                 continue
#
#             # Get the original 'flag' value
#             try:
#                 original_flag = original_data[str(idx)]['flag']
#             except KeyError:
#                 original_flag = 0  # Default value if not found
#
#             data[self.section][idx] = {
#                 'name': name_editor.text(),
#                 'value': value_editor.text(),
#                 'description': description_editor.text() if description_editor.text() else '',
#                 'flag': original_flag
#             }
#
#         self.tokens.set_data(data)
