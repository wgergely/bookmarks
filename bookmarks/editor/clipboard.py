import functools

from PySide2 import QtWidgets, QtCore

from . import base
from .. import common
from .. import database
from .. import log



def close():
    """Closes the :class:`AssetPropertyEditor` editor.

    """
    if common.clipboard_editor is None:
        return
    try:
        common.clipboard_editor.close()
        common.clipboard_editor.deleteLater()
    except:
        pass
    common.clipboard_editor = None


def show(server, job, root, asset=None):
    """Show the :class:`CopyClipboardEditor` window.

    Args:
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.
        asset (str, optional): Asset name. Default: `None`.

    """
    close()
    common.clipboard_editor = CopyClipboardEditor(
        server,
        job,
        root,
        asset=asset
    )
    common.restore_window_geometry(common.clipboard_editor)
    common.restore_window_state(common.clipboard_editor)
    return common.clipboard_editor


class CopyClipboardEditor(base.BasePropertyEditor):
    sections = {
        0: {
            'name': 'Copy Properties',
            'icon': 'settings',
            'color': common.Color.Green(),
            'groups': {
                0: {
                    0: {
                        'name': '',
                        'key': 'options',
                        'validator': None,
                        'widget': None,
                        'placeholder': None,
                        'description': None,
                        'button': 'Select All',
                        'button2': 'Deselect All',
                        'help': 'Select the properties to copy to the clipboard'
                    },
                },
                1: {},
            },
        },
    }

    def __init__(self, server, job, root, asset=None, parent=None):
        if asset:
            db_table = database.AssetTable
        else:
            db_table = database.BookmarkTable

        self.user_settings_keys = []

        # Construct the sections dict
        for idx, k in enumerate(database.TABLES[db_table]):
            if k == 'id':
                continue

            user_settings_key = f'properties/copy{db_table}_{k}'
            self.user_settings_keys.append(user_settings_key)

            self.sections[0]['groups'][1][idx] = {
                'name': k.replace('_', ' ').title(),
                'key': user_settings_key,
                'validator': None,
                'widget': functools.partial(QtWidgets.QCheckBox, 'Copy'),  # keep the 20 char limit
                'placeholder': '',
                'description': f'"{k}"',
            }

        super().__init__(
            server,
            job,
            root,
            asset=asset,
            buttons=('Copy Properties', 'Cancel'),
            db_table=db_table,
            hide_thumbnail_editor=True,
            parent=parent
        )

        self.setWindowTitle('Copy Properties')
        self.setFixedWidth(common.Size.DefaultWidth(0.66))

    def db_source(self):
        return None

    def init_data(self):
        self.load_saved_user_settings(self.user_settings_keys)
        self._connect_settings_save_signals(self.user_settings_keys)

    @common.debug
    @common.error
    @QtCore.Slot()
    def save_changes(self):
        data = {}
        db = database.get(
            self.server,
            self.job,
            self.root,
        )

        for k in database.TABLES[self._db_table]:
            if k == 'id':
                continue

            user_settings_key = f'properties/copy{self._db_table}_{k}'
            editor = getattr(self, f'{user_settings_key}_editor')
            if not editor.isChecked():
                continue
            if self.asset:
                data[k] = db.value(db.source(self.asset), k, self._db_table)
            else:
                data[k] = db.value(db.source(), k, self._db_table)

        if not data:
            raise RuntimeError('No properties selected to copy to clipboard!')

        if self._db_table == database.BookmarkTable:
            common.CLIPBOARD[common.BookmarkPropertyClipboard] = data
            log.success('Copied bookmark properties to clipboard')
        elif self._db_table == database.AssetTable:
            common.CLIPBOARD[common.AssetPropertyClipboard] = data
            log.success('Copied asset properties to clipboard')
        else:
            log.error(f'Unknown db_table: {self._db_table}')
        return True

    @QtCore.Slot()
    def options_button_clicked(self):
        for k in self.user_settings_keys:
            editor = getattr(self, f'{k}_editor')
            editor.setChecked(True)

    @QtCore.Slot()
    def options_button2_clicked(self):
        for k in self.user_settings_keys:
            editor = getattr(self, f'{k}_editor')
            editor.setChecked(False)
