# -*- coding: utf-8 -*-
"""Various widgets used to edit token values.

See the :mod:`bookmarks.tokens.tokens` for the interface details.

"""
import functools

from PySide2 import QtWidgets, QtCore

from . import tokens
from .. import common
from .. import log
from .. import ui
from ..editor import base

SECTIONS = (
    (tokens.PublishConfig, 'Configure publish folders'),
    (tokens.FileNameConfig, 'Configure file-name templates'),
    (tokens.AssetFolderConfig, 'Configure asset folders'),
    (tokens.FileFormatConfig, 'Configure file-format filters'),
)


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
        super(TokenEditor, self).__init__(parent=parent)
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
            lambda x: self.tokenSelected.emit(x.data(QtCore.Qt.DisplayRole))
        )
        editor.itemClicked.connect(
            lambda x: self.done(QtWidgets.QDialog.Accepted)
        )

        self.layout().addWidget(editor, 0)

        config = tokens.get(self.server, self.job, self.root)
        v = config.get_tokens(
            user='MyName',
            version='v001',
            host='localhost',
            task='ANIM',
            mode='ANIM',
            element='MyElement',
            ext=common.thumbnail_format,
            prefix='MYP',
            asset='MyAsset',
            seq='###',
            shot='###',
            sequence='###',
            project=self.job,
        )
        for k in sorted(v.keys()):
            token = '{{{}}}'.format(k)
            editor.addItem(token)
            item = editor.item(editor.count() - 1)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setData(
                QtCore.Qt.ToolTipRole,
                'Current value: "{}"'.format(v[k])
            )

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def item_clicked(self, item):
        item = item.data(QtCore.Qt.DisplayRole)

    def sizeHint(self):
        return QtCore.QSize(
            self.parent().geometry().width(),
            common.size(common.HeightRow) * 7
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

        self.setWindowTitle('Edit Formats')
        self._create_ui()

    def _create_ui(self):
        o = common.size(common.WidthMargin)
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
                common.HeightRow
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
    """A popup editor used to edit the subfolders of a task folder.

    """

    def __init__(self, section, k, v, data, parent=None):
        super(SubfolderEditor, self).__init__(parent=parent)
        self.section = section
        self.k = k
        self.v = v
        self.data = data

        self.setWindowTitle('Edit Subfolders')
        self._create_ui()

    def _create_ui(self):
        o = common.size(common.WidthMargin)
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        main_grp = base.add_section('', 'Edit Subfolders', self)
        grp = ui.get_group(parent=main_grp)

        for _k, _v in self.v['subfolders'].items():
            if not isinstance(_v, dict):
                log.error('Invalid data. Key: {}, Value: {}'.format(_k, _v))
                continue

            _row = ui.add_row(_v['name'], parent=grp)
            editor = ui.LineEdit(parent=_row)
            editor.setText(_v['value'])

            key = '{}/{}/subfolders/{}/value'.format(self.section, self.k, _k)
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
                common.HeightRow
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
        super(TokenConfigEditor, self).__init__(parent=parent)
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

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        common.set_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        o = common.size(common.WidthMargin)
        h = common.size(common.HeightRow)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o)

        # Re-fetch the config data from the database
        data = self.tokens.data(force=True)

        for section, section_name in SECTIONS:
            if section not in data:
                continue
            if not isinstance(data[section], dict):
                log.error('Invalid data.')
                return
            for k, v in data[section].items():
                if not isinstance(
                        v, dict
                ) or 'name' not in v or 'description' not in v:
                    log.error('Invalid data. Key: {}, value: {}'.format(k, v))
                    return

            main_grp = base.add_section(
                '',
                section_name,
                self,
                color=common.color(common.BackgroundDarkColor)
            )

            # Save header data for later use
            self.header_buttons.append((section_name, main_grp))

            _grp = ui.get_group(parent=main_grp)
            for k, v in data[section].items():
                _name = v['name'].title()
                _name = '{} Folder'.format(
                    _name
                ) if section == tokens.AssetFolderConfig else _name
                row = ui.add_row(
                    _name, padding=None, height=h, parent=_grp
                )
                row.setStatusTip(v['description'])
                row.setWhatsThis(v['description'])
                row.setToolTip(v['description'])
                row.setAccessibleDescription(v['description'])

                editor = ui.LineEdit(parent=row)
                editor.setAlignment(QtCore.Qt.AlignRight)
                editor.setText(v['value'])

                # Save current data
                key = '{}/{}/value'.format(section, k)
                self.current_data[key] = v['value']

                editor.textChanged.connect(
                    functools.partial(self.text_changed, key, editor)
                )

                row.layout().addWidget(editor)

                if section == tokens.PublishConfig:
                    editor.setValidator(base.tokenvalidator)
                    button = ui.PaintedButton('+', parent=row)
                    button.clicked.connect(
                        functools.partial(self.show_token_editor, editor)
                    )
                    row.layout().addWidget(button, 0)

                if section == tokens.FileNameConfig:
                    editor.setValidator(base.tokenvalidator)
                    button = ui.PaintedButton('+', parent=row)
                    button.clicked.connect(
                        functools.partial(self.show_token_editor, editor)
                    )
                    row.layout().addWidget(button, 0)

                if section == tokens.AssetFolderConfig:
                    button = ui.PaintedButton('Formats', parent=row)
                    row.layout().addWidget(button, 0)
                    if 'filter' in v:
                        key = '{}/{}/filter'.format(section, k)
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
        self.tokens = tokens.get(self.server, self.job, self.root)

    def contextMenuEvent(self, event):
        action = QtWidgets.QAction(
            'Reset all template settings to their defaults'
        )
        action.triggered.connect(self.restore_to_defaults)

        menu = QtWidgets.QMenu(parent=self)
        menu.addAction(action)
        pos = self.mapToGlobal(event.pos())
        menu.move(pos)
        menu.exec_()
        menu.deleteLater()

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

    @QtCore.Slot()
    def restore_to_defaults(self):
        mbox = ui.MessageBox(
            'Are you sure you want to restore all templates to the default value?',
            'Your custom settings will be permanently lost.',
            buttons=[ui.YesButton, ui.CancelButton],
        )
        res = mbox.exec_()
        if res == QtWidgets.QDialog.Rejected:
            return
        self.tokens.set_data(tokens.DEFAULT_TOKEN_CONFIG.copy())
        self.window().close()

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
            editor.setStyleSheet(
                'color: {};'.format(common.rgb(common.color(common.GreenColor)))
            )
            return

        if key in self.changed_data:
            del self.changed_data[key]
        editor.setStyleSheet(
            'color: {};'.format(common.rgb(common.color(common.TextColor)))
        )

    @QtCore.Slot()
    def save_changes(self):
        """Saves changed values to the bookmark database.

        """
        if not self.changed_data:
            return
        data = self.tokens.data()
        for keys, v in self.changed_data.copy().items():
            _set(data, keys, v)
            del self.changed_data[keys]
        self.tokens.set_data(data)

    def _connect_signals(self):
        pass
