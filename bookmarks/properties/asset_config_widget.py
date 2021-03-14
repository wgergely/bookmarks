# -*- coding: utf-8 -*-
"""Defines the widget used to edit a bookmark's default asset properties.

The asset properties allows for setting basic information about the
asset folder structures and the format types. The settings are predominantly
used to control what extension types are visible in the FileList widget, and
when saving files to help set the destination folders.

The data is stored in the bookmark database and getting and saving the data
is handled by the `asset_config.py` module.

"""
import functools

from PySide2 import QtWidgets, QtCore, QtGui

from . import asset_config
from .. import common
from .. import log
from .. import ui
from .. import images
from . import base


SECTIONS = (
    (asset_config.FileNameConfig, u'File Names Templates'),
    (asset_config.AssetFolderConfig, u'Asset Folders'),
    (asset_config.FileFormatConfig, u'Accepted File Formats'),
)


def _set(d, keys, v):
    """Utility method for updating a value in a dict.

    """
    if isinstance(keys, (str, unicode)):
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
    tokenSelected = QtCore.Signal(unicode)

    def __init__(self, server, job, root, parent=None):
        super(TokenEditor, self).__init__(parent=parent)
        self.server = server
        self.job = job
        self.root = root

        self.setWindowFlags(QtCore.Qt.Popup)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, on=True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._create_ui()

    def _create_ui(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)

        editor = ui.ListWidget(parent=self)
        editor.setSpacing(0)

        editor.itemClicked.connect(
            lambda x: self.tokenSelected.emit(x.data(QtCore.Qt.DisplayRole)))
        editor.itemClicked.connect(
            lambda x: self.done(QtWidgets.QDialog.Accepted))

        self.layout().addWidget(editor, 0)

        config = asset_config.get(self.server, self.job, self.root)
        v = config.get_tokens(
            user=u'MyName',
            version=u'v001',
            host=u'localhost',
            task=u'ANIM',
            mode=u'ANIM',
            element=u'Tower',
            ext=images.THUMBNAIL_FORMAT,
            prefix=u'ABC',
            asset='test'
        )
        for k in sorted(v.keys()):
            token = u'{{{}}}'.format(k)
            editor.addItem(token)
            item = editor.item(editor.count() - 1)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setData(
                QtCore.Qt.ToolTipRole,
                u'Current value: "{}"'.format(v[k])
            )

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def item_clicked(self, item):
        item = item.data(QtCore.Qt.DisplayRole)

    def sizeHint(self):
        return QtCore.QSize(
            self.parent().geometry().width(),
            common.ROW_HEIGHT() * 7
        )

    def showEvent(self, event):
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
        super(FormatEditor, self).__init__(*args, **kwargs)
        self.listwidget = None

        self.setWindowTitle(u'Edit Formats')
        self._create_ui()

    def _create_ui(self):
        o = common.MARGIN()
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

        row = ui.add_row(None, height=common.ROW_HEIGHT(), parent=self)
        row.layout().addWidget(self.save_button, 1)
        row.layout().addWidget(self.cancel_button, 0)

        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected))


class SubfolderEditor(QtWidgets.QDialog):
    """A popup editor used to edit the subfolders of a task folder.

    s"""

    def __init__(self, section, k, v, data, parent=None):
        super(SubfolderEditor, self).__init__(parent=parent)
        self.section = section
        self.k = k
        self.v = v
        self.data = data

        self.setWindowTitle(u'Edit Subfolders')
        self._create_ui()

    def _create_ui(self):
        o = common.MARGIN()
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        maingroup = base.add_section(u'', u'Edit Subfolders', self)
        grp = ui.get_group(parent=maingroup)

        for _k, _v in sorted(self.v['subfolders'].items(), key=lambda x: x[1]['name']):
            if not isinstance(_v, dict):
                log.error(u'Invalid data. Key: {}, Value: {}'.format(_k, _v))
                continue

            _row = ui.add_row(_v['name'], parent=grp)
            editor = ui.LineEdit(parent=_row)
            editor.setText(_v['value'])

            key = u'{}/{}/subfolders/{}/value'.format(self.section, self.k, _k)
            self.parent().current_data[key] = _v['value']

            editor.textChanged.connect(
                functools.partial(self.parent().text_changed, key, editor))

            _row.layout().addWidget(editor, 1)
            _row.setStatusTip(_v['description'])
            _row.setWhatsThis(_v['description'])
            _row.setToolTip(_v['description'])

        self.save_button = ui.PaintedButton('Save')
        self.cancel_button = ui.PaintedButton('Cancel')

        row = ui.add_row(None, height=common.ROW_HEIGHT(), parent=self)
        row.layout().addWidget(self.save_button, 1)
        row.layout().addWidget(self.cancel_button, 0)

        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected))


