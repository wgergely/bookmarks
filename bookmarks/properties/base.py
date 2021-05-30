# -*- coding: utf-8 -*-
"""The module contains the base class used by all property editors across
Bookmarks.

The editor widgets provide a unified approach for editing job, bookmark, asset
and file properties. If the base-class is passed the optional `db_table`
keyword, it will try to load/save/update data found in the bookmark database.


PropertiesWidget
----------------

The `PropertiesWidget` base class is relatively flexible and has a number of
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

        editor = PropertiesWidget(
            SECTIONS,
            server,
            job,
            root,
            asset=asset,
            alignment=QtCore.Qt.AlignLeft,
            fallback_thumb=u'file_sm',
            db_table=bookmark_db.AssetTable,
        )
        editor.open()


The editor UI is created by passing a `SECTIONS` dictionary to the
base class.


"""
import uuid
import functools
import datetime

from PySide2 import QtCore, QtGui, QtWidgets

from .. import log
from .. import common
from .. import ui
from .. import images
from .. import bookmark_db
from .. import actions
from . import base_widgets


floatvalidator = QtGui.QRegExpValidator()
floatvalidator.setRegExp(QtCore.QRegExp(ur'[0-9]+[\.]?[0-9]*'))
intvalidator = QtGui.QRegExpValidator()
intvalidator.setRegExp(QtCore.QRegExp(ur'[0-9]+'))
textvalidator = QtGui.QRegExpValidator()
textvalidator.setRegExp(QtCore.QRegExp(ur'[a-zA-Z0-9]+'))
namevalidator = QtGui.QRegExpValidator()
namevalidator.setRegExp(QtCore.QRegExp(ur'[a-zA-Z0-9\-\_]+'))
domainvalidator = QtGui.QRegExpValidator()
domainvalidator.setRegExp(QtCore.QRegExp(ur'[a-zA-Z0-9/:\.]+'))
versionvalidator = QtGui.QRegExpValidator()
versionvalidator.setRegExp(QtCore.QRegExp(ur'[v]?[0-9]{1,4}'))
tokenvalidator = QtGui.QRegExpValidator()
tokenvalidator.setRegExp(QtCore.QRegExp(ur'[0-0a-zA-Z\_\-\.\{\}]*'))


span = {
    'start': '<span style="color:{}">'.format(common.rgb(common.GREEN)),
    'end': '</span>',
}


def add_section(icon, label, parent, color=None):
    """Used to a new section with an icon and a title to a widget.

    Args:
        icon (unicode):     The name of an rsc image.
        parent (QWidget):   A widget to add the section to.
        color (QColor):     The color of the icon. Defaults to `None`.

    Returns:
        QWidget:            A widget to add editors to.

    """
    parent = ui.add_row(u'', height=None, vertical=True, parent=parent)

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

    row = ui.add_row(u'', height=h, parent=parent)
    row.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
    row.layout().addWidget(_label, 0)
    row.layout().addWidget(label, 0)
    row.layout().addStretch(1)

    return parent


