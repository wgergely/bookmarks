# -*- coding: utf-8 -*-
"""The module contains the base class used by property editors across
Bookmarks.

The editor widgets provide a unified approach for editing job, bookmark, asset
and file item properties. If the base-class is passed the optional `db_table`
keyword, the class will try to load/save/update data found in the bookmark
database.


BasePropertyEditor
----------------

The `BasePropertyEditor` base class is relatively flexible and has a number of
abstract methods that need implementing in subclasses depending on the
desired functionality. Namely, `db_source()`, `init_data()` and `save_changes()`
are functions responsbile for providing values and methods needed to load and
save default values from the bookmark database or another source.

The editor provides a thumbnail editor widget that can be used to save a custom
thumbnail for a job, bookmark, asset or file. The default thumbnail can be set
by providing the optional `fallback_thumb` keyword to the instance constructor.

Example
-------

    .. code-block:: python

        editor = BasePropertyEditor(
            SECTIONS,
            server,
            job,
            root,
            asset=asset,
            alignment=QtCore.Qt.AlignLeft,
            fallback_thumb='file_sm',
            db_table=database.AssetTable,
        )
        editor.open()


The editor UI is created by passing a `SECTIONS` dictionary to the
base class.


"""
import functools
import datetime

from PySide2 import QtCore, QtGui, QtWidgets

from .. import log
from .. import common
from .. import ui
from .. import images
from .. import database
from .. import settings
from . import base_widgets


floatvalidator = QtGui.QRegExpValidator()
floatvalidator.setRegExp(QtCore.QRegExp(r'[0-9]+[\.]?[0-9]*'))
intvalidator = QtGui.QRegExpValidator()
intvalidator.setRegExp(QtCore.QRegExp(r'[0-9]+'))
textvalidator = QtGui.QRegExpValidator()
textvalidator.setRegExp(QtCore.QRegExp(r'[a-zA-Z0-9]+'))
namevalidator = QtGui.QRegExpValidator()
namevalidator.setRegExp(QtCore.QRegExp(r'[a-zA-Z0-9\-\_]+'))
domainvalidator = QtGui.QRegExpValidator()
domainvalidator.setRegExp(QtCore.QRegExp(r'[a-zA-Z0-9/:\.]+'))
versionvalidator = QtGui.QRegExpValidator()
versionvalidator.setRegExp(QtCore.QRegExp(r'[v]?[0-9]{1,4}'))
tokenvalidator = QtGui.QRegExpValidator()
tokenvalidator.setRegExp(QtCore.QRegExp(r'[0-0a-zA-Z\_\-\.\{\}]*'))


span = {
    'start': '<span style="color:{}">'.format(common.rgb(common.GREEN)),
    'end': '</span>',
}


def add_section(icon, label, parent, color=None):
    """Used to a new section with an icon and a title to a widget.

    Args:
        icon (str):     The name of an rsc image.
        parent (QWidget):   A widget to add the section to.
        color (QColor):     The color of the icon. Defaults to `None`.

    Returns:
        QWidget:            A widget to add editors to.

    """
    parent = ui.add_row('', height=None, vertical=True, parent=parent)

    h = common.ROW_HEIGHT()

    _label = QtWidgets.QLabel(parent=parent)
    pixmap = images.ImageCache.get_rsc_pixmap(icon, color, h * 0.8)
    _label.setPixmap(pixmap)
    label = ui.PaintedLabel(
        label,
        size=common.LARGE_FONT_SIZE(),
        color=common.TEXT,
        parent=parent
    )

    row = ui.add_row('', height=h, parent=parent)
    row.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
    row.layout().addWidget(_label, 0)
    row.layout().addWidget(label, 0)
    row.layout().addStretch(1)

    return parent


def _save_local_value(key, value):
    settings.instance().setValue(
        settings.CurrentUserPicksSection,
        key,
        value
    )


