"""Contains :class:`.BasePropertyEditor` the property editor base class used
across the application.

The editor is designed to interact with the bookmark item database and user
settings file but can be used without either as a general dialog for user actions.

The editor's layout is defined by SECTIONS
dictionary. This contains the sections, rows and editor widget definitions - plus
linkage information needed to associate the widget with a bookmark database columns or
user setting keys.

:class:`BasePropertyEditor` is relatively flexible and has a number of
abstract methods that need implementing in subclasses depending on the desired
functionality. In all subclasses, the :meth:`.BasePropertyEditor.db_source`,
:meth:`.BasePropertyEditor.init_data` and :meth:`.BasePropertyEditor.save_changes`
methods must be implemented.

"""
import datetime
import functools
import re

from PySide2 import QtCore, QtGui, QtWidgets

from . import base_widgets
from .. import common
from .. import database
from .. import images
from .. import log
from .. import ui

float_validator = QtGui.QRegExpValidator()
float_validator.setRegExp(QtCore.QRegExp(r'[0-9]+[\.]?[0-9]*'))
int_validator = QtGui.QRegExpValidator()
int_validator.setRegExp(QtCore.QRegExp(r'[0-9]+'))
text_validator = QtGui.QRegExpValidator()
text_validator.setRegExp(QtCore.QRegExp(r'[a-zA-Z0-9]+'))
name_validator = QtGui.QRegExpValidator()
name_validator.setRegExp(QtCore.QRegExp(r'[a-zA-Z0-9\-\_]+'))
job_name_validator = QtGui.QRegExpValidator()
job_name_validator.setRegExp(QtCore.QRegExp(r'[a-zA-Z0-9\-\_/]+'))
domain_validator = QtGui.QRegExpValidator()
domain_validator.setRegExp(QtCore.QRegExp(r'[a-zA-Z0-9/:\.]+'))
version_validator = QtGui.QRegExpValidator()
version_validator.setRegExp(QtCore.QRegExp(r'[v]?[0-9]{1,4}'))
token_validator = QtGui.QRegExpValidator()
token_validator.setRegExp(QtCore.QRegExp(r'.*'))

span = {
    'start': f'<span style="color:{common.rgb(common.color_green)}">',
    'end': '</span>',
}


def add_section(icon, label, parent, color=None):
    """Adds a new section with an icon and a title.

    Args:
        icon (str): The name of a rsc image.
        label (str): The name of the section.
        parent (QWidget): A widget to add the section to.
        color (QColor, optional): The color of the icon. Defaults to None.

    Returns:
        QWidget:            A widget to add editors to.

    """
    common.check_type(icon, (None, str))
    common.check_type(label, (None, str))
    common.check_type(parent, QtWidgets.QWidget)
    common.check_type(color, (QtGui.QColor, None))

    h = common.size(common.size_row_height)
    parent = ui.add_row('', height=None, vertical=True, parent=parent)

    if not any((icon, label)):
        return parent

    row = ui.add_row('', height=h, parent=parent)
    row.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

    if icon:
        w = QtWidgets.QLabel(parent=parent)
        pixmap = images.rsc_pixmap(icon, color, h * 0.8)
        w.setPixmap(pixmap)
        row.layout().addWidget(w, 0)

    if label:
        w = ui.PaintedLabel(
            label,
            size=common.size(common.size_font_large),
            color=common.color(common.color_text),
            parent=parent
        )
        row.layout().addWidget(w, 0)

    row.layout().addStretch(1)

    return parent