class AssetConfigEditor(QtWidgets.QWidget):
    """The widget used to display and edit a bookmark's asset configuration.

    """

    def __init__(self, server, job, root, parent=None):
        super(AssetConfigEditor, self).__init__(parent=parent)
        self.server = server
        self.job = job
        self.root = root

        self.current_data = {}
        self.changed_data = {}

        self._section_widgets = []
        self.scrollarea = None

        self.asset_config = asset_config.get(server, job, root)

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        common.set_custom_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        h = common.ROW_HEIGHT()
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o)

        # Refetching the config data from the database
        data = self.asset_config.data(force=True)
        for section, section_name in SECTIONS:
            if section not in data:
                continue
            if not isinstance(data[section], dict):
                log.error('Invalid data.')
                return
            for k, v in data[section].items():
                if not isinstance(v, dict) or 'name' not in v or 'description' not in v:
                    log.error('Invalid data. Key: {}, value: {}'.format(k, v))
                    return

            maingroup = base.add_section(
                u'',
                section_name,
                self,
                color=common.DARK_BG
            )

            _grp = ui.get_group(parent=maingroup)
            for k, v in sorted(data[section].items(), key=lambda x: x[1]['name']):
                _name = v['name'].title()
                _name = u'{} Folder'.format(
                    _name) if section == asset_config.AssetFolderConfig else _name
                row = ui.add_row(
                    _name, padding=None, height=h, parent=_grp)
                row.setStatusTip(v['description'])
                row.setWhatsThis(v['description'])
                row.setToolTip(v['description'])
                row.setAccessibleDescription(v['description'])

                editor = ui.LineEdit(parent=row)
                editor.setAlignment(QtCore.Qt.AlignRight)
                editor.setText(v['value'])

                # Save current data
                key = u'{}/{}/value'.format(section, k)
                self.current_data[key] = v['value']

                editor.textChanged.connect(
                    functools.partial(self.text_changed, key, editor))

                row.layout().addWidget(editor)

                if section == asset_config.FileNameConfig:
                    editor.setValidator(base.tokenvalidator)
                    button = ui.PaintedButton(u'+', parent=row)
                    button.clicked.connect(
                        functools.partial(self.show_token_editor, editor))
                    row.layout().addWidget(button, 0)

                if section != asset_config.AssetFolderConfig:
                    continue

                button = ui.PaintedButton(u'Formats', parent=row)
                row.layout().addWidget(button, 0)
                if 'filter' in v:
                    key = u'{}/{}/filter'.format(section, k)
                    self.current_data[key] = v['filter']
                    button.clicked.connect(
                        functools.partial(self.show_filter_editor, key, v, data))
                else:
                    button.setDisabled(True)

                button = ui.PaintedButton(u'Subfolders', parent=row)
                row.layout().addWidget(button, 0)
                if 'subfolders' in v and isinstance(v['subfolders'], dict):
                    button.clicked.connect(
                        functools.partial(self.show_subfolders_editor, section, k, v, data))
                else:
                    button.setDisabled(True)

    @QtCore.Slot(unicode)
    @QtCore.Slot(dict)
    @QtCore.Slot(dict)
    def show_filter_editor(self, key, v, data):
        editor = FormatEditor(parent=self)
        editor.listwidget.itemClicked.connect(
            functools.partial(self.filter_changed, key, editor))
        for _v in data[asset_config.FileFormatConfig].itervalues():
            editor.listwidget.addItem(_v['name'])

            item = editor.listwidget.item(editor.listwidget.count() - 1)
            item.setData(QtCore.Qt.UserRole, _v['flag'])
            item.setData(QtCore.Qt.StatusTipRole, _v['description'])
            item.setData(QtCore.Qt.ToolTipRole, _v['description'])
            item.setData(QtCore.Qt.AccessibleDescriptionRole,
                         _v['description'])
            item.setData(QtCore.Qt.WhatsThisRole, _v['description'])

            if _v['flag'] & v['filter']:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)

        editor.finished.connect(lambda x: self.save_changes(
        ) if x == QtWidgets.QDialog.Accepted else None)
        editor.exec_()

    @QtCore.Slot(unicode)
    @QtCore.Slot(dict)
    @QtCore.Slot(dict)
    def show_subfolders_editor(self, section, k, v, data):
        editor = SubfolderEditor(section, k, v, data, parent=self)
        editor.finished.connect(lambda x: self.save_changes(
        ) if x == QtWidgets.QDialog.Accepted else None)
        editor.exec_()

    @QtCore.Slot(QtWidgets.QWidget)
    def show_token_editor(self, editor):
        w = TokenEditor(self.server, self.job, self.root, parent=editor)
        w.tokenSelected.connect(editor.insert)
        w.exec_()

    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
    @QtCore.Slot(QtWidgets.QWidget)
    def filter_changed(self, key, editor, *args):
        v = 0
        for n in xrange(editor.listwidget.count()):
            item = editor.listwidget.item(n)
            if item.checkState() == QtCore.Qt.Checked:
                v |= item.data(QtCore.Qt.UserRole)
        self.changed_data[key] = v

    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
    @QtCore.Slot(QtWidgets.QWidget)
    def text_changed(self, key, editor, v):
        """Slot responsible for marking an entry as changed.

        """
        if key not in self.current_data:
            self.current_data[key] = v

        if v != self.current_data[key]:
            self.changed_data[key] = v
            editor.setStyleSheet(
                u'color: {};'.format(common.rgb(common.GREEN)))
            return

        if key in self.changed_data:
            del self.changed_data[key]
        editor.setStyleSheet(
            u'color: {};'.format(common.rgb(common.TEXT)))

    @QtCore.Slot()
    def save_changes(self):
        """Saves changed values to the bookmark database.

        """
        if not self.changed_data:
            return
        data = self.asset_config.data()
        for keys, v in self.changed_data.items():
            _set(data, keys, v)
            del self.changed_data[keys]
        self.asset_config.set_data(data)

    def _connect_signals(self):
        pass