class BasePropertyEditor(QtWidgets.QDialog):
    """Base class for constructing a property editor widget.

    Args:
        sections (dict):        The data needed to construct the ui layout.
        server (unciode):       A server.
        job (str):              A job.
        root (str):             A root folder.
        asset (str):            An optional asset. Defaults to `None`.
        db_table (str):         An optional name of a bookmark database table.
                                When not `None`, the editor will load and save data
                                to the database. Defaults to `None`.
        buttons (tuple):        Button labels. Defaults to `('Save', 'Cancel')`.
        alignment (int):        Text alignment. Defaults to `QtCore.Qt.AlignRight`.
        fallback_thumb (str):   An image name. Defaults to `'placeholder'`.

    """
    itemCreated = QtCore.Signal(str)

    itemUpdated = QtCore.Signal(str)
    thumbnailUpdated = QtCore.Signal(str)

    def __init__(
        self,
        sections,
        server,
        job,
        root,
        asset=None,
        db_table=None,
        buttons=('Save', 'Cancel'),
        alignment=QtCore.Qt.AlignRight,
        fallback_thumb='placeholder',
        hide_thumbnail_editor=False,
        parent=None
    ):
        common.check_type(sections, dict)

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

        self._fallback_thumb = fallback_thumb
        self._alignment = alignment
        self._sections = sections
        self._section_widgets = []
        self._buttons = buttons
        self._db_table = db_table

        self.server = server
        self.job = job
        self.root = root
        self.asset = asset

        self.thumbnail_editor = None
        self._hide_thumbnail_editor = hide_thumbnail_editor

        if not self.parent():
            common.set_custom_stylesheet(self)

        self.current_data = {}
        self.changed_data = {}

        self.scrollarea = None
        self.save_button = None
        self.cancel_button = None

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.setMinimumWidth(common.WIDTH() * 0.5)
        self.setMinimumHeight(common.HEIGHT() * 0.5)

        if all((server, job, root)):
            if not asset:
                self.setWindowTitle('{}/{}/{}'.format(
                    server, job, root))
            else:
                self.setWindowTitle('{}/{}/{}/{}'.format(
                    server, job, root, asset))

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        o = common.MARGIN()

        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        if not self.server or not self.job or not self.root:
            source = ''
        elif not self.asset:
            source = '/'.join((self.server, self.job, self.root))
        else:
            source = '/'.join((self.server, self.job, self.root, self.asset))

        self.thumbnail_editor = base_widgets.ThumbnailEditorWidget(
            self.server,
            self.job,
            self.root,
            source=source,
            fallback_thumb=self._fallback_thumb,
            parent=self
        )

        # Separator pixmap
        pixmap = images.ImageCache.get_rsc_pixmap(
            'gradient3', None, common.MARGIN(), opacity=0.5)
        separator = QtWidgets.QLabel(parent=self)
        separator.setScaledContents(True)
        separator.setPixmap(pixmap)

        self.left_row = QtWidgets.QWidget(parent=self)
        if self._hide_thumbnail_editor:
            self.left_row.hide()

        self.left_row.setStyleSheet(
            'background-color: {};'.format(common.rgb(common.SEPARATOR)))
        QtWidgets.QHBoxLayout(self.left_row)
        self.left_row.layout().setSpacing(0)
        self.left_row.layout().setContentsMargins(0, 0, 0, 0)
        self.left_row.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Minimum
        )
        self.layout().addWidget(self.left_row)

        parent = QtWidgets.QWidget(parent=self.left_row)
        QtWidgets.QVBoxLayout(parent)
        parent.layout().setContentsMargins(o, o, 0, o)

        parent.layout().addWidget(self.thumbnail_editor, 0)
        parent.layout().addStretch(1)
        self.left_row.layout().addWidget(parent)
        self.left_row.layout().addWidget(separator)

        self.right_row = ui.add_row(
            None, parent=self, padding=None, height=None, vertical=True)
        self.right_row.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        self.right_row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Minimum
        )

        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)
        self.right_row.layout().addWidget(self.scrollarea)

        parent = QtWidgets.QWidget(parent=self)

        QtWidgets.QVBoxLayout(parent)
        parent.layout().setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        parent.layout().setContentsMargins(o, o, o, o)
        parent.layout().setSpacing(o * 2)
        self.scrollarea.setWidget(parent)

        self._create_sections()
        self._add_buttons()

    def _create_sections(self):
        """Expands the section data into an UI layout.

        """
        parent = self.scrollarea.widget()

        for section in self._sections.values():
            grp = add_section(
                section['icon'],
                section['name'],
                parent,
                color=section['color'],
            )
            self._section_widgets.append(grp)

            for item in section['groups'].values():
                _grp = ui.get_group(parent=grp)

                for v in item.values():
                    row = ui.add_row(
                        v['name'], parent=_grp, height=None)

                    if 'description' in v and v['description']:
                        row.setStatusTip(v['description'])
                        row.setToolTip(v['description'])
                        row.setWhatsThis(v['description'])

                    if 'widget' in v and v['widget']:
                        if 'no_group' in v and v['no_group']:
                            editor = v['widget'](parent=grp)
                            grp.layout().insertWidget(1, editor, 1)
                        else:
                            editor = v['widget'](parent=row)
                            if isinstance(editor, QtWidgets.QCheckBox):
                                # We don't want checkboxes to fully extend accross a row
                                editor.setSizePolicy(
                                    QtWidgets.QSizePolicy.Maximum,
                                    QtWidgets.QSizePolicy.Maximum,
                                )
                                row.layout().addStretch(1)
                                row.layout().addWidget(editor, 0)
                            else:
                                row.layout().addWidget(editor, 1)

                        # Set the editor as an attribute on the widget for later access
                        if v['key'] is not None:
                            setattr(
                                self,
                                v['key'] + '_editor',
                                editor
                            )
                        else:
                            setattr(
                                self,
                                v['name'].lower() + '_editor',
                                editor
                            )

                        if hasattr(editor, 'setAlignment'):
                            editor.setAlignment(self._alignment)

                        if v['key'] is not None and self._db_table in database.TABLES and v['key'] in database.TABLES[self._db_table]:
                            _type = database.TABLES[self._db_table][v['key']]['type']
                            self._connect_editor_signals(
                                v['key'], _type, editor)

                        if 'validator' in v and v['validator']:
                            if hasattr(editor, 'setValidator'):
                                editor.setValidator(v['validator'])

                        if 'placeholder' in v and v['placeholder']:
                            if hasattr(editor, 'setPlaceholderText'):
                                editor.setPlaceholderText(v['placeholder'])

                        if 'protect' in v and v['protect']:
                            if hasattr(editor, 'setEchoMode'):
                                editor.setEchoMode(
                                    QtWidgets.QLineEdit.Password)

                        if 'description' in v and v['description']:
                            editor.setStatusTip(v['description'])
                            editor.setToolTip(v['description'])
                            editor.setWhatsThis(v['description'])

                            row.setStatusTip(v['description'])
                            row.setToolTip(v['description'])
                            row.setWhatsThis(v['description'])

                    if 'help' in v and v['help']:
                        ui.add_description(
                            v['help'], label=None, parent=_grp)

                    if 'button' in v and v['button']:
                        button = ui.PaintedButton(
                            v['button'], parent=row)
                        button.setFixedHeight(common.ROW_HEIGHT() * 0.8)

                        if v['key'] is not None:
                            if hasattr(self, v['key'] + '_button_clicked'):
                                button.clicked.connect(
                                    getattr(self, v['key'] + '_button_clicked')
                                )
                        else:
                            if hasattr(self, v['name'].lower() + '_button_clicked'):
                                button.clicked.connect(
                                    getattr(
                                        self, v['name'].lower() + '_button_clicked')
                                )
                        row.layout().addWidget(button, 0)

                    if 'button2' in v and v['button2']:
                        button2 = ui.PaintedButton(
                            v['button2'], parent=row)
                        button2.setFixedHeight(common.ROW_HEIGHT() * 0.8)

                        if v['key'] is not None:
                            if hasattr(self, v['key'] + '_button2_clicked'):
                                button2.clicked.connect(
                                    getattr(self, v['key'] +
                                            '_button2_clicked')
                                )
                        else:
                            if hasattr(self, v['name'].lower() + '_button2_clicked'):
                                button2.clicked.connect(
                                    getattr(
                                        self, v['name'].lower() + '_button2_clicked')
                                )
                        row.layout().addWidget(button2, 0)

    def _add_buttons(self):
        if not self._buttons:
            return
        h = common.ROW_HEIGHT()

        self.save_button = ui.PaintedButton(
            self._buttons[0], parent=self)
        self.save_button.setFixedHeight(h)
        self.cancel_button = ui.PaintedButton(
            self._buttons[1], parent=self)
        self.cancel_button.setFixedHeight(h)

        row = ui.add_row(
            None, padding=None, height=h * 2, parent=self.right_row)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        row.layout().addSpacing(common.MARGIN())
        row.layout().addWidget(self.save_button, 1)
        row.layout().addWidget(self.cancel_button, 0)
        row.layout().addSpacing(common.MARGIN())

    def _connect_editor_signals(self, key, _type, editor):
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

    def _connect_signals(self):
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected))
        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

    def _connect_settings_save_signals(self, keys):
        """Utility method for connecting editor signals to save their current
        value in the user settings.

        Args:
            keys (tuple):   A list of editor keys that save their current value
                            in the user settings.

        """
        for k in keys:
            if not hasattr(self, k + '_editor'):
                continue

            editor = getattr(self, k + '_editor')

            if hasattr(editor, 'currentTextChanged'):
                signal = getattr(editor, 'currentTextChanged')
            elif hasattr(editor, 'textChanged'):
                signal = getattr(editor, 'textChanged')
            elif hasattr(editor, 'stateChanged'):
                signal = getattr(editor, 'stateChanged')
            else:
                continue

            signal.connect(functools.partial(_save_local_value, k))

    def load_saved_user_settings(self, keys):
        """Utilty method will load values from the user setting  and apply
        it to the corresponding editors.

        Args:
            keys (tuple):   A list of editor keys that save their current value
                            in the user settings.

        """
        for k in keys:
            if not hasattr(self, k + '_editor'):
                continue

            v = settings.instance().value(
                settings.CurrentUserPicksSection,
                k
            )
            if not v:
                continue

            editor = getattr(self, k + '_editor')

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
            else:
                continue

    @QtCore.Slot()
    def set_thumbnail_source(self):
        """Slot connected to the update timer and used to set the source value
        of the thumbnail editor.

        """
        source = self.thumbnail_editor.source
        _source = self.db_source()

        self.thumbnail_editor.source = _source
        if source != _source:
            self.thumbnail_editor.update()

    def init_db_data(self):
        """Method will load data from the bookmark database.

        To be able to load data, the `db_table`, `server`, `job` and `root`
        values must have all been specified when the class was initialised.

        Call this method from `init_data()` when the widget is associated with
        a bookmark database.

        """
        if not all((self._db_table, self.server, self.job, self.root)):
            raise RuntimeError(
                'To load data from the database, the `db_table`, `server`, `job` andd `root` must all be specified.')

        if self._db_table not in database.TABLES:
            raise RuntimeError(
                f'"{self._db_table}" is not a valid database table.')

        db = database.get_db(self.server, self.job, self.root)
        for k in database.TABLES[self._db_table]:
            # Skip items that don't have editors
            if not hasattr(self, k + '_editor'):
                continue

            # If the source is not returning a valid value we won't  be able to
            # load data from the database.
            if self.db_source() is None:
                self.current_data[k] = None
                continue

            editor = getattr(self, k + '_editor')
            v = db.value(self.db_source(), k, table=self._db_table)
            if v is not None:

                # Make sure the type loaded from the database maches the required type
                for section in self._sections.values():
                    for group in section['groups'].values():
                        for item in group.values():
                            if item['key'] != k:
                                continue

                            # Get the required type
                            _type = database.TABLES[self._db_table][item['key']]['type']

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
                    v = '{}'.format(v)
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

            source = '{}/{}/{}'.format(self.server, self.job, self.root)
            v = db.value(source, k, table=database.InfoTable)

            if k == 'created':
                try:
                    v = datetime.datetime.fromtimestamp(
                        float(v)).strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    v = 'error'

            if hasattr(self, k + '_editor'):
                editor = getattr(self, k + '_editor')
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
                'To load data fomr the database, the `table`, `server`, `job`, `root` must all be specified.')
        if self._db_table not in database.TABLES:
            raise RuntimeError(
                f'"{self._db_table}" is not a valid database table.')

        # Can't save if db_source is not returning a valid value
        if self.db_source() is None:
            return

        db = database.get_db(self.server, self.job, self.root)
        with db.connection():
            for k, v in self.changed_data.copy().items():
                db.setValue(
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
        """Signal called when the user changes a value in the editor.

        Args:
            key (str):          The database key.
            _type (type):           The data type.
            editor (QWidget):       The editor widget.

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
                    'color: {};'.format(common.rgb(common.GREEN)))
            return

        if key in self.changed_data:
            del self.changed_data[key]

        if not isinstance(editor, QtWidgets.QCheckBox):
            editor.setStyleSheet(
                'color: {};'.format(common.rgb(common.TEXT)))

    def db_source(self):
        """The path of the file database values are associated with.

        Eg. in the case of assets this is `server/job/root/asset`

        """
        raise NotImplementedError('Must be overridden in subclass.')

    @QtCore.Slot()
    def init_data(self):
        """Initialises the current/default values.

        """
        raise NotImplementedError(
            'Init data must be overriden in the subclass.')

    @QtCore.Slot()
    def save_changes(self):
        """Abstract method responsible for saving changed data.

        """
        raise NotImplementedError('Must be overriden in the subclass.')

    @QtCore.Slot()
    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            if self.changed_data:
                mbox = ui.MessageBox(
                    'Are you sure you want to close the editor?',
                    'Your changes will be lost.',
                    buttons=[ui.YesButton, ui.NoButton]
                )
                if mbox.exec_() == QtWidgets.QMessageBox.Rejected:
                    return
            return super(BasePropertyEditor, self).done(result)

        if not self.save_changes():
            return

        return super(BasePropertyEditor, self).done(result)

    def showEvent(self, event):
        QtCore.QTimer.singleShot(100, self.init_data)
        common.center_window(self)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH() * 1.33, common.HEIGHT() * 1.5)

    @QtCore.Slot(str)
    @QtCore.Slot(str)
    @QtCore.Slot(object)
    def update_changed_database_value(self, table, source, key, value):
        """Slot responsible updating the gui when  database value is updated.

        """
        if source != self.db_source():
            return

        if not hasattr(self, key + '_editor'):
            return
        editor = getattr(self, key + '_editor')

        self.current_data[key] = value
        self.changed_data[key] = value

        if value is None:
            value = ''
        elif not isinstance(value, str):
            value = '{}'.format(value)

        if hasattr(editor, 'setText'):
            editor.setText(value)
            editor.textChanged.emit(value)
        elif hasattr(editor, 'setCurrentText'):
            if value:
                editor.setCurrentText(value)
                editor.currentTextChanged.emit(value)

    @QtCore.Slot()
    def url1_button_clicked(self):
        v = self.url1_editor.text()
        if not v:
            return
        QtGui.QDesktopServices.openUrl(v)

    @QtCore.Slot()
    def url2_button_clicked(self):
        v = self.url2_editor.text()
        if not v:
            return
        QtGui.QDesktopServices.openUrl(v)