class BasePropertyEditor(QtWidgets.QDialog):
    """Base class for constructing a property editor widgets.

    Args:
        server (str or None): `server` path segment.
        job (str or None): `job` path segment.
        root (str or None): `root` path segment.
        asset (str or None): `asset` path segment.
        db_table (str or None):
            An optional name of a bookmark database table. When set, the editor
            will load and save data to and from the bookmark item database. Defaults to `None`.
        buttons (tuple): Button labels. Defaults to `('Save', 'Cancel')`.
        alignment (int): Text alignment. Defaults to `QtCore.Qt.AlignRight`.
        fallback_thumb (str): An image name. Defaults to `'placeholder'`.

    """
    #: Signal the editor created an item
    itemCreated = QtCore.Signal(str)

    #: Signal emitted when the item's thumbnail was updated
    thumbnailUpdated = QtCore.Signal(str)

    sections = {}

    def __init__(
            self,
            server,
            job,
            root,
            asset=None,
            db_table=None,
            buttons=('Save', 'Cancel'),
            alignment=QtCore.Qt.AlignRight,
            fallback_thumb='placeholder',
            hide_thumbnail_editor=False,
            section_buttons=True,
            frameless=False,
            parent=None,
    ):
        super().__init__(
            parent=parent,
            f=(
                    QtCore.Qt.CustomizeWindowHint |
                    QtCore.Qt.WindowTitleHint |
                    QtCore.Qt.WindowSystemMenuHint |
                    QtCore.Qt.WindowMinMaxButtonsHint |
                    QtCore.Qt.WindowCloseButtonHint
            )
        )

        common.check_type(server, (str, None))
        common.check_type(job, (str, None))
        common.check_type(root, (str, None))
        common.check_type(asset, (str, None))
        common.check_type(db_table, (str, None))
        common.check_type(buttons, (tuple, list))
        common.check_type(alignment, int)
        common.check_type(fallback_thumb, str)
        common.check_type(hide_thumbnail_editor, bool)
        common.check_type(section_buttons, bool)
        common.check_type(frameless, bool)
        common.check_type(parent, (QtWidgets.QWidget, None))

        if len(buttons) > 2:
            raise ValueError('`buttons` must be a tuple of 1 or 2 items.')

        self._fallback_thumb = fallback_thumb
        self._alignment = alignment
        self._buttons = buttons
        self._db_table = db_table
        self._frameless = frameless

        self.section_buttons = section_buttons
        self._section_widgets = []

        self.server = server
        self.job = job
        self.root = root
        self.asset = asset

        self.thumbnail_editor = None
        self._hide_thumbnail_editor = hide_thumbnail_editor
        self.section_headers_widget = None

        if not self.parent():
            common.set_stylesheet(self)

        self.current_data = {}
        self.changed_data = {}

        self.scroll_area = None
        self.save_button = None
        self.cancel_button = None

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.setMinimumWidth(common.size(common.size_width) * 0.5)
        self.setMinimumHeight(common.size(common.size_height) * 0.5)

        if all((server, job, root)):
            if not asset:
                self.setWindowTitle(f'{server}/{job}/{root}')
            else:
                self.setWindowTitle(f'{server}/{job}/{root}/{asset}')

        if self._frameless:
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

            self.setWindowFlags(
                QtCore.Qt.Dialog |
                QtCore.Qt.FramelessWindowHint
            )

            # Shadow effect
            self.effect = QtWidgets.QGraphicsDropShadowEffect(self)
            self.effect.setBlurRadius(common.size(common.size_margin) * 2)
            self.effect.setXOffset(0)
            self.effect.setYOffset(0)
            self.effect.setColor(QtGui.QColor(0, 0, 0, 200))
            self.setGraphicsEffect(self.effect)

        self._create_ui()
        self._connect_signals()

        self.init_data()

    def _create_ui(self):
        o = common.size(common.size_margin)

        QtWidgets.QHBoxLayout(self)

        if self._frameless:
            o = common.size(common.size_margin) * 2
            self.layout().setContentsMargins(o, o, o, o)
        else:
            self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.thumbnail_editor = base_widgets.ThumbnailEditorWidget(
            fallback_thumb=self._fallback_thumb,
            parent=self
        )

        # Separator pixmap
        pixmap = images.rsc_pixmap(
            'gradient3', None, common.size(common.size_margin), opacity=0.5
        )
        separator = QtWidgets.QLabel(parent=self)
        separator.setScaledContents(True)
        separator.setPixmap(pixmap)

        self.left_row = QtWidgets.QWidget(parent=self)
        if self._hide_thumbnail_editor:
            self.left_row.hide()

        self.left_row.setStyleSheet(
            f'background-color: {common.rgb(common.color_separator)};'
        )
        QtWidgets.QHBoxLayout(self.left_row)
        self.left_row.layout().setSpacing(0)
        self.left_row.layout().setContentsMargins(0, 0, 0, 0)
        self.left_row.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Minimum
        )
        self.layout().addWidget(self.left_row)

        self.section_headers_widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(self.section_headers_widget)
        self.section_headers_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.section_headers_widget.layout().setSpacing(
            common.size(common.size_indicator) * 2
        )

        parent = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(parent)
        parent.layout().setContentsMargins(o, o, 0, o)

        parent.layout().addWidget(self.thumbnail_editor, 0)
        parent.layout().addWidget(self.section_headers_widget, 0)
        parent.layout().addStretch(1)

        self.left_row.layout().addWidget(parent)
        self.left_row.layout().addWidget(separator)

        self.right_row = ui.add_row(None, parent=self, height=None, vertical=True)
        self.right_row.layout().setAlignment(
            QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter
        )
        self.right_row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Minimum
        )

        self.scroll_area = QtWidgets.QScrollArea(parent=self)
        self.scroll_area.setWidgetResizable(True)

        self.setFocusProxy(self.scroll_area)
        self.scroll_area.setFocusPolicy(QtCore.Qt.NoFocus)

        self.right_row.layout().addWidget(self.scroll_area)

        parent = QtWidgets.QWidget(parent=self)

        QtWidgets.QVBoxLayout(parent)
        parent.layout().setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        parent.layout().setContentsMargins(o, o, o, o)
        parent.layout().setSpacing(o * 2)
        self.scroll_area.setWidget(parent)

        self._create_sections()
        parent.layout().addStretch(1)
        self._add_buttons()

    def _connect_signals(self):
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected)
        )
        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted)
        )

        common.signals.databaseValueUpdated.connect(self.update_changed_database_value)

    def _connect_data_changed_signals(self, key, _type, editor):
        """Utility method for connecting an editor's change signal to `data_changed`.

        `data_changed` will save the changed current value internally. This data
        later can be used, for instance, to save the changed values to the
        database.

        """
        if hasattr(editor, 'dataUpdated'):
            editor.dataUpdated.connect(
                functools.partial(
                    self.data_changed,
                    key,
                    _type,
                    editor
                )
            )
        elif hasattr(editor, 'textChanged'):
            editor.textChanged.connect(
                functools.partial(
                    self.data_changed,
                    key,
                    _type,
                    editor
                )
            )
        elif hasattr(editor, 'currentTextChanged'):
            editor.currentTextChanged.connect(
                functools.partial(
                    self.data_changed,
                    key,
                    _type,
                    editor
                )
            )
        elif hasattr(editor, 'stateChanged'):
            editor.stateChanged.connect(
                functools.partial(
                    self.data_changed,
                    key,
                    _type,
                    editor
                )
            )

    def _connect_settings_save_signals(self, keys):
        """Utility method for connecting editor signals to save their current
        value in the user setting file.

        Args:
            keys (tuple): A tuple of user setting keys.

        """
        for k in keys:
            _k = k.replace('/', '_')
            if not hasattr(self, f'{_k}_editor'):
                print(f'No editor found for {k}')
                continue

            editor = getattr(self, f'{_k}_editor')

            if hasattr(editor, 'currentTextChanged'):
                signal = getattr(editor, 'currentTextChanged')
            elif hasattr(editor, 'textChanged'):
                signal = getattr(editor, 'textChanged')
            elif hasattr(editor, 'stateChanged'):
                signal = getattr(editor, 'stateChanged')
            else:
                continue

            func = functools.partial(common.settings.setValue, k)
            signal.connect(func)

    def _create_sections(self):
        """Translates the section data into a UI layout.

        """
        parent = self.scroll_area.widget()
        for section in self.sections.values():
            section_widget = add_section(
                section['icon'],
                section['name'],
                parent,
                color=section['color'],
            )

            if self.section_buttons:
                self.add_section_header_button(section['name'], section_widget)

            for item in section['groups'].values():
                group_widget = ui.get_group(parent=section_widget)
                for v in item.values():
                    self._add_row(v, group_widget)

    def _add_row(self, v, group_widget):
        """Utility method for translating a row item in the section data to a UI layout.

        Args:
            v (dict): The row data.
            group_widget.parent() (QWidget): The parent group widget.
            group_widget (QWidget): The child group widget.

        """
        row = ui.add_row(v['name'], parent=group_widget, height=None)

        k = v['key']
        _k = k.replace('/', '_') if k else k

        name = v['name']
        _name = name.lower() if name else name
        _name = re.sub(r'\W+', '_', _name) if _name else _name

        if 'description' in v and v['description']:
            row.setStatusTip(v['description'])
            row.setToolTip(v['description'])
            row.setWhatsThis(v['description'])

        if 'widget' in v and v['widget']:
            if 'no_group' in v and v['no_group']:
                editor = v['widget'](parent=group_widget.parent())
                group_widget.parent().layout().insertWidget(1, editor, 1)
            else:
                editor = v['widget'](parent=row)
                if isinstance(editor, QtWidgets.QCheckBox):
                    # We don't want checkboxes to fully extend across a row

                    editor.setSizePolicy(
                        QtWidgets.QSizePolicy.Maximum,
                        QtWidgets.QSizePolicy.Maximum,
                    )
                    row.layout().addStretch(1)
                    row.layout().addWidget(editor, 0)
                else:
                    row.layout().addWidget(editor, 1)

            # Close editor on enter presses
            if hasattr(editor, 'returnPressed'):
                editor.returnPressed.connect(
                    functools.partial(
                        self.done,
                        QtWidgets.QDialog.Accepted,
                    )
                )

            # Set the editor as an attribute on the widget for later
            # access
            if k is not None:
                setattr(self, f'{_k}_editor', editor)
            else:
                setattr(self, f'{_name}_editor', editor)

            if hasattr(editor, 'setAlignment'):
                editor.setAlignment(self._alignment)

            if (
                    k is not None and
                    self._db_table in database.TABLES and
                    k in database.TABLES[self._db_table]
            ):
                _type = database.TABLES[self._db_table][k]['type']
                self._connect_data_changed_signals(k, _type, editor)

            if 'validator' in v and v['validator']:
                if hasattr(editor, 'setValidator'):
                    editor.setValidator(v['validator'])

            if 'placeholder' in v and v['placeholder']:
                if hasattr(editor, 'setPlaceholderText'):
                    editor.setPlaceholderText(v['placeholder'])

            if 'protect' in v and v['protect']:
                if hasattr(editor, 'setEchoMode'):
                    editor.setEchoMode(
                        QtWidgets.QLineEdit.Password
                    )

            if 'description' in v and v['description']:
                editor.setStatusTip(v['description'])
                editor.setToolTip(v['description'])
                editor.setWhatsThis(v['description'])

                row.setStatusTip(v['description'])
                row.setToolTip(v['description'])
                row.setWhatsThis(v['description'])

        if 'help' in v and v['help']:
            ui.add_description(
                v['help'], label=None, parent=group_widget
            )

        if 'button' in v and v['button']:
            button = ui.PaintedButton(
                v['button'], parent=row
            )

            if k is not None:
                if hasattr(self, f'{_k}_button_clicked'):
                    button.clicked.connect(getattr(self, f'{_k}_button_clicked'))
            else:
                if hasattr(self, f'{_name}_button_clicked'):
                    button.clicked.connect(
                        getattr(self, f'{_name}_button_clicked')
                    )
            row.layout().addWidget(button, 0)

        if 'button2' in v and v['button2']:
            button2 = ui.PaintedButton(
                v['button2'], parent=row
            )

            if k is not None:
                if hasattr(self, f'{_k}_button2_clicked'):
                    button2.clicked.connect(
                        getattr(self, f'{_k}_button2_clicked')
                    )
            else:
                if hasattr(self, f'{_name}_button2_clicked'):
                    button2.clicked.connect(
                        getattr(self, f'{_name}_button2_clicked')
                    )
            row.layout().addWidget(button2, 0)

    def _add_buttons(self):
        if not self._buttons:
            return
        h = common.size(common.size_row_height)

        self.save_button = ui.PaintedButton(
            self._buttons[0], parent=self
        )
        if len(self._buttons) > 1:
            self.cancel_button = ui.PaintedButton(
                self._buttons[1], parent=self
            )
        else:
            self.cancel_button = ui.PaintedButton(
                'Close', parent=self
            )
            self.cancel_button.setHidden(True)

        row = ui.add_row(
            None, height=h * 2, parent=self.right_row
        )
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        row.layout().addSpacing(common.size(common.size_margin))
        row.layout().addWidget(self.save_button, 1)
        row.layout().addWidget(self.cancel_button, 0)
        row.layout().addSpacing(common.size(common.size_margin))

    def add_section_header_button(self, name, widget):
        """Add a header button to help reveal the given section widget.

        """
        if not name:
            return
        button = ui.PaintedLabel(name, parent=self.section_headers_widget)

        self.section_headers_widget.layout().addWidget(button)
        button.clicked.connect(
            functools.partial(self.scroll_to_section, widget)
        )

    @QtCore.Slot(QtWidgets.QWidget)
    def scroll_to_section(self, widget):
        """Slot used to scroll to a section when a section header is clicked.

        """
        point = widget.mapTo(self.scroll_area, QtCore.QPoint(0, 0))
        self.scroll_area.verticalScrollBar().setValue(
            point.y() + self.scroll_area.verticalScrollBar().value()
        )

    def load_saved_user_settings(self, keys):
        """Utility method will load user setting values and apply them to the
        corresponding editors.

        Args:
            keys (tuple): A list of editor keys that save their current value
                            in the user settings file.

        """
        for k in keys:
            _k = k.replace('/', '_')
            if not hasattr(self, f'{_k}_editor'):
                continue

            v = common.settings.value(k)
            if not v:
                continue

            editor = getattr(self, f'{_k}_editor')

            if hasattr(editor, 'setCurrentText'):
                if not isinstance(v, str):
                    continue
                editor.blockSignals(True)
                editor.setCurrentText(v)
                editor.blockSignals(False)

            if hasattr(editor, 'setText') and not hasattr(editor, 'setCheckState'):
                if not isinstance(v, str):
                    continue
                editor.blockSignals(True)
                editor.setText(v)
                editor.blockSignals(False)

            if hasattr(editor, 'setCheckState'):
                if not isinstance(v, (int, QtCore.Qt.CheckState)):
                    continue
                editor.blockSignals(True)
                editor.setCheckState(QtCore.Qt.CheckState(v))
                editor.blockSignals(False)

    def init_db_data(self):
        """Method will load data from the bookmark database.

        To be able to load data, the `db_table`, `server`, `job` and `root`
        values must have all been specified when the class was initialized.

        Call this method from `init_data()` when the widget is associated with
        a bookmark database.

        """
        if not all((self._db_table, self.server, self.job, self.root)):
            raise RuntimeError(
                'To load data from the database, `db_table`, `server`, '
                '`job` and `root` must all be specified.'
            )

        if self._db_table not in database.TABLES:
            raise RuntimeError(
                f'"{self._db_table}" is not a valid database table.'
            )

        db = database.get(self.server, self.job, self.root)
        for k in database.TABLES[self._db_table]:
            # Skip items that don't have editors
            if not hasattr(self, f'{k}_editor'):
                continue

            # If the source is not returning a valid value we won't be able to
            # load data from the database.
            if self.db_source() is None:
                self.current_data[k] = None
                continue

            editor = getattr(self, f'{k}_editor')
            v = db.value(self.db_source(), k, self._db_table)
            if v is not None:

                # Make sure the type loaded from the database matches the required
                # type
                for section in self.sections.values():
                    for group in section['groups'].values():
                        for item in group.values():
                            if item['key'] != k:
                                continue

                            # Get the required type
                            _type = database.TABLES[self._db_table][item['key']][
                                'type']

                            if isinstance(v, _type):
                                continue  # Nothing to do if already the right type

                            try:
                                v = _type(v)
                            except Exception as e:
                                log.error(e)

            # Add value to `current_data`
            if k not in self.current_data:
                self.current_data[k] = v

            if v is not None:
                if hasattr(editor, 'setValue'):
                    editor.setValue(v)

                if not isinstance(v, str):
                    v = str(v)
                if hasattr(editor, 'setText'):
                    editor.setText(v)
                if hasattr(editor, 'setCurrentText'):
                    editor.setCurrentText(v)
            else:
                if hasattr(editor, 'setCurrentText'):
                    editor.setCurrentIndex(-1)

        for k in database.TABLES[database.InfoTable]:
            if k == 'id':
                continue

            source = f'{self.server}/{self.job}/{self.root}'
            v = db.value(source, k, database.InfoTable)

            if k == 'created':
                try:
                    v = datetime.datetime.fromtimestamp(
                        float(v)
                    ).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    v = 'error'

            if hasattr(self, f'{k}_editor'):
                editor = getattr(self, f'{k}_editor')
                editor.setDisabled(True)
                editor.setText(v)

    def save_changed_data_to_db(self):
        """This will save changed data to the bookmark database.

        To be able to save data, the `_db_table`, `server`, `job` and `root`
        values must have all been specified.

        Call this method from `save_data()` when the editor is used to edit
        database values.

        """
        if not all((self._db_table, self.server, self.job, self.root)):
            raise RuntimeError(
                'To load data from the database, `table`, `server`, `job`, '
                '`root` must all be specified.'
            )
        if self._db_table not in database.TABLES:
            raise RuntimeError(
                f'"{self._db_table}" is not a valid database table.'
            )

        # Can't save if db_source is not returning a valid value
        if self.db_source() is None:
            return

        db = database.get(self.server, self.job, self.root)
        with db.connection():
            for k, v in self.changed_data.copy().items():
                db.set_value(
                    self.db_source(),
                    k,
                    v,
                    table=self._db_table
                )

    @QtCore.Slot(str)
    @QtCore.Slot(type)
    @QtCore.Slot(QtWidgets.QWidget)
    @QtCore.Slot(str)
    def data_changed(self, key, _type, editor, v):
        """Slot called when the user changes a value in the editor.

        Args:
            key (str): The database key.
            _type (type): The data type.
            editor (QWidget): The editor widget.
            v (object): The changed value.

        """
        if v == '':
            v = None
        elif _type is not None and v is not isinstance(v, _type) and v != '':
            try:
                v = _type(v)
            except:
                log.error('Type conversion failed.')

        if key not in self.current_data:
            self.current_data[key] = v

        if v != self.current_data[key]:
            self.changed_data[key] = v

            if not isinstance(editor, QtWidgets.QCheckBox):
                editor.setStyleSheet(
                    f'color: {common.rgb(common.color_green)};'
                )
            return

        if key in self.changed_data:
            del self.changed_data[key]

        if not isinstance(editor, QtWidgets.QCheckBox):
            editor.setStyleSheet(
                f'color: {common.rgb(common.color_text)};'
            )

    @QtCore.Slot()
    def done(self, result):
        """Finish editing the item.

        """
        if result == QtWidgets.QDialog.Rejected:
            if self.changed_data:
                if common.show_message(
                        'Are you sure you want to close the editor?',
                        body='Your changes will be lost.',
                        buttons=[common.YesButton, common.NoButton],
                        modal=True,
                ) == QtWidgets.QDialog.Rejected:
                    return
            return super().done(result)

        if not self.save_changes():
            return

        return super().done(result)

    def paintEvent(self, event):
        if self._frameless:
            painter = QtGui.QPainter(self)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.color(common.color_background))

            o = common.size(common.size_margin) * 2
            painter.drawRect(self.rect().adjusted(o, o, -o, -o))
            painter.end()

        super().paintEvent(event)

    def changeEvent(self, event):
        """Change event handler.

        """
        if event.type() == QtCore.QEvent.WindowStateChange:
            common.save_window_state(self)
        super().changeEvent(event)

    def hideEvent(self, event):
        """Hide event handler.

        """
        common.save_window_state(self)
        super().hideEvent(event)

    def closeEvent(self, event):
        """Close event.

        """
        common.save_window_state(self)
        super().closeEvent(event)

    def showEvent(self, event):
        """Show event handler.

        """
        super().showEvent(event)
        common.restore_window_geometry(self)
        QtCore.QTimer.singleShot(100, self.init_data)

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width) * 1.33,
            common.size(common.size_height) * 1.5
        )

    @QtCore.Slot(str)
    @QtCore.Slot(str)
    @QtCore.Slot(str)
    @QtCore.Slot(object)
    def update_changed_database_value(self, table, source, key, value):
        """Slot responsible updating the widget when a database value has changed.

        Args:
            table (str): Name of the db table.
            source (str): Source file path.
            key (str): Database key.
            value (object): The new database value.

        """
        try:
            self.db_source()
        except NotImplementedError:
            print('Skipping database updates, no db source set.')
            return

        if source != self.db_source():
            return

        if not hasattr(self, f'{key}_editor'):
            return
        editor = getattr(self, f'{key}_editor')

        self.current_data[key] = value
        self.changed_data[key] = value

        if value is None:
            value = ''
        elif not isinstance(value, str):
            value = str(value)

        if hasattr(editor, 'setText'):
            editor.setText(value)
            editor.textChanged.emit(value)
        elif hasattr(editor, 'setCurrentText'):
            if value:
                editor.setCurrentText(value)
                editor.currentTextChanged.emit(value)

    @QtCore.Slot()
    def url1_button_clicked(self):
        """Url1 button action.

        """
        v = self.url1_editor.text()
        if not v:
            return
        QtGui.QDesktopServices.openUrl(v)

    @QtCore.Slot()
    def url2_button_clicked(self):
        """Url2 button action.

        """
        v = self.url2_editor.text()
        if not v:
            return
        QtGui.QDesktopServices.openUrl(v)

    def db_source(self):
        """A file path to use as the source of database values.

        When returns `None`, the editor will not load or save data to the
        database.

        Returns:
            str: A file or folder path.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    @QtCore.Slot()
    def init_data(self):
        """Implement this method to initialize the editor's data.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')

    @QtCore.Slot()
    def save_changes(self):
        """Implement to execute any actions and/or save data before closing the
        editor.

        For editors that interact with the user database, this method should call
        :meth:`save_changed_data_to_db` to save the changed data to the database.

        """
        raise NotImplementedError('Abstract method must be implemented by subclass.')