class PropertiesWidget(QtWidgets.QDialog):
    """Base class for editing bookmark and asset properties.

    Args:
        sections (dict):        The data needed to construct the ui layout.
        server (unciode):       A server.
        job (unicode):          A job.
        root (unicode):         A root folder.
        asset (unicode):        An optional asset. Defaults to `None`.
        db_table (unicode):     An optional name of a bookmark database table.
                                When `None`, the editor won't load or save data
                                to the databse. Defaults to `None`.
        buttons (tuple):        Button labels. Defaults to `('Save', 'Cancel')`.
        alignment (int):        Text alignment. Defaults to `QtCore.Qt.AlignRight`.
        fallback_thumb (unicode): An rsc image name. Defaults to `'placeholder'`.

    """
    itemCreated = QtCore.Signal(unicode)

    itemUpdated = QtCore.Signal(unicode)
    thumbnailUpdated = QtCore.Signal(unicode)

    def __init__(
        self,
        sections,
        server,
        job,
        root,
        asset=None,
        db_table=None,
        buttons=(u'Save', 'Cancel'),
        alignment=QtCore.Qt.AlignRight,
        fallback_thumb=u'placeholder',
        parent=None
    ):
        if not isinstance(sections, dict):
            raise TypeError('Invalid section data.')

        super(PropertiesWidget, self).__init__(
            parent=parent,
            f=QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowMinMaxButtonsHint | QtCore.Qt.WindowCloseButtonHint
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
                self.setWindowTitle(u'{}/{}/{}'.format(
                    server, job, root))
            else:
                self.setWindowTitle(u'{}/{}/{}/{}'.format(
                    server, job, root, asset))

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        o = common.MARGIN()

        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        if not self.server or not self.job or not self.root:
            source = u''
        elif not self.asset:
            source = u'/'.join((self.server, self.job, self.root))
        else:
            source = u'/'.join((self.server, self.job, self.root, self.asset))

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
            u'gradient3', None, common.MARGIN(), opacity=0.5)
        separator = QtWidgets.QLabel(parent=self)
        separator.setScaledContents(True)
        separator.setPixmap(pixmap)

        self.left_row = QtWidgets.QWidget(parent=self)
        self.left_row.setStyleSheet(
            u'background-color: {};'.format(common.rgb(common.SEPARATOR)))
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

        self._add_sections()
        self._add_buttons()

    def _add_sections(self):
        """Expands the section data into an UI layout.

        """
        parent = self.scrollarea.widget()

        for section in self._sections.itervalues():
            grp = add_section(
                section['icon'],
                section['name'],
                parent,
                color=section['color'],
            )
            self._section_widgets.append(grp)

            for item in section['groups'].itervalues():
                _grp = ui.get_group(parent=grp)

                for v in item.itervalues():
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

                        if v['key'] is not None and self._db_table in bookmark_db.TABLES and v['key'] in bookmark_db.TABLES[self._db_table]:
                            _type = bookmark_db.TABLES[self._db_table][v['key']]['type']
                            self._connect_editor(v['key'], _type, editor)

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

    def _connect_editor(self, key, _type, editor):
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

    def _connect_signals(self):
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected))
        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

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

    def _init_db_data(self):
        """Loads the current values form the bookmark database.

        """
        if self._db_table is None or self._db_table not in bookmark_db.TABLES:
            raise RuntimeError(u'Invalid database table.')

        db = bookmark_db.get_db(self.server, self.job, self.root)
        for k in bookmark_db.TABLES[self._db_table]:
            if not hasattr(self, k + '_editor'):
                continue

            # If the source is not specified we won't be able to load data
            # from the database
            if self.db_source() is None:
                self.current_data[k] = None
                continue

            editor = getattr(self, k + '_editor')

            v = db.value(self.db_source(), k, table=self._db_table)
            if v is not None:

                # Type verification
                for section in self._sections.itervalues():
                    for group in section['groups'].itervalues():
                        for item in group.itervalues():
                            if item['key'] != k:
                                continue
                            _type = bookmark_db.TABLES[self._db_table][item['key']]['type']
                            try:
                                v = _type(v)
                            except Exception as e:
                                log.error(e)
                            break

            if k not in self.current_data:
                self.current_data[k] = v

            if v is not None:
                if hasattr(editor, 'setValue'):
                    editor.setValue(v)

                if not isinstance(v, unicode):
                    v = u'{}'.format(v)
                if hasattr(editor, 'setText'):
                    editor.setText(v)
                if hasattr(editor, 'setCurrentText'):
                    editor.setCurrentText(v)
            else:
                if hasattr(editor, 'setCurrentText'):
                    editor.setCurrentIndex(-1)

        for k in bookmark_db.TABLES[bookmark_db.InfoTable]:
            if k == u'id':
                continue

            source = u'{}/{}/{}'.format(self.server, self.job, self.root)
            v = db.value(source, k, table=bookmark_db.InfoTable)

            if k == 'created':
                try:
                    v = datetime.datetime.fromtimestamp(
                        float(v)).strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    v = u'error'

            if hasattr(self, k + '_editor'):
                editor = getattr(self, k + '_editor')
                editor.setDisabled(True)
                editor.setText(v)

    def _save_db_data(self):
        if self._db_table is None or self._db_table not in bookmark_db.TABLES:
            raise RuntimeError(u'Invalid database table.')

        if self.db_source() is None:
            return

        db = bookmark_db.get_db(self.server, self.job, self.root)
        with db.connection():
            for k, v in self.changed_data.copy().iteritems():
                db.setValue(
                    self.db_source(),
                    k,
                    v,
                    table=self._db_table
                )

    @QtCore.Slot(unicode)
    @QtCore.Slot(type)
    @QtCore.Slot(QtWidgets.QWidget)
    @QtCore.Slot(unicode)
    def data_changed(self, key, _type, editor, v):
        """Signal called when the user changes a value in the editor.

        Args:
            key (unicode):          The database key.
            _type (type):           The data type.
            editor (QWidget):       The editor widget.

        """
        if _type is not None and v is not isinstance(v, _type) and v != u'':
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
                    u'color: {};'.format(common.rgb(common.GREEN)))
            return

        if key in self.changed_data:
            del self.changed_data[key]

        if not isinstance(editor, QtWidgets.QCheckBox):
            editor.setStyleSheet(
                u'color: {};'.format(common.rgb(common.TEXT)))

    def db_source(self):
        """The path of the file database values are associated with.

        Eg. in the case of assets this is `server/job/root/asset`

        """
        raise NotImplementedError(u'Must be overridden in subclass.')

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
                    u'Are you sure you want to close the editor?',
                    u'Your changes will be lost.',
                    buttons=[ui.YesButton, ui.NoButton]
                )
                if mbox.exec_() == QtWidgets.QMessageBox.Rejected:
                    return
            return super(PropertiesWidget, self).done(result)

        if not self.save_changes():
            return

        return super(PropertiesWidget, self).done(result)

    def showEvent(self, event):
        QtCore.QTimer.singleShot(100, self.init_data)
        common.center_window(self)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH() * 1.33, common.HEIGHT() * 1.5)

    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
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
            value = u''
        elif not isinstance(value, unicode):
            value = u'{}'.format(value)

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
